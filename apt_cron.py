import argparse
import hashlib
import html
import json
import mimetypes
import os
import re
import sys
import tempfile
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


HTTP_TIMEOUT = 20
DOCUMENT_UPLOAD_TIMEOUT = 120
USER_AGENT = "apt-cron/1.0"
# Telegram's documented document upload limit, also the in-memory fetch bound.
DOCUMENT_MAX_BYTES = 50 * 1024 * 1024


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
    "otypeId": "otypeId",
    "rootId": "rootId",
    "rootOtypeid": "rootOtypeid",
    "cntAutoritaMittente": "cntAutoritaMittente",
    "cntAnnoNumeroRpap": "cntAnnoNumeroRpap",
    "cntDataAnnullamento": "cntDataAnnullamento",
    "cntDataAnnullamentoTime": "cntDataAnnullamentoTime",
    "cntDataDocumentoOrigine": "cntDataDocumentoOrigine",
    "cntDataNumeroPap": "cntDataNumeroPap",
    "cntDataNumeroPapTime": "cntDataNumeroPapTime",
    "cntDataNumeroRpap": "cntDataNumeroRpap",
    "cntDataNumeroRpapTime": "cntDataNumeroRpapTime",
    "cntDataRigetto": "cntDataRigetto",
    "cntDataRigettoTime": "cntDataRigettoTime",
    "cntDate": "cntDate",
    "cntDocumentoOrigine": "cntDocumentoOrigine",
    "cntDurataPubblicazione": "cntDurataPubblicazione",
    "cntExternalId": "cntExternalId",
    "cntExternalOggetto": "cntExternalOggetto",
    "cntExternalSource": "cntExternalSource",
    "cntExternalStatus": "cntExternalStatus",
    "cntNaturaAtto": "cntNaturaAtto",
    "cntNoteAnnullamento": "cntNoteAnnullamento",
    "cntNoteRigetto": "cntNoteRigetto",
    "cntNumeri": "cntNumeri",
    "cntNumeroDocumentoOrigine": "cntNumeroDocumentoOrigine",
    "cntNumeroGara": "cntNumeroGara",
    "cntNumeroRpap": "cntNumeroRpap",
    "cntParentObjectId": "cntParentObjectId",
    "cntParentOtypeId": "cntParentOtypeId",
    "cntProponente": "cntProponente",
    "cntSettoreProponente": "cntSettoreProponente",
}

FIELD_LABELS = {
    "id": "ID",
    "title": "Titolo",
    "category": "Categoria",
    "sector": "Settore",
    "published": "Pubblicato il",
    "expires": "Scade il",
    "year": "Anno",
    "number": "Numero",
    "status": "Stato",
    "otypeId": "Tipo oggetto",
    "rootId": "Oggetto radice",
    "rootOtypeid": "Tipo oggetto radice",
    "cntAutoritaMittente": "Autorita mittente",
    "cntAnnoNumeroRpap": "Anno RPAP",
    "cntDataAnnullamento": "Data annullamento",
    "cntDataAnnullamentoTime": "Ora annullamento",
    "cntDataDocumentoOrigine": "Data documento di origine",
    "cntDataNumeroPap": "Data numero PAP",
    "cntDataNumeroPapTime": "Ora numero PAP",
    "cntDataNumeroRpap": "Data numero RPAP",
    "cntDataNumeroRpapTime": "Ora numero RPAP",
    "cntDataRigetto": "Data rigetto",
    "cntDataRigettoTime": "Ora rigetto",
    "cntDate": "Date",
    "cntDocumentoOrigine": "Documento di origine",
    "cntDurataPubblicazione": "Durata pubblicazione",
    "cntExternalId": "ID esterno",
    "cntExternalOggetto": "Oggetto esterno",
    "cntExternalSource": "Fonte esterna",
    "cntExternalStatus": "Stato esterno",
    "cntNaturaAtto": "Natura atto",
    "cntNoteAnnullamento": "Note annullamento",
    "cntNoteRigetto": "Note rigetto",
    "cntNumeri": "Numeri",
    "cntNumeroDocumentoOrigine": "Numero documento di origine",
    "cntNumeroGara": "Numero gara",
    "cntNumeroRpap": "Numero RPAP",
    "cntParentObjectId": "Oggetto padre",
    "cntParentOtypeId": "Tipo oggetto padre",
    "cntProponente": "Proponente",
    "cntSettoreProponente": "Codice settore proponente",
}


