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
| 4 | [Decide production secret storage and schedule ownership](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/9) | P1 | none | Decision | Accepted in [ADR 0003](adr/0003-production-secret-storage-and-schedule.md); all five items recorded | Operator closes the issue. |
| 5 | [Define withdrawal and retention handling for messages and index](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/11) | P1 | none | Decision | Accepted in [ADR 0004](adr/0004-withdrawal-and-retention.md); all six items recorded | Operator closes the issue. |
| 6 | [Decide what can be published, retained and removed](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/6) | P1 | none | Decision | Accepted in [ADR 0005](adr/0005-publication-boundary.md); all items recorded and implemented | Operator closes the issue. |
| 7 | [Validate Telegram delivery in the private test channel](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/10) | P1 | none | Test | Checklist in [Telegram private-channel validation](validation/telegram-private-channel.md); NOT RUN | Operator supplies test credentials and executes V1-V9. |
| 8 | [Choose one accessible notification format and channel](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/7) | P2 | 5, 6 | Decision | Accepted in [ADR 0006](adr/0006-notification-format-and-channel.md) items 1-5; format sign-off (item 6) pending validation | Operator closes the issue after the private-channel check. |
| 9 | [Define release gate for faibtes production rollout](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/13) | P2 | 9, 10, 11, 12 | Release | Proposed in [ADR 0007](adr/0007-release-gate.md); sign-off, rollback and target recorded, gate parts 2-5 not met | Recheck GitHub CI and run the private-channel validation. |

## Recorded decisions and verification

- [ADR 0001](adr/0001-hourly-acquisition-and-metadata-contract.md) records ticket 5: the read-only acquisition request, allowed public metadata, SHA-256 dedupe, first-run seeding and operator-owned hourly schedule.
- [ADR 0002](adr/0002-api-anything-runtime-status.md) records ticket 12: `api-anything` was a planning aid, `fast-anything` is a future aid, and the Python standard library is the runtime authority.
- [ADR 0003](adr/0003-production-secret-storage-and-schedule.md) records ticket 9: protected cron environment file, `Europe/Rome`, portable deployment managed by whoever maintains the repository, and cron `MAILTO` for failures.
- [ADR 0004](adr/0004-withdrawal-and-retention.md) records ticket 11: no automatic withdrawal, messages stay in the chat as the permanent record, and state, index and messages are retained indefinitely.
- [ADR 0005](adr/0005-publication-boundary.md) records ticket 6 and is implemented: two publication surfaces (the Telegram channel and `public/index.*` committed hourly), every public register field published (`Titolo` and `Settore` included, 41 keys plus the derived links), the 12 internal account, login, audit and responsible-person keys excluded, captions by act number and year, and a credential-free `--refresh-index` path.
- [ADR 0006](adr/0006-notification-format-and-channel.md) records ticket 7: one Telegram channel, plain text without `parse_mode`, label-value lines and the `Categoria` hashtag; format sign-off still needs the private-channel check.
- [ADR 0007](adr/0007-release-gate.md) records ticket 13: `faibtes` defined as the portable deployment, and the repository operator as sign-off and rollback owner. The gate itself is not satisfied.
- Ticket 8 local verification on the current tree: `python3 -m py_compile apt_cron.py tests/test_apt_cron.py` PASS; `python3 -m unittest discover -s tests -v` PASS, 33 tests; `git diff --check` PASS. At the first push GitHub CI was green on commit `4c1b5c1`; the release gate rechecks the final commit.
- Ticket 6 implementation on the current tree, after the failing tests were written first: the index and the Telegram message carry every published field (`Titolo` and `Settore` restored, 41 source keys plus the derived links, no internal key), captions read `PDF ufficiale: Atto <number>/<year>` and stay within 1024, the message stays within 4096 by shortening the widest lines, `--refresh-index` writes `public/index.*` with no state and no Telegram call, and `.github/workflows/update-index.yml` runs it hourly and commits only changed `public/index.*`. One live `--refresh-index` run against the source returned exit code `0` with 14 notices and 44 published keys per notice. Because fingerprints cover every published field, operators reseed state once after this change.
- Ticket 10 caption bound: a regression test proved RED before the change and GREEN after it; the caption is now the act number and year, capped at 1024 characters through the public run path.
- ADRs 0003-0007 and the Telegram checklist record items 4-9. The only open sign-off is ADR 0006 item 6; the Telegram checklist still needs live credentials and a real PDF size observation.

## Evidence used

- `README.md`: source, fields, PDF links, configuration, privacy boundary and download behavior.
- `apt_cron.py`: notice acquisition, state, PDF link enrichment, Telegram message and document delivery, generated index, credential-free index refresh.
- `tests/test_apt_cron.py`: 33 tests with simulated HTTP, including the pinned included and excluded field sets.
- `.github/workflows/ci.yml`: compile and full test suite.
- `.github/workflows/update-index.yml`: hourly index refresh and commit.
- GitHub native sub-issue and dependency data from [the map](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1).
- GitHub Actions run inventory is recorded at discovery time and must be rechecked at release time.

## Blocked by external information

Issue 10 needs test credentials, which the operator will supply later through a protected local
environment file. Issue 13 (release gate) remains blocked until that validation runs and the final
commit has a green GitHub CI run. Issues 9, 11, 6 and 7 have their decisions recorded and stay open
only for operator closure and format sign-off.
