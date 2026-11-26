# 0007 — Release gate for the faibtes production rollout

- Status: proposed (operator input required)
- Decision record: GitHub issue #13 (open, blocked by issues #9, #10, #11, #12)

## Context

There is no deployment artifact and no production run. The repository contains one workflow and no
packaging or ops file:

- `.github/workflows/ci.yml` runs on push to `main` and on pull requests: it checks out, sets up
  Python 3.11, runs `python3 -m py_compile apt_cron.py tests/test_apt_cron.py` and then
  `python3 -m unittest discover -s tests -v`.
- `docs/wayfinder-execution-order.md` records "GitHub Actions run inventory: zero runs at
  discovery time". The master verified with `gh run list -R github.com/darkrei08/apt-cron-albo-pretorio
  --limit 5 --json databaseId,status,conclusion,headBranch` that no run existed and with
  `git status --short --branch --untracked-files=all` that `main` was ahead by six at authoring time.
  Both are time-bound observations; part 2 of the gate must re-check them at release time. Local
  passing tests were the only CI evidence at that point.
- Nothing in the repository deploys anything: the root has no `Dockerfile`, no `pyproject.toml`, no
  `requirements.txt`, no systemd unit, no compose file and no deploy job. The scheduled run is
  described only as a cron example (`README.md:63-68`).
- Outside this ADR, the word `faibtes` appears in the ticket title in
  `docs/wayfinder-execution-order.md`. No artifact, target, host or environment defines it.
- The four prerequisite decisions are open: secret storage and schedule (issue #9, ADR 0003),
  private-channel validation (issue #10, checklist), withdrawal and retention (issue #11, ADR 0004),
  and publication boundary (issue #6, ADR 0005) — plus the format decision (issue #7, ADR 0006).

Decisions the operator must make are marked `[INSERT DECISION]` with a recommendation.

## Decision

The release gate has five parts. All five must be satisfied and recorded; a partially satisfied gate
is not a release.

1. **Decisions closed and approved.** ADRs 0001 through 0007 have every `[INSERT DECISION]`
   replaced with an operator choice, and issues #5, #6, #7, #9, #11 and #12 are closed by the
   operator. Issue #10 is covered by part 3. *No placeholder is allowed to survive into production.*
2. **CI evidence exists on GitHub.** A run of `ci.yml` on `main` or on a pull request target shows
   the compile step and the full test suite green, and the commits carrying the release are pushed
   so that run refers to them. Local test runs do not satisfy this part.
3. **Private-channel validation passed.** `docs/validation/telegram-private-channel.md` has every
   item at PASS (or an explicitly accepted FAIL with a named owner), covering plain-text render,
   official link, `sendDocument` by URL, PDF size, caption bound and the `message_id` decision.
4. **Operational readiness confirmed.** The secret store, host timezone, schedule, failure alert and
   overlap protection chosen in ADR 0003 are installed on the named host, and one manual production
   run has been observed completing with exit code 0 and a state file written.
5. **Withdrawal and rollback rehearsed.** The ADR 0004 removal procedure has been exercised once
   against the real channel, the retention windows are recorded, and a rollback owner can stop the
   schedule and remove published messages without contacting anyone else.

Open operator inputs:

- **faibtes target.** `[INSERT DECISION]` — *Recommendation: define `faibtes` as a named host or
  environment in one sentence here (hostname/environment, Python version ≥ 3.11, writable state and
  index directories) before the gate can be evaluated, since today the term is undefined in the
  repository.*
- **Sign-off owner.** `[INSERT DECISION]` — *Recommendation: one named person who records the five
  PASS lines in the ticket, with the evidence links or commands used for each.*
- **Rollback owner.** `[INSERT DECISION]` — *Recommendation: a named person, distinct from the
  sign-off owner where staffing allows, who owns disabling the schedule and executing the removal
  procedure.*
- **Rollback action.** `[INSERT DECISION]` — *Recommendation: disable the scheduled unit, then
  delete the published messages and the regenerated index following ADR 0004; state that the
  sequence is reversible only by re-enabling the schedule, because `state/` is not restored.*
- **Whether a pilot period is a gate part.** `[INSERT DECISION]` — *Recommendation: no separate
  pilot; make one manual production run part of part 4 and treat the first 24 hours of hourly runs
  as post-release observation, not as a sixth gate.*

## Consequences

- The gate cannot be passed by code quality alone: three of its five parts depend on operator
  infrastructure and on evidence from GitHub and Telegram that the repository cannot produce.
- Part 2 stays red until commits are pushed; that is deliberate, since an unpushed tree cannot be
  the artifact anyone else deploys or audits.
- Part 3 depends on a checklist that has never run, so the schedule for the release is bounded by
  operator availability, not by development work.
- If `faibtes` turns out to require packaging (container image, unit file), that work is a new
  ticket, not part of this gate.

## Evidence

- `.github/workflows/ci.yml`: triggers, Python 3.11, compile step, `unittest discover` step.
- Root listing: no `Dockerfile`, `pyproject.toml`, `requirements.txt`, compose file or ops unit.
- `docs/wayfinder-execution-order.md:24` (ticket title with `faibtes`), `:38` (zero Actions runs),
  `:42` (remaining blockers).
- `README.md:63-68` (cron example only), `:85` (nothing sent live, no production schedule
  installed), `:87-92` (production checks that exist today).
- `docs/adr/0003-production-secret-storage-and-schedule.md`, `0004-withdrawal-and-retention.md`,
  `0005-publication-boundary.md`, `0006-notification-format-and-channel.md` (the decision inputs).
- `docs/validation/telegram-private-channel.md` (part 3 evidence format).

## Not verified

The GitHub Actions run count and the six-commit divergence were verified with the exact commands
recorded in Context at ADR authoring time; they are not re-verified by this document and must be
checked again at release. `faibtes` has no definition anywhere in the repository, so no part of the
gate can be evaluated against a concrete target yet.
