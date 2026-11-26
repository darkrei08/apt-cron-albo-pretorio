# cron-albo-pretorio

Publishes new and changed notices from the official APT Basilicata public notices register to a Telegram channel, and keeps a public index of the current notices published from this repository. The job uses only Python's standard library and calls no LLM.

The Wayfinder map is [APT public notices crawler and notification plan](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1). It records the operator decisions and the linked ticket graph. The current dependency order is in [docs/wayfinder-execution-order.md](docs/wayfinder-execution-order.md). Decision records are in [docs/adr/](docs/adr/), and the live Telegram validation checklist is in [docs/validation/telegram-private-channel.md](docs/validation/telegram-private-channel.md).

## How it works

1. Reads the official APT Basilicata public notices API once per run.
2. Extracts every public field the register exposes for an act: 41 source keys covering title, category, sector, publication dates, year, notice number, status and the remaining register fields, excluding only internal account, login, audit and responsible-person keys.
3. Reads official PDF links from the source attachment endpoint and caches them in local state.
4. Compares SHA-256 fingerprints with local state.
5. Sends a short Telegram HTML message with the official links, then uploads each official PDF for new or changed notices: the bytes are fetched into memory and posted in a multipart `sendDocument` body, bounded at 50 MB and never written to disk. Each PDF URL is sent once; the document caption identifies the act number and year.
6. Regenerates `public/index.json`, `public/index.md` and `public/index.html` from the same published fields.
7. Saves state incrementally after each successful publish.
8. A scheduled GitHub Actions workflow refreshes the index hourly and commits only changed `public/index.*` files.

Messages are always published oldest to newest, so within one run the newest act is the last message in
the chat. The index keeps the source order, newest first.

The message is sent with `parse_mode` `HTML` ([ADR 0009](docs/adr/0009-readable-telegram-act-message.md)).
A bold headline, the underlined act number and year, the title, the publication and expiry dates, the
document date when the source has one, the category and sector hashtags, the status and the labelled
official and PDF links are visible. Every other non-empty public field sits in an expandable
`<blockquote>`, so the message stays short without dropping a field. When the source has no expiry
date the quote says `Scadenza: non nota`. Every dynamic value is HTML-escaped, and the rendered HTML is
bounded to 4096 characters.

The first run seeds state from the current source without publishing. This avoids an initial channel flood.

Fingerprints cover every published field, so a deploy that changes the field set changes every fingerprint. Move or delete `APT_STATE_PATH` once before the first run after such a change; otherwise that run publishes every current notice as an update.

The publication boundary is fixed by [ADR 0005](docs/adr/0005-publication-boundary.md): there are two publication surfaces, the Telegram channel and the committed `public/index.*`, and both carry the same field set. Every public field of an act is published, including `Titolo` and `Settore`; only the internal account, login, audit and responsible-person keys (`cntAutore*`, `cntResponsabileProcedimento*`, `cntResponsabilePubblicazione*`, `ultimaAnnotazione*`) never leave the source projection.

