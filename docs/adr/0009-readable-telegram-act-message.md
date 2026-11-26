# 0009 — Readable Telegram act message in HTML

- Status: accepted
- Supersedes: [ADR 0006](0006-notification-format-and-channel.md) for message formatting only
- Decision record: operator decision to replace the plain-text wall of fields

## Context

ADR 0006 accepted a plain-text message without `parse_mode`. That decision still holds for the channel
and for the document captions, but the operator replaced its format contract: a typical act rendered
15-20 `Label: value` lines of similar weight, so the newest act did not stand out and a reader had to
scan every technical field to find the title, the dates or the official link. Every field still has to
be published (ADR 0005), so the fix is hierarchy, not suppression.

Telegram Bot API facts this decision relies on (Bot API documentation, `parse_mode` `HTML`): the
supported tags are `b`/`strong`, `i`/`em`, `u`/`ins`, `s`/`strike`/`del`, `tg-spoiler`, `a href`,
`code`, `pre`, `blockquote` and `blockquote expandable`; `&`, `<` and `>` in a dynamic value must be
escaped or the message is rejected; the message limit is 4096 characters after entities are parsed;
captions stay at 0-1024 characters.

## Decision

`format_message` renders Telegram HTML and `publish_message` sends `parse_mode: HTML`.

1. **Visible part.** Bold headline (`Nuovo atto` / `Atto aggiornato`), the act number and year
   underlined, then in order: title, published date, expiry date, document date from
   `cntDataDocumentoOrigine` when present, the category and sector hashtags on one line, the status, and
   the labelled official link. The PDF document and attachment links follow as labelled links. The
   newest act is the last message in the chat, and inside the message its identity is now the first
   thing read.
2. **Everything else inside the quote.** All remaining non-empty public fields from `NOTICE_FIELDS`
   (`id`, `otypeId` and the other technical register fields) are one `Label: value` line each inside
   `<blockquote expandable>`. The quote collapses in the client, so the visible message is short and no
   public field is lost.
3. **Unknown expiry is explicit.** When `expires` is empty the visible part carries no expiry line and
   the quote starts with `Scadenza: non nota`, so a reader never has to guess whether an act has no
   end date or the data is missing.
4. **Escaping.** Every dynamic value, hashtag and URL passes through `html.escape(..., quote=True)`.
   Values are clipped after escaping, and the clip never ends inside an entity or a tag, so a hostile
   or long value cannot inject markup and cannot break the message.
5. **Bound.** The rendered HTML is bounded at `TELEGRAM_TEXT_LIMIT` (4096). The visible part shrinks
   only by dropping whole trailing lines (never a partial tag), and the quote body is clipped to the
   remaining budget. A normal act never reaches the bound.
6. **Unchanged.** One destination channel, the document captions, the publication order, the state,
   the index and the field set are untouched. ADR 0006 remains the record for the channel and the
   caption decision.

Fields rendered outside the quote are listed once in `MESSAGE_MAIN_FIELDS`; the quote is produced by
the same `_field_rows` used by the index, so the message and the index cannot drift apart.

## Consequences

- The message is now markup, so escaping is a correctness requirement, not a nicety: a title with `&`
  or `<` must not fail the run. Tests pin the escaping of a hostile title, status, technical field and
  URL.
- Telegram clients that do not render `blockquote expandable` show the quote expanded; the message is
  still complete and readable, only longer.
- The visible part carries the fields a reader acts on; the quote carries the register dump. A reader
  who needs `cntNumeroGara` or `otypeId` still finds it, one tap away.
- The bound is applied to HTML, not to plain text, so it counts escaped characters. Only pathological
  notices reach it, and the tests assert balanced tags at that point.
- Rendering in a real client was not re-verified by this change: the private-channel checklist still
  governs live sign-off, and no live message was sent while implementing this ADR.

## Evidence

- `apt_cron.py`: `MESSAGE_MAIN_FIELDS`, `QUOTE_OPEN`, `_esc`, `_link`, `_clip`, `_bounded`,
  `format_message`, `publish_message` (`parse_mode`), `_display_date` (tolerates a non-ISO value),
  `TELEGRAM_TEXT_LIMIT`.
- `tests/test_apt_cron.py`: `FormatMessageTest` (exact layout, escaping, unknown expiry, document date,
  every public field in the quote, no internal field), `PublishMessageTest.test_posts_html_to_telegram`,
  `ProductionConfigTest.test_message_stays_within_telegram_text_limit` (length and tag balance).
- `README.md`: message format paragraph, production checks, tests paragraph.
