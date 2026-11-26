# 0003 — Production secret storage and schedule ownership

- Status: accepted
- Decision record: GitHub issue #9 (open)

## Context

`apt_cron.py` needs two credentials and one clock, and the repository records none of them:

- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are read from the environment
  (`apt_cron.py:418-419`). `README.md:38-48` lists them as required in every mode except
  `--dry-run` and `--refresh-index`, with the note "keep it outside Git". No secret store, file
  permission, rotation procedure or owner is recorded anywhere.
- The publication-window filter uses `date.today()` (`apt_cron.py:431`), so the "today" that bounds
  `cntDataInizioPubblicazione`/`cntDataFinePubblicazione` is the host's local date. No timezone is
  configured, so a host in UTC and a host in `Europe/Rome` can disagree on the boundary date for up
  to two hours around midnight.
- The schedule is an advisory cron line in `README.md` (`0 * * * *` with `CRON_TZ` and `TZ` set to
  `Europe/Rome`) plus the hourly index workflow (`update-index.yml`). No installable unit, timer,
  supervisor or host is named. ADR 0001 §7 states that the schedule is the operator's
  responsibility and installs nothing.
- Failure handling exists but has no in-script destination: a runtime error prints one redacted line
  to stderr and exits `1` (`apt_cron.py:453-455`), bad `APT_PAGE_SIZE` exits `2` via `parser.error`
  (`apt_cron.py:426-428`), and a missing credential (outside `--dry-run` and `--refresh-index`) also
  exits `2` (`apt_cron.py:419-422`). The chosen deployment adds cron `MAILTO` and a `flock -n` wrapper;
  the script itself has no lock.

Operator decisions are recorded below.

## Decision

1. **Credential store.** Accepted: a protected cron environment file, for example
   `/etc/apt-cron/albo.env`, owned by the service user with mode `0600`, sourced by the cron command
   and never committed. `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` live only in that file; no
   credential is written inline in the crontab, in shell history or in the repository.
   The operator may instead keep the file inside the repository as a gitignored local `.env`, or
   point `APT_ENV_FILE` at any other path. `apt_cron.py:load_env_file` reads it before argparse,
   accepts `KEY=VALUE` with `#` comments and an optional `export ` prefix, and uses
   `os.environ.setdefault`, so a value already exported by the environment wins over the file.
   `.env` and `.env.*` are gitignored; variable names and placeholders are documented in the README.
   Base64 is not encryption: an encoded token in the repository or in Git history
   is a leaked token, so base64 (or any other repository-stored encoding) is rejected as a storage
   mechanism and no decryption path exists in the script.
2. **Timezone.** Accepted: `Europe/Rome`, set explicitly by the schedule (`CRON_TZ` and `TZ` on the
   cron line, `TZ` in the hourly index workflow), never inherited from an unrecorded host default.
3. **Schedule owner and host.** Accepted: the deployment is portable. The hourly cron runs on
   whichever host cloned or installed the repository, and it is managed by whoever can maintain the
   repository; that maintainer is also the failure-alert recipient. No named host or unit file is
   part of the deliverable.
4. **Failure path.** Accepted: cron `MAILTO` sends the single redacted stderr line to the
   maintainer's mailbox. The email does not carry the exit status; that stays visible in the cron
   daemon log and in the script's error line. Exit codes remain `1` for a runtime failure and `2`
   for a configuration error. Runtime errors pass through `redact_credentials`
   (`apt_cron.py:387-389`); argparse configuration errors print only usage text and do not echo
   environment values. The cron command sources the environment file but never prints it, so the
   mail body contains no credential value.
5. **Concurrent-run protection.** Accepted: wrap the cron command in `flock -n` so a second hourly
   invocation exits without publishing. No lock is added to the script; the scheduler owns overlap.

## Consequences

- Items 1-5 make the deployment reproducible from this document alone: the variables, where their
  values live, the timezone, the schedule, the alert destination and overlap protection are recorded.
- `date.today()` stays timezone-dependent by design. Choosing `Europe/Rome` as the cron environment
  is sufficient; no code change is implied by this ADR.
- A failure after the message is sent but before all documents can leave a notice marked published
  without every PDF: the fingerprint is saved after the message, while each `sent_documents` entry is
  saved only after that document succeeds (`apt_cron.py:297-317`). The next run does not republish an
  unchanged notice, so recovery needs a changed notice or manual state handling.
- Recording a secret store here does not authorize any commit of credentials: `state/` and
  `cron.log` are ignored (`.gitignore`), and the local env file is ignored as well unless it is the
  committed `.env.example` template. Files loaded by the script are plain text on disk, so the
  permission and ownership of the file remain the operator's responsibility.

## Evidence

- `apt_cron.py`: `load_env_file` and its `os.environ.setdefault` precedence, environment reads and
  config assembly in `main` (`date.today()` included), error redaction in `redact_credentials`,
  exit codes for a missing credential, a bad `APT_PAGE_SIZE` and a runtime failure.
- `.gitignore`: `.env` and `.env.*` ignored; no credential template is committed.
- `README.md`: configuration table (`:38-48`), protected environment file, hourly cron example and
  the `--refresh-index` command (`:67-88`), production checks (`:106-113`).
- `.github/workflows/update-index.yml`: hourly index refresh with `TZ: Europe/Rome`.
- `docs/adr/0001-hourly-acquisition-and-metadata-contract.md` §7 (operator owns the schedule).
- `docs/wayfinder-execution-order.md` row 4 (this ticket blocked on the same four choices).

## Not verified

No production environment file, cron installation or mail destination exists in this repository, and
no run has been made against a real host. The timezone and alert claims describe the deployment the
operator chose, not an observation of a deployed system.
