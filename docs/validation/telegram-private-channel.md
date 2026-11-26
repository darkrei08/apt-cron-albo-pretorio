# Telegram private-channel validation

Manual checklist for issue #10. It closes the gap recorded in `README.md`: Telegram delivery had
been exercised only partially before this run (a live message and `getChat` succeeded, a document
sent by URL failed with HTTP 400), and `docs/adr/0006-notification-format-and-channel.md` could not
be fully accepted until the rendered result was observed.

Everything here ran in a **private test channel**, never in production. No automated test in this
repository contacts Telegram (`tests/` uses fake transports). The operator supplied the test
credentials through a local env file (`APT_ENV_FILE`), and the recorded results are below.

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

Result: PASS

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

Result: PASS

## V3 — Publish one notice

Make one already-seeded notice look new by removing its key from the `notices` map in
`$APT_STATE_PATH` (edit the JSON; keep the rest of the file intact), then repeat the V2 command.

Expected: one plain-text message plus one document message per official PDF for that notice;
`sent_documents` gains one entry per document URL; index files regenerated.

Result: PASS

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

Result: PASS

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
     Recorded largest observed PDF: 9.55 MB. A PDF above the bound is rejected before upload and
     fails the run with exit code `1`, as the unit suite proves for the boundary.
5. Non-PDF attachments are never sent. The local unit test proves that `fetch_attachments` keeps only
   PDF MIME types and its fixture includes an `image/png` entry. In the live channel this item remains
   NOT RUN unless a real notice with a non-PDF attachment is observed and no document message appears
   for it (`apt_cron.py:217-240`). If no such notice exists during validation, mark this item
   NOT RUN and record it as accepted non-applicable with the repository operator as named owner; the
   release gate allows that disposition explicitly.

Result: PASS (PDF upload); V5.5 NOT RUN / accepted non-applicable: no live non-PDF attachment was observed in the selected notice

## V6 — Caption bound

The caption identifies the act by number and year and is bounded to 1024 characters by
`document_caption` (`apt_cron.py:426-430`). The message text remains bounded separately at 4096
characters. The caption carries no title, so a long title cannot affect it; if a notice with an
unusually long act number is available, confirm the truncated caption is accepted.

1. Confirm captions arrive intact and identify the act unambiguously.
2. Confirm no title text appears in any caption.
3. **Caption decision.** Accepted and implemented. This item is PASS only after a caption has been
   observed in the private channel.

Result: PASS

## V7 — Message identifier decision

`publish_message` and `publish_document` return Telegram's `result` object, which contains
`message_id`; `run_once` discards both (`apt_cron.py:376-412`). Nothing in `$APT_STATE_PATH`
therefore identifies a published message.

- **Store `message_id`?** Accepted decision: no. ADR 0004 keeps messages as the permanent record and
  performs no deletion, so state does not need message identifiers.
- Observation for the record: note whether the Telegram client shows any way to locate a message by
  content if `message_id` were absent (search by title, by hashtag) and how reliable it is.

Result: PASS

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
env -u TELEGRAM_BOT_TOKEN -u TELEGRAM_CHAT_ID APT_ENV_FILE=/nonexistent python3 apt_cron.py
```

Expected: exit code `2` and the message about `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`
(`apt_cron.py:586-589`). The invalid-page-size case above remains a separate configuration check and
does not test credentials, because `--dry-run` does not require them.
With `--refresh-index` and no credentials the same run must instead succeed without contacting
Telegram (`apt_cron.py:615-616`).

Result: PASS

## V9 — Record and hand off

- [x] Every item above is PASS, or an accepted non-applicable with a named owner.
- [x] Evidence captured: the message text, the document names, the largest PDF size (9.55 MB), and
      the exit codes of V1, V2 and V8.
- [x] `docs/adr/0006-notification-format-and-channel.md` records all items as accepted after V4,
      V5, V6 and V7 were answered.
- [x] The local env file was deleted after the check; no token was written into this file or any
      commit.

Result: PASS with one residual action: rotate the token that was pasted into the conversation

## Known limits of this checklist

- It validates one Telegram client on one platform; another client (mobile, web, desktop) can render
  hashtags, previews and documents differently.
- It cannot prove long-term source availability or that the source keeps returning the same PDF URLs.
- It does not exercise schedule, secret storage or failure alerting: those are ADR 0003 and
  ADR 0007 parts 4-5.

## Evidence from the 2026-11-26 run

- V1: `python3 apt_cron.py --dry-run` exited `0` with `{"dry_run": true, "notices": 14, "published": 0}`.
- V2: the first live run exited `0`, seeded 14 notices, wrote state and the three index files, and published nothing.
- V3: after removing one state key, the run exited `0`, published one notice and uploaded two PDF documents. The state recorded two sent document URLs.
- V4: the private channel rendered the full plain-text field set, category and sector hashtags, and the official detail link.
- V5: both PDF documents arrived with bounded captions. The largest observed PDF was 9.55 MB, below the 50 MB bound.
- V6: captions were bounded and identified the act by number and year.
- V8: an invalid token exited `1` with one redacted error line; a bad page size exited `2`; missing credentials exited `2`.
- GitHub Actions `ci.yml` was green on the final pushed commit.
- The token used for the test was pasted into the conversation and must be rotated before any production use.
