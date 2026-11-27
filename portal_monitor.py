#!/usr/bin/env python3
"""Check the APT portal and record reachability and content changes as JSON history."""

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone

import apt_cron

HISTORY_LIMIT = 200
HISTORY_VERSION = 1


def _digest(snapshot):
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_snapshot(transport, config):
    payload = apt_cron.notice_query(config["today"], config["nature_id"], False)
    response = transport.request("POST", config["source_url"], payload=payload)
    notices = apt_cron.parse_source_response(response)
    structure = {
        "response_keys": sorted(response.keys()) if isinstance(response, dict) else [],
        "results_count": len(response.get("results", [])) if isinstance(response, dict) else 0,
        "total_pages": response.get("totalPages") if isinstance(response, dict) else None,
        "notice_keys": sorted({key for notice in notices for key in notice}),
    }
    snapshot = {
        "structure": structure,
        "notices": [
            {
                "key": apt_cron.notice_key(notice),
                "id": notice.get("id"),
                "fingerprint": apt_cron.fingerprint(notice),
                "detail_url": notice.get("detail_url")
                or apt_cron.build_detail_url(config["detail_base"], notice.get("id") or ""),
                "attachment_urls": sorted(notice.get("attachment_urls") or []),
            }
            for notice in notices
        ],
    }
    snapshot["digest"] = _digest(snapshot)

    probe_error = None
    if notices and notices[0].get("id"):
        try:
            links = apt_cron.fetch_attachments(
                transport, config["attachments_base"], notices[0]["id"]
            )
            first_url = links["document_url"] or next(
                iter(links["attachment_urls"]), None
            )
            if first_url:
                transport.fetch_bytes(first_url)
        except Exception as error:
            probe_error = str(error)
    return snapshot, probe_error


def diff_snapshots(previous, current):
    if previous is None:
        return ["baseline snapshot recorded"]
    changes = []
    old_structure = previous.get("structure", {})
    new_structure = current.get("structure", {})
    for field in ("response_keys", "notice_keys", "total_pages", "results_count"):
        old_value = old_structure.get(field)
        new_value = new_structure.get(field)
        if old_value != new_value:
            if isinstance(old_value, list) and isinstance(new_value, list):
                old_text = ", ".join(str(item) for item in old_value)
                new_text = ", ".join(str(item) for item in new_value)
            else:
                old_text, new_text = str(old_value), str(new_value)
            changes.append(f"{field.replace('_', ' ')} changed: {old_text} -> {new_text}")

    old_notices = {item["key"]: item for item in previous.get("notices", [])}
    new_notices = {item["key"]: item for item in current.get("notices", [])}
    for key in sorted(new_notices.keys() - old_notices.keys()):
        changes.append(f"notice {key} added")
    for key in sorted(old_notices.keys() - new_notices.keys()):
        changes.append(f"notice {key} removed")
    for key in sorted(old_notices.keys() & new_notices.keys()):
        old_notice = old_notices[key]
        new_notice = new_notices[key]
        for field, label in (
            ("fingerprint", "fingerprint"),
            ("detail_url", "detail url"),
            ("attachment_urls", "attachment urls"),
        ):
            if old_notice.get(field) != new_notice.get(field):
                changes.append(f"notice {key} {label} changed")
    return changes


def append_event(history, event, limit=HISTORY_LIMIT):
    history.setdefault("events", []).append(event)
    if limit > 0:
        del history["events"][:-limit]


def load_history(path):
    history = apt_cron.load_state(path)
    if history is None:
        return {"version": HISTORY_VERSION, "events": [], "last_snapshot": None}
    if not isinstance(history, dict) or not isinstance(history.get("events"), list):
        raise RuntimeError("invalid portal history")
    return history


def send_alert(transport, token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        transport.request("POST", url, payload={"chat_id": chat_id, "text": text[:4000]})
    except Exception as error:
        raise RuntimeError(apt_cron.redact_credentials(str(error), token)) from error


def run_monitor(transport, config):
    snapshot, probe_error = build_snapshot(transport, config)
    history = load_history(config["history_path"])
    changes = diff_snapshots(history.get("last_snapshot"), snapshot)
    if probe_error:
        changes.append(f"attachment probe failed: {probe_error}")

    alertable = [change for change in changes if change != "baseline snapshot recorded"]
    alerted = False
    if not config["dry_run"]:
        if alertable:
            summary = "APT portal monitor: " + "; ".join(alertable)
            token = config.get("alert_token")
            chat_id = config.get("alert_chat_id")
            if token and chat_id:
                send_alert(transport, token, chat_id, summary)
                alerted = True

        if alertable or history.get("last_snapshot") is None:
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "status": "error" if probe_error else "changed",
                "changes": changes,
                "snapshot_digest": snapshot["digest"],
            }
            append_event(history, event)
        history["last_snapshot"] = snapshot
        apt_cron.save_state(config["history_path"], history)

    status = "error" if probe_error else ("changed" if alertable else "ok")
    return {
        "notices": len(snapshot["notices"]),
        "changes": len(changes),
        "status": status,
        "alerted": alerted,
        "dry_run": bool(config["dry_run"]),
    }


def main(argv=None):
    apt_cron.load_env_file()
    parser = argparse.ArgumentParser(description="Monitor the APT portal and record change history")
    parser.add_argument("--dry-run", action="store_true", help="read the portal without writing history or alerting")
    parser.add_argument(
        "--history-path",
        default=os.environ.get("APT_PORTAL_HISTORY_PATH", "portal-history.json"),
        help="JSON file holding last snapshot and change events",
    )
    parser.add_argument(
        "--source-url",
        default=os.environ.get(
            "APT_SOURCE_URL", "https://siopi.publisys.it/kapi-aptbasilicata/api/pap/filter"
        ),
    )
    parser.add_argument(
        "--attachments-base",
        default=os.environ.get(
            "APT_ATTACHMENTS_BASE", "https://siopi.publisys.it/kapi-aptbasilicata/api/pap/files"
        ),
    )
    parser.add_argument(
        "--detail-base",
        default=os.environ.get(
            "APT_DETAIL_BASE",
            "https://siopi.publisys.it/sito-aptbasilicata/albo-pretorio/dettaglio",
        ),
    )
    args = parser.parse_args(argv)

    token = os.environ.get("APT_ALERT_TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("APT_ALERT_TELEGRAM_CHAT_ID", "")
    if not args.dry_run and (not token or not chat_id):
        parser.error(
            "APT_ALERT_TELEGRAM_BOT_TOKEN and APT_ALERT_TELEGRAM_CHAT_ID are required "
            "unless --dry-run is used"
        )
    try:
        size = apt_cron.parse_positive_int(os.environ.get("APT_PAGE_SIZE", "20"), "APT_PAGE_SIZE")
    except ValueError as error:
        parser.error(str(error))

    config = {
        "source_url": args.source_url,
        "attachments_base": args.attachments_base,
        "detail_base": args.detail_base,
        "history_path": args.history_path,
        "today": date.today().isoformat(),
        "nature_id": os.environ.get("APT_NATURE_ID", "200152"),
        "size": size,
        "dry_run": args.dry_run,
        "alert_token": token,
        "alert_chat_id": chat_id,
    }
    try:
        stats = run_monitor(apt_cron.UrllibTransport(), config)
    except Exception as error:
        print(f"error: {apt_cron.redact_credentials(str(error), token)}", file=sys.stderr)
        return 1
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
