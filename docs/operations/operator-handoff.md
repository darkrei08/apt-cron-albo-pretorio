# Operator handoff for the protected production host

This is the operator-only checklist for the actions that cannot be performed inside this
repository. It contains commands and evidence fields, not credentials. The repository does not
have access to `/opt/apt-cron-pretorio`, `/etc/apt-cron`, `/var/lib/apt-cron`, `/run/apt-cron`,
`/var/log/apt-cron` or the private Telegram channel.

[ADR 0015](../adr/0015-actions-sole-publisher.md) makes GitHub Actions the only scheduler and
publisher. Host-local publication and cron activation instructions below are historical; do not
activate them while ADR 0015 stands.

ADR 0007 and issue #32 remain **HOLD**. Opening a pull request and seeing CI pass only satisfies
part 2; it does not authorize publication. Steps 5-9 are operator execution. Steps 5-6 and 9 may run
before GO only under an explicit pilot authorization recorded by the release owner; that pilot must
name the owner, the private destination channel and its exact scope, and it authorizes both the real
backfill and one manual production run plus the rollback rehearsal. Steps 7-8 require a recorded GO.
Without that pilot authorization, do not run any of steps 5-9 while the gate is HOLD. This checklist
alone never grants approval.

All placeholders in angle brackets must be replaced by the operator. No token, chat id or other
secret value belongs in this file, a commit, a shell history entry, a crontab, an issue or a log.

## 1. Install the exact CI-green candidate

The operator owns checkout and installation on the named host.

```sh
cd /opt/apt-cron-pretorio
git fetch origin
git checkout --detach <EXACT_CI_GREEN_COMMIT>
git rev-parse HEAD
git status --short
python3 --version
python3 -m py_compile apt_cron.py tests/test_apt_cron.py
python3 -m unittest discover -s tests -v
```

Record: host name, exact commit, CI run URL, Python version, compile result, test count and clean
worktree status. A different commit does not satisfy the gate.

## 2. Configure rotated credentials without exposing them

The production credentials for scheduled publication are the GitHub Actions repository secrets
`APT_TEST_TELEGRAM_BOT_TOKEN` and `APT_TEST_TELEGRAM_CHAT_ID`. Under
[ADR 0014](../adr/0014-production-credential-override-and-destination-channel.md) they are
production-classified credentials for the Destination channel. Rotate them in repository settings and
record only rotation date, owner and a redacted evidence link in
[production-credentials-evidence.md](../validation/production-credentials-evidence.md).

For explicit manual CLI runs only, the script supports `APT_ENV_FILE` with the legacy production
names `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`; keep `APT_TELEGRAM_PROFILE=production` explicit.
Isolated checks use a separate gitignored env file with `APT_TELEGRAM_PROFILE=test` and the
`APT_TEST_TELEGRAM_*` names. ADR 0015 keeps the host cron inactive; there is no hourly host job to
install.

```sh
sudo touch /etc/apt-cron/albo.env
sudo chown apt-cron:apt-cron /etc/apt-cron/albo.env
sudo chmod 0600 /etc/apt-cron/albo.env
stat -c '%a %U:%G %n' /etc/apt-cron/albo.env
```

Do not use `cat`, `echo`, `source`, or a command-line assignment for the credential values. Verify
only metadata with `stat`; do not read the file contents in a terminal, ticket, log or transcript.

Record: protected path, owner, group, mode, rotation date and the operator who performed it. Leave
the values themselves unrecorded.

## 3. Seed state without publishing

Use the explicit seeder. Do not run `apt_cron.py` in publish mode while the gate is HOLD.

```sh
python3 publication_state.py \
  --index /opt/apt-cron-pretorio/public/index.json \
  --state /var/lib/apt-cron/state/notices.json
```

Expected: exit code `0` and a version-2 state file. Confirm with a separate dry run that
`published: 0` before any publication. No message may appear in the channel.

Use isolated paths from `docs/validation/telegram-private-channel.md` for the private HTML
validation. Do not reuse production state for that check.

## 4. Private Telegram HTML validation

Follow `docs/validation/telegram-private-channel.md` on the current release candidate only under
explicit operator authorization for a Destination-channel send; [ADR 0014](../adr/0014-production-credential-override-and-destination-channel.md)
classifies that chat as production and does not authorize publication. Use isolated state and index
paths. Update that record with PASS, FAIL or NOT RUN results for V2, V3, V4, V5 and V8. The local
synthetic tests in `tests/test_apt_cron.py` cover payload construction and escaping only; they do not
replace a live observation.

Record: evidence links or message IDs in the private channel, exact commit, and named owner of any
accepted non-applicable item.

## 5. Real archive backfill, oldest to newest (release execution)

This is the production publication to the private destination channel, not the isolated validation
channel. It is irreversible: Telegram messages are permanent. Run it only under the explicit pilot
authorization described above or after a recorded GO. Disable the `update-index.yml` workflow before
this manual publication. After the run, reconcile the committed index with the manual result before
re-enabling the workflow; otherwise the next scheduled run can repeat the publication. No host cron is
active under ADR 0015.

