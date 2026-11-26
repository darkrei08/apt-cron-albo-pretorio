# 0006 — Notification format and channel

- Status: accepted; superseded for message formatting by [ADR 0009](0009-readable-telegram-act-message.md)
- Decision record: GitHub issue #7 (closed after issues #11 and #6)

## Context

One format function and one destination exist today.

**Format.** The plain-text message recorded here has been replaced by the Telegram HTML message of
ADR 0009. The description below is the state this ADR accepted and the reason it did; the channel and
caption decisions in it still stand.

The message was a sequence of plain-text lines with no `parse_mode`:

- a headline distinguishing a new notice from an updated notice;
- identity lines for publication date, title, category hashtag, sector hashtag, act number and year,
  status and official link;
- one label/value line for each other non-empty published field;
- one or more PDF link lines when documents exist.

Those first lines are the identity block (`MESSAGE_IDENTITY_FIELDS`, `apt_cron.py:434`). Every other
non-empty field of the 41 in `NOTICE_FIELDS` follows as its own `Label: value` line, labelled from
`FIELD_LABELS` and rendered in register order (`_field_rows`, `apt_cron.py:269-275`). Fields the
source returns empty produce no line.

Properties worth noting, all verified in code or tests:

- The official detail link is always present: a missing `detail_url` falls back to
  `detail_base.rstrip('/') + '/' + id` (`apt_cron.py:461`), and the test
  `test_formats_plain_text_with_searchable_fields_and_official_link` asserts the link survives.
- Hashtags are derived from the category and the sector by transliterating to ASCII and replacing
  non-alphanumerics with `_` (`_hashtag`, `apt_cron.py:121-124`), which makes them searchable in
  Telegram.
- The message is bounded at 4096 characters (`TELEGRAM_TEXT_LIMIT`, `apt_cron.py:422`). When a notice
  carries long values the widest lines are shortened in place (`_bounded`, `apt_cron.py:437-448`), so
  the bound holds without dropping the label; the tests cover both a pathological URL and a notice
  whose every field is long.
- Document messages use a caption that identifies the act by number and year and are bounded to 1024
  characters by `document_caption` (`apt_cron.py:426-430`) before being passed through
  `publish_document`. The caption carries no title and no other field, so it cannot vary with them.
  The document itself is uploaded as bytes: `publish_document` fetches the PDF into memory and posts
  a multipart `sendDocument` body with `chat_id`, `caption`, the file name and the content. Telegram
  is never asked to fetch the source URL.

**Channel.** A single destination, `TELEGRAM_CHAT_ID` (`apt_cron.py:586`), used for both
`sendMessage` and `sendDocument`. There is no per-category routing, no second channel and no
fallback chat. The generated index is a separate publication surface (ADR 0005), not a second
notification channel.

**What is unverified.** `README.md:130` records that the multipart document upload has only been
exercised against a local server and the unit suite, so rendering in a real client, hashtag
behaviour, PDF acceptance and caption length behaviour are all untested on the platform. A live
`sendDocument` by URL failed with `400 Bad Request: failed to get HTTP URL content`, which is why the
upload now carries the bytes. The private-channel checklist in
`docs/validation/telegram-private-channel.md` exists to close that gap.

Decisions the operator must make are marked `[INSERT DECISION]` with a recommendation.

## Decision

1. **Plain text was the final format at the time.** Accepted: plain text, no
   `parse_mode`/HTML/Markdown. Plain text needs no escaping, cannot break on a value containing `*`,
   `_` or `<`, is read linearly by screen readers, and keeps the official link before the optional
   PDF line. Superseded for formatting by ADR 0009: the operator chose a Telegram HTML layout after
   the plain-text message proved too flat to read.
2. **Accessibility detail.** Accepted: the `label: value` line format with the headline first,
   followed by identity fields (date, title, category, sector, act, status, official link), then one
   labelled line per remaining non-empty published field, then optional PDF link lines.
   Label-value pairs survive translation and
   screen-reader navigation without layout. Every field the register publishes for an act reaches the
   message (ADR 0005 item 3); empty fields are skipped rather than printed blank.
