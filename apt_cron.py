import argparse
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import unicodedata
from datetime import date
from pathlib import Path
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


def notice_key(notice):
    if notice.get("id") not in (None, ""):
        return str(notice["id"])
    for field in ("detail_url", "document_url", "attachment_url"):
        value = notice.get(field)
        if value:
            return hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    raise ValueError("notice has no stable identifier")


def empty_state():
    return {"version": 2, "notices": {}, "attachments": {}, "sent_documents": {}}


def migrate_state(state):
    if state is None:
        return None
    migrated = empty_state()
    migrated["notices"] = dict(state.get("notices", {}))
    migrated["attachments"] = dict(state.get("attachments", {}))
    migrated["sent_documents"] = dict(state.get("sent_documents", {}))
    return migrated


def select_changes(notices, state):
    state = migrate_state(state)
    current = {notice_key(notice): fingerprint(notice) for notice in notices}
    if state is None:
        return [], dict(empty_state(), notices=current)

    previous = state["notices"]
    changes = [
        (notice, notice_key(notice) in previous)
        for notice in notices
        if current[notice_key(notice)] != previous.get(notice_key(notice))
    ]
    return changes, dict(state, notices=current)


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


def fetch_attachments(transport, attachments_base, notice_id):
    empty = {"document_url": None, "attachment_urls": []}
    if notice_id in (None, ""):
        return empty
    url = f"{attachments_base.rstrip('/')}/{notice_id}"
    response = transport.request("GET", url)
    if response.get("error"):
        raise RuntimeError(response.get("errorMessage") or "attachments error")
    results = response.get("results") or []
    if not results:
        return empty
    root = results[0]
    document = root.get("documentoUnico") or {}
    document_url = (
        document.get("downloadUrl")
        if document.get("mimeType") == "application/pdf"
        else None
    )
    attachment_urls = [
        item["downloadUrl"]
        for item in root.get("files") or []
        if item.get("mimeType") == "application/pdf" and item.get("downloadUrl")
    ]
    return {"document_url": document_url, "attachment_urls": attachment_urls}


def publish_document(transport, telegram_url, chat_id, document_url, caption):
    response = transport.request(
        "POST",
        telegram_url,
        {"chat_id": chat_id, "document": document_url, "caption": caption},
    )
    if not response.get("ok"):
        raise RuntimeError(response.get("description") or "telegram document error")
    return response["result"]


INDEX_FIELDS = (
    "id",
    "title",
    "category",
    "sector",
    "published",
    "expires",
    "year",
    "number",
    "status",
    "detail_url",
    "document_url",
    "attachment_urls",
)


def build_index(notices):
    return {"notices": [{field: notice.get(field) for field in INDEX_FIELDS} for notice in notices]}


