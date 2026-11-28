# Production credential rotation evidence

Ticket: [Rotate credentials now classified for production and confirm protected runtime paths](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/28).

Status: template, NOT RUN. No secret value belongs in this record.

## Scheduled publication (GitHub Actions)

Under ADR 0014 these legacy-named repository secrets are production-classified credentials for the
Destination channel. They are the only credentials used by the hourly publisher.

| Field | Record |
|---|---|
| Credential 1 | `APT_TEST_TELEGRAM_BOT_TOKEN` |
| Credential 2 | `APT_TEST_TELEGRAM_CHAT_ID` |
| Location | GitHub repository Settings > Secrets and variables > Actions |
| Rotation date | <YYYY-MM-DD> |
| Owner | <operator who rotated both values> |
| Redacted evidence | <link to audit entry or screenshot with values hidden> |
| Job run | <URL of the first successful run after rotation> |

## Manual CLI runs only

The host cron is inactive under ADR 0015. These paths matter only for an explicitly authorized manual
run or rollback investigation.

| Field | Record |
|---|---|
| Environment file | `/etc/apt-cron/albo.env` |
| Owner | `apt-cron:apt-cron` |
| Mode | `0600` |
| Rotation date | <YYYY-MM-DD> |
| Metadata check | `stat -c '%a %U:%G %s %n' /etc/apt-cron/albo.env` output, no contents |
| State file | `/var/lib/apt-cron/state/notices.json`, manual runs only |
| Index directory | `/opt/apt-cron-pretorio/public` |
| Lock path | `/run/apt-cron/apt-cron.lock`, manual runs only |
| Failure destination | GitHub Actions job notifications; no cron `MAILTO` |

Runtime state is ephemeral in the scheduled workflow and is never committed. Record metadata only;
never paste a token, chat id, file contents or a command containing a credential value.
