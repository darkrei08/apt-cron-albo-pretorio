# 0003 — Production secret storage and schedule ownership

- Status: proposed (operator input required)
- Decision record: GitHub issue #9 (open)

## Context

`apt_cron.py` needs two credentials and one clock, and the repository records none of them:

- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are read from the environment
  (`apt_cron.py:409-410`). `README.md:36-46` lists them as required in every mode except
  `--dry-run`, with the note "keep it outside Git". No secret store, file permission, rotation
  procedure or owner is recorded anywhere.
- The publication-window filter uses `date.today()` (`apt_cron.py:422`), so the "today" that bounds
  `cntDataInizioPubblicazione`/`cntDataFinePubblicazione` is the host's local date. No timezone is
  configured, so a host in UTC and a host in `Europe/Rome` can disagree on the boundary date for up
  to two hours around midnight.
- The schedule is an advisory cron line in `README.md` (`0 * * * *` with `CRON_TZ` and `TZ` set to
  `Europe/Rome`). No installable unit, timer, supervisor or host is named. ADR 0001 §7 states that the
  schedule is the operator's responsibility and installs nothing.
- Failure handling exists but has no destination: a runtime error prints one redacted line to stderr
  and exits `1` (`apt_cron.py:434-438`), bad `APT_PAGE_SIZE` exits `2` via `parser.error`
  (`apt_cron.py:414-417`), and a missing credential (outside `--dry-run`) also exits `2`
  (`apt_cron.py:411-412`). Nothing alerts anyone, and no run lock prevents two overlapping runs from
  both publishing the same notice.

Decisions the operator must make are marked `[INSERT DECISION]` with a recommendation.

## Decision

1. **Credential store.** `[INSERT DECISION]` — *Recommendation: a `systemd` `EnvironmentFile`
   (e.g. `/etc/apt-cron/albo.env`) owned by the service user with mode `0600`, referenced as
   `EnvironmentFile=` and never committed; a protected cron file is the fallback when systemd is
   unavailable.* The store must keep both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` outside Git
   and outside shell history, and must be readable only by the service user.
2. **Timezone.** `[INSERT DECISION]` — *Recommendation: `Europe/Rome` for the host and the timer,
   because the source publishes Italian public-administration dates in local time and the boundary
   date is the only thing `date.today()` controls.* Whichever is chosen must be set explicitly on
   the scheduled unit, not inherited from an unrecorded host default.
3. **Schedule owner and host.** `[INSERT DECISION]` — *Recommendation: named operator host
   running a `systemd` timer at hourly cadence, `Timezone=Europe/Rome`, installed and monitored by a
   named person; the cron line in `README.md` stays an example only.* The owner is also the person
   who receives failure alerts.
4. **Failure path.** `[INSERT DECISION]` — *Recommendation: bind the run to an `OnFailure=` unit
   that notifies a named operator destination (mail or Telegram), keeping the current contract of
   one redacted stderr line and a non-zero exit as the machine-readable signal.* The redaction in
   `redact_credentials` (`apt_cron.py:383-385`) means the alert can quote stderr safely.
5. **Concurrent-run protection.** `[INSERT DECISION]` — *Recommendation: rely on the scheduler's own
   non-overlap (`systemd` timer or a cron lock), not on code, because the script has no lock and
   adding one would change runtime behavior.* With an hourly cadence and a 20-second HTTP timeout
   per request, overlap requires a run longer than an hour; the operator should still confirm it.

## Consequences

- Until items 1-5 are filled in, the deployment is reproducible only for a reader who already knows
  the host: the repository documents the variables but not where their values live.
- `date.today()` stays timezone-dependent by design. Choosing the host timezone is sufficient; no
  code change is implied by this ADR.
- A failure after the message is sent but before all documents can leave a notice marked published
  without every PDF: the fingerprint is saved after the message, while each `sent_documents` entry is
  saved only after that document succeeds (`apt_cron.py:291-310`). The next run does not republish an
  unchanged notice, so recovery needs a changed notice or manual state handling.
- Recording a secret store here does not authorize any commit of credentials: `state/` and
  `cron.log` are ignored (`.gitignore`), the environment file lives outside the repository.

## Evidence

- `apt_cron.py`: environment reads at `:409-410`, config assembly at `:419-433` with
  `date.today()` at `:422`, error redaction in `redact_credentials` `:383-385`, exit codes at
  `:411-412`, `:414-417`, `:434-438`.
- `README.md:36-46` (configuration table), `:63-68` (hourly cron example and the "prefer a
  protected environment" note), `:87-92` (production checks).
- `docs/adr/0001-hourly-acquisition-and-metadata-contract.md` §7 (operator owns the schedule).
- `docs/wayfinder-execution-order.md` row 4 (this ticket blocked on the same four choices).

## Not verified

No production schedule, timer, environment file or alert destination exists in this repository, and
no run has been made against a real host. The timezone/host claim is a recommendation about
deployment, not an observation of a deployed system.
