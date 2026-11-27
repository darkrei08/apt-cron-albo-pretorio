# cron-albo-pretorio

Publishes new and changed notices from the official APT Basilicata public notices register to a Telegram channel, and keeps a public index of the current notices published from this repository. The job uses only Python's standard library and calls no LLM.

The repository owns two publication surfaces: the Telegram destination and the committed `public/index.*` files. It does not archive official documents, delete channel messages, or send anything unless a publication command is run.

The Wayfinder map is [APT public notices crawler and notification plan](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1). It records the operator decisions and the linked ticket graph. The current dependency order is in [docs/wayfinder-execution-order.md](docs/wayfinder-execution-order.md). Decision records are in [docs/adr/](docs/adr/), and the live Telegram validation checklist is in [docs/validation/telegram-private-channel.md](docs/validation/telegram-private-channel.md). The operator-only protected-host checklist is in [docs/operations/operator-handoff.md](docs/operations/operator-handoff.md).

## How it works

1. Reads the official APT Basilicata public notices API once per run.
2. Extracts every public field the register exposes for an act: 42 source keys covering title, category, sector, publication dates, year, notice number, status, the procedural responsible person and the remaining register fields, excluding only internal account, login, audit and remaining responsible-person keys.
3. Reads the official published PDF and every downloadable attachment link from the source attachment endpoint and caches them in local state.
4. Compares SHA-256 fingerprints with local state.
5. Sends a short Telegram HTML message with the official links, then uploads the published PDF and every downloadable attachment for new or changed notices: the bytes are fetched into memory and posted in multipart `sendDocument` bodies, bounded at 50 MB and never written to disk. Each document URL is sent once; the caption identifies the act number and year.
6. Regenerates `public/index.json`, `public/index.md` and `public/index.html` from the same published fields.
7. Saves state incrementally after each successful message and document, and commits a notice fingerprint only after all its documents have uploaded.
8. A scheduled GitHub Actions workflow refreshes the index hourly and commits only changed `public/index.*` files.

Messages are always published oldest to newest, so within one run the newest act is the last message in
the chat. The index keeps the source order, newest first.

The message is sent with `parse_mode` `HTML` ([ADR 0009](docs/adr/0009-readable-telegram-act-message.md)).
A bold headline, the underlined act number and year, the title, the publication and expiry dates, the
procedural responsible person, the document date when the source has one, the category and sector
hashtags, the status and the labelled official, PDF and attachment links are visible. The headline uses one of four fixed Italian labels for new, updated,
expired or archived acts. Precedence is updated, expired, archived, new. The state comes from fields
already published plus the run mode, so the headline adds no source field and needs no state migration.
The renderer places remaining non-empty public fields in an expandable `<blockquote>` when the
message budget permits; normal messages stay short while the 4096-character bound may clip trailing
quote lines for pathological input. When the
source has no expiry date, the quote uses the tested Italian unknown-expiry marker. Every dynamic value is HTML-escaped, and the rendered HTML is bounded to 4096
characters.

The first run seeds state from the current source without publishing. This avoids an initial channel flood.

State tracks the fingerprint of the last sent text message separately from the notice fingerprint. If a run stops after the message, the next unchanged run uploads only the missing document URLs and sends no second message. A legacy state seeds that sent-message fingerprint only for notices whose document was already uploaded, so migration does not duplicate text messages or upload documents for acts that were only seeded.

Fingerprints cover every published field, so a deploy that changes the field set changes every fingerprint. Move or delete `APT_STATE_PATH` once before the first run after such a change; otherwise that run publishes every current notice as an update.

The publication boundary is fixed by [ADR 0005](docs/adr/0005-publication-boundary.md) and [ADR 0011](docs/adr/0011-publish-procedural-responsible.md): there are two publication surfaces, the Telegram channel and the committed `public/index.*`, and both carry the same field set. Every public field of an act is published, including `Titolo`, `Settore` and `Responsabile` (`cntResponsabileProcedimento`); the internal account, login, audit and remaining responsible-person keys (`cntAutore*`, `cntResponsabile*Login`, `cntResponsabilePubblicazione*`, `ultimaAnnotazione*`) never leave the source projection.