The source API exposes notice discovery only as a read-only `POST /api/pap/filter`, confirmed by the [official OpenAPI document](https://siopi.publisys.it/kapi-aptbasilicata/v3/api-docs). The user authorized that POST. PDF links are read with `GET /api/pap/files/{id}`. Publishing uses `POST /sendMessage` and `POST /sendDocument` with the PDF bytes in a multipart body.

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
| `TELEGRAM_BOT_TOKEN` | yes, unless `--dry-run` or `--refresh-index` | none | Bot token; only from the environment or a gitignored env file |
| `TELEGRAM_CHAT_ID` | yes, unless `--dry-run` or `--refresh-index` | none | Channel or chat identifier |
| `APT_SOURCE_URL` | no | `https://siopi.publisys.it/kapi-aptbasilicata/api/pap/filter` | API base URL, without query string |
| `APT_NATURE_ID` | no | `200152` | Notice category identifier from the source |
| `APT_PAGE_SIZE` | no | `20` | Number of notices requested per run |
| `APT_DETAIL_BASE` | no | `https://siopi.publisys.it/sito-aptbasilicata/albo-pretorio/dettaglio` | Base URL used to build official detail links |
| `APT_ATTACHMENTS_BASE` | no | `https://siopi.publisys.it/kapi-aptbasilicata/api/pap/files` | Base URL for official PDF link lookup |
| `APT_INDEX_DIR` | no | `public` | Directory receiving generated index files |
| `APT_STATE_PATH` | no | `state/notices.json` | File holding fingerprints, cached PDF links and sent document URLs |

The generated `state/` directory and Telegram credentials are not committed.

Configuration can come from a local `KEY=VALUE` file instead of the shell environment. Before
reading any setting the script loads `$APT_ENV_FILE`, or `.env` in the repository root when that
variable is unset, and it never overrides a variable that is already set, so a real environment
value always wins. Blank lines, `#` comments, an optional `export ` prefix and surrounding quotes are
accepted. `.env` and `.env.*` are gitignored; only `.env.example`, which holds variable names and
placeholders, is committed. Do not store a base64-encoded credential: base64 is not encryption, and
an encoded token in the repository or in Git history is a leaked token.

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
rebuild. This is a one-off recovery path: it reads every page the source holds, sends a message for
every act not yet in state, and publishes nothing on a rerun of unchanged acts. Archived acts that
no longer expose PDFs still produce their metadata message; only the document messages are omitted.

```sh
python3 apt_cron.py --backfill --dry-run   # read the archive and report without sending
python3 apt_cron.py --backfill            # publish it, credentials required
```

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
set -a
. /etc/apt-cron/albo.env
set +a
python3 apt_cron.py
```

Hourly cron example:

```cron
0 * * * * cd /path/to/cron-albo-pretorio && CRON_TZ=Europe/Rome TZ=Europe/Rome /usr/bin/flock -n /tmp/apt-cron.lock /bin/sh -c '. /etc/apt-cron/albo.env && exec /usr/bin/python3 apt_cron.py' >> cron.log 2>&1
```

Do not put literal credentials in shell history or crontab lines. The cron command above sources the
file outside the repository; with a repository-local `.env` the `/bin/sh -c` wrapper can simply be
`exec /usr/bin/python3 apt_cron.py`, because the script loads `.env` from its own directory. Set
`CRON_TZ` and `TZ` to `Europe/Rome` as in the example, and set `MAILTO` so a failed run reaches the
maintainer.

The committed index is refreshed by `.github/workflows/update-index.yml` every hour and on manual
dispatch. The workflow needs no Telegram credentials: it runs `apt_cron.py --refresh-index` and
commits only changed `public/index.json`, `public/index.md` and `public/index.html` with the
repository `GITHUB_TOKEN`.

## Download section

**What is downloaded:** the JSON notice list, the JSON attachment-link list, and the PDF bytes of each published official document. PDF bytes are fetched into memory, sent to Telegram in a multipart `sendDocument` body and never written to disk. Telegram does not fetch the source URL itself (that failed live with `400 Bad Request: failed to get HTTP URL content`). A PDF above 50 MB is rejected before the upload and fails the run.

**Where it is downloaded from:** `https://siopi.publisys.it/kapi-aptbasilicata/api/pap/filter?page=0&size=<APT_PAGE_SIZE>` by read-only POST, and `https://siopi.publisys.it/kapi-aptbasilicata/api/pap/files/{id}` by GET for notices not already cached in state. Requests use `User-Agent: apt-cron/1.0` and a 20-second timeout. With `--backfill` the same POST is sent without the two publication-window criteria and once per page, up to the page count the source reports.

**When:** once per invocation. The intended schedule is hourly, but scheduling is the operator's choice and is not performed by the script.

**Where it is saved:** raw responses and PDF bytes stay in memory. SHA-256 fingerprints, cached official PDF URLs and URLs already sent to Telegram are written to `APT_STATE_PATH` (`state/notices.json` by default). Generated public index files are written to `APT_INDEX_DIR` (`public/` by default) and are committed to this repository by the hourly workflow, so the repository and any hosting of it are a publication surface. No PDF bytes are written. The field allowlist publishes every public field of an act, so the free-text fields (`Titolo`, `Categoria`, `Settore`, `Proponente`, `Autorita mittente`, notes) are published text; it excludes only the internal account, login, audit and responsible-person keys listed above.

**What the project does:** reads public metadata and official PDF links, publishes a short message followed by the PDF documents, records fingerprints and sent URLs, and regenerates the published index from the same allowed fields. It does not copy official documents into the repository or into a local archive.

**What the operator is responsible for:** providing credentials through a gitignored local `.env`, an
`APT_ENV_FILE` file, or the protected environment file, choosing the state and index paths, scheduling
the job, protecting logs, checking that the Telegram bot has the right permissions, monitoring failures, and answering data-rights requests. Withdrawal is not automated: a withdrawn notice stays in the channel as the permanent record and leaves the index on the next hourly refresh (ADR 0004). Publishing a key that the allowlist excludes (an internal account, login, audit or responsible-person field) would require a new Wayfinder decision; every other public field of an act is already published. After a change to the field set, reseed state once as described above.

**Not verified:** no production cron schedule was installed. A live `sendMessage` and multipart `sendDocument` both succeeded in the private validation channel: one notice produced one text message and two PDF documents. A `sendDocument` that passed the official PDF URL failed earlier with `400 Bad Request: failed to get HTTP URL content`, which is why documents are now uploaded as bytes. The `--refresh-index` path was exercised against the live source; long-term source availability, the hourly GitHub workflow and rendering in other Telegram clients remain unverified.

## Production checks

- `APT_PAGE_SIZE` must be a positive integer; invalid values exit with status 2.
- Runtime failures print a single redacted line, so `TELEGRAM_BOT_TOKEN` is not written to logs.
- Telegram HTML is bounded to 4096 characters; the expandable quote is clipped and, only if the visible part alone overflows, its trailing lines are dropped. Tags stay balanced, so Telegram accepts the message.
- Every dynamic value is escaped with `html.escape(..., quote=True)` before it reaches the HTML message.
- Document captions state the act number and year and are bounded to 1024 characters.
- `--refresh-index` needs no Telegram credentials, writes no state and sends nothing.
- `--backfill` reads the whole archive page by page, publishes oldest to newest, writes no index and
  keeps state per successful publish, so an interrupted backfill resumes on the next run.
- GitHub Actions runs compile and the full test suite on pushes to `main` and pull requests, and refreshes the committed index hourly.

## Tests

Run the full suite:

```sh
python3 -m unittest discover -s tests -v
```

The tests use local fixtures and fake transports; they do not contact APT Basilicata or Telegram. They cover the published outputs (Telegram HTML, captions, index files), the exact message layout, HTML escaping of hostile values, the unknown-expiry note, the multipart document upload and its 50 MB bound, the exact included and excluded field sets, the unchanged dedupe behavior, the credential-free refresh path, the archive criteria and pagination, the oldest-to-newest publication order and the `--backfill` path.
