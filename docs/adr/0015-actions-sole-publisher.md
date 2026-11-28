# 0015 — GitHub Actions as sole publisher

- Status: accepted
- Supersedes: [ADR 0014](0014-production-credential-override-and-destination-channel.md) item 4 and the issue 26 decision for two active schedulers; all other ADR 0014 credential and channel decisions remain in force
- Decision record: [Define the shared-state protocol for the two production schedulers](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/38)

## Context

The operator selected `herdr`, GitHub Pages and `darkrei08` in issue 26, with GitHub Actions at minute
`0` and a host cron at minute `15` publishing to the same Destination channel. That protocol required
a shared committed state file, but runtime state carries fingerprints, cached links and sent-document
records, which must not be committed. The operator then decided that if the local cron is superseded
by GitHub Actions, GitHub Actions should remain the only scheduler. A single publisher removes the
duplicate-publication condition without a second state owner.

## Decision

1. **Single publisher.** GitHub Actions is the only scheduler and the only publisher. The host cron is
   not installed, activated or documented as an active publisher. No host-local publication job may
   be enabled while this ADR stands.
2. **Ephemeral state.** The hourly workflow seeds `APT_STATE_PATH` from the committed `public/index.json`
   into a runner-local temporary file with `publication_state.py`. Runtime state is never committed.
   No second scheduler reads it, so duplicate publication between schedulers is removed. A workflow
   that accepts a Telegram message but fails before committing the updated index can still retry that
   notice on the next run; that is an operator recovery case, not a second scheduler.
3. **Commit ownership.** GitHub Actions commits generated `public/index.*` and `reports/**/*.md` with
   the repository `GITHUB_TOKEN`. It does not commit runtime state. Concurrency remains
   `cancel-in-progress: false`.
4. **Recovery boundary.** `publication_state.py` remains an explicit operator recovery command for a
   local state file. The scheduled job uses only the committed index as its seed source.
5. **Unchanged.** Telegram profile and credentials, Destination-channel classification, HTML message
   layout, published field set, captions, document upload bounds and exit codes are unchanged. ADR 0014
   remains the record for credential names and channel classification.

## Evidence

- Operator decision in issue 38: GitHub Actions remains the sole scheduler; the local cron is no longer
  needed if superseded by Actions.
- `.github/workflows/update-index.yml` is the only workflow with a `schedule` trigger and already owns
  index and report commits.
- `publication_state.py` seeds state from `public/index.json`; the workflow runs it before publication.
- `apt_cron.py` loads and saves the path supplied by `APT_STATE_PATH`; no runtime code changes are
  needed for this decision.

## Consequences

- Duplicate publication from two schedulers is removed structurally: one scheduler, one publisher, one
  ephemeral state file. Recovery after a partially failed run remains possible and is recorded as an
  operator concern rather than claimed impossible.
- No runtime fingerprint, cached link or sent-document record is added to the repository.
- The release gate remains `HOLD`. Credential rotation, current HTML validation and operator evidence
  are separate operator gates.
- Rollback keeps published report history intact; reverting the workflow is a new reviewed change, not
  an automatic cleanup.
