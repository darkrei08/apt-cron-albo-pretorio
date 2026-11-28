# Production runbook

This runbook defines the reproducible operator sequence for the Telegram publisher and the generated
public index. It does not contain credentials and does not claim that a host has been provisioned.
The release candidate must be an immutable Git commit that has passed CI and the private-channel gate.

## Recommended host contract

The operator selects the actual host in ticket 26. The following layout is the recommended portable
contract already accepted by ADR 0003:

- Python 3.11 or newer, with no third-party Python dependency.
- Code checkout: `/opt/apt-cron-pretorio`, owned by the deployment operator.
- Protected environment: `/etc/apt-cron/albo.env`, mode `0600`, readable only by the service user.
- State: `/var/lib/apt-cron/state/notices.json`, in a directory mode `0700` owned by the service user.
- Generated index: the checkout's `public/` directory, committed by the existing hourly GitHub Actions workflow.
- Lock: `/run/apt-cron/apt-cron.lock`, provisioned by the administrator and writable by the service user.
- Failure destination: cron `MAILTO` for the service owner plus GitHub Actions notifications for index refresh failures.

The production host, public-index destination and operational owner remain explicit inputs to ticket 26.
The locations above are a recommended contract, not evidence that those resources exist.

## Install and verify a candidate

Run as the service user after the operator has selected the host and checked out the exact candidate:

```sh
cd /opt/apt-cron-pretorio
git rev-parse HEAD
python3 --version
python3 -m py_compile apt_cron.py tests/test_apt_cron.py
python3 -m unittest discover -s tests -v
```

Create the protected paths as an administrator, then place the rotated credentials in the environment
file out of band. Never put a token in a command, crontab, issue, log or repository file:

```sh
install -d -m 0700 -o apt-cron -g apt-cron /var/lib/apt-cron/state
install -d -m 0750 -o root -g apt-cron /etc/apt-cron
install -d -m 0750 -o root -g apt-cron /run/apt-cron
install -m 0660 -o apt-cron -g apt-cron /dev/null /run/apt-cron/apt-cron.lock
install -d -m 0750 -o apt-cron -g apt-cron /var/log/apt-cron
touch /etc/apt-cron/albo.env
chown apt-cron:apt-cron /etc/apt-cron/albo.env
chmod 0600 /etc/apt-cron/albo.env
```

The exact service account and group are host decisions. The commands are a template and must be
adapted before execution; they are not a provisioning record.

## Seed, validate and activate

1. **Seed:** with the rotated production credentials loaded from the protected `APT_ENV_FILE`, run
   one normal invocation and verify exit code `0`, `published: 0`, a version-2 state file and generated current
   index files. The first normal run must not send a Telegram message.
2. **Private validation:** use an isolated state path and the current checklist. Verify HTML rendering,
   official links, every PDF upload, caption and size limits, failure behavior and the absence of
   credential values in output. Do not reuse production state for this test.
3. **Archive backfill:** after the private gate passes, run `python3 apt_cron.py --backfill` with
   `APT_TELEGRAM_PROFILE=production` and the production state path to publish the whole archive
only under explicit pilot authorization or after a recorded GO. It publishes acts already seeded by
   step 1 because selection uses `sent_messages`, not `notices`.
4. **Manual production run:** after the backfill completes, run once with
   `APT_TELEGRAM_PROFILE=production` and the production state path under the same authorization.
   Record the immutable commit, exit code `0`, state-file mtime and index result, and retain logs
   without secrets.
5. **Activate the hourly job:** install the following crontab shape only after the GO is recorded in
   ticket #32. A pre-GO pilot remains cron-disabled:

```cron
CRON_TZ=Europe/Rome
MAILTO=operator@example.invalid
0 * * * * cd /opt/apt-cron-pretorio && TZ=Europe/Rome /usr/bin/flock -n /run/apt-cron/apt-cron.lock /bin/sh -c 'export APT_ENV_FILE=/etc/apt-cron/albo.env APT_TELEGRAM_PROFILE=production APT_STATE_PATH=/var/lib/apt-cron/state/notices.json APT_INDEX_DIR=/opt/apt-cron-pretorio/public; exec /usr/bin/python3 apt_cron.py'
```

Replace the placeholder mailbox and host paths before installation. `CRON_TZ` is a crontab variable
line, while `TZ` is part of the command environment. The separate `Publish acts and reports` GitHub
Actions workflow uses the `APT_TEST_TELEGRAM_*` repository secrets with the `test` profile. Under
[ADR 0014](../adr/0014-production-credential-override-and-destination-channel.md) those values are
production-classified Destination-channel credentials; the host cron remains a different job with the
protected production profile. This classification does not change the release gate.

## Monitor and observe

For the first 24 hours, the operator records each hourly run's exit status, state-file update, source
notice count, Telegram publication count and index workflow result. A non-zero cron run, missing state
update, unexpected publication count, failed index workflow or lock contention that persists beyond
one interval is an incident. The crontab intentionally leaves stdout/stderr unredirected so cron's
`MAILTO` receives the redacted failure line; if persistent logs are required, add an external logging
handler that preserves the non-zero exit status. GitHub Actions notifications cover the index workflow.
Ticket 31 must name the actual observer and alert destination.

The hourly GitHub workflow writes a human-readable report to the Actions job summary. Open the latest
`Publish acts and reports` run and read the `Build hourly and daily reports` step. The report shows the
check time in `Europe/Rome`, the outcome, and counts for acts in the current window, published acts,
new, changed, removed and unchanged. `no_changes` means no act was added, modified or withdrawn in the
current publication window.

For a local check with no credentials and no repository write:

```sh
cp public/index.json /tmp/index-before.json
APT_INDEX_DIR=/tmp/cron-index-check python3 apt_cron.py --refresh-index
python3 hourly_report.py --before /tmp/index-before.json --after /tmp/cron-index-check/index.json --stdout
```

For the publication state, run `python3 apt_cron.py --dry-run` and feed its JSON to
`python3 hourly_report.py --stats <stats.json> --stdout`. `published: 0` means no new or changed act
would be sent to the destination channel.

## Rollback

1. Remove or disable the cron entry and disable the hourly index workflow. Confirm no new publication
   occurs; do not delete Telegram messages.
2. Preserve the state file and logs for diagnosis. Do not restore an older state snapshot unless the
   release owner explicitly approves that data operation.
3. Revert `public/index.*` with a normal Git commit to the last approved snapshot. Do not rewrite Git
   history or force-push.
4. Record the candidate commit, stop time, last successful run, index commit and reason. Re-enable the
   schedule only after the release owner approves a new candidate and repeats the applicable gates.

## Gate mapping

- Ticket 26: name the host, index destination and operational owner.
- Ticket 28: rotate credentials and record only protected paths, ownership and modes.
- Ticket 29: execute and evidence the install, seed, manual run, activation and rollback steps above.
- Ticket 30: rerun the current private-channel checklist and one manual production run.
- Ticket 31: name the observer, alert destinations and rollback trigger.
- Ticket 32: record the final go/no-go decision against ADR 0007. This runbook is preparation, not
  production approval.

The separate operator checklist in [operator-handoff.md](operator-handoff.md) lists the exact commands
and evidence records for installation, credential rotation, seed, private validation, real backfill,
manual run, cron activation, 24-hour monitoring and rollback rehearsal. It contains no credentials
and does not record a GO.
