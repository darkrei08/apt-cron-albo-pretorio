# Local host provisioning 2026-11-26

Provisioning was applied only after verifying `hostname=herdr`, Debian 13 and Python 3.13.5.
No credential file contents were read or written.

## Applied

- Created system user `apt-cron` with home `/var/lib/apt-cron` and shell `/usr/sbin/nologin`.
- Created `/opt/apt-cron-pretorio` as `root:root`, mode `0755`; the application candidate was not copied because the local branch is waiting for PR publication.
- Created `/etc/apt-cron` as `root:apt-cron`, mode `0750`, so the service user can traverse to its protected environment file.
- Created empty `/etc/apt-cron/albo.env` as `apt-cron:apt-cron`, mode `0600`.
- Created `/var/lib/apt-cron` and `/var/lib/apt-cron/state` as `apt-cron:apt-cron`, mode `0700`.
- Created `/run/apt-cron` as `root:apt-cron`, mode `0750`.
- Created `/run/apt-cron/apt-cron.lock` as `apt-cron:apt-cron`, mode `0660`.
- Created `/var/log/apt-cron` as `apt-cron:apt-cron`, mode `0750`.
- Prepared `/etc/apt-cron/cron.disabled` as `root:root`, mode `0644`, outside `/etc/cron.d`.

## Verification

- Host guard: `hostname=herdr` PASS.
- `cron` service: active, but no `/etc/cron.d/apt-cron-pretorio` file exists.
- Cron status: disabled by placement in `/etc/apt-cron/cron.disabled`.
- Lock probe: `flock -n /run/apt-cron/apt-cron.lock -c true` PASS.
- Candidate deployment: NOT RUN; waiting for PR publication/approval.
- Seed, Telegram validation, manual production run and rollback rehearsal: NOT RUN.