3. **Hashing and casing conventions.** Accepted: `Categoria: #<hashtag>` and `Settore: #<hashtag>`
   exactly as generated, including the ASCII transliteration, because users build a search habit on
   them.
4. **Final channel.** Accepted and still valid: one Telegram channel, promoted from the private test
   channel validated in `docs/validation/telegram-private-channel.md`. One channel is
   a deliberate limit: routing by category would multiply the publication surfaces that ADR 0005 has
   to govern. The message is now sent with `parse_mode` `HTML` (ADR 0009); the channel choice is
   unchanged.
5. **Caption bound.** Accepted: document captions identify the act by number and year and are capped
   at 1024 characters, preserving the fixed caption prefix. The caption no longer depends on the
   title, so a long title cannot trigger the bound; the cap stays as a guard and as a regression test
   through the public run path.
6. **Format acceptance sign-off.** Accepted after the private-channel check: the rendered message,
   category and sector hashtags, official link and both PDF documents were observed in channel
   `-1005772944869`. The bounded caption and the full field set rendered as designed.

## Consequences

- Choosing plain text fixed the format contract; that contract is now ADR 0009. The 4096-character
  bound is still enforced, now on the rendered HTML: the visible part drops whole trailing lines and
  the expandable quote is clipped, so the message stays readable and under the limit even when a
  source value is long.
- The message no longer grows with the number of filled fields: the fields a reader acts on are
  visible and the rest collapse into one expandable quote.
- The caption is independent of the source title, so a long title can no longer be rejected by
  Telegram after the news message and state write have already succeeded. The private-channel
  checklist still needs to confirm that the act-number caption renders acceptably in a real client.
- One channel keeps notification and retention simple but means ADR 0004's withdrawal rule has
  exactly one destination to consider.

## Evidence

Line numbers and test names below are those of the tree this ADR was accepted on. The format symbols
(`format_message`, `_bounded`, `MESSAGE_IDENTITY_FIELDS`, `publish_message` `parse_mode`) and the format
tests moved to ADR 0009; the caption and channel symbols are unchanged.

- `apt_cron.py`: `format_message` `:451-469`, `TELEGRAM_TEXT_LIMIT` `:422`,
  `TELEGRAM_CAPTION_LIMIT` `:423`, `document_caption` `:426-430`, `_bounded` `:437-448`,
  `MESSAGE_IDENTITY_FIELDS` `:434`, `_field_rows` `:269-275`, `FIELD_LABELS` `:65-107`, `_hashtag`
  `:121-124`, `_display_date` `:117-118`, `document_filename` `:243-245`, `publish_document`
  `:248-260`, `multipart_body` `:472-489`, caption construction in `run_once` `:403`,
  `publish_message` `:415-419`, `TELEGRAM_CHAT_ID` `:586`.
- `tests/test_apt_cron.py`: `test_formats_plain_text_with_searchable_fields_and_official_link`,
  `test_includes_every_public_field_and_never_an_internal_one`,
  `test_message_stays_within_telegram_text_limit`,
  `test_document_caption_uses_the_act_number_and_stays_within_telegram_limit`,
  `test_document_caption_carries_no_public_or_internal_text`, `test_posts_plain_text_to_telegram`,
  `test_fetches_the_pdf_bytes_and_uploads_them_as_a_document`.
- `README.md:13` (send order: message first, then PDFs uploaded as bytes), `:130` (live validation is
  partial), `:122` (4096 and caption bounds stated).
- `docs/wayfinder-execution-order.md` row 8 (blocked by issues #11 and #6).

## Not verified

The message, hashtags, official link and two PDF documents were rendered in one private Telegram
client and recorded in the validation checklist. Other clients and platforms remain unverified:
inline link previews, hashtag indexing in other clients, emoji width and caption rendering can differ.
