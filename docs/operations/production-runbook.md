# Production runbook

This runbook defines the reproducible operator sequence for the Telegram publisher and the generated
public index. It does not contain credentials and does not claim that a host has been provisioned.
The release candidate must be an immutable Git commit that has passed CI and the current
Destination-channel validation gate.

[ADR 0015](../adr/0015-actions-sole-publisher.md) makes GitHub Actions the only scheduler and
publisher. The host cron and host-local state paths below are historical operator references; do not
activate them while ADR 0015 stands.

## Current publisher contract

- Python 3.11 or newer, with no third-party Python dependency in the GitHub Actions job.
- Source of truth: committed `public/index.json`; the workflow seeds runner-local state from it before publishing.
- Generated index: committed `public/` directory, deployed to GitHub Pages.
- Lock: GitHub Actions concurrency group `publish-acts` with `cancel-in-progress: false`.
- Failure destination: GitHub Actions job notifications.
- Historical host layout: `/opt/apt-cron-pretorio`, `/etc/apt-cron/albo.env`,
  `/var/lib/apt-cron/state/notices.json` and `/run/apt-cron/apt-cron.lock` are retained only for
  rollback evidence and manual investigation.

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

## Seed, validate and hand back to Actions

Any host-local publication in this section requires explicit pilot authorization or recorded GO.
Disable `update-index.yml` before a manual send and reconcile the committed index before re-enabling
it; otherwise the next scheduled run can repeat the publication.

1. **Seed:** use `publication_state.py --index public/index.json --state <isolated-state>` to create a
   version-2 state file without contacting Telegram. Verify `apt_cron.py --dry-run` reports
   `published: 0` before any manual send.
2. **Private validation:** use an isolated state path and the current checklist. Verify HTML rendering,
   official links, every PDF upload, caption and size limits, failure behavior and the absence of
   credential values in output. Do not reuse production state for this test.
3. **Archive backfill:** after the private gate passes, run `python3 apt_cron.py --backfill` with
   `APT_TELEGRAM_PROFILE=production` and the production state path to publish the whole archive
   only under explicit pilot authorization or after a recorded GO, with `update-index.yml` disabled.
   It publishes acts already seeded by step 1 because selection uses `sent_messages`, not `notices`.
4. **Manual production run:** after the backfill completes, run once with
   `APT_TELEGRAM_PROFILE=production` and the production state path under the same authorization and
   with `update-index.yml` disabled. Record the immutable commit, exit code `0`, state-file mtime and
   index result, and retain logs without secrets.
5. **Keep only the GitHub Actions schedule active:** do not install or enable a host cron. The
   `Publish acts and reports` workflow seeds ephemeral state from the committed index and uses the
   protected `APT_TEST_TELEGRAM_*` repository secrets with the `test` profile. ADR 0014 classifies
   those values as production Destination-channel credentials; ADR 0015 assigns publication and the
   generated index and report commits to this workflow alone. A historical cron template is not an
   activation instruction.

## Monitor and observe

For the first 24 hours, the operator records each hourly Actions run's status, outcome, source notice
count, Telegram publication count and index commit. A failed workflow or unexpected publication count
is an incident. GitHub Actions notifications cover the workflow; no host cron is active. Ticket 31
must name the actual observer and alert destination.

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

1. Disable the hourly `Publish acts and reports` workflow. Confirm no new publication occurs; do not
   delete Telegram messages. No host cron entry exists to remove while ADR 0015 stands.
2. Preserve run logs and report artifacts for diagnosis. Runtime state is ephemeral; do not restore an
   older index snapshot unless the release owner explicitly approves that data operation.
3. Revert `public/index.*` with a normal Git commit to the last approved snapshot. Do not rewrite Git
   history or force-push.
4. Record the candidate commit, stop time, last successful run, index commit and reason. Re-enable the
   workflow only after the release owner approves a new candidate and repeats the applicable gates.

## Gate mapping

- Ticket 26: name the host, index destination and operational owner.
- Ticket 28: rotate the `APT_TEST_TELEGRAM_*` Actions secrets, record protected manual-run path metadata and link redacted evidence.
- Ticket 29: execute and evidence the install, seed, manual run, activation and rollback steps above.
- Ticket 30: rerun the current private-channel checklist and one manual production run.
- Ticket 31: name the observer, alert destinations and rollback trigger.
- Ticket 32: record the final go/no-go decision against ADR 0007. This runbook is preparation, not
  production approval.

The separate operator checklist in [operator-handoff.md](operator-handoff.md) lists the exact commands
and evidence records for installation, credential rotation, seed, private validation, real backfill,
manual run, cron activation, 24-hour monitoring and rollback rehearsal. It contains no credentials
and does not record a GO.
