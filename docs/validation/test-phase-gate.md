# Test-phase gate record

Scope: tickets 28, 29, 31, 30 and 32 of [Wayfinder: production readiness](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/24). This record covers repository-testable work only. It is not a production GO.

## Ticket 29 — installation and rollback procedure

Accepted sequence under ADR 0015:

1. Install an exact CI-green commit; verify Python version, compile and full unit suite.
2. Seed runner-local state from committed `public/index.json` with `publication_state.py`; no publication.
3. Keep `update-index.yml` as the sole scheduled publisher at minute `0`; no host cron at minute `15`.
4. Any manual backfill or run is explicit, pilot-authorized, workflow-disabled and followed by index reconciliation before re-enabling.
5. Rollback disables the workflow, preserves logs and messages, and reverts only `public/index.*` by reviewed commit/PR.

Interrupted first publish: unit tests cover incremental state within one runner-local state file, including a failed document retrying only its missing URL without a second text message. Across Actions runs, state is reseeded from the committed index; a run that publishes before committing that index can retry the notice. That recovery case remains **NOT RUN** and is an operator concern.

Live install, host execution, manual publication and rollback rehearsal: **NOT RUN**.

## Ticket 31 — monitoring ownership

- Observer: `darkrei08`.
- Alert destination: GitHub Actions job notifications.
- Incident trigger: a failed workflow or unexpected publication count.
- Rollback trigger: the same incident; disable `update-index.yml`, preserve logs and report artifacts, do not delete Telegram messages.
- First 24-hour evidence: hourly Actions run status, outcome, notice count, published count, index commit and report artifact.

Live 24-hour observation and alert delivery: **NOT RUN**.

## Ticket 30 — current-release validation verdicts

| Check | Test-phase result |
|---|---|
| HTML rendering and official links | Local unit PASS; live current HTML **NOT RUN** |
| Every PDF and non-PDF attachment upload | Local unit PASS; live current all-attachment contract **NOT RUN** |
| Caption and size bounds | Local unit PASS; live current PASS **NOT RUN** |
| Source response and index output | Local and dry-run PASS; scheduled live output **NOT RUN** |
| Duplicate suppression and interrupted retry | Local unit PASS; live PASS **NOT RUN** |
| Failure behavior | Local unit PASS; current live rerun **NOT RUN** |
| Manual production run with exit `0` and state mtime | **NOT RUN** |

No token, chat id or host credential value was read, invented or recorded.

## Ticket 32 — named gate decision

Decision: **NO-GO**, release gate remains **HOLD**.

Parts 1 and 2 of ADR 0007 have PASS evidence. Parts 3, 4 and 5 remain **NOT RUN** until token rotation, current Destination-channel validation, one manual production run and rollback rehearsal are executed by the operator. Partial test-phase evidence is not production approval. The first 24 hours of `update-index.yml` operation are post-release observation under ADR 0007, not a sixth gate prerequisite.

Post-test work: token rotation, protected-path metadata, live validation, manual run, rollback rehearsal, then a new GO decision. Twenty-four-hour observation follows activation.
