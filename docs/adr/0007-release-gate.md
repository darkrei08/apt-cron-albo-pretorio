# 0007 — Release gate for the faibtes production rollout

- Status: HOLD; parts 1-2 PASS, parts 3-5 blocked by missing rotated production-classified credentials and unexecuted operator evidence
- Credential names: [ADR 0014](0014-production-credential-override-and-destination-channel.md) supersedes the separated names below for GitHub Actions; rotation remains mandatory
- Decision record: GitHub issue #13 (closed after issues #9, #10, #11 and #12)

## Context

There is no deployment artifact and no production run. At the time of this decision the repository
contained two workflows and no packaging or ops file; the current workflow set is documented in
`docs/ci-cd.md`:

- `.github/workflows/ci.yml` runs on push to `main` and on pull requests: it checks out, sets up
  Python 3.11, runs `python3 -m py_compile apt_cron.py tests/test_apt_cron.py` and then
  `python3 -m unittest discover -s tests -v`.
- `.github/workflows/update-index.yml` ran hourly and on manual dispatch: at that time it ran
  `apt_cron.py --refresh-index` with `TZ: Europe/Rome` and committed changed `public/index.*` with the
  repository `GITHUB_TOKEN`. It needed no Telegram credentials. The current workflow also publishes
  acts and reports and is documented in `docs/ci-cd.md`.
