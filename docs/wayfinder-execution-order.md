# Wayfinder execution order

This document records the historical order of the tickets in [APT public notices crawler and notification plan](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1) by dependency, impact and resolvability. Production readiness is now tracked separately by [Wayfinder: production readiness, audit and release of cron-albo-pretorio](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/24), while the readable-message and archive-backfill effort remains in [Wayfinder: readable Telegram acts and full archive backfill](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/14). It contains decisions and execution order only; it does not change crawler behavior.

## Principles

- Resolve prerequisite decisions before gated tickets.
- Prefer tickets that can be resolved from verified repository evidence.
- Leave tickets requiring credentials, legal choices or operator ownership waiting for that input.
- Keep implementation already delivered in issues 8 and the related commits intact.

## Order

| Order | Ticket | Priority | Blockers | Type | Status | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | [Choose an hourly acquisition and metadata contract](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/5) | P0 | none | Decision | Decision recorded in ADR 0001; complete | Operator closure recorded |
| 2 | [Resolve api-anything runtime integration status](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/12) | P0 | none | Decision | Decision recorded in ADR 0002; complete | Operator closure recorded; map Notes edit still pending |
| 3 | [Publish only new APT notices with PDF links and generated index](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/8) | P0 | none | Implementation | Implementation verified live; complete | Operator acceptance recorded |
| 4 | [Decide production secret storage and schedule ownership](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/9) | P1 | none | Decision | Accepted in ADR 0003; complete | Operator closure recorded |
| 5 | [Define withdrawal and retention handling for messages and index](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/11) | P1 | none | Decision | Accepted in ADR 0004; complete | Operator closure recorded |
| 6 | [Decide what can be published, retained and removed](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/6) | P1 | none | Decision | Accepted in ADR 0005 and implemented; complete | Operator closure recorded |
| 7 | [Validate Telegram delivery in the private test channel](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/10) | P1 | none | Test | Private-channel validation PASS for the historical plain-text format; complete | Current HTML rerun tracked by production readiness |
| 8 | [Choose one accessible notification format and channel](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/7) | P2 | 5, 6 | Decision | Accepted in ADR 0006 after live validation; complete | Operator closure recorded |
| 9 | [Define release gate for faibtes production rollout](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/13) | P2 | 9, 10, 11, 12 | Release | Release gate defined; CI green on the checked-in commit; complete | Operator closure recorded; production installation remains separate |

## Recorded decisions and verification

