# Telegram private-channel validation

Manual checklist for issue #10. It closes the gap recorded in `README.md:130`: Telegram delivery has
been exercised only partially (a live message and `getChat` succeeded, a document sent by URL failed
with HTTP 400), and `docs/adr/0006-notification-format-and-channel.md` cannot be fully accepted until
the rendered result is observed.

Everything here runs in a **private test channel**, never in production. No automated test in this
repository contacts Telegram (`tests/` uses fake transports). No item has been run: the operator will
supply the test credentials later through a local env file (`.env` or `APT_ENV_FILE`).

## Prerequisites

- Python 3.11 or newer on the machine performing the check.
- A private test channel (or a test group) where the bot is an administrator with permission to post
  messages and send documents.
- A bot token and the test channel's chat id, obtained and owned as follows:
  - **Token and chat owner.** Accepted: the repository operator supplies a dedicated test bot token
    and the test channel id later through a local env file, never on a command line that lands in
    shell history. The file may be a gitignored `.env` in the repository root (loaded automatically)
    or any path named by `APT_ENV_FILE`, mode `0600`. No credential is committed or written into
    this checklist, and no base64-encoded value is used: base64 is not encryption.
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

Put the dedicated test bot token and chat id in a local env file: the gitignored `.env` in the
repository root, or the file named by `APT_ENV_FILE`. It must not be committed and must not appear in
shell history. The script loads the file itself, so nothing needs to be sourced and no value is
typed on a command line.

```sh
python3 apt_cron.py
```

Expected: exit code `0`; `"published": 0`; `$APT_STATE_PATH` created with `version`, `notices`,
`attachments` and `sent_documents`; `index.json`, `index.md` and `index.html` created in
`$APT_INDEX_DIR`; **no** message in the channel.

Result: NOT RUN

## V3 — Publish one notice

Make one already-seeded notice look new by removing its key from the `notices` map in
`$APT_STATE_PATH` (edit the JSON; keep the rest of the file intact), then repeat the V2 command.

Expected: one plain-text message plus one document message per official PDF for that notice;
`sent_documents` gains one entry per document URL; index files regenerated.

Result: NOT RUN

## V4 — Message rendering and official link

Check against the message from V3:

1. The headline distinguishes a new notice from an updated notice after a first publish. Format
   source: `apt_cron.py:451-469`.
2. The identity block is present in order: headline, date, title, category hashtag, sector hashtag,
   act number and year, status and official link, plus PDF link lines when documents exist. Every
   included public source field with a non-empty value also appears as a label/value line, per ADR
   0005.
3. No markup appears literally: no asterisks, underscores or HTML tags introduced by the sender.
   The code sets no `parse_mode`, so any `_` or `*` you see comes from the source data itself.
4. `Categoria:` and `Settore:` render as single-token hashtags (`#Category_With_Underscore`) and
   Telegram turns them into tappable/searchable hashtags.
5. `Link:` opens the official APT detail page in a browser (the exact notice, not the register
   home page), and the link is worth a preview card only if that is acceptable.
6. Screen-reader order is linear and the official link is the last core field before any optional
   PDF line.

Result: NOT RUN

## V5 — Document delivery as uploaded bytes

1. A document message arrives for each official PDF (`documentoUnico` plus PDF attachments).
2. Opening the document works. The script fetches the PDF into memory and uploads the bytes in a
   multipart `sendDocument` body (`publish_document` `apt_cron.py:248-260`, `multipart_body`
   `:472-489`, transport `send_document` `:514-527`), so Telegram no longer fetches the source URL
   and an expiring source URL shows up as a fetch error in the run, not as a document Telegram could
   not open. This replaces the previous URL hand-off, which failed live with
   `400 Bad Request: failed to get HTTP URL content`.
3. File name and type are those of the source (`notice.pdf` style) or `document.pdf` when the source
   URL carries no file name (`document_filename` `apt_cron.py:243-245`); content type is
   `application/pdf`.
