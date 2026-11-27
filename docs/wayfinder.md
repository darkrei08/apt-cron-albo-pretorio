# Local wayfinder — operational documentation

This file mirrors the GitHub map [APT public notices crawler and notification plan](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1). The GitHub map remains the canonical tracker; this file keeps the repository-local evidence readable by contributors and checks.

## Destination

A professional Italian README, an operational wiki under `docs/wiki/`, and tracking of risks, skipped work and missing verification. Functional code stays unchanged.

## Language decision

- The operator requested an Italian README and wiki and later authorized the complete release cycle.
- The verbatim operator texts are recorded in `odd/tasks/documentation-refresh.md`.
- Decision: user-facing README and wiki pages use Italian. Code, comments, tests, ADRs and this wayfinder file use English.
- Canonical tracker record: comment `7218303464` on the GitHub map.

## Status

- README and wiki rewritten.
- `portal_monitor.py`, its tests and ADR 0012 added.
- CI commands: `python3 -m py_compile apt_cron.py tests/test_apt_cron.py` and `python3 -m unittest discover -s tests -v`.
- Local verification: 121 tests PASS, `py_compile` PASS, `git diff --check` PASS.
- PR #36 is open, mergeable, and its required `test` check passes.

## Release decision

- Operator authorized the full release cycle and asked to record GO.
- Gate registry: ADR 0007 and issue #32. Current recorded status remains HOLD / no evidenced GO: parts 1-2 PASS, parts 3-5 BLOCKED by missing rotated credentials, unexecuted private HTML validation, unexecuted manual run and unexecuted rollback rehearsal.
- This authorization is not represented as a passed gate. No GO is claimed without the five required parts.
- Version: `[INSERT VERSIONE]`. No tag, changelog, product-version convention or release exists in 56 commits, remote tags, remote releases or repository metadata.
- Therefore PR #36 is not merged and no tag or GitHub release is created.

## Risks

- The monitor detects failures but does not alert until `APT_ALERT_TELEGRAM_BOT_TOKEN` and `APT_ALERT_TELEGRAM_CHAT_ID` are configured.
- `portal-history.json` is generated runtime state and must not be committed.
- ADR 0007 is `HOLD`; issue #32 has no GO.

## Skipped

- Live Telegram alert delivery.
- Commit, push, PR, merge and release before repository checks pass.
- Ticket closure.

## Not verified

- Real Telegram alert.
- Windows and macOS.
- Manual count of 748 chat messages; the count is verified through state and dry-run.

## To clarify

- The unclear operator text is recorded verbatim in `odd/tasks/documentation-refresh.md`.
- Exact unresolved point: intended action and meaning of the phrase. It is unclear whether it refers to header/orchestration, workflow extension or engineering-excellence work. No repository, history, issue or PR evidence resolves it.

## Next actions

- Supply `[INSERT VERSIONE]` or define a versioning convention.
- Satisfy and record ADR 0007 parts 3-5, then record an evidenced GO on issue #32.
- Merge PR #36 only after the gate decision and version are available.
- Clarify the garbled operator phrase before acting on it.
