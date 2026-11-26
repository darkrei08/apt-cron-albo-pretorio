# 0006 — Notification format and channel

- Status: accepted for items 1-5; format sign-off (item 6) pending private-channel validation
- Decision record: GitHub issue #7 (open, blocked by issues #11 and #6)

## Context

One format function and one destination exist today.

**Format.** `format_message` (`apt_cron.py:436-454`) builds plain text with no `parse_mode` (the
string `parse_mode` appears nowhere in `apt_cron.py` or the tests), so Telegram renders it verbatim:

The message is a sequence of plain-text lines:

- a headline distinguishing a new notice from an updated notice;
- identity lines for publication date, title, category hashtag, sector hashtag, act number and year,
  status and official link;
- one label/value line for each other non-empty published field;
- one or more PDF link lines when documents exist.

Those first lines are the identity block (`MESSAGE_IDENTITY_FIELDS`, `apt_cron.py:419`). Every other
non-empty field of the 41 in `NOTICE_FIELDS` follows as its own `Label: value` line, labelled from
`FIELD_LABELS` and rendered in register order (`_field_rows`, `apt_cron.py:254-260`). Fields the
source returns empty produce no line.

Properties worth noting, all verified in code or tests:

- The official detail link is always present: a missing `detail_url` falls back to
  `detail_base.rstrip('/') + '/' + id` (`apt_cron.py:444`), and the test
  `test_formats_plain_text_with_searchable_fields_and_official_link` asserts the link survives.
- Hashtags are derived from the category and the sector by transliterating to ASCII and replacing
  non-alphanumerics with `_` (`_hashtag`, `apt_cron.py:115-118`), which makes them searchable in
  Telegram.
- The message is bounded at 4096 characters (`TELEGRAM_TEXT_LIMIT`, `apt_cron.py:407`). When a notice
  carries long values the widest lines are shortened in place (`_bounded`, `apt_cron.py:422-434`), so
  the bound holds without dropping the label; the tests cover both a pathological URL and a notice
  whose every field is long.
- Document messages use a caption that identifies the act by number and year and are bounded to 1024
  characters by `document_caption` (`apt_cron.py:411-416`) before being passed through
  `publish_document`. The caption carries no title and no other field, so it cannot vary with them.

**Channel.** A single destination, `TELEGRAM_CHAT_ID` (`apt_cron.py:514`), used for both
`sendMessage` and `sendDocument`. There is no per-category routing, no second channel and no
fallback chat. The generated index is a separate publication surface (ADR 0005), not a second
notification channel.

**What is unverified.** `README.md:85` records that no live message or document has been sent, so
rendering in a real client, hashtag behaviour, PDF acceptance and caption length behaviour are all
untested on the platform. The private-channel checklist in
`docs/validation/telegram-private-channel.md` exists to close that gap.

Decisions the operator must make are marked `[INSERT DECISION]` with a recommendation.

## Decision

1. **Keep the current plain text as the final format.** Accepted: plain text, no
   `parse_mode`/HTML/Markdown. Plain text needs no escaping, cannot break on a value containing `*`,
   `_` or `<`, is read linearly by screen readers, and keeps the official link before the optional
   PDF line.
2. **Accessibility detail.** Accepted: the `label: value` line format with the headline first,
   followed by identity fields (date, title, category, sector, act, status, official link), then one
   labelled line per remaining non-empty published field, then optional PDF link lines.
   Label-value pairs survive translation and
   screen-reader navigation without layout. Every field the register publishes for an act reaches the
   message (ADR 0005 item 3); empty fields are skipped rather than printed blank.
3. **Hashing and casing conventions.** Accepted: `Categoria: #<hashtag>` and `Settore: #<hashtag>`
   exactly as generated, including the ASCII transliteration, because users build a search habit on
   them.
4. **Final channel.** Accepted: one Telegram channel, plain text without `parse_mode`, promoted from
   the private test channel validated in `docs/validation/telegram-private-channel.md`. One channel is
   a deliberate limit: routing by category would multiply the publication surfaces that ADR 0005 has
   to govern.
5. **Caption bound.** Accepted: document captions identify the act by number and year and are capped
   at 1024 characters, preserving the fixed caption prefix. The caption no longer depends on the
   title, so a long title cannot trigger the bound; the cap stays as a guard and as a regression test
   through the public run path.
6. **Format acceptance sign-off.** `[INSERT DECISION]` — *Recommendation: the operator confirms the
   rendered message, hashtag, link and PDF in the private channel and records that confirmation
   before this ADR is fully accepted. The test credentials will be supplied later through a
   protected local environment file; no live check has been run.*

## Consequences

- Choosing plain text fixes the format contract: any future rich formatting is a new decision. The
  4096-character bound is now a per-line truncation of the widest lines rather than a hard cut, so the
  message stays readable and under the limit even when a source value is long.
- The message grows with the number of filled fields: a typical live act renders 15-20 lines (about
  1200-1400 characters), not 8. Every extra line is one more field a reader can search; the trade-off
  is a longer notification and no field-level suppression other than an empty value.
- The caption is independent of the source title, so a long title can no longer be rejected by
  Telegram after the news message and state write have already succeeded. The private-channel
  checklist still needs to confirm that the act-number caption renders acceptably in a real client.
- One channel keeps notification and retention simple but means ADR 0004's withdrawal rule has
  exactly one destination to consider.

## Evidence

- `apt_cron.py`: `format_message` `:436-454`, `TELEGRAM_TEXT_LIMIT` `:407`,
  `TELEGRAM_CAPTION_LIMIT` `:408`, `document_caption` `:411-416`, `_bounded` `:422-434`,
  `MESSAGE_IDENTITY_FIELDS` `:419`, `_field_rows` `:254-260`, `FIELD_LABELS` `:59-101`, `_hashtag`
  `:115-118`, `_display_date` `:111-112`, `publish_document` `:237-245`, caption construction in
  `run_once` `:388`, `publish_message` `:400-405`, `TELEGRAM_CHAT_ID` `:514`.
- `tests/test_apt_cron.py`: `test_formats_plain_text_with_searchable_fields_and_official_link`,
  `test_includes_every_public_field_and_never_an_internal_one`,
  `test_message_stays_within_telegram_text_limit`,
  `test_document_caption_uses_the_act_number_and_stays_within_telegram_limit`,
  `test_document_caption_carries_no_public_or_internal_text`, `test_posts_plain_text_to_telegram`,
  `test_sends_pdf_by_url_as_telegram_document`.
- `README.md:13` (send order: message first, then PDFs by URL), `:106` (nothing sent live), `:112`
  (4096 and caption bounds stated).
- `docs/wayfinder-execution-order.md` row 8 (blocked by issues #11 and #6).

## Not verified

No message or document has been rendered in a real Telegram client. Client-specific behaviour —
inline link previews, hashtag indexing in the channel, emoji width, PDF size acceptance and caption
rendering — is untested here and is the subject of the validation checklist. Item 6 stays open until
that checklist has run.
