import argparse
import hashlib
import json
import os
import re
import tempfile
import unicodedata
from datetime import date
from urllib.request import Request, urlopen


NOTICE_FIELDS = {
    "id": "id",
    "title": "cntTitle",
    "category": "cntNaturaAttoLabel",
    "sector": "cntSettoreProponenteLabel",
    "published": "cntDataInizioPubblicazione",
    "expires": "cntDataFinePubblicazione",
    "year": "cntAnnoNumeroPap",
    "number": "cntNumeroPap",
    "status": "status",
}


def parse_source_response(response):
    return [
        {name: item.get(source) for name, source in NOTICE_FIELDS.items()}
        for item in response.get("results", [])
    ]


def _display_date(value):
    return date.fromisoformat(value).strftime("%d/%m/%Y") if value else ""


def _hashtag(value):
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+", "_", ascii_text).strip("_")


def load_state(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_state(path, state):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=directory, delete=False
    ) as handle:
        json.dump(state, handle, sort_keys=True, indent=2)
        handle.write("\n")
        temporary = handle.name
    os.replace(temporary, path)


def fingerprint(notice):
    payload = json.dumps(notice, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def select_changes(notices, state):
    current = {str(notice["id"]): fingerprint(notice) for notice in notices}
    if state is None:
        return [], {"version": 1, "notices": current}

    previous = state.get("notices", {})
    changes = [
        (notice, str(notice["id"]) in previous)
        for notice in notices
        if current[str(notice["id"])] != previous.get(str(notice["id"]))
    ]
    return changes, {"version": 1, "notices": current}


def fetch_notices(transport, source_url, today, nature_id, size):
    payload = {
        "dataOption": "all",
        "papSearchCriteriaList": [
            {"filterKey": "cntNaturaAtto", "operation": "eq", "value": nature_id},
            {
                "filterKey": "cntDataFinePubblicazione",
                "operation": "ge",
                "value": today,
            },
            {
                "filterKey": "cntDataInizioPubblicazione",
                "operation": "le",
                "value": today,
            },
            {"filterKey": "cntExternalStatus", "operation": "nu", "value": ""},
            {"filterKey": "cntNumeroPap", "operation": "nn"},
            {"filterKey": "cntAnnoNumeroPap", "operation": "nn"},
        ],
    }
    url = f"{source_url}?page=0&size={size}"
    response = transport.request("POST", url, payload)
    if response.get("error"):
        raise RuntimeError(response.get("errorMessage") or "source error")
    return parse_source_response(response)


def run_once(transport, config):
    notices = fetch_notices(
        transport,
        config["source_url"],
        config["today"],
        config["nature_id"],
        config["size"],
    )
    state = load_state(config["state_path"])
    changes, next_state = select_changes(notices, state)
    dry_run = bool(config.get("dry_run"))
    committed_state = (
        next_state if state is None else {"version": 1, "notices": dict(state.get("notices", {}))}
    )
    published = 0
    for notice, updated in changes:
        text = format_message(notice, config["detail_base"], updated=updated)
        if not dry_run:
            publish_message(transport, config["telegram_url"], config["chat_id"], text)
            committed_state["notices"][str(notice["id"])] = next_state["notices"][str(notice["id"])]
            save_state(config["state_path"], committed_state)
        published += 1
    if not dry_run:
        save_state(config["state_path"], next_state)
    return {"notices": len(notices), "published": published, "dry_run": dry_run}


def publish_message(transport, telegram_url, chat_id, text):
    response = transport.request("POST", telegram_url, {"chat_id": chat_id, "text": text})
    if not response.get("ok"):
        raise RuntimeError(response.get("description") or "telegram error")
    return response["result"]


def format_message(notice, detail_base, updated=False):
    headline = "Atto aggiornato APT Basilicata" if updated else "Nuovo atto APT Basilicata"
    return "\n".join(
        [
            headline,
            f"Data: {_display_date(notice.get('published'))}",
            f"Titolo: {notice.get('title') or ''}",
            f"Categoria: #{_hashtag(notice.get('category'))}",
            f"Settore: #{_hashtag(notice.get('sector'))}",
            f"Atto: {notice.get('number') or ''}/{notice.get('year') or ''}",
            f"Stato: {notice.get('status') or ''}",
            f"Link: {detail_base.rstrip('/')}/{notice.get('id')}",
        ]
    )


class UrllibTransport:
    def request(self, method, url, payload=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            url,
            data=data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "apt-cron/1.0",
            },
            method=method,
        )
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Publish new APT Basilicata notices to Telegram")
    parser.add_argument("--dry-run", action="store_true", help="read the source without publishing or saving state")
    parser.add_argument(
        "--source-url",
        default=os.environ.get("APT_SOURCE_URL", "https://siopi.publisys.it/kapi-aptbasilicata/api/pap/filter"),
    )
    parser.add_argument("--state-path", default=os.environ.get("APT_STATE_PATH", "state/notices.json"))
    args = parser.parse_args(argv)

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not args.dry_run and (not token or not chat_id):
        parser.error("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required unless --dry-run is used")

    config = {
        "source_url": args.source_url,
        "state_path": args.state_path,
        "today": date.today().isoformat(),
        "nature_id": os.environ.get("APT_NATURE_ID", "200152"),
        "size": int(os.environ.get("APT_PAGE_SIZE", "20")),
        "detail_base": os.environ.get(
            "APT_DETAIL_BASE",
            "https://siopi.publisys.it/sito-aptbasilicata/albo-pretorio/dettaglio",
        ),
        "telegram_url": f"https://api.telegram.org/bot{token}/sendMessage",
        "chat_id": chat_id,
        "dry_run": args.dry_run,
    }
    stats = run_once(UrllibTransport(), config)
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
