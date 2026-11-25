# cron-albo-pretorio

Publishes new and changed notices from the official APT Basilicata public notices register to a Telegram channel. The job uses only Python's standard library and calls no LLM.

The Wayfinder map is [APT public notices crawler and notification plan](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1). It records the operator decisions and the linked ticket graph.

## How it works

1. Reads the official APT Basilicata public notices API once per run.
2. Extracts only title, category, sector, publication dates, year, notice number, status and official detail link.
3. Reads official PDF links from the source attachment endpoint and caches them in local state.
4. Compares SHA-256 fingerprints with local state.
5. Sends a plain-text message with the official PDF link, then sends the PDF files to Telegram by URL for new or changed notices. Each PDF URL is sent once.
6. Regenerates `public/index.json`, `public/index.md` and `public/index.html` from public fields only.
7. Saves state incrementally after each successful publish.

The first run seeds state from the current source without publishing. This avoids an initial channel flood.

The source API exposes notice discovery only as a read-only `POST /api/pap/filter`, confirmed by the [official OpenAPI document](https://siopi.publisys.it/kapi-aptbasilicata/v3/api-docs). The user authorized that POST. PDF links are read with `GET /api/pap/files/{id}`. Publishing uses `POST /sendMessage` and `POST /sendDocument`.

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
| `TELEGRAM_BOT_TOKEN` | yes, unless `--dry-run` | none | Bot token; keep it outside Git |
| `TELEGRAM_CHAT_ID` | yes, unless `--dry-run` | none | Channel or chat identifier |
| `APT_SOURCE_URL` | no | `https://siopi.publisys.it/kapi-aptbasilicata/api/pap/filter` | API base URL, without query string |
| `APT_NATURE_ID` | no | `200152` | Notice category identifier from the source |
| `APT_PAGE_SIZE` | no | `20` | Number of notices requested per run |
| `APT_DETAIL_BASE` | no | `https://siopi.publisys.it/sito-aptbasilicata/albo-pretorio/dettaglio` | Base URL used to build official detail links |
| `APT_ATTACHMENTS_BASE` | no | `https://siopi.publisys.it/kapi-aptbasilicata/api/pap/files` | Base URL for official PDF link lookup |
| `APT_INDEX_DIR` | no | `public` | Directory receiving generated index files |
| `APT_STATE_PATH` | no | `state/notices.json` | File holding fingerprints, cached PDF links and sent document URLs |

The generated `state/` directory and Telegram credentials are not committed.

## Run

Simulate a read without publishing or writing state:

```sh
python3 apt_cron.py --dry-run
```

Publish new or changed notices:

```sh
TELEGRAM_BOT_TOKEN='...' TELEGRAM_CHAT_ID='...' python3 apt_cron.py
```

Hourly cron example:

```cron
0 * * * * cd /path/to/cron-albo-pretorio && TELEGRAM_BOT_TOKEN='...' TELEGRAM_CHAT_ID='...' /usr/bin/python3 apt_cron.py >> cron.log 2>&1
```

Prefer a protected environment or cron file over literal credentials in a crontab line.

## Download section

**What is downloaded:** the JSON notice list, the JSON attachment-link list, and no PDF bytes. The script does not store PDF files or images. Telegram receives each official PDF URL and fetches the document itself.

**Where it is downloaded from:** `https://siopi.publisys.it/kapi-aptbasilicata/api/pap/filter?page=0&size=<APT_PAGE_SIZE>` by read-only POST, and `https://siopi.publisys.it/kapi-aptbasilicata/api/pap/files/{id}` by GET for notices not already cached in state. Requests use `User-Agent: apt-cron/1.0` and a 20-second timeout.

**When:** once per invocation. The intended schedule is hourly, but scheduling is the operator's choice and is not performed by the script.

**Where it is saved:** raw responses stay in memory. SHA-256 fingerprints, cached official PDF URLs and URLs already sent to Telegram are written to `APT_STATE_PATH` (`state/notices.json` by default). Generated public index files are written to `APT_INDEX_DIR` (`public/` by default) and can be reviewed and committed by the operator. No PDF bytes, personal names, RUP names, responsible persons or non-public groups are written.

**What the project does:** reads public metadata and official PDF links, publishes a short message followed by the PDF documents, records fingerprints and sent URLs, and generates a public index from the same allowed fields. It does not copy official documents into the repository or into a local archive.

**What the operator is responsible for:** providing credentials, choosing the state and index paths, scheduling the job, protecting logs, reviewing generated index files before committing them, checking that the Telegram bot has the right permissions, monitoring failures, and deciding how to remove published messages if a source notice is withdrawn or a data-rights request arrives. Adding personal names, RUPs, responsible persons or non-public groups would require a new Wayfinder decision; none is enabled here.

**Not verified:** no live Telegram message or document was sent and no production cron schedule was installed. Automated tests use simulated HTTP on both sides. Long-term source availability, Telegram document size acceptance and client rendering should be checked in the destination channel before public use.

## Tests

Run the full suite:

```sh
python3 -m unittest discover -s tests -v
```

The tests use local fixtures and fake transports; they do not contact APT Basilicata or Telegram.
