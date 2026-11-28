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
  messages and send documents. This was the historical setup for this checklist, not a current
  second publication surface.
- A dedicated bot token and chat id for the historical validation check, obtained and owned as follows:
  - **Classification.** Under [ADR 0014](../adr/0014-production-credential-override-and-destination-channel.md)
    the historical validation chat is the Destination channel for GitHub Actions and the separate
    Validation channel is retired. This checklist remains historical validation evidence.
  - **Token and chat owner.** Accepted: the repository operator supplies these values through
    a gitignored env file such as `.env.test`, never on a command line that lands in shell history.
    The file must be mode `0600` and is selected with `APT_ENV_FILE`. The test values belong only in
    `APT_TEST_TELEGRAM_BOT_TOKEN` and `APT_TEST_TELEGRAM_CHAT_ID`, with
    `APT_TELEGRAM_PROFILE=test`. Production credential names are ignored in this profile.
    No credential is committed or written into this checklist, and base64 is not encryption.
- A clean state path and index directory for the check, so nothing touches production state:

```sh
export CHECK_DIR="$(mktemp -d)"
export APT_ENV_FILE=.env.test
export APT_TELEGRAM_PROFILE=test
export APT_STATE_PATH="$CHECK_DIR/state/notices.json"
export APT_INDEX_DIR="$CHECK_DIR/public"
```

Record every result as PASS, FAIL or NOT RUN. A FAIL is only acceptable with a named owner and a
follow-up ticket.

**Historical scope.** The PASS results below were recorded on 2026-11-26 against the plain-text
message format, before the current HTML format (ADR 0009), before `sent_messages`, before
`--backfill` and before the all-attachment contract. They do not validate the current tree. V2, V4
and V5 must be rerun because the state schema, message layout, archive mode and attachment contract
changed.

## V1 — Read-only dry run

```sh
python3 apt_cron.py --dry-run
```

Expected: exit code `0`; a single JSON line such as `{"dry_run": true, "notices": <N>,
"published": 0}`; **no** file created at `APT_STATE_PATH` and **no** index directory created.

Result: PASS (historical plain-text run; the read-only path is unchanged)

## V2 — First live run seeds state without publishing

Put the dedicated test bot token and chat id in the gitignored `.env.test` named by
`APT_ENV_FILE`, using the two `APT_TEST_TELEGRAM_*` variable names. It must not be committed and
must not appear in shell history. The script loads the file itself; the profile must be `test`.

```sh
python3 apt_cron.py
```

Expected: exit code `0`; `"published": 0`; `$APT_STATE_PATH` created with `version`, `notices`,
`attachments`, `sent_documents` and `sent_messages`; `index.json`, `index.md` and `index.html` created
in `$APT_INDEX_DIR`; **no** message in the channel.

Result: HISTORICAL PASS against a state schema without `sent_messages`; rerun required for the
current schema.

## V3 — Publish one notice

The V3 and V4 steps are historical procedures. Rerun them only under explicit operator authorization
for a Destination-channel publication; ADR 0014 classifies the chat as production and does not
authorize publication by itself.

Make one already-seeded notice publishable again. For that key, remove it from `notices` and
`sent_messages`, and remove every `sent_documents` entry whose value equals the key. Keep the rest
of the JSON intact, then repeat the V2 command. Removing only `notices` leaves `sent_messages` and
`sent_documents` able to suppress the message and uploads.

Expected: one HTML-formatted message plus one document message for the published PDF and every
downloadable attachment for that notice; `sent_documents` gains one entry per document URL; index
files regenerated.

Result: HISTORICAL PASS for the previous plain-text format; current HTML execution is not recorded.

## V4 — Message rendering and official link

Check against the message from V3:

1. The first line is a bold headline and distinguishes new, updated, expired and archive-backfill
   notices, with precedence updated, expired, archived, new. Format source: `format_message` and
   `_act_headline` in `apt_cron.py`.
2. The second line is the underlined identity `<u>Atto <number>/<year></u>`.
3. The labelled official, PDF and attachment links follow the identity when documents exist. The
   remaining visible lines are the translated title, publication, expiry and optional document dates,
   the category and sector hashtags, then the status. This order is asserted by
   `FormatMessageTest.test_formats_a_readable_html_message`.
4. Non-empty public source fields not shown in the visible block appear as `Label: value` lines
   inside one expandable `<blockquote expandable>` (ADR 0005) while the 4096-character budget allows
   it; long quotes may be clipped as documented in `README.md`. When the source has no expiry, the
   quote starts with the tested Italian unknown-expiry marker.
5. Telegram renders the tags from the sender's `parse_mode: HTML` payload, with no literal tags
   visible in the client. Dynamic values, hashtags and URLs are escaped before rendering, so source
   `_` or `*` characters remain data rather than sender markup.
6. `Categoria:` and `Settore:` render as single-token hashtags (`#Category_With_Underscore`) and
   Telegram turns them into tappable/searchable hashtags.
7. `Atto ufficiale` opens the official APT detail page in a browser (the exact notice, not the
   register home page), and the link is worth a preview card only if that is acceptable.
8. Screen-reader order is linear: headline, identity, links, visible fields, then the expandable quote.

Result: HISTORICAL PASS for the plain-text format; **NOT RUN for the current HTML format**. The
repository operator must rerun V4 against the Destination channel under ADR 0014 before the release
gate can pass. The retired private Validation channel is not a valid destination for that rerun.

## V5 — Document delivery as uploaded bytes

1. A document message arrives for the published PDF (`documentoUnico`) and every downloadable
   attachment, including non-PDF files.