def parse_source_response(response):
    return [
        {name: item.get(source) for name, source in NOTICE_FIELDS.items()}
        for item in response.get("results", [])
    ]


def _display_date(value):
    if not value:
        return ""
    try:
        return date.fromisoformat(str(value)).strftime("%d/%m/%Y")
    except ValueError:
        return str(value)


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
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory, delete=False
        ) as handle:
            temporary = handle.name
            json.dump(state, handle, sort_keys=True, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    except Exception:
        if temporary:
            Path(temporary).unlink(missing_ok=True)
        raise


def fingerprint(notice):
    payload = json.dumps(notice, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def notice_key(notice):
    if notice.get("id") not in (None, ""):
        return str(notice["id"])
    for field in ("detail_url", "document_url", "attachment_urls"):
        value = notice.get(field)
        if isinstance(value, list):
            value = value[0] if value else None
        if value:
            return hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    raise ValueError("notice has no stable identifier")


def empty_state():
    return {
        "version": 2,
        "notices": {},
        "attachments": {},
        "sent_documents": {},
        "sent_messages": {},
    }


def migrate_state(state):
    if state is None:
        return None
    migrated = empty_state()
    migrated["notices"] = dict(state.get("notices", {}))
    migrated["attachments"] = dict(state.get("attachments", {}))
    migrated["sent_documents"] = dict(state.get("sent_documents", {}))
    sent_messages = state.get("sent_messages")
    if sent_messages is None:
        # A legacy notice fingerprint alone does not prove its text message was sent:
        # first-run seeding also stored one. Only a notice whose document was uploaded
        # is known to have been announced, so seed just those and never flood the rest.
        documented = set(migrated["sent_documents"].values())
        sent_messages = {
            key: value
            for key, value in migrated["notices"].items()
            if key in documented
        }
    migrated["sent_messages"] = dict(sent_messages)
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
    return changes, dict(state, notices={**previous, **current})


def notice_query(today, nature_id, archive):
    criteria = [{"filterKey": "cntNaturaAtto", "operation": "eq", "value": nature_id}]
    if not archive:
        criteria.extend(
            [
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
            ]
        )
    criteria.extend(
        [
            {"filterKey": "cntExternalStatus", "operation": "nu", "value": ""},
            {"filterKey": "cntNumeroPap", "operation": "nn"},
            {"filterKey": "cntAnnoNumeroPap", "operation": "nn"},
        ]
    )
    return {"dataOption": "all", "papSearchCriteriaList": criteria}


def fetch_notices(transport, source_url, today, nature_id, size, archive=False):
    """Read the source; archive mode walks every page of the whole published history."""
    notices = []
    page = 0
    total_pages = 1
    while page < total_pages:
        url = f"{source_url}?page={page}&size={size}"
        response = transport.request("POST", url, notice_query(today, nature_id, archive))
        if response.get("error"):
            raise RuntimeError(response.get("errorMessage") or "source error")
        notices.extend(parse_source_response(response))
        # The source answers 404 past the last page, so totalPages is the only stop condition.
        total_pages = int(response.get("totalPages") or 1) if archive else 1
        page += 1
    return notices


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
        (public_url(document.get("downloadUrl")) or None)
        if document.get("mimeType") == "application/pdf"
        else None
    )
    attachment_urls = []
    for item in root.get("files") or []:
        url = public_url(item.get("downloadUrl"))
        if url:
            attachment_urls.append(url)
    return {"document_url": document_url, "attachment_urls": attachment_urls}


def public_url(url):
    """Only absolute http(s) URLs may be fetched or published as links."""
    try:
        parts = urlsplit(str(url or ""))
    except ValueError:
        return ""
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return ""
    return str(url)


def _header_value(value):
    # MIME header values must not carry a line break.
    return str(value).replace("\r", " ").replace("\n", " ")


def document_filename(document_url):
    name = Path(str(document_url or "").split("?", 1)[0]).name
    name = re.sub(r'[\\\x00-\x1f"]', "_", name)
    return name if name and Path(name).suffix else "document.pdf"


def publish_document(transport, telegram_url, chat_id, document_url, caption):
    content = transport.fetch_bytes(document_url)
    if len(content) > DOCUMENT_MAX_BYTES:
        raise RuntimeError(f"document exceeds {DOCUMENT_MAX_BYTES} bytes: {document_url}")
    response = transport.send_document(
        telegram_url,
        {"chat_id": chat_id, "caption": caption},
        document_filename(document_url),
        content,
    )
    if not response.get("ok"):
        raise RuntimeError(response.get("description") or "telegram document error")
    return response["result"]


INDEX_FIELDS = tuple(NOTICE_FIELDS) + ("detail_url", "document_url", "attachment_urls")

# Fields rendered as the identity block of an index entry instead of a label: value line.
INDEX_IDENTITY_FIELDS = ("published", "title", "number", "year")


def _field_rows(row, skip):
    for name in NOTICE_FIELDS:
        if name in skip:
            continue
        value = row.get(name)
        if value not in (None, ""):
            yield FIELD_LABELS[name], value


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
        markdown.append(f"- {row['published'] or ''} - {row['title'] or ''}")
        markdown.append(f"  - Atto: {row['number'] or ''}/{row['year'] or ''}")
        for label, value in _field_rows(row, INDEX_IDENTITY_FIELDS):
            markdown.append(f"  - {label}: {value}")
        detail = public_url(row["detail_url"])
        markdown.append(
            f"  - [Atto ufficiale]({detail})" if detail else "  - Atto ufficiale: link non disponibile"
        )
        if row["document_url"]:
            document = public_url(row["document_url"])
            markdown.append(
                f"  - [PDF ufficiale]({document})"
                if document
                else "  - PDF ufficiale: link non disponibile"
            )
        for url in row["attachment_urls"] or []:
            attachment = public_url(url)
            markdown.append(
                f"  - [Allegato]({attachment})"
                if attachment
                else "  - Allegato: link non disponibile"
            )
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
        html_lines.append(
            f"<li>{html.escape(str(row['published'] or ''))} - {html.escape(str(row['title'] or ''))}"
        )
        html_lines.append(
            f"<ul><li>Atto: {html.escape(str(row['number'] or ''))}/{html.escape(str(row['year'] or ''))}</li>"
        )
        for label, value in _field_rows(row, INDEX_IDENTITY_FIELDS):
            html_lines.append(f"<li>{html.escape(label)}: {html.escape(str(value))}</li>")
        detail = public_url(row["detail_url"])
        html_lines.append(
            f'<li><a href="{html.escape(detail, quote=True)}">Atto ufficiale</a></li>'
            if detail
            else "<li>Atto ufficiale: link non disponibile</li>"
        )
        if row["document_url"]:
            document = public_url(row["document_url"])
            html_lines.append(
                f'<li><a href="{html.escape(document, quote=True)}">PDF ufficiale</a></li>'
                if document
                else "<li>PDF ufficiale: link non disponibile</li>"
            )
        for url in row["attachment_urls"] or []:
            attachment = public_url(url)
            html_lines.append(
                f'<li><a href="{html.escape(attachment, quote=True)}">Allegato</a></li>'
                if attachment
                else "<li>Allegato: link non disponibile</li>"
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
        # The stored fingerprint was taken with the cached links applied, so it still
        # matches only while the source metadata is unchanged. A changed notice may have
        # gained or replaced an official document, so its links are refetched instead of reused.
        unchanged = cached is not None and state["notices"].get(key) == fingerprint(
            {**item, **cached}
        )
        links = cached if unchanged else fetch_attachments(
            transport, attachments_base, item.get("id")
        )
        item.update(links)
        attachments[key] = links
        enriched.append(item)
    return enriched, attachments


def fetch_enriched_notices(transport, config, state):
    notices = fetch_notices(
        transport,
        config["source_url"],
        config["today"],
        config["nature_id"],
        config["size"],
        archive=bool(config.get("archive")),
    )
    return enrich_notices(
        transport,
        notices,
        state,
        config["attachments_base"],
        config["detail_base"],
    )


def refresh_index(transport, config):
    notices, _ = fetch_enriched_notices(transport, config, None)
    write_index(config["index_dir"], build_index(notices))
    return {"notices": len(notices)}


def publication_order(changes):
    """Oldest first, so the newest act is always the last message in the chat."""
    # The source answers newest first, so reversing puts the same-day acts oldest first too.
    return sorted(reversed(changes), key=lambda change: change[0].get("published") or "")


def run_once(transport, config):
    state = migrate_state(load_state(config["state_path"]))
    archive = bool(config.get("archive"))
    if archive and state is None:
        # A backfill exists to publish the archive, so a missing state seeds nothing.
        state = empty_state()
    notices, attachments = fetch_enriched_notices(transport, config, state)
    changes, next_state = select_changes(notices, state)
    dry_run = bool(config.get("dry_run"))
    previous_sent = state["sent_messages"] if state else {}
    # A document retry is not a new publication: only count content not announced before.
    published = sum(
        1
        for notice, _ in changes
        if previous_sent.get(notice_key(notice)) != next_state["notices"][notice_key(notice)]
    )
    if dry_run:
        return {"notices": len(notices), "published": published, "dry_run": True}

    previous_notices = state["notices"] if state else {}
    working = empty_state()
    working["notices"] = dict(previous_notices)
    working["attachments"] = dict(state["attachments"]) if state else {}
    working["sent_documents"] = dict(state["sent_documents"]) if state else {}
    working["sent_messages"] = dict(previous_sent)
    # A first run only seeds: write state once at the end so an interruption
    # cannot leave a partial seed that the next run treats as a real state.
    seeding = state is None and not archive

    updated = {notice_key(notice): was_update for notice, was_update in changes}
    for notice, _ in publication_order(
        [(notice, notice_key(notice) in updated) for notice in notices]
    ):
        key = notice_key(notice)
        current = next_state["notices"][key]
        if key in updated and working["sent_messages"].get(key) != current:
            text = format_message(
                notice,
                config["detail_base"],
                updated=updated[key],
                archived=archive,
                today=config["today"],
            )
            publish_message(transport, config["telegram_url"], config["chat_id"], text)
            working["sent_messages"][key] = current
            save_state(config["state_path"], working)

        # A seeded notice has no published message, so it uploads no documents. Any notice
        # with a sent message retries the URLs it is still missing.
        missing = []
        if working["sent_messages"].get(key) == current:
            pdf_urls = [notice.get("document_url")] + list(notice.get("attachment_urls") or [])
            pdf_urls = list(dict.fromkeys(url for url in pdf_urls if url))
            missing = [url for url in pdf_urls if url not in working["sent_documents"]]
        for url in missing:
            publish_document(
                transport,
                config["document_base"],
                config["chat_id"],
                url,
                document_caption(notice),
            )
            working["sent_documents"][url] = key
            save_state(config["state_path"], working)

        # Every required document succeeded, so this fingerprint is safe to commit.
        if working["notices"].get(key) != current:
            working["notices"][key] = current
            working["attachments"][key] = attachments[key]
            if not seeding:
                save_state(config["state_path"], working)

    if not archive:
        write_index(config["index_dir"], build_index(notices))
    save_state(config["state_path"], working)
    return {"notices": len(notices), "published": published, "dry_run": False}


def publish_message(transport, telegram_url, chat_id, text):
    response = transport.request(
        "POST", telegram_url, {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    )
    if not response.get("ok"):
        raise RuntimeError(response.get("description") or "telegram error")
    return response["result"]


TELEGRAM_TEXT_LIMIT = 4096
TELEGRAM_CAPTION_LIMIT = 1024


def document_caption(notice):
    caption = f"PDF ufficiale: Atto {notice.get('number') or ''}/{notice.get('year') or ''}"
    if len(caption) > TELEGRAM_CAPTION_LIMIT:
        caption = caption[: TELEGRAM_CAPTION_LIMIT - 3] + "..."
    return caption


# Fields rendered as the visible part of the message; every other public field goes inside the quote.
MESSAGE_MAIN_FIELDS = (
    "published",
    "title",
    "category",
    "sector",
    "year",
    "number",
    "status",
    "expires",
    "cntDataDocumentoOrigine",
)
MESSAGE_VALUE_LIMIT = 500
MESSAGE_URL_LIMIT = 300
QUOTE_OPEN = "<blockquote expandable>"
QUOTE_CLOSE = "</blockquote>"


def _clip(text, size):
    if len(text) <= size:
        return text
    if size <= 3:
        return ""
    clipped = text[: size - 3] + "..."
    cut = clipped.rfind("&")
    if cut > clipped.rfind(";"):
        # An ampersand only comes from an escaped value, so it starts an entity that must stay whole.
        clipped = clipped[:cut] + "..."
    return clipped


def _esc(value, limit=MESSAGE_VALUE_LIMIT):
    text = "" if value is None else str(value)
    # Escaping first, then clipping keeps a long or hostile value from breaking the message bound.
    return _clip(html.escape(text, quote=True), limit)


def _link(url, label):
    safe = public_url(url)
    if not safe:
        return f"{label}: link non disponibile"
    return f'<a href="{_esc(safe, MESSAGE_URL_LIMIT)}">{label}</a>'


def _bounded(head, quote):
    def render(lines, body):
        parts = list(lines)
        if body:
            parts.append(f"{QUOTE_OPEN}{body}{QUOTE_CLOSE}")
        return "\n".join(parts)

    message = render(head, quote)
    if len(message) <= TELEGRAM_TEXT_LIMIT:
        return message
    # Whole lines keep every tag balanced, so a message that is still too long loses its last lines.
    overhead = len(QUOTE_OPEN) + len(QUOTE_CLOSE) + 1
    while len(head) > 1 and len(render(head, "")) + overhead > TELEGRAM_TEXT_LIMIT:
        head.pop()
    budget = TELEGRAM_TEXT_LIMIT - len(render(head, "")) - overhead
    return render(head, _clip(quote, budget))


def _is_expired(notice, today):
    if str(notice.get("status") or "").strip().upper() == "SCADUTO":
        return True
    try:
        return date.fromisoformat(str(today)) > date.fromisoformat(str(notice.get("expires")))
    except ValueError:
        return False


def _act_headline(notice, updated, archived, today):
    # Precedence is fixed: a changed act is updated, an expired one is expired before archived.
    if updated:
        return "Atto aggiornato APT Basilicata"
    if _is_expired(notice, today):
        return "Atto scaduto APT Basilicata"
    if archived:
        return "Atto archiviato APT Basilicata"
    return "Nuovo atto APT Basilicata"


def format_message(notice, detail_base, updated=False, archived=False, today=None):
    headline = _act_headline(notice, updated, archived, today)
    head = [
        f"<b>{headline}</b>",
        f"<u>Atto {_esc(notice.get('number'))}/{_esc(notice.get('year'))}</u>",
    ]
    detail_url = notice.get("detail_url") or f"{detail_base.rstrip('/')}/{notice.get('id') or ''}"
    head.append(_link(detail_url, "Atto ufficiale"))
    if notice.get("document_url"):
        head.append(_link(notice["document_url"], "PDF ufficiale"))
    for url in notice.get("attachment_urls") or []:
        head.append(_link(url, "Allegato"))
    if notice.get("title"):
        head.append(f"<b>Titolo:</b> {_esc(notice['title'])}")
    if notice.get("published"):
        head.append(f"<b>Pubblicato il:</b> {_esc(_display_date(notice['published']))}")
    if notice.get("expires"):
        head.append(f"<b>Scade il:</b> {_esc(_display_date(notice['expires']))}")
    if notice.get("cntDataDocumentoOrigine"):
        head.append(
            f"<b>Documento del:</b> {_esc(_display_date(notice['cntDataDocumentoOrigine']))}"
        )
    tags = [f"#{_hashtag(notice.get('category'))}", f"#{_hashtag(notice.get('sector'))}"]
    tags = [tag for tag in tags if len(tag) > 1]
    if tags:
        head.append(" ".join(_esc(tag) for tag in tags))
    if notice.get("status"):
        head.append(f"<b>Stato:</b> {_esc(notice['status'])}")
    quote = [
        f"{_esc(label)}: {_esc(value)}" for label, value in _field_rows(notice, MESSAGE_MAIN_FIELDS)
    ]
    if not notice.get("expires"):
        quote.insert(0, "Scadenza: non nota")
    return _bounded(head, "\n".join(quote))


def multipart_body(fields, filename, content):
    boundary = f"aptcron{os.urandom(16).hex()}"
    filename = re.sub(r'[\\\r\n"]', "_", str(filename))
    head = b"".join(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{_header_value(name)}"\r\n\r\n'
        f"{_header_value(value)}\r\n".encode("utf-8")
        for name, value in fields.items()
    )
    head += (
        f'--{boundary}\r\nContent-Disposition: form-data; name="document"; '
        f'filename="{_header_value(filename)}"\r\n'
        f"Content-Type: {mimetypes.guess_type(filename)[0] or 'application/octet-stream'}\r\n\r\n"
    ).encode("utf-8")
    # shortcut: the body is assembled in memory, so a 50 MB document peaks at roughly twice its size;
    # stream the parts only if the Telegram limit grows.
    return (
        head + content + f"\r\n--{boundary}--\r\n".encode("utf-8"),
        f"multipart/form-data; boundary={boundary}",
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
                "User-Agent": USER_AGENT,
            },
            method=method,
        )
        with urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))

    def fetch_bytes(self, url):
        if not public_url(url):
            raise RuntimeError(f"refusing a non-http document URL: {url}")
        request = Request(url, headers={"Accept": "application/pdf", "User-Agent": USER_AGENT})
        with urlopen(request, timeout=HTTP_TIMEOUT) as response:
            # One byte past the bound is enough for publish_document to reject it.
            return response.read(DOCUMENT_MAX_BYTES + 1)

    def send_document(self, url, fields, filename, content):
        data, content_type = multipart_body(fields, filename, content)
        request = Request(
            url,
            data=data,
            headers={
                "Accept": "application/json",
                "Content-Type": content_type,
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        with urlopen(request, timeout=DOCUMENT_UPLOAD_TIMEOUT) as response:
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


def load_env_file(path=None):
    """Load KEY=VALUE lines without overriding values already in the environment."""
    source = path or os.environ.get("APT_ENV_FILE") or Path(__file__).resolve().parent / ".env"
    env_path = Path(source)
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.strip().partition("=")
        if not separator or not name or name.startswith("#"):
            continue
        os.environ.setdefault(name.removeprefix("export ").strip(), value.strip().strip("'\""))


def main(argv=None):
    load_env_file()
    parser = argparse.ArgumentParser(description="Publish new APT Basilicata notices to Telegram")
    parser.add_argument("--dry-run", action="store_true", help="read the source without publishing or saving state")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--refresh-index",
        action="store_true",
        help="rebuild the public index without state or Telegram credentials",
    )
    mode.add_argument(
        "--backfill",
        action="store_true",
        help="publish the whole published archive oldest first, without rebuilding the index",
    )
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
    if not (args.dry_run or args.refresh_index) and (not token or not chat_id):
        parser.error(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required unless --dry-run or --refresh-index is used"
        )

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
        "archive": args.backfill,
    }
    try:
        if args.refresh_index:
            stats = refresh_index(UrllibTransport(), config)
        else:
            stats = run_once(UrllibTransport(), config)
    except Exception as error:
        print(f"error: {redact_credentials(error, token)}", file=sys.stderr)
        return 1
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
