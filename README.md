# cron-albo-pretorio

Publishes new and changed notices from the official APT Basilicata public notices register to a Telegram channel. The job uses only Python's standard library and calls no LLM.

The Wayfinder map is [APT public notices crawler and notification plan](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1). It records the operator decisions and the linked ticket graph.

## How it works

1. Reads the official APT Basilicata public notices API once per run.
2. Extracts only title, category, sector, publication dates, year, notice number, status and official detail link.
3. Compares SHA-256 fingerprints with local state.
4. Sends a plain-text message to Telegram for new or changed notices.
5. Saves the new state only after all publishes in the run succeed.

The first run seeds state from the current source without publishing. This avoids an initial channel flood.

The source API exposes notice discovery only as a read-only `POST /api/pap/filter`, confirmed by the [official OpenAPI document](https://siopi.publisys.it/kapi-aptbasilicata/v3/api-docs). The user authorized that POST. Publishing to Telegram uses `POST /sendMessage`.

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
| `APT_STATE_PATH` | no | `state/notices.json` | File holding notice fingerprints |

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

**What is downloaded:** only the JSON response from the official APT Basilicata notice API. The script never downloads PDF attachments, images or full documents.

**Where it is downloaded from:** `https://siopi.publisys.it/kapi-aptbasilicata/api/pap/filter?page=0&size=<APT_PAGE_SIZE>`. The request is a read-only HTTP POST with a JSON filter body, using `User-Agent: apt-cron/1.0` and a 20-second timeout.

**When:** once per invocation. The intended schedule is hourly, but scheduling is the operator's choice and is not performed by the script.

**Where it is saved:** nowhere as raw data. The response stays in memory. Only SHA-256 fingerprints of the selected fields are written to `APT_STATE_PATH` (`state/notices.json` by default). The state file contains no title text, personal names, PDF content or credentials.

**What the project does:** reads public metadata, builds a detail URL, publishes a short text message and a direct official link, and records fingerprints. It does not copy official documents into the repository or into a local archive.

**What the operator is responsible for:** providing credentials, choosing the state path, scheduling the job, protecting logs, checking that the Telegram bot has the right permissions, monitoring failures, and deciding how to remove published messages if a source notice is withdrawn or a data-rights request arrives. Adding PDF attachments or indexing personal names would require a new Wayfinder decision; neither is enabled here.

**Not verified:** no live Telegram message was sent and no production cron schedule was installed. Automated tests use simulated HTTP on both sides. Long-term source availability and Telegram client rendering should be checked in the destination channel before public use.

## Tests

Run the full suite:

```sh
python3 -m unittest discover -s tests -v
```

The tests use local fixtures and fake transports; they do not contact APT Basilicata or Telegram.
