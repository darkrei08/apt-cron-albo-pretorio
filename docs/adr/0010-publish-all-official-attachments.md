# 0010 — Publish every official attachment

- Status: accepted
- Supersedes: the attachment MIME filter in the implementation described by ADR 0006

## Context

The source attachment endpoint returns one published document (`documentoUnico`) and a `files` list.
The published document remains limited to the official PDF. The previous implementation filtered the
`files` list to PDF URLs, so a downloadable non-PDF attachment was visible in the source but was not
sent to the Telegram chat.

## Decision

For each new or changed notice, the Telegram publication consists of:

1. the HTML message containing the official detail link, published PDF link when present, and every
   safe attachment link;
2. the published PDF bytes when the source identifies `documentoUnico` as a PDF; and
3. every downloadable attachment in `files`, regardless of MIME type.

Attachment URLs are deduplicated by the existing sent-document state. Bytes remain in memory and use
the existing 50 MB bound and HTTP(S) validation. Multipart upload content type is inferred from the
sanitized filename, with `application/octet-stream` as the fallback. An extensionless URL keeps the
existing `document.pdf` fallback filename.

An absent published PDF or empty attachment list produces no document upload; the notice message and
official detail link keep their existing behavior. A failed attachment upload keeps the existing
incremental state semantics, so later runs retry only the missing document URL.

## Consequences

- The Telegram chat now receives non-PDF attachments such as images when the source exposes a
  downloadable URL.
- The public index keeps the existing URL-only `attachment_urls` field; no document bytes are stored
  locally or committed.
- The source attachment response and the fake transport tests must cover both PDF and non-PDF files.
- Existing PDF-only behavior, captions, deduplication, ordering and failure handling remain unchanged.

## Evidence

- `apt_cron.py`: `fetch_attachments`, `document_filename`, `multipart_body` and `run_once`.
- `tests/test_apt_cron.py`: attachment extraction and end-to-end delivery tests assert the published
  PDF plus every attachment are sent.
- `README.md`: publication and download behavior.
