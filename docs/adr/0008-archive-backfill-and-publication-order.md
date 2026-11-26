# 0008 — Archived-acts backfill and oldest-to-newest publication

- Status: accepted, implemented
- Decision record: Wayfinder map #14, tickets #19 and #20

## Context

ADR 0001 fixes one page of the current publication window per run: a single read-only
`POST APT_SOURCE_URL?page=0&size=APT_PAGE_SIZE` whose criteria include
`cntDataFinePubblicazione >= today` and `cntDataInizioPubblicazione <= today`. The registry holds far
more than a window: the same query without the two date criteria returns the whole published history
(748 acts in the current live probe) over eight pages at size 100, while the `sort` query parameters
are ignored by the source. The source orders results newest first, and asking for a page past `totalPages`
answers HTTP 404 rather than an empty page.

The channel currently receives new and changed acts in source order, newest first, so within one run
the last message in the chat is the oldest act of that run. The operator wants the opposite: the
newest act must be the final message, so a reader opening the channel sees the latest act first, and
the archived history must be publishable in one pass.

## Decision

1. **The archive is the same query without the publication window.** `notice_query` builds the
   criteria list once: category, external status and notice-number filters always; the two date
   criteria only in the current-window mode. `fetch_notices(..., archive=True)` therefore reads the
   whole published history with the same read-only `POST`, the same six-to-four criteria and the same
   projection through `NOTICE_FIELDS`. No new endpoint, no new field, no write to the source.
2. **Archived reads paginate up to `totalPages`.** In archive mode the fetch walks
   `page=0..totalPages-1` and accumulates the parsed notices; `totalPages` comes from each response.
   A page past the end answers 404, so the page count is the only stop condition and the loop never
   requests the failing page. The current-window path still sends exactly one request to `page=0`.
3. **The index is not written during a backfill.** `run_once` rebuilds `public/index.*` only in the
   current-window path, because the index describes the current window and its order (newest first,
   as the source returns it). A backfill publishes messages only.
4. **Publication order is oldest to newest in every run.** `publication_order` reverses the fetched
   order and sorts by `published` date, so the newest act is always the last message. Acts sharing a
   publication date keep the reversed source order, which puts the older same-day act first. The
   stored state, the dedupe fingerprints and the index order are unchanged.
5. **A backfill on a fresh state publishes instead of seeding.** First-run seeding exists to avoid a
   channel flood of the current window (ADR 0001). A backfill whose purpose is to publish the archive
   starts from an empty notice map, so nothing is silently seeded; the dedupe fingerprints are then
   written per successful publish, and rerunning the backfill publishes nothing for unchanged acts.
6. **Archived acts without a PDF still produce a message.** Archived records usually have no
   `documentoUnico` and no attachments, and the publish loop already skips empty document URLs, so a
   backfill message carries metadata and the official detail link only.
7. **`--backfill` is the operator entry point.** The flag sets the archive mode; it needs Telegram
   credentials like a normal run (or `--dry-run`), writes no index, and is not part of the hourly
   workflow, which keeps running `--refresh-index`.

## Consequences

- The hourly cron behavior is unchanged except message order: within one run the newest act is the
  last message.
- A backfill is bounded by the archive size and the attachment lookup: it reads one attachment
  request per act whose links are not cached in state, which for the full archive is hundreds of
  `GET`s in one invocation.
- A backfill publishes every act not yet in state, including acts that the current window already
  covered. Use it once, then keep the hourly run as the steady-state path.
- `--backfill` with `--refresh-index` is not supported: the index stays the current-window surface.
- The archive criteria and the 404 boundary are properties of the live source. If the source starts
  answering an empty page instead of 404, or changes `totalPages`, only `fetch_notices` needs review.

## Evidence

- `apt_cron.py`: `notice_query`, `fetch_notices` (`archive` flag, `totalPages` loop),
  `fetch_enriched_notices`, `publication_order`, `run_once` (`archive` state seeding, index skip,
  ordered publish), `main` (`--backfill`, `archive` config key).
- `tests/test_apt_cron.py`: `ArchiveQueryTest` (criteria without date filters, pagination over
  `totalPages` with a 404 past the end, current window still one page), `PublicationOrderTest`
  (order, same-day tie-break, `run_once` message order), `BackfillTest` (oldest-first backfill,
  no index, no-PDF message, rerun publishes nothing, CLI flag), `PartialFailureTest` (state after a
  failure under the new order).
- `README.md`, sections "How it works" and "Run".

## Not verified

No Telegram message was sent while implementing this. A credential-free live probe on 2026-11-26
with `APT_PAGE_SIZE=100` requested eight archive pages and returned 748 notices, 748 unique IDs and
no duplicate IDs, with years 2024-2026 and publication dates from 2024-05-03 through 2026-11-26.
`totalPages` reported 8 on every response. The `--backfill --dry-run` path also returned 748 notices
without writing state or contacting Telegram. The backfill publish path itself is exercised only
against fake transports in the unit suite; a real full-archive publish remains intentionally
operator-controlled.