def write_index(directory, index):
    os.makedirs(directory, exist_ok=True)
    rows = index["notices"]
    (Path(directory) / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown = ["# APT Basilicata public notices index", ""]
    for row in rows:
        markdown.append(f"- {row['published']} - {row['title']}")
        markdown.append(f"  - Atto: {row['number']}/{row['year']} - {row['status']}")
        markdown.append(f"  - Categoria: {row['category']} - Settore: {row['sector']}")
        markdown.append(f"  - [Atto ufficiale]({row['detail_url']})")
        if row["document_url"]:
            markdown.append(f"  - [PDF ufficiale]({row['document_url']})")
        for url in row["attachment_urls"] or []:
            markdown.append(f"  - [Allegato PDF]({url})")
    (Path(directory) / "index.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    html_lines = [
        "<!doctype html>",
        '<html lang="it">',
        "<head><meta charset=\"utf-8\"><title>APT Basilicata public notices index</title></head>",
        "<body>",
        "<h1>APT Basilicata public notices index</h1>",
        "<ul>",
    ]
    for row in rows:
        escaped_title = html.escape(str(row["title"] or ""))
        html_lines.append(
            f"<li>{html.escape(str(row['published'] or ''))} - {escaped_title}"
        )
        html_lines.append(
            f"<ul><li>Atto: {html.escape(str(row['number'] or ''))}/{html.escape(str(row['year'] or ''))} - "
            f"{html.escape(str(row['status'] or ''))}</li>"
        )
        html_lines.append(
            f"<li>Categoria: {html.escape(str(row['category'] or ''))} - "
            f"Settore: {html.escape(str(row['sector'] or ''))}</li>"
        )
        html_lines.append(
            f'<li><a href="{html.escape(str(row["detail_url"] or ""), quote=True)}">Atto ufficiale</a></li>'
        )
        if row["document_url"]:
            html_lines.append(
                f'<li><a href="{html.escape(row["document_url"], quote=True)}">PDF ufficiale</a></li>'
            )
        for url in row["attachment_urls"] or []:
            html_lines.append(
                f'<li><a href="{html.escape(url, quote=True)}">Allegato PDF</a></li>'
            )
        html_lines.append("</ul></li>")
    html_lines.extend(["</ul>", "</body>", "</html>"])
    (Path(directory) / "index.html").write_text("\n".join(html_lines) + "\n", encoding="utf-8")


def enrich_notices(transport, notices, state, attachments_base, detail_base):
    state = migrate_state(state) or empty_state()
    enriched = []
    attachments = dict(state["attachments"])
    for notice in notices:
        item = dict(notice)
        key = notice_key(item)
        if item.get("id") not in (None, ""):
            item["detail_url"] = f"{detail_base.rstrip('/')}/{item['id']}"
        cached = attachments.get(key)
        links = cached if cached is not None else fetch_attachments(
            transport, attachments_base, item.get("id")
        )
        item.update(links)
        attachments[key] = links
        enriched.append(item)
    return enriched, attachments


def run_once(transport, config):
    notices = fetch_notices(
        transport,
        config["source_url"],
        config["today"],
        config["nature_id"],
        config["size"],
    )
    state = migrate_state(load_state(config["state_path"]))
    notices, attachments = enrich_notices(
        transport,
        notices,
        state,
        config["attachments_base"],
        config["detail_base"],
    )
    changes, next_state = select_changes(notices, state)
    next_state["attachments"] = attachments
    sent_documents = dict(state["sent_documents"]) if state else {}
    next_state["sent_documents"] = sent_documents
    dry_run = bool(config.get("dry_run"))
    committed_state = next_state if state is None else dict(state, notices=dict(state["notices"]))
    published = 0
    for notice, updated in changes:
        text = format_message(notice, config["detail_base"], updated=updated)
        if not dry_run:
            publish_message(transport, config["telegram_url"], config["chat_id"], text)
            key = notice_key(notice)
            committed_state["notices"][key] = next_state["notices"][key]
            committed_state["attachments"][key] = attachments[key]
            save_state(config["state_path"], committed_state)
            pdf_urls = [notice.get("document_url")] + list(notice.get("attachment_urls") or [])
            for url in pdf_urls:
                if not url or url in sent_documents:
                    continue
                publish_document(
                    transport,
                    config["document_base"],
                    config["chat_id"],
                    url,
                    f"PDF ufficiale: {notice.get('title') or ''}",
                )
                sent_documents[url] = key
                committed_state["sent_documents"] = dict(sent_documents)
                save_state(config["state_path"], committed_state)
        published += 1
    if not dry_run:
        write_index(config["index_dir"], build_index(notices))
        save_state(config["state_path"], next_state)
    return {"notices": len(notices), "published": published, "dry_run": dry_run}


def publish_message(transport, telegram_url, chat_id, text):
    response = transport.request("POST", telegram_url, {"chat_id": chat_id, "text": text})
    if not response.get("ok"):
        raise RuntimeError(response.get("description") or "telegram error")
    return response["result"]


TELEGRAM_TEXT_LIMIT = 4096


def format_message(notice, detail_base, updated=False):
    headline = "Atto aggiornato APT Basilicata" if updated else "Nuovo atto APT Basilicata"
    lines = [
        headline,
        f"Data: {_display_date(notice.get('published'))}",
        f"Titolo: {notice.get('title') or ''}",
        f"Categoria: #{_hashtag(notice.get('category'))}",
        f"Settore: #{_hashtag(notice.get('sector'))}",
        f"Atto: {notice.get('number') or ''}/{notice.get('year') or ''}",
        f"Stato: {notice.get('status') or ''}",
        f"Link: {notice.get('detail_url') or detail_base.rstrip('/') + '/' + str(notice.get('id') or '')}",
    ]
    if notice.get("document_url"):
        lines.append(f"PDF: {notice['document_url']}")

    message = "\n".join(lines)
    if len(message) > TELEGRAM_TEXT_LIMIT:
        title_index = 2
        overhead = len(message) - len(lines[title_index]) + 3
        available = TELEGRAM_TEXT_LIMIT - overhead
        if available > 0:
            lines[title_index] = lines[title_index][:available] + "..."
            message = "\n".join(lines)
        else:
            message = message[: TELEGRAM_TEXT_LIMIT - 3] + "..."
    return message


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


def parse_positive_int(value, name):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a positive integer") from None
    if parsed < 1:
        raise ValueError(f"{name} must be a positive integer")
    return parsed


def redact_credentials(text, token):
    message = str(text)
    return message.replace(token, "[REDACTED]") if token else message


def main(argv=None):
    parser = argparse.ArgumentParser(description="Publish new APT Basilicata notices to Telegram")
    parser.add_argument("--dry-run", action="store_true", help="read the source without publishing or saving state")
    parser.add_argument(
        "--source-url",
        default=os.environ.get("APT_SOURCE_URL", "https://siopi.publisys.it/kapi-aptbasilicata/api/pap/filter"),
    )
    parser.add_argument("--state-path", default=os.environ.get("APT_STATE_PATH", "state/notices.json"))
    parser.add_argument(
        "--attachments-base",
        default=os.environ.get(
            "APT_ATTACHMENTS_BASE",
            "https://siopi.publisys.it/kapi-aptbasilicata/api/pap/files",
        ),
    )
    parser.add_argument(
        "--index-dir",
        default=os.environ.get("APT_INDEX_DIR", "public"),
    )
    args = parser.parse_args(argv)

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not args.dry_run and (not token or not chat_id):
        parser.error("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required unless --dry-run is used")

    try:
        page_size = parse_positive_int(os.environ.get("APT_PAGE_SIZE", "20"), "APT_PAGE_SIZE")
    except ValueError as error:
        parser.error(str(error))

    config = {
        "source_url": args.source_url,
        "state_path": args.state_path,
        "today": date.today().isoformat(),
        "nature_id": os.environ.get("APT_NATURE_ID", "200152"),
        "size": page_size,
        "detail_base": os.environ.get(
            "APT_DETAIL_BASE",
            "https://siopi.publisys.it/sito-aptbasilicata/albo-pretorio/dettaglio",
        ),
        "attachments_base": args.attachments_base,
        "index_dir": args.index_dir,
        "telegram_url": f"https://api.telegram.org/bot{token}/sendMessage",
        "document_base": f"https://api.telegram.org/bot{token}/sendDocument",
        "chat_id": chat_id,
        "dry_run": args.dry_run,
    }
    try:
        stats = run_once(UrllibTransport(), config)
    except Exception as error:
        print(f"error: {redact_credentials(error, token)}", file=sys.stderr)
        return 1
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
