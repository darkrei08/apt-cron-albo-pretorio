# 0007 — Release gate for the faibtes production rollout

- Status: proposed (gate not satisfied: private-channel validation and final recheck pending)
- Decision record: GitHub issue #13 (open, blocked by issues #9, #10, #11, #12)

## Context

There is no deployment artifact and no production run. The repository contains two workflows and no
packaging or ops file:

- `.github/workflows/ci.yml` runs on push to `main` and on pull requests: it checks out, sets up
  Python 3.11, runs `python3 -m py_compile apt_cron.py tests/test_apt_cron.py` and then
  `python3 -m unittest discover -s tests -v`.
- `.github/workflows/update-index.yml` runs hourly and on manual dispatch: it runs
  `apt_cron.py --refresh-index` with `TZ: Europe/Rome` and commits changed `public/index.*` with the
  repository `GITHUB_TOKEN`. It needs no Telegram credentials.
- `docs/wayfinder-execution-order.md` records "GitHub Actions run inventory: zero runs at
  discovery time". The master verified with `gh run list -R github.com/darkrei08/apt-cron-albo-pretorio
  --limit 5 --json databaseId,status,conclusion,headBranch` that no run existed and with
  `git status --short --branch --untracked-files=all` that `main` was ahead by six at authoring time.
  Both are time-bound observations; part 2 of the gate must re-check them at release time. Local
  passing tests were the only CI evidence at that point.
- Nothing in the repository deploys the Telegram job: the root has no `Dockerfile`,
  `pyproject.toml`, `requirements.txt`, systemd unit, compose file or deploy job. The scheduled
  Telegram run is described only as a cron example (`README.md:76-83`); the hourly index workflow is
  the only scheduled job the repository owns.
- Outside this ADR, the word `faibtes` appears in the ticket title in
  `docs/wayfinder-execution-order.md`. No artifact, target, host or environment defines it; item 1
  below records what the operator chose it to mean.
- The prerequisite decisions are recorded: secret storage, timezone, schedule ownership, failure
  alerting and overlap protection in ADR 0003, withdrawal and retention in ADR 0004, publication
  boundary in ADR 0005, and format and channel in ADR 0006 except final sign-off. Private-channel
  validation (issue #10) has not run.

Decisions the operator must make are marked `[INSERT DECISION]` with a recommendation.

## Decision

The release gate has five parts. All five must be satisfied and recorded; a partially satisfied gate
is not a release.

1. **Decisions closed and approved.** Every `[INSERT DECISION]` in ADRs 0001 through 0007 is
   replaced with an operator choice, except format sign-off in ADR 0006 item 6, which is satisfied by
   the recorded result of part 3. Issues #5, #6, #7, #9, #11 and #12 are closed by the operator.
   Issue #10 is covered by part 3. *No unresolved placeholder is allowed to survive into production.*
2. **CI evidence exists on GitHub.** A run of `ci.yml` on `main` or on a pull request target shows
   the compile step and the full test suite green, and the commits carrying the release are pushed
   so that run refers to them. Local test runs do not satisfy this part.
3. **Private-channel validation passed.** `docs/validation/telegram-private-channel.md` has every
   core item at PASS or an explicitly accepted FAIL with a named owner, covering plain-text render,
   official link, in-memory PDF upload, PDF size and caption bound. A NOT RUN / non-applicable
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
- Part 2 stays red until the CI workflow has run on GitHub. The one live evidence now available is a
  manual `--refresh-index` run against the source (exit code `0`, 14 notices, index files written, no
  state file), which is not part 2 and does not replace it.
- Part 3 depends on a checklist that has never run, so the schedule for the release is bounded by
  operator availability and by the test credentials the operator has not supplied yet.
- Part 1 now depends only on ADR 0006 item 6 and the live validation in part 3.
- Rollback is limited by design: messages stay published and index history stays in Git, so rollback
  stops future publishing rather than erasing what was already published.
- If `faibtes` turns out to require packaging (container image, unit file), that work is a new
  ticket, not part of this gate.

## Evidence

- `.github/workflows/ci.yml`: triggers, Python 3.11, compile step, `unittest discover` step.
- `.github/workflows/update-index.yml`: hourly and manual dispatch refresh and index commit.
- Root listing: no `Dockerfile`, `pyproject.toml`, `requirements.txt`, compose file or ops unit.
- `docs/wayfinder-execution-order.md:24` (ticket title with `faibtes`), `:48` (zero Actions runs),
  `:50` (remaining blockers).
- `README.md:76-83` (cron example only), `:104` (nothing sent live, no production schedule
  installed, one live index refresh observed), `:106-113` (production checks that exist today).
- `docs/adr/0003-production-secret-storage-and-schedule.md`, `0004-withdrawal-and-retention.md`,
  `0005-publication-boundary.md`, `0006-notification-format-and-channel.md` (the decision inputs).
- `docs/validation/telegram-private-channel.md` (part 3 evidence format; every item NOT RUN).

## Not verified

The GitHub Actions run count and the commit divergence recorded in Context were verified with the
exact commands recorded there at ADR authoring time; they are not re-verified by this document and
must be checked again at release. The `update-index` workflow has never run on GitHub Actions. No
part of the gate has been evaluated against the real host.