```sh
export APT_ENV_FILE=/etc/apt-cron/albo.env
export APT_TELEGRAM_PROFILE=production
export APT_STATE_PATH=/var/lib/apt-cron/state/notices.json
export APT_INDEX_DIR=/opt/apt-cron-pretorio/public
export TZ=Europe/Rome
/usr/bin/python3 apt_cron.py --backfill --dry-run
/usr/bin/python3 apt_cron.py --backfill
```

Expected on the real run: exit code `0`; acts published oldest first; the newest act sent by this
backfill is the last message in the private destination channel; the result contains no
`attachment_errors` or `document_errors`. Archive selection in
`select_changes(..., archive=True)` compares `sent_messages` with the current fingerprint, not
`notices`; the step 3 seed populates `notices` but leaves `sent_messages` empty, so those seeded
notices are selected and published. The simulated-HTTP test
`test_backfill_publishes_notices_seeded_by_a_normal_run` verifies that contract. Do not infer from
`notices` alone that the backfill is complete. If either error count is non-zero, rerun the unchanged
backfill to retry only missing documents and confirm that no duplicate text message is sent.

Record: start and end time, result JSON, total published notices, first and last act identifiers,
first and last publication dates, and the operator's visual confirmation that the newest act sent by
the backfill is the last message.

## 6. Manual production run (release execution)

This single normal-mode run is the gate part 4 evidence run. A pilot authorization is required to
collect this evidence before GO; the run follows the pilot backfill, is the only normal-mode run
allowed, and does not activate the schedule. Keep `update-index.yml` disabled during this run and
reconcile its committed index before re-enabling it. Without a pilot, this step is not authorized and
the gate cannot reach GO. After the backfill is complete:

```sh
export APT_TELEGRAM_PROFILE=production
/usr/bin/flock -n /run/apt-cron/apt-cron.lock /usr/bin/python3 apt_cron.py \
  >> /var/log/apt-cron/manual-run.log 2>&1
echo $?
```

Expected: exit code `0`, state-file mtime updated, no unexpected duplicate publication. A busy lock
is not a successful run. Logs must contain only redacted error text; verify without printing any
credential value.

Record: exact commit, exit code, state path and mtime, notice count, published count, log path and
index result.

## 7. Keep the host cron inactive (release execution)

Do not activate a host cron. ADR 0015 assigns scheduling, publication and state commit to the
hourly GitHub Actions workflow alone. The previous crontab template is historical and is not an
activation instruction. Record instead the workflow schedule, the named monitoring owner and the
absence of a host cron entry.

## 8. Observe the first 24 hours

For each hourly run, record the Actions job status, outcome, notice count, published count, index
commit and report artifact. Useful read-only commands:

```sh
gh run list --repo darkrei08/apt-cron-albo-pretorio --workflow update-index.yml --limit 24
gh run view <RUN_ID> --repo darkrei08/apt-cron-albo-pretorio
git -C /opt/apt-cron-pretorio log --oneline -5
```

A failed workflow or unexpected publication count is an incident. Disable the workflow and follow
the rollback step; no host cron is active.

Record: observer name, alert address, 24-hour window, table of hourly results and incident decision.

## 9. Rollback rehearsal

Rehearsal stops future publication; it does not delete Telegram messages. ADR 0004 keeps published
messages as the permanent record. Rehearse under the explicit pilot authorization or after a recorded
GO; do not treat an unauthorized rehearsal as gate evidence.

```sh
gh workflow disable update-index.yml --repo darkrei08/apt-cron-albo-pretorio
```

No host cron entry exists to edit under ADR 0015.

Confirm no new publication occurs. Revert only the current index files with a normal commit, then
publish that commit through the normal review path so the index workflow does not overwrite it:

```sh
git -C /opt/apt-cron-pretorio log --oneline -- public/index.json public/index.md public/index.html
git -C /opt/apt-cron-pretorio switch -c rollback/index-<TIMESTAMP>
git -C /opt/apt-cron-pretorio restore --source=<APPROVED_INDEX_COMMIT> -- public/index.json public/index.md public/index.html
git -C /opt/apt-cron-pretorio commit --only -m "docs(index): revert to approved snapshot" -- public/index.json public/index.md public/index.html
git -C /opt/apt-cron-pretorio push -u origin rollback/index-<TIMESTAMP>
gh pr create --repo darkrei08/apt-cron-albo-pretorio --base main --head rollback/index-<TIMESTAMP> \
  --title "docs(index): restore approved snapshot" \
  --body "Restore public/index.* to the last approved snapshot after rollback rehearsal."
```

Merge that PR only after the normal human approval. Do not rewrite Git history or force-push. Preserve state and logs. Record candidate commit, stop
time, last successful run, index commit, reason and the owner who approved or rejected
re-activation. Re-enable the workflow only after a new explicit GO. Do not re-enable a host cron while ADR 0015 stands.

## 10. Gate decision

Ticket #32 and ADR 0007 stay HOLD until all five parts have recorded PASS evidence:

1. decisions closed and approved;
2. CI green on the exact release commit;
3. current private-channel validation passed;
4. protected host installed, credentials rotated and one manual production run observed under the
   pilot authorization;
5. rollback rehearsed under the same pilot authorization.

Record the GO only after those five PASS lines and their evidence links exist. Steps 7-8 then become
authorized.

This document is preparation only. It does not record a GO and does not authorize sending any act.