2. Opening each document works. The script fetches each source file into memory and uploads the bytes
   in a multipart `sendDocument` body (`publish_document` and `multipart_body` in `apt_cron.py`,
   transport `UrllibTransport.send_document`), so Telegram no longer fetches the source URL
   and an expiring source URL shows up as a fetch error in the run, not as a document Telegram could
   not open. This replaces the previous URL hand-off, which failed live with
   `400 Bad Request: failed to get HTTP URL content`.
3. File name and type are those of the source (`notice.pdf` or `attachment.png` style) or
   `document.pdf` when the source URL carries no file name (`document_filename`); multipart content
   type is inferred from the filename and falls back to `application/octet-stream`.
4. The largest real notice PDF is accepted.
   - **PDF size check.** The upload is bounded at 50 MB (`DOCUMENT_MAX_BYTES`).
     Recorded largest observed PDF: 9.55 MB. A PDF above the bound is rejected before upload and
     fails the run with exit code `1`, as the unit suite proves for the boundary.
5. Non-PDF attachments are sent when the source exposes a safe downloadable URL. Confirm a selected
   notice with a non-PDF attachment arrives in the chat, retains its source filename/type, and is
   recorded in `sent_documents`. If no such notice exists, record the item as NOT RUN with the
   repository operator as owner and repeat it when one becomes available.

Result: HISTORICAL PASS for PDF upload only; current all-attachment delivery is NOT RUN.

## V6 — Caption bound

The caption identifies the act by number and year and is bounded to 1024 characters by
`document_caption`. The message text remains bounded separately at 4096 characters. The caption
carries no title, so a long title cannot affect it; if a notice with an unusually long act number is
available, confirm the truncated caption is accepted.

1. Confirm captions arrive intact and identify the act unambiguously.
2. Confirm no title text appears in any caption.
3. **Caption decision.** Accepted and implemented. This item is PASS only after a caption has been
   observed in the private channel.

Result: HISTORICAL PASS for the plain-text run; the caption path is unchanged.

## V7 — Message identifier decision

`publish_message` and `publish_document` return Telegram's `result` object, which contains
`message_id`; `run_once` discards both. Nothing in `$APT_STATE_PATH`
therefore identifies a published message.

- **Store `message_id`?** Accepted decision: no. ADR 0004 keeps messages as the permanent record and
  performs no deletion, so state does not need message identifiers.
- Observation for the record: note whether the Telegram client shows any way to locate a message by
  content if `message_id` were absent (search by title, by hashtag) and how reliable it is.

Result: PASS (historical plain-text run; message identifiers are unused by design)

## V8 — Failure path

Prepare a publishable notice first, as in V3. For one selected notice key, remove it from `notices`
and `sent_messages`, and remove every `sent_documents` entry whose value equals that key. Removing
only `notices` is insufficient because `sent_messages` suppresses the text message and
`sent_documents` suppresses uploads. Alternatively use a genuinely new notice. If no publishable
notice exists, the invalid-token case is NOT RUN.

Put a deliberately invalid token and the Destination chat id in a temporary env file outside the
repository, for example `/tmp/apt-invalid.env`, using the `APT_TEST_TELEGRAM_*` names. Do not overwrite
`.env.test`; delete the temporary file after the check. Run it without printing the file:

```sh
APT_ENV_FILE=/tmp/apt-invalid.env APT_TELEGRAM_PROFILE=test python3 apt_cron.py
```

Expected: exit code `1`, one stderr line beginning `error:`, no traceback, and the token value not
printed (`redact_credentials`; the exception handler in `main`). Also check:

```sh
APT_PAGE_SIZE=bogus python3 apt_cron.py --dry-run
```

Expected: exit code `2` with an argparse usage message. Run the no-credential case with the
variables explicitly unset so a previously sourced file cannot mask it:

```sh
env -u APT_TEST_TELEGRAM_BOT_TOKEN -u APT_TEST_TELEGRAM_CHAT_ID \
  APT_TELEGRAM_PROFILE=test APT_ENV_FILE=/nonexistent python3 apt_cron.py
```

Expected: exit code `2` and the message about `APT_TEST_TELEGRAM_BOT_TOKEN` /
`APT_TEST_TELEGRAM_CHAT_ID` (the credential guard in `main`). The invalid-page-size case above remains a separate configuration
check and does not test credentials, because `--dry-run` does not require them.
With `--refresh-index` and no credentials the same run must instead succeed without contacting
Telegram (`refresh_index` in `apt_cron.py`).

Result: HISTORICAL PASS for the plain-text run; rerun against the current tree.

## V9 — Record and hand off

- [ ] Current release candidate has every core item at PASS, or an accepted non-applicable result
      with a named owner. V2, V3, V4, V5 and V8 must be rerun against the current release
      candidate for the current schema, HTML format, all-attachment contract and configuration.
- [x] Historical evidence captured: the message text, document names, largest PDF size (9.55 MB),
      and exit codes of V1, V2 and V8.
- [ ] The current HTML rendering and all-attachment delivery are accepted in release evidence after
      the new V4/V5 runs.
- [x] The local env file was deleted after the historical check; no token was written into this file
      or any commit.

Result: HOLD for the current release candidate. The repository operator must rerun V2, V3, V4, V5
and V8, update this record and rotate the token that was pasted into the conversation before production.

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
- Historical V4: the private channel rendered the full plain-text field set, category and sector hashtags, and the official detail link. This does not validate the current HTML format.
- V5: both PDF documents arrived with bounded captions. The largest observed PDF was 9.55 MB, below the 50 MB bound.
- V6: captions were bounded and identified the act by number and year.
- V8: an invalid token exited `1` with one redacted error line; a bad page size exited `2`; missing credentials exited `2`.
- GitHub Actions `ci.yml` was green on the final pushed commit.
- The token used for the test was pasted into the conversation and must be rotated before any production use.