The source API exposes notice discovery only as a read-only `POST /api/pap/filter`, confirmed by the [official OpenAPI document](https://siopi.publisys.it/kapi-aptbasilicata/v3/api-docs). The user authorized that POST. The published PDF and every downloadable attachment link are read with `GET /api/pap/files/{id}`. Publishing uses `POST /sendMessage` and `POST /sendDocument` with document bytes in multipart bodies.

The implementation is tracked in [Publish only new APT notices with PDF links and generated index](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/8).

During planning, the [`api-anything`](https://github.com/goodnight000/api-anything) skill was used to inspect the site's own traffic and identify the source request. The runtime script does not call `api-anything` or require Node. [`fast-anything`](https://github.com/EL4CTEO/fast-anything) is recorded in the map as a future performance aid, not an extraction dependency.

## Requirements

- Python 3.11 or newer
- A Telegram bot with permission to post in the destination channel
- Write access to a local state directory

No third-party Python package is required.

## Configuration

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `APT_TELEGRAM_PROFILE` | no | `production` | Destination profile: `production` or `test`; selects which credential names are read |
| `TELEGRAM_BOT_TOKEN` | yes in `production` mode, unless `--dry-run` or `--refresh-index` | none | Production bot token; only from the environment or a protected env file |
| `TELEGRAM_CHAT_ID` | yes in `production` mode, unless `--dry-run` or `--refresh-index` | none | Production channel or chat identifier |
| `APT_TEST_TELEGRAM_BOT_TOKEN` | yes in `test` mode, unless `--dry-run` or `--refresh-index` | none | Test bot token; never reused as production credentials |
| `APT_TEST_TELEGRAM_CHAT_ID` | yes in `test` mode, unless `--dry-run` or `--refresh-index` | none | Test channel or chat identifier |
| `APT_SOURCE_URL` | no | `https://siopi.publisys.it/kapi-aptbasilicata/api/pap/filter` | API base URL, without query string |
| `APT_NATURE_ID` | no | `200152` | Notice category identifier from the source |
| `APT_PAGE_SIZE` | no | `20` | Number of notices requested per run |
| `APT_DETAIL_BASE` | no | `https://siopi.publisys.it/sito-aptbasilicata/albo-pretorio/dettaglio` | Base URL used to build official detail links |
| `APT_ATTACHMENTS_BASE` | no | `https://siopi.publisys.it/kapi-aptbasilicata/api/pap/files` | Base URL for official PDF and attachment link lookup |
| `APT_INDEX_DIR` | no | `public` | Directory receiving generated index files |
| `APT_STATE_PATH` | no | `state/notices.json` | File holding fingerprints, cached document links and sent document URLs |
| `APT_ENV_FILE` | no | `.env` in the repository root | Alternative `KEY=VALUE` file loaded before any setting |

The generated `state/` directory and Telegram credentials are not committed.

## Destination profiles and where secrets belong

The default profile is `production`. Set `APT_TELEGRAM_PROFILE=test` only for isolated validation in
a private test channel. The program reads only the credential names selected by the profile; test
credentials never fall back to production credentials, and an unknown profile exits with code `2`.

| Profile | Required variables | Where the operator writes them |
| --- | --- | --- |
| `production` | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Protected file `/etc/apt-cron/albo.env`, mode `0600`, or a gitignored local `.env` for development. The cron job points `APT_ENV_FILE` at the protected file. |
| `test` | `APT_TEST_TELEGRAM_BOT_TOKEN`, `APT_TEST_TELEGRAM_CHAT_ID` | A separate gitignored local file such as `.env.test` (already ignored by `.env.*`), pointed to by `APT_ENV_FILE`, with mode `0600`. Use a dedicated bot and private test channel. |

Never put a token or chat id in a shell command, crontab line, issue, log, commit or this README.
The script redacts the selected token in its error output. A token pasted into a chat must be treated
as exposed and rotated before use.

Configuration can come from a local `KEY=VALUE` file instead of the shell environment. Before
reading any setting the script loads `$APT_ENV_FILE`, or `.env` in the repository root when that
variable is unset, and it never overrides a variable that is already set, so a real environment
value always wins. Blank lines, `#` comments, an optional `export ` prefix and surrounding quotes are
accepted. `.env` and `.env.*` are gitignored, so a local env file is never committed; the variable
names and placeholders are documented in the configuration table above. Do not store a
base64-encoded credential: base64 is not encryption, and
an encoded token in the repository or in Git history is a leaked token.

## Test message template

The renderer sends HTML through `sendMessage` with `parse_mode: HTML`. The synthetic shape below is
its structural template; real values are escaped and clipped before sending:

```html
<b>Nuovo atto APT Basilicata</b>
<u>Atto &lt;number&gt;/&lt;year&gt;</u>
<a href="https://.../dettaglio/&lt;id&gt;/dettaglio-pap">Atto ufficiale</a>
<a href="https://.../download/unico/...">PDF ufficiale</a>
<a href="https://.../download/single/...">Allegato</a>
<b>Titolo:</b> &lt;title&gt;
<b>Pubblicato il:</b> &lt;dd/mm/yyyy&gt;
<b>Scade il:</b> &lt;dd/mm/yyyy&gt;
<b>Responsabile:</b> &lt;responsible&gt;
#Categoria_Con_Sottolineature #SETTORE
<b>Stato:</b> &lt;status&gt;
<blockquote expandable>Label: value</blockquote>
```

The first line changes to `Atto aggiornato`, `Atto scaduto` or `Atto archiviato` according to the
state of the notice. Tests in `tests/test_apt_cron.py` use fake transports and synthetic notices; they
never contact Telegram. Use `APT_TELEGRAM_PROFILE=test` and isolated state/index paths for any live
private-channel check.

## Run

Simulate a read without publishing or writing state:

```sh
python3 apt_cron.py --dry-run
```

Rebuild `public/index.*` from the current source without credentials and without touching state. This
is the path the hourly workflow uses:

```sh
python3 apt_cron.py --refresh-index
```

Publish the whole published archive, not just the current window, oldest act first and with no index
rebuild. This is a one-off recovery path: it reads every page the source holds and sends a message
when the act's `sent_messages` fingerprint does not match the current fingerprint. Acts seeded by a
normal run are still published because seeding fills `notices` but leaves `sent_messages` empty. It
publishes nothing on a rerun of unchanged acts. Archived acts that
no longer expose documents still produce their metadata message; only the document messages are omitted.

```sh
python3 apt_cron.py --backfill --dry-run   # read the archive and report without sending
python3 apt_cron.py --backfill            # publish it, credentials required
```

### CLI command reference

| Command | Credentials | Effect |
| --- | --- | --- |
| `python3 apt_cron.py --dry-run` | none | Reads the source and reports counts; no state and no index write. |
| `python3 apt_cron.py --refresh-index` | none | Rebuilds `public/index.*` only; no state and no Telegram traffic. |
| `python3 apt_cron.py --backfill --dry-run` | none | Reads the whole archive and reports counts without publishing. |
| `python3 apt_cron.py --backfill` | selected profile | Publishes the archive oldest first; no index rebuild. |
| `python3 apt_cron.py` | selected profile | Publishes new or changed notices in the current window and rebuilds the index. |

Set the profile and the environment file outside the command that contains secrets. For example,
run a local test check with `APT_ENV_FILE=.env.test APT_TELEGRAM_PROFILE=test python3 apt_cron.py --backfill --dry-run`;
the dry run still sends nothing.

Publish new or changed notices with a local credentials file inside the repository. The script
loads it itself, so no shell sourcing is needed and no credential reaches shell history:

```sh
touch .env
chmod 600 .env
$EDITOR .env
python3 apt_cron.py
```

Publishing from a protected environment file outside the repository, readable only by the service
user, is equally supported. Point `APT_ENV_FILE` at it to have the script load it:

```sh
export APT_ENV_FILE=/etc/apt-cron/albo.env
export APT_TELEGRAM_PROFILE=production
python3 apt_cron.py
```

Hourly cron example:

```cron
CRON_TZ=Europe/Rome
MAILTO=operator@example.invalid
0 * * * * cd /path/to/cron-albo-pretorio && TZ=Europe/Rome APT_ENV_FILE=/etc/apt-cron/albo.env APT_TELEGRAM_PROFILE=production /usr/bin/flock -n /tmp/apt-cron.lock /usr/bin/python3 apt_cron.py
```

Customize the cron entry by replacing `/path/to/cron-albo-pretorio` with the installed checkout,
`/tmp/apt-cron.lock` with the protected lock path, `operator@example.invalid` with the real alert
mailbox, and the environment-file path with the protected production file. Never add token or chat
values to the crontab line. Set `CRON_TZ` and `TZ` to `Europe/Rome`, keep `APT_TELEGRAM_PROFILE=production`
explicit, and set `MAILTO` so cron mails the redacted failure output to the maintainer. Do not redirect
cron output to `cron.log` if `MAILTO` is the alert path; add a separate logging handler when persistent
logs are required. A test profile must never be installed in the hourly cron entry.

The committed index is refreshed by `.github/workflows/update-index.yml` every hour and on manual
dispatch. The workflow needs no Telegram credentials: it runs `apt_cron.py --refresh-index` and
commits only changed `public/index.json`, `public/index.md` and `public/index.html` with the
repository `GITHUB_TOKEN`.

## Download section

**What is downloaded:** the JSON notice list, the JSON attachment-link list, and the bytes of the published PDF plus every downloadable attachment. Document bytes are fetched into memory, sent to Telegram in multipart `sendDocument` bodies and never written to disk. Telegram does not fetch the source URL itself (that failed live with `400 Bad Request: failed to get HTTP URL content`). Any document above 50 MB is rejected before the upload and fails the run.

**Where it is downloaded from:** `https://siopi.publisys.it/kapi-aptbasilicata/api/pap/filter?page=0&size=<APT_PAGE_SIZE>` by read-only POST, and `https://siopi.publisys.it/kapi-aptbasilicata/api/pap/files/{id}` by GET for notices not already cached in state. Requests use `User-Agent: apt-cron/1.0` and a 20-second timeout. With `--backfill` the same POST is sent without the two publication-window criteria and once per page, up to the page count the source reports.

**When:** once per invocation. The intended schedule is hourly, but scheduling is the operator's choice and is not performed by the script.

**Where it is saved:** raw responses and document bytes stay in memory. SHA-256 fingerprints, cached official document URLs and URLs already sent to Telegram are written to `APT_STATE_PATH` (`state/notices.json` by default). Generated public index files are written to `APT_INDEX_DIR` (`public/` by default) and are committed to this repository by the hourly workflow, so the repository and any hosting of it are a publication surface. No document bytes are written. The field allowlist publishes every public field of an act, so the free-text fields (`Titolo`, `Categoria`, `Settore`, `Proponente`, `Autorita mittente`, notes) are published text; it excludes only the internal account, login, audit and remaining responsible-person keys listed above.

**What the project does:** reads public metadata and official document links, publishes a short message followed by the published PDF and every downloadable attachment, records fingerprints and sent URLs, and regenerates the published index from the same allowed fields. It does not copy official documents into the repository or into a local archive.

**What the operator is responsible for:** providing credentials through a gitignored local `.env`, an
`APT_ENV_FILE` file, or the protected environment file, choosing the state and index paths, scheduling
the job, protecting logs, checking that the Telegram bot has the right permissions, monitoring failures, and answering data-rights requests. Withdrawal is not automated: a withdrawn notice stays in the channel as the permanent record and leaves the index on the next hourly refresh (ADR 0004). Publishing a key that the allowlist excludes (an internal account, login, audit or remaining responsible-person field) would require a new Wayfinder decision; every other public field of an act is already published, including the procedural responsible person under ADR 0011. After a change to the field set, reseed state once as described above.

**Not verified:** no production cron schedule was installed. A live `sendMessage` and multipart `sendDocument` both succeeded in the private validation channel: one notice produced one text message and two documents; the historical fixture contained PDFs only and did not validate non-PDF attachments. That validation predates the current HTML message format, so live HTML rendering and live all-attachment delivery remain unverified until the private checklist is rerun; their simulated behavior is covered by unit tests. A `sendDocument` that passed the official PDF URL failed earlier with `400 Bad Request: failed to get HTTP URL content`, which is why documents are now uploaded as bytes. The `--refresh-index` path was exercised against the live source; long-term source availability, workflow longevity and rendering in other Telegram clients remain unverified.

## Production checks

- `APT_PAGE_SIZE` must be a positive integer; invalid values exit with status 2.
- Runtime failures print a single redacted line, so `TELEGRAM_BOT_TOKEN` is not written to logs.
- Telegram HTTP `429` responses are retried with the `Retry-After` header or the JSON
  `parameters.retry_after` body, up to six attempts and a 60-second cap per wait. Transient Telegram
  connection resets are retried with exponential backoff up to the same bound; non-Telegram requests
  are not retried.
- Telegram HTML is bounded to 4096 characters; the expandable quote is clipped and, only if the visible part alone overflows, its trailing lines are dropped. Tags stay balanced, so Telegram accepts the message.
- Every dynamic value is escaped with `html.escape(..., quote=True)` before it reaches the HTML message.
- Document captions state the act number and year and are bounded to 1024 characters.
- `--refresh-index` needs no Telegram credentials, writes no state and sends nothing.
- `--backfill` reads the whole archive page by page, publishes oldest to newest, writes no index and
  keeps state per successful publish, so an interrupted backfill resumes on the next run. It cannot be
  combined with `--refresh-index`.
- A failed document upload leaves the notice fingerprint uncommitted; the next unchanged run retries only
  the missing document URLs and never resends the text message.
- Cached document links are refreshed when a notice's source metadata changes; unchanged notices reuse their
  cached links.
- `.github/workflows/ci.yml` compiles and runs the full test suite on pushes to `main` and pull requests;
  `.github/workflows/update-index.yml` refreshes the committed index hourly.

## Tests

Run the full suite:

```sh
python3 -m unittest discover -s tests -v
```

The tests use local fixtures and fake transports; they do not contact APT Basilicata or Telegram. They cover the published outputs (Telegram HTML, captions, index files), the exact message layout, the four state headlines and their precedence, HTML escaping of hostile values, the unknown-expiry note, the multipart document upload and its 50 MB bound, the exact included and excluded field sets, the unchanged dedupe behavior, PDF and non-PDF attachments, partial document-failure recovery, the credential-free refresh path, the archive criteria and pagination, the oldest-to-newest publication order and the `--backfill` path.
