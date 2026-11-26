# Telegram formatting constraints for the act message

Research answer for issue 15, child of issue 14. Research date: 2026-11-26. Primary sources only: Telegram Bot API reference, page self-identifies as Bot API 10.5 with Recent changes dated November 22, 2026, and the Bots FAQ.

## Answer

- Message text is 1-4096 characters after entities parsing. Captions are 0-1024 characters after entities parsing. Markup tags are not counted; escaped text is counted after parsing.
- HTML mode uses `parse_mode=HTML` and a fixed tag set: `b`, `strong`, `i`, `em`, `u`, `ins`, `s`, `strike`, `del`, `tg-spoiler`, `a href`, `code`, `pre`, `blockquote`, `tg-emoji` and `tg-time`. It does not support headings, lists, tables, media or inline buttons.
- Untrusted values must escape `<`, `>` and `&`. Only four named entities are supported: `&lt;`, `&gt;`, `&amp;`, `&quot;`; numerical entities are supported.
- Entities must nest fully inside one another. Nothing may be placed inside `pre` or `code`, and `blockquote` cannot be nested.
- Link previews are controlled with `link_preview_options.url` or `is_disabled`; otherwise the first URL in the text is previewed. A labelled inline link triggers a client confirmation dialog; a bare URL does not.
- Channel posts use the same text limit and formatting dialect. The bot must be an administrator with `can_post_messages`; channels have no threads.
- The Bots FAQ recommends at most one message per second in a single chat and about 30 messages per second overall; exceeding the limits yields 429 errors.
- Bot API 10.5 also documents `sendRichMessage`, which uses a much wider HTML dialect with headings, lists, tables, `details`, figures and buttons. That is a separate dialect and must not be conflated with `parse_mode` HTML.

## Repo relevance

Today `format_message` builds plain text, `publish_message` sends no `parse_mode`, and the text is bounded at 4096 characters. `document_caption` builds a bounded caption. The current constraints that already bind are therefore text length and caption length; escaping, entity nesting and link preview control start to bind as soon as HTML mode is adopted.

## Not documented by the primary sources

- Exact behavior on malformed or unbalanced markup.
- Treatment of unsupported or unknown tags.
- Whether the 4096 and 1024 limits count Unicode code points or UTF-16 code units.
- Client coverage and fallback behavior for rich messages.

## Sources

- https://core.telegram.org/bots/api#recent-changes
- https://core.telegram.org/bots/api#formatting-options
- https://core.telegram.org/bots/api#html-style
- https://core.telegram.org/bots/api#markdownv2-style
- https://core.telegram.org/bots/api#sendmessage
- https://core.telegram.org/bots/api#linkpreviewoptions
- https://core.telegram.org/bots/api#senddocument
- https://core.telegram.org/bots/api#messageentity
- https://core.telegram.org/bots/api#chatadministratorrights
- https://core.telegram.org/bots/api#sendrichmessage
- https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this
- https://core.telegram.org/bots/faq#how-can-i-message-all-of-my-bots-subscribers-at-once