- Current GitHub Actions evidence includes a successful CI run for checked-in commit
  `cef13761aed1f33d9847395588763a656e1a8a98` at
  [run 45844836581](https://github.com/darkrei08/apt-cron-albo-pretorio/actions/runs/45844836581),
  plus a successful scheduled index refresh for commit `74b425482f2df1063407fa9b10671fb51b9430a0`
  at [run 45787926316](https://github.com/darkrei08/apt-cron-albo-pretorio/actions/runs/45787926316).
  These runs cover checked-in commits only; the current worktree has uncommitted changes, so part 2
  must be rechecked for the exact release commit.
- Nothing in the repository deploys the Telegram job: the root has no `Dockerfile`,
  `pyproject.toml`, `requirements.txt`, systemd unit, compose file or deploy job. The scheduled
  Telegram run is described only as a cron example (README "Run" section); the hourly index workflow is
  the only scheduled job the repository owns.
- Outside this ADR, the word `faibtes` appears in the ticket title in
  `docs/wayfinder-execution-order.md`. No artifact, target, host or environment defines it; item 1
  below records what the operator chose it to mean.
- The prerequisite decisions are recorded: secret storage, timezone, schedule ownership, failure
  alerting and overlap protection in ADR 0003, withdrawal and retention in ADR 0004, publication
  boundary in ADR 0005, and format and channel including sign-off in ADR 0006. Private-channel
  validation (issue #10) passed in the historical plain-text run; the current HTML render is pending.

Decisions the operator must make are marked `[INSERT DECISION]` with a recommendation.

## Decision

The release gate has five parts. All five must be satisfied and recorded; a partially satisfied gate
is not a release.

1. **Decisions closed and approved.** Every `[INSERT DECISION]` in ADRs 0001 through 0007 is
   replaced with an operator choice. Current HTML format sign-off remains part 3 of this gate; the
   historical plain-text result does not satisfy it. Issues #5, #6, #7, #9, #11 and #12 are closed by the operator.
   Issue #10 is covered by part 3. *No unresolved placeholder is allowed to survive into production.*
2. **CI evidence exists on GitHub.** A run of `ci.yml` on `main` or on a pull request target shows
   the compile step and the full test suite green, and the commits carrying the release are pushed
   so that run refers to them. Local test runs do not satisfy this part.
3. **Destination-channel validation passed.** `docs/validation/telegram-private-channel.md` has every
   core item at PASS or an explicitly accepted FAIL with a named owner, covering the current HTML
   render, official link, in-memory PDF upload, PDF size and caption bound. A NOT RUN / non-applicable
   disposition with a named owner is allowed only for an item that genuinely cannot apply, such as
   the non-PDF attachment check when no such attachment exists.
4. **Operational readiness confirmed.** The secret store, host timezone, schedule, failure alert and
   overlap protection chosen in ADR 0003 are installed on the named host, and one manual production
   run has been observed completing with exit code 0 and a state file written.
5. **Rollback rehearsed.** No message deletion is rehearsed, because ADR 0004 keeps messages as the
   permanent record. The rollback owner demonstrates stopping the cron entry and the hourly index
   workflow, confirms that current `public/index.*` can be reverted by a commit, and confirms that
   earlier Git history and channel messages remain.

Open operator inputs:

- **faibtes target.** Accepted: `faibtes` means the portable production deployment — the host that
  cloned or installed this repository, running Python 3.11 or newer with writable state and index
  directories, scheduled by the cron entry recorded in ADR 0003. There is no single named host, so a
  gate check names the host actually in use at release time.
- **Sign-off owner.** Accepted: the repository operator records the five PASS lines in the ticket,
  with the evidence links or commands used for each.
- **Rollback owner.** Accepted: the repository operator also owns rollback; no second person is
  available, so the same person stops the schedule and records the action.
- **Rollback action.** Accepted: remove or disable the cron entry and disable the `update-index`
  workflow, then stop publishing. Published Telegram messages are not deleted (ADR 0004 item 1) and
  earlier committed `public/index.*` snapshots stay in Git history; only current index files can be
  reverted by a commit. Re-enabling the cron entry resumes publishing; `state/` is not restored.
- **Whether a pilot period is a gate part.** Accepted: no separate pilot. One manual production run
  is part of part 4 and the first 24 hours of hourly runs are post-release observation, not a sixth
  gate.

## Consequences

- The gate cannot be passed by code quality alone: three of its five parts depend on operator
  infrastructure and on evidence from GitHub and Telegram that the repository cannot produce.
- Part 2 passed on GitHub Actions for checked-in commit `cef13761aed1f33d9847395588763a656e1a8a98`
  ([run 45844836581](https://github.com/darkrei08/apt-cron-albo-pretorio/actions/runs/45844836581));
  uncommitted worktree changes are not covered by that run.
- Part 3 has historical evidence for the plain-text format: one notice, its full field set, two PDF
  documents and bounded captions were observed. Current HTML format sign-off remains pending until
  the private checklist is rerun; the non-PDF attachment check remains accepted as non-applicable
  only for the historical notice.

- Recorded decisions are documented, but release status remains HOLD because current HTML format
  sign-off is pending under part 3.
- Rollback is limited by design: messages stay published and index history stays in Git, so rollback
  stops future publishing rather than erasing what was already published.
- If `faibtes` turns out to require packaging (container image, unit file), that work is a new
  ticket, not part of this gate.

## Evidence

- `.github/workflows/ci.yml`: triggers, Python 3.11, compile step, `unittest discover` step.
- `.github/workflows/update-index.yml`: hourly and manual dispatch refresh and index commit.
- Root listing: no `Dockerfile`, `pyproject.toml`, `requirements.txt`, compose file or ops unit.
- `docs/wayfinder-execution-order.md` (historical `faibtes` ticket title) and the current
  GitHub Actions records [CI run 45844836581](https://github.com/darkrei08/apt-cron-albo-pretorio/actions/runs/45844836581)
  and [index run 45787926316](https://github.com/darkrei08/apt-cron-albo-pretorio/actions/runs/45787926316).
- `README.md` "Run" (cron example only), "Download section" (historical private-channel delivery,
  no production schedule installed, one live index refresh observed) and "Production checks" (the checks that exist today).
- `docs/adr/0003-production-secret-storage-and-schedule.md`, `0004-withdrawal-and-retention.md`,
  `0005-publication-boundary.md`, `0006-notification-format-and-channel.md` (the decision inputs).
- `docs/validation/telegram-private-channel.md` (historical part 3 evidence; current HTML validation remains pending, with the non-PDF attachment check accepted non-applicable only for the historical notice).
- `docs/operations/production-runbook.md` (reproducible operator procedure and recommended protected-path contract; host execution remains unverified).
- `docs/operations/operator-handoff.md` (separate operator-only commands and evidence records for the protected host; it contains no credentials and records no GO).
- `docs/validation/production-rollout-2026-11-26.md` (operator sign-off, exact release installation, dry-run archive counts, credential blocker and current part-by-part gate status).

## Not verified

The release commit `979a03d756673da9ba38e4605e5062d0a8d74da9` has a successful CI run
([45904384468](https://github.com/darkrei08/apt-cron-albo-pretorio/actions/runs/45904384468)) and is installed at `/opt/apt-cron-pretorio` on host `herdr`. Parts 1 and 2 are PASS. Parts 3-5 remain BLOCKED: rotated production-classified credentials are absent from the protected environment files, so no real HTML validation, publication, manual production run, cron activation, 24-hour observation or rollback rehearsal has occurred. ADR 0014 classifies the GitHub Actions `APT_TEST_TELEGRAM_*` values as Destination-channel production credentials while the host cron keeps the ADR 0003 production-profile names. The archive dry run found 748 notices with 725 attachment errors and sent nothing. No GO is claimed; see `docs/validation/production-rollout-2026-11-26.md`.
