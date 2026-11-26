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

1. **Visible part.** Bold headline, the act number and year underlined, then in order: title,
   published date, expiry date, document date from `cntDataDocumentoOrigine` when present, the category
   and sector hashtags on one line, the status, and the labelled official link. The PDF document and
   attachment links follow as labelled links. The newest act is the last message in the chat, and inside
   the message its identity is now the first thing read.
2. **The headline states the act state.** Four fixed Italian labels describe updated, expired, archived
   and new notices, decided in that order. An update label is used when the notice changed since the
   last run; an expired label is used when `status` is `SCADUTO` or `expires` is a parsable ISO date
   earlier than the run's `today`; an archived label is used for archive backfill; the new label is the
   default. Precedence is updated, expired, archived, new, so an expired act inside a backfill is
   labelled expired. The state is derived from fields already published (`status`, `expires`) plus the
   run mode: no new source field, no state migration and no extra Telegram call.
3. **Everything else inside the quote.** The renderer places remaining non-empty public fields from
   `NOTICE_FIELDS` (`id`, `otypeId` and the other technical register fields) as `Label: value` lines
   inside `<blockquote expandable>` when the message budget permits. The quote collapses in the
   client, so normal messages stay compact; the global bound may clip trailing quote lines for
   pathological input.
3. **Unknown expiry is explicit.** When `expires` is empty the visible part carries no expiry line and
   the quote starts with the tested Italian unknown-expiry marker, so a reader never has to guess
   whether an act has no end date or the data is missing.
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
  governs live sign-off, and the production-readiness map tracks the required rerun before release.
- The headline is text only. The status field keeps its own escaped `Stato:` line, and nothing in the
  message changes colour, so the state is readable in every client, including one that ignores
  `blockquote expandable`.
- `today` is the run's own date and comes from the configuration; no clock is read in `format_message`,
  so the rendered message is a pure function of the notice and the run mode and a test can pin it.
- A backfill of the whole history labels every act archived except the ones already expired; nothing
  in the stored state records the label, so a later run re-renders from scratch.

## Evidence

- `apt_cron.py`: `MESSAGE_MAIN_FIELDS`, `QUOTE_OPEN`, `_esc`, `_link`, `_clip`, `_bounded`,
  `_is_expired`, `_act_headline`, `format_message`, `run_once` (passes `archive` and `today`),
  `publish_message` (`parse_mode`), `_display_date` (tolerates a non-ISO value),
  `TELEGRAM_TEXT_LIMIT`.
- `tests/test_apt_cron.py`: `FormatMessageTest` (exact layout, escaping, unknown expiry, document date,
  every public field in the quote, no internal field, the four headlines and their precedence),
  `BackfillHeadlineTest` (a backfill labels the history archived and an act expired before `today`),
  `RunOnceTest` (a regular run keeps the new/updated headline), `PublishMessageTest.test_posts_html_to_telegram`,
  `ProductionConfigTest.test_message_stays_within_telegram_text_limit` (length and tag balance).
- `README.md`: message format paragraph, production checks, tests paragraph.
