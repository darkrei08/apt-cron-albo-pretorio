# 0001 — Hourly acquisition and public metadata contract

- Status: accepted, implemented; archive pagination and publication order amended by [ADR 0008](0008-archive-backfill-and-publication-order.md)
- Decision record: GitHub issue #5 (closed)

## Context

`apt_cron.py` already acquires APT Basilicata public notices and publishes them to Telegram. The
acquisition shape, the fields taken from the source and the schedule model were chosen during
Wayfinder planning and are visible only in the code and in `README.md`. Issue #5 records the same
decision in the tracker. This ADR states the contract once, so later changes can be checked against
it instead of re-deriving it from the implementation.

The source exposes notice discovery only as a read-only query: the official OpenAPI document
describes `POST /api/pap/filter`, and the operator authorized that POST. There is no `GET`
alternative for the notice list.

## Decision

1. **One read-only query per run.** Each invocation sends exactly one `POST` to
   `APT_SOURCE_URL?page=0&size=APT_PAGE_SIZE` (default `APT_PAGE_SIZE=20`). `page=0` is fixed in
   the code; the body carries only the filter criteria for category, publication window, external
   status and notice number. Nothing is written to the source.
2. **PDF links come from the attachment endpoint.** For a notice whose links are not cached in
   state, `GET APT_ATTACHMENTS_BASE/{id}` is read, and only links whose MIME type is
   `application/pdf` (`documentoUnico.downloadUrl`) plus PDF attachment URLs are kept. When a
   document is published, its bytes are fetched into memory with the same 20-second timeout and
   uploaded in a multipart `POST /sendDocument` body, bounded at 50 MB before the upload; no PDF is
   written to disk and no source URL is handed to Telegram. Publishing uses `POST /sendMessage` and
   `POST /sendDocument`, and state, index and messages carry URLs only.
3. **Only allowed public metadata fields are read and published.** `NOTICE_FIELDS` maps 41 of the 53
   source keys an act carries: nine under stable output names (id, title, category, sector,
   publication start and end dates, year/number pair and status) and the other 32 under their register
   key (`otypeId`, `cntProponente`, `cntDurataPubblicazione`, ...). `detail_url` is derived from
   `APT_DETAIL_BASE` and the id; `document_url` and `attachment_urls` come from the attachment
   endpoint. The field map excludes the 12 internal account, login, audit and responsible-person keys
   listed in ADR 0005, so those never reach state, Telegram or the index. Everything else the register
   exposes for an act is published: the Telegram message renders the identity block plus one line per
   non-empty field, and the generated index (`public/index.json`, `index.md`, `index.html`) uses
   `INDEX_FIELDS`, which is `tuple(NOTICE_FIELDS)` plus the three derived links. Widening or narrowing
   the map requires a new decision.
4. **Dedupe by SHA-256 fingerprint.** A notice's fingerprint is the SHA-256 of its canonical JSON
   (`sort_keys=True`, compact separators). The state key is the notice `id`, or, when the id is
   missing, the SHA-256 of the first available stable URL (detail, document, attachment). A notice
   is published when its fingerprint is new or changed relative to state. The `sent_documents` map
   records PDF URLs already delivered, so a PDF URL is sent at most once even if the notice changes
   again.
5. **First run seeds state and publishes nothing.** When no state file exists, the current notices
   are recorded as fingerprints and the run reports zero published notices. This avoids an initial
   channel flood and is what makes the hourly cadence safe to start at any time.
6. **Standard-library runtime.** The job runs on Python 3.11 or newer using only the standard
   library: no third-party package, no Node, no LLM call at runtime.
7. **Hourly is a schedule the operator owns.** The script performs one pass per invocation and
   installs nothing. Hourly cadence is the intended schedule, declared as a cron example in
   `README.md`; choosing, protecting and monitoring that schedule is the operator's responsibility.

## Consequences

- A run sees at most one page of notices (`APT_PAGE_SIZE`, default 20). Older or additional pages
  are read only by the archive backfill (`--backfill`), which paginates without the publication
  window (ADR 0008).
- State is the only memory. Deleting `APT_STATE_PATH` re-seeds it and suppresses publishing for that
  run.
- Fingerprints cover every projected field, so adding a field to `NOTICE_FIELDS` changes every stored
  fingerprint. After such a deploy, reseed once by moving `APT_STATE_PATH` away before the first run;
  otherwise that run reports every current notice as "Atto aggiornato".
- The published field set is the privacy boundary as well as the schema. Any new field is a new
  decision, not an implementation detail.

## Evidence

- `apt_cron.py`: `NOTICE_FIELDS`, `FIELD_LABELS`, `fetch_notices` (`page=0&size=`), `fetch_attachments`,
  `enrich_notices`, `fingerprint`, `notice_key`, `select_changes`, `run_once`, `INDEX_FIELDS`,
  `format_message`, `UrllibTransport`.
- `tests/test_apt_cron.py`: `test_posts_only_a_read_query_to_the_official_source`,
  `test_projects_every_documented_public_source_field`,
  `test_fetch_attachments_exposes_only_pdf_urls`, `test_first_run_seeds_state_and_does_not_publish`,
  `test_pdf_is_not_sent_again_when_notice_changes_again`,
  `test_published_fields_are_the_notice_fields_plus_derived_links`.
- `README.md`, sections "How it works", "Configuration", "Run" and "Download section".

## Not verified

A live `sendMessage` and multipart `sendDocument` were exercised in the private validation channel;
no production cron schedule was installed. Automated tests use simulated HTTP on both sides.
Rendering across Telegram clients and long-term source availability remain unverified.
