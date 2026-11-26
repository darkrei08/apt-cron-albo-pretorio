# Telegram private-channel validation

Manual checklist for issue #10. It closes the gap recorded in `README.md:85`: no live Telegram
message or document has been sent, and `docs/adr/0006-notification-format-and-channel.md` cannot be
accepted until the rendered result is observed.

Everything here runs in a **private test channel**, never in production. No automated test in this
repository contacts Telegram (`tests/` uses fake transports).

## Prerequisites

- Python 3.11 or newer on the machine performing the check.
- A private test channel (or a test group) where the bot is an administrator with permission to post
  messages and send documents.
- A bot token and the test channel's chat id, obtained and owned as follows:
  - **Token and chat owner.** `[INSERT DECISION]` — *Recommendation: the operator named in ADR 0003
    item 3 creates a dedicated test bot (not the production bot) and supplies its token only through
    the environment, never on a command line that lands in shell history.*
- A clean state path and index directory for the check, so nothing touches production state:

```sh
export CHECK_DIR="$(mktemp -d)"
export APT_STATE_PATH="$CHECK_DIR/state/notices.json"
export APT_INDEX_DIR="$CHECK_DIR/public"
```

Record every result as PASS, FAIL or NOT RUN. A FAIL is only acceptable with a named owner and a
follow-up ticket.

## V1 — Read-only dry run

```sh
python3 apt_cron.py --dry-run
```

Expected: exit code `0`; a single JSON line such as `{"dry_run": true, "notices": <N>,
"published": 0}`; **no** file created at `APT_STATE_PATH` and **no** index directory created.

Result: NOT RUN

## V2 — First live run seeds state without publishing

Use a protected environment file containing the dedicated test bot token and chat id. It must not
be committed and must not appear in shell history.

```sh
set -a
. /path/to/protected-test.env
set +a
python3 apt_cron.py
```

Expected: exit code `0`; `"published": 0`; `$APT_STATE_PATH` created with `version`, `notices`,
`attachments` and `sent_documents`; `index.json`, `index.md` and `index.html` created in
`$APT_INDEX_DIR`; **no** message in the channel.

Result: NOT RUN

## V3 — Publish one notice

Make one already-seeded notice look new by removing its key from the `notices` map in
`$APT_STATE_PATH` (edit the JSON; keep the rest of the file intact), then repeat the V2 command.

Expected: one plain-text message plus one document message per official PDF URL for that notice;
`sent_documents` gains one entry per document URL; index files regenerated.

Result: NOT RUN

## V4 — Message rendering and official link

Check against the message from V3:

1. The headline reads `Nuovo atto APT Basilicata` (or `Atto aggiornato APT Basilicata` when the
   notice changed after a first publish). Format source: `apt_cron.py:328-354`.
2. All eight lines are present in order: headline, `Data:`, `Titolo:`, `Categoria:`, `Settore:`,
   `Atto:`, `Stato:`, `Link:` — plus `PDF:` when a document exists.
3. No markup appears literally: no asterisks, underscores or HTML tags introduced by the sender.
   The code sets no `parse_mode`, so any `_` or `*` you see comes from the source data itself.
4. `Categoria:` and `Settore:` render as single-token hashtags (`#Parola_Con_Underscore`) and
   Telegram turns them into tappable/searchable hashtags.
5. `Link:` opens the official APT detail page in a browser (the exact notice, not the register
   home page), and the link is worth a preview card only if that is acceptable.
6. Screen-reader order is linear and the official link is the last core field before any optional
   PDF line.

Result: NOT RUN

## V5 — Document delivery by URL

1. A document message arrives for each official PDF (`documentoUnico` plus PDF attachments).
2. Opening the document works: Telegram fetched the file from the official URL, so a broken or
   expiring source URL shows up here (`sendDocument` by URL, `apt_cron.py:161-169`, call site
   `:301-307`).
3. File name and type are the source's own (`PAP-00244-2026`, `notice.pdf` style), not renamed by
   this project.
4. The largest real notice PDF is accepted.
   - **PDF size check.** `[INSERT DECISION]` — *Recommendation: record the size of the largest PDF
     observed (in MB) next to this line, because Telegram's documented limit for a document sent by
     URL is 50 MB (external platform limit, not verified in this repository). A PDF above it will
     fail with a Telegram error and exit code `1`.*
5. Non-PDF attachments are never sent. The local unit test proves that `fetch_attachments` keeps only
   PDF MIME types and its fixture includes an `image/png` entry. In the live channel this item remains
   NOT RUN unless a real notice with a non-PDF attachment is observed and no document message appears
   for it (`apt_cron.py:135-158`).

Result: NOT RUN

## V6 — Caption bound

The caption is `PDF ufficiale: <title>` and is now bounded to 1024 characters by
`document_caption`, preserving the prefix and truncating an overlong title with an ellipsis. The
message text remains bounded separately at 4096 characters.

1. Confirm captions arrive intact for normal titles.
2. If a notice with a very long title is available, confirm the truncated caption is accepted.
   Telegram's documented caption limit is 1024 characters (external, not verified here).
3. **Caption decision.** Accepted and implemented. This item is PASS only after a long-title case
   has been observed in the private channel.

Result: NOT RUN

## V7 — Message identifier decision

`publish_message` and `publish_document` return Telegram's `result` object, which contains
`message_id`; `run_once` discards both (`apt_cron.py:292-307`). Nothing in `$APT_STATE_PATH`
therefore identifies a published message.

- **Store `message_id`?** `[INSERT DECISION]` — *Recommendation: yes, record `message_id` per notice
  and per document in state, because it is the only handle for later edits or deletion required by
  ADR 0004; the change needs its own ticket and a state migration.*
- Observation for the record: note whether the Telegram client shows any way to locate a message by
  content if `message_id` were absent (search by title, by hashtag) and how reliable it is.

Result: NOT RUN

## V8 — Failure path

Prepare a publishable notice first, as in V3: remove one notice key from the state file so this run
actually sends a Telegram request. If the state is already seeded and unchanged, the invalid token is
not exercised and this item is NOT RUN.

```sh
TELEGRAM_BOT_TOKEN='invalid-token-for-check' TELEGRAM_CHAT_ID='<test chat id>' python3 apt_cron.py
```

Expected: exit code `1`, one stderr line beginning `error:`, no traceback, and the token value not
printed (`redact_credentials`, `apt_cron.py:383-385`; handler `:434-438`). Also check:

```sh
APT_PAGE_SIZE=bogus python3 apt_cron.py --dry-run
```

Expected: exit code `2` with an argparse usage message. And with no credentials at all:
exit code `2` and the message about `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` (`apt_cron.py:411-412`).

Result: NOT RUN

## V9 — Record and hand off

- [ ] Every item above is PASS, or FAIL with an owner and a ticket.
- [ ] Evidence captured: the message text, the document names, the largest PDF size, and the exit
      codes of V1, V2, V8.
- [ ] `docs/adr/0006-notification-format-and-channel.md` updated from `proposed` to `accepted` only
      after V4, V5, V6 and V7 are answered.
- [ ] Test credentials removed from the machine after the check; no token written into this file or
      any commit.

Result: NOT RUN

## Known limits of this checklist

- It validates one Telegram client on one platform; another client (mobile, web, desktop) can render
  hashtags, previews and documents differently.
- It cannot prove long-term source availability or that the source keeps returning the same PDF URLs.
- It does not exercise schedule, secret storage or failure alerting: those are ADR 0003 and
  ADR 0007 parts 4-5.
