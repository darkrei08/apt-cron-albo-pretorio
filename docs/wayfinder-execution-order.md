# Wayfinder execution order

This document orders the open tickets of [APT public notices crawler and notification plan](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1) by dependency, impact and resolvability. It contains decisions and execution order only; it does not change crawler behavior.

## Principles

- Resolve prerequisite decisions before gated tickets.
- Prefer tickets that can be resolved from verified repository evidence.
- Leave tickets requiring credentials, legal choices or operator ownership waiting for that input.
- Keep implementation already delivered in issues 8 and the related commits intact.

## Order

| Order | Ticket | Priority | Blockers | Type | Status | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | [Choose an hourly acquisition and metadata contract](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/5) | P0 | none | Decision | Decision recorded in [ADR 0001](adr/0001-hourly-acquisition-and-metadata-contract.md); issue open | Operator approves issue closure. |
| 2 | [Resolve api-anything runtime integration status](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/12) | P0 | none | Decision | Decision recorded in [ADR 0002](adr/0002-api-anything-runtime-status.md); issue open | Operator approves issue closure and the stale map Notes edit. |
| 3 | [Publish only new APT notices with PDF links and generated index](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/8) | P0 | none | Implementation | Local verification PASS; issue open | Operator accepts the delivered behavior. |
| 4 | [Decide production secret storage and schedule ownership](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/9) | P1 | none | Decision | Proposed in [ADR 0003](adr/0003-production-secret-storage-and-schedule.md) with `[INSERT DECISION]` fields | Operator fills the four decision fields. |
| 5 | [Define withdrawal and retention handling for messages and index](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/11) | P1 | none | Decision | Proposed in [ADR 0004](adr/0004-withdrawal-and-retention.md) with `[INSERT DECISION]` fields | Operator chooses removal, retention and rights-request procedure. |
| 6 | [Decide what can be published, retained and removed](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/6) | P1 | none | Decision | Proposed in [ADR 0005](adr/0005-publication-boundary.md) with `[INSERT DECISION]` fields | Operator resolves the publication surface and PII review. |
| 7 | [Validate Telegram delivery in the private test channel](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/10) | P1 | none | Test | Checklist in [Telegram private-channel validation](validation/telegram-private-channel.md); NOT RUN | Operator supplies test credentials and executes V1-V9. |
| 8 | [Choose one accessible notification format and channel](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/7) | P2 | 5, 6 | Decision | Proposed in [ADR 0006](adr/0006-notification-format-and-channel.md) with `[INSERT DECISION]` fields | Resolve after issues 5 and 6 and private-channel validation. |
| 9 | [Define release gate for faibtes production rollout](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/13) | P2 | 9, 10, 11, 12 | Release | Proposed in [ADR 0007](adr/0007-release-gate.md) with `[INSERT DECISION]` fields | Resolve only after all four blockers are closed and CI has run on GitHub. |

## Recorded decisions and verification

- [ADR 0001](adr/0001-hourly-acquisition-and-metadata-contract.md) records ticket 5: the read-only acquisition request, allowed public metadata, SHA-256 dedupe, first-run seeding and operator-owned hourly schedule.
- [ADR 0002](adr/0002-api-anything-runtime-status.md) records ticket 12: `api-anything` was a planning aid, `fast-anything` is a future aid, and the Python standard library is the runtime authority.
- Ticket 8 local verification on the current tree: `python3 -m py_compile apt_cron.py tests/test_apt_cron.py` PASS; `python3 -m unittest discover -s tests -v` PASS, 26 tests; `git diff --check` PASS. GitHub CI has zero runs, so this is local evidence only.
- Ticket 10 caption bound: a regression test proved RED before the change and GREEN after it; the document caption is capped at 1024 characters through the public run path.
- ADRs 0003-0007 and the Telegram checklist record items 4-9 with recommendations. Every value the repository cannot determine is marked `[INSERT DECISION]`.

## Evidence used

- `README.md`: source, fields, PDF links, configuration, privacy boundary and download behavior.
- `apt_cron.py`: notice acquisition, state, PDF link enrichment, Telegram message and document delivery, generated index.
- `tests/test_apt_cron.py`: 26 tests with simulated HTTP.
- `.github/workflows/ci.yml`: compile and full test suite.
- GitHub native sub-issue and dependency data from [the map](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1).
- GitHub Actions run inventory: zero runs at discovery time.

## Blocked by external information

Issue 9 needs operator-owned infrastructure decisions. Issue 10 needs test credentials. Issues 11 and 6 need operator privacy and retention decisions. Issue 13 remains blocked until those decisions and a GitHub CI run exist.
