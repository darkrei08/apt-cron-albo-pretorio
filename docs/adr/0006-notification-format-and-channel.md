# 0006 — Notification format and channel

- Status: proposed (operator input required)
- Decision record: GitHub issue #7 (open, blocked by issues #11 and #6)

## Context

One format function and one destination exist today.

**Format.** `format_message` (`apt_cron.py:328-354`) builds plain text with no `parse_mode` (the
string `parse_mode` appears nowhere in `apt_cron.py` or the tests), so Telegram renders it verbatim:

```
Nuovo atto APT Basilicata            (or "Atto aggiornato APT Basilicata" when the notice changed)
Data: 25/11/2026
Titolo: <title>
Categoria: #<hashtag>
Settore: #<hashtag>
Atto: <number>/<year>
Stato: <status>
Link: <detail_url, or detail_base + id>
PDF: <document_url>                  (only when a document exists)
```

Properties worth noting, all verified in code or tests:

- The official detail link is always present: a missing `detail_url` falls back to
  `detail_base.rstrip('/') + '/' + id` (`apt_cron.py:338`), and the test
  `test_formats_plain_text_with_searchable_fields_and_official_link` asserts the link survives.
- Hashtags are derived from category and sector by transliterating to ASCII and replacing
  non-alphanumerics with `_` (`_hashtag`, `apt_cron.py:39-42`), which makes them searchable in
  Telegram.
- The message is bounded at 4096 characters (`TELEGRAM_TEXT_LIMIT`, `apt_cron.py:325`); when there
  is room, truncation shortens only the title line and preserves the trailing link. An extreme-overhead
  fallback hard-cuts the message at the limit, so link preservation is not guaranteed in that edge case
  (`apt_cron.py:343-354`, test `test_message_stays_within_telegram_text_limit`).
- Document messages use the caption `PDF ufficiale: <title>` and are bounded to 1024 characters
  by `document_caption` before being passed through `publish_document`. The prefix is preserved and
  an overlong title is truncated with an ellipsis.

**Channel.** A single destination, `TELEGRAM_CHAT_ID` (`apt_cron.py:409-410`), used for both
`sendMessage` and `sendDocument`. There is no per-category routing, no second channel and no
fallback chat.

**What is unverified.** `README.md:85` records that no live message or document has been sent, so
rendering in a real client, hashtag behaviour, PDF acceptance and caption length behaviour are all
untested on the platform. The private-channel checklist in
`docs/validation/telegram-private-channel.md` exists to close that gap.

Decisions the operator must make are marked `[INSERT DECISION]` with a recommendation.

## Decision

1. **Keep the current plain text as the final format.** `[INSERT DECISION]` — *Recommendation: yes,
   keep it, and do not add `parse_mode`/HTML/Markdown.* Plain text needs no escaping, cannot break
   on a title containing `*`, `_` or `<`, is read linearly by screen readers, keeps hashtags as
   searchable text, and keeps the official link immediately before the optional PDF line, so it
   remains near the end of the message.
2. **Accessibility detail to accept or reject.** `[INSERT DECISION]` — *Recommendation: accept the
   `Etichetta: valore` line format with the headline first, because label-value pairs survive
   translation and screen-reader navigation without layout, and drop nothing from the eight lines.*
   The alternative — a shorter message with only title and link — would reduce scanning noise but
   changes what is published.
3. **Hashing and casing conventions.** `[INSERT DECISION]` — *Recommendation: keep
   `Categoria: #<hashtag>` and `Settore: #<hashtag>` exactly as generated, including the ASCII
   transliteration, because changing them silently breaks the search habit users build up.*
4. **Final channel.** `[INSERT DECISION]` — *Recommendation: one private-to-public test channel as
   validated in `docs/validation/telegram-private-channel.md`, promoted to the single production
   channel, with the channel owner and bot admin named.* One channel is a deliberate limit: routing
   by category would multiply the publication surfaces that ADR 0005 has to govern.
5. **Caption bound.** Accepted: document captions are capped at 1024 characters, preserving the
   `PDF ufficiale:` prefix and truncating an overlong title with an ellipsis. This matches Telegram's
   documented `sendDocument` caption limit (external platform limit, not verified in this repository)
   and is covered by a regression test through the public run path.
6. **Format acceptance sign-off.** `[INSERT DECISION]` — *Recommendation: the operator confirms the
   rendered message, hashtags, link and PDF in the private channel and records that confirmation
   before this ADR moves to accepted.*

## Consequences

- Choosing plain text fixes the format contract: any future rich formatting is a new decision, and
  the 4096-character truncation logic is the only bound the format has.
- The caption bound prevents a long title from being rejected by Telegram after the news message
  and state write have already succeeded. The private-channel checklist still needs to confirm that
  the truncated caption renders acceptably in a real client.
- One channel keeps notification and retention simple but means ADR 0004's withdrawal procedure has
  exactly one destination to clean up.

## Evidence

- `apt_cron.py`: `format_message`, `TELEGRAM_TEXT_LIMIT`, `TELEGRAM_CAPTION_LIMIT`,
  `document_caption`, `_hashtag`, `_display_date`, `publish_document`, caption construction in
  `run_once`, `publish_message`, `TELEGRAM_CHAT_ID`.
- `tests/test_apt_cron.py`: `test_formats_plain_text_with_searchable_fields_and_official_link`,
  `test_message_stays_within_telegram_text_limit`, `test_posts_plain_text_to_telegram`,
  `test_sends_pdf_by_url_as_telegram_document`.
- `README.md:12` (send order: message first, then PDFs by URL), `:85` (nothing sent live), `:90`
  (4096 bound stated).
- `docs/wayfinder-execution-order.md` row 8 (blocked by issues #11 and #6).

## Not verified

No message or document has been rendered in a real Telegram client. Client-specific behaviour —
inline link previews, hashtag indexing in the channel, emoji width, PDF size acceptance and caption
length limits — is untested here and is the subject of the validation checklist.