4. The largest real notice PDF is accepted.
   - **PDF size check.** The upload is bounded at 50 MB (`DOCUMENT_MAX_BYTES`, `apt_cron.py:18`).
     `[INSERT DECISION]` — *Recommendation: record the size of the largest PDF observed (in MB) next
     to this line. A PDF above the bound is rejected before the upload and fails the run with exit
     code `1`, as the unit suite proves for the boundary.*
5. Non-PDF attachments are never sent. The local unit test proves that `fetch_attachments` keeps only
   PDF MIME types and its fixture includes an `image/png` entry. In the live channel this item remains
   NOT RUN unless a real notice with a non-PDF attachment is observed and no document message appears
   for it (`apt_cron.py:217-240`). If no such notice exists during validation, mark this item
   NOT RUN and record it as accepted non-applicable with a named owner; the release gate allows that
   disposition explicitly.

Result: NOT RUN

## V6 — Caption bound

The caption identifies the act by number and year and is bounded to 1024 characters by
`document_caption` (`apt_cron.py:426-430`). The message text remains bounded separately at 4096
characters. The caption carries no title, so a long title cannot affect it; if a notice with an
unusually long act number is available, confirm the truncated caption is accepted.

1. Confirm captions arrive intact and identify the act unambiguously.
2. Confirm no title text appears in any caption.
3. **Caption decision.** Accepted and implemented. This item is PASS only after a caption has been
   observed in the private channel.

Result: NOT RUN

## V7 — Message identifier decision

`publish_message` and `publish_document` return Telegram's `result` object, which contains
`message_id`; `run_once` discards both (`apt_cron.py:376-412`). Nothing in `$APT_STATE_PATH`
therefore identifies a published message.

- **Store `message_id`?** Accepted decision: no. ADR 0004 keeps messages as the permanent record and
  performs no deletion, so state does not need message identifiers.
- Observation for the record: note whether the Telegram client shows any way to locate a message by
  content if `message_id` were absent (search by title, by hashtag) and how reliable it is.

Result: NOT RUN

## V8 — Failure path

Prepare a publishable notice first, as in V3: remove one notice key from the state file so this run
actually sends a Telegram request. If the state is already seeded and unchanged, the invalid token is
not exercised and this item is NOT RUN.

Put a deliberately invalid token and the test chat id in the local env file (root `.env` or the
`APT_ENV_FILE` path) and run it without printing the file:

```sh
python3 apt_cron.py
```

Expected: exit code `1`, one stderr line beginning `error:`, no traceback, and the token value not
printed (`redact_credentials`, `apt_cron.py:540-542`; handler `:620`). Also check:

```sh
APT_PAGE_SIZE=bogus python3 apt_cron.py --dry-run
```

Expected: exit code `2` with an argparse usage message. Run the no-credential case with the
variables explicitly unset so a previously sourced file cannot mask it:

```sh
env -u TELEGRAM_BOT_TOKEN -u TELEGRAM_CHAT_ID python3 apt_cron.py
```

Expected: exit code `2` and the message about `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`
(`apt_cron.py:586-589`). The invalid-page-size case above remains a separate configuration check and
does not test credentials, because `--dry-run` does not require them.
With `--refresh-index` and no credentials the same run must instead succeed without contacting
Telegram (`apt_cron.py:615-616`).

Result: NOT RUN

## V9 — Record and hand off

- [ ] Every item above is PASS, or FAIL with an owner and a ticket.
- [ ] Evidence captured: the message text, the document names, the largest PDF size, and the exit
      codes of V1, V2, V8.
- [ ] `docs/adr/0006-notification-format-and-channel.md` records items 1-5 as accepted; item 6
      (format sign-off) moves from open to accepted only after V4, V5, V6 and V7 are answered.
- [ ] Test credentials removed from the machine after the check; the local env file deleted, no
      token written into this file or any commit.

Result: NOT RUN

## Known limits of this checklist

- It validates one Telegram client on one platform; another client (mobile, web, desktop) can render
  hashtags, previews and documents differently.
- It cannot prove long-term source availability or that the source keeps returning the same PDF URLs.
- It does not exercise schedule, secret storage or failure alerting: those are ADR 0003 and
  ADR 0007 parts 4-5.