- [ADR 0001](adr/0001-hourly-acquisition-and-metadata-contract.md) records ticket 5: the read-only acquisition request, allowed public metadata, SHA-256 dedupe, first-run seeding and operator-owned hourly schedule.
- [ADR 0002](adr/0002-api-anything-runtime-status.md) records ticket 12: `api-anything` was a planning aid, `fast-anything` is a future aid, and the Python standard library is the runtime authority.
- [ADR 0003](adr/0003-production-secret-storage-and-schedule.md) records ticket 9: protected cron environment file, `Europe/Rome`, portable deployment managed by whoever maintains the repository, and cron `MAILTO` for failures.
- [ADR 0004](adr/0004-withdrawal-and-retention.md) records ticket 11: no automatic withdrawal, messages stay in the chat as the permanent record, and state, index and messages are retained indefinitely.
- [ADR 0005](adr/0005-publication-boundary.md) records ticket 6 and is implemented: two publication surfaces (the Telegram channel and `public/index.*` committed hourly), every public register field published (`Titolo` and `Settore` included, 41 keys plus the derived links), the 12 internal account, login, audit and responsible-person keys excluded, captions by act number and year, and a credential-free `--refresh-index` path.
- [ADR 0006](adr/0006-notification-format-and-channel.md) records ticket 7: one Telegram channel, the historical plain-text format, label-value lines and the `Categoria` hashtag; the channel and caption decisions stand, while message formatting is superseded by ADR 0009. The historical private-channel evidence does not validate the current HTML format.
- [ADR 0007](adr/0007-release-gate.md) records ticket 13: `faibtes` defined as the portable deployment, and the repository operator as sign-off and rollback owner. The gate is defined; CI and index workflow runs are recorded for checked-in commits, while current HTML validation and production installation remain separate release work.
- [ADR 0008](adr/0008-archive-backfill-and-publication-order.md) records the archived-acts backfill: the archive is the same read-only query without the publication window, read page by page up to the page count the source reports because a page past the end answers 404; a backfill publishes oldest to newest and writes no index; publication order is oldest to newest in every run, so the newest act is the last message.
- [ADR 0009](adr/0009-readable-telegram-act-message.md) records the readable Telegram message: `parse_mode` `HTML`, a bold headline, the underlined act number and year, title, dates, hashtags, status and labelled links visible, every other non-empty public field inside an expandable `blockquote`, an explicit `Scadenza: non nota` when the source has no expiry, HTML escaping of every dynamic value and a 4096-character bound that keeps tags balanced. The channel and the document captions are unchanged. The headline is a fixed text label derived from the run: `Nuovo atto`, `Atto aggiornato`, `Atto scaduto` (`status` `SCADUTO` or an expiry before the run date) and `Atto archiviato` (archive backfill), with precedence updated, expired, archived, new, from already published fields and the run mode only.
- Ticket 8 local verification on the current tree: `python3 -m py_compile apt_cron.py tests/test_apt_cron.py` PASS; `python3 -m unittest discover -s tests -v` PASS, 41 tests; `git diff --check` PASS. GitHub CI was green on the final pushed commit.
- Ticket 6 implementation on the current tree, after the failing tests were written first: the index and the Telegram message carry every published field (`Titolo` and `Settore` restored, 41 source keys plus the derived links, no internal key), captions read `PDF ufficiale: Atto <number>/<year>` and stay within 1024, the message stays within 4096 by shortening the widest lines, `--refresh-index` writes `public/index.*` with no state and no Telegram call, and `.github/workflows/update-index.yml` runs it hourly and commits only changed `public/index.*`. One live `--refresh-index` run against the source returned exit code `0` with 14 notices and 44 published keys per notice. Because fingerprints cover every published field, operators reseed state once after this change.
- Ticket 10 caption bound: a regression test proved RED before the change and GREEN after it; the caption is now the act number and year, capped at 1024 characters through the public run path.
- Ticket 10 document delivery, after the live failure: `sendDocument` handed the official URL to Telegram and returned `400 Bad Request: failed to get HTTP URL content`. `publish_document` now fetches the PDF into memory with the existing 20-second timeout, rejects more than 50 MB before the upload, and posts a multipart body with `chat_id`, caption, file name and bytes; state, `sent_documents` and the index still hold URLs only and no PDF is written to disk. Tests were written first through the `run_once` seam (multipart upload, no local file, URL-only state, size bound) and the full suite passes with 41 tests.
- ADRs 0003-0007 and the Telegram checklist record items 4-9. Historical plain-text private-channel validation observed a 9.55 MB PDF below the 50 MB bound; current HTML validation, credential rotation and production-host evidence remain pending. Checked-in commit `cef13761aed1f33d9847395588763a656e1a8a98` has successful [CI run 45844836581](https://github.com/darkrei08/apt-cron-albo-pretorio/actions/runs/45844836581), and scheduled index refresh [run 45787926316](https://github.com/darkrei08/apt-cron-albo-pretorio/actions/runs/45787926316).
- Readable message on the current tree, after the failing tests were written first: `python3 -m py_compile apt_cron.py tests/test_apt_cron.py` PASS; `python3 -m unittest discover -s tests -v` PASS, 53 tests; the exact small-message HTML, escaping, unknown expiry, full quote field set, `parse_mode` payload and the 4096 bound with balanced tags are pinned by tests. No live Telegram message was sent for this change.
- Act state headlines at commit `aad3360`, after the failing tests were written first: `python3 -m py_compile apt_cron.py tests/test_apt_cron.py` PASS; `python3 -m unittest discover -s tests -v` PASS, 77 tests; the four labels and the precedence updated, expired, archived, new are pinned by `FormatMessageTest` and `BackfillHeadlineTest`, and `run_once` passes the run mode and the run date into `format_message`. No new field, no state migration and no live Telegram message.
- Production-hardening follow-up at commit `eaf5b978c764c471e57eb4cd38e65d2e89a8902b`: attachment cache refresh on source metadata changes is covered by three public tests; the full suite passed with 80 tests.
- Ticket 19 archive evidence is recorded in `docs/validation/archive-probe-2026-11-26.md`: 8 pages, 748 notices, 748 unique IDs, no duplicate IDs, years 2024-2026, and publication dates from 2024-05-03 through 2026-11-26. The dry-run performed no state or Telegram publication.

## Evidence used

- `README.md`: source, fields, PDF links, configuration, privacy boundary and download behavior.
- `apt_cron.py`: notice acquisition, state, PDF link enrichment, Telegram message and document delivery, generated index, credential-free index refresh.
- `tests/test_apt_cron.py`: 80 tests with simulated HTTP, including the pinned included and excluded field sets, the exact Telegram HTML message and its escaping, the act state headlines, attachment cache refresh, and the in-memory PDF upload path.
- `.github/workflows/ci.yml`: compile and full test suite.
- `.github/workflows/update-index.yml`: hourly index refresh and commit.
- GitHub native sub-issue and dependency data from [the map](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1).
- GitHub Actions run inventory is recorded at discovery time and must be rechecked at release time.

## Remaining deployment work

Tickets in this historical map are resolved, but production readiness is not. The production-readiness map tracks the remaining audit, correction, validation, host-installation, monitoring and rollback work. The token used for the private-channel test was pasted into the conversation and must be rotated before production use.
