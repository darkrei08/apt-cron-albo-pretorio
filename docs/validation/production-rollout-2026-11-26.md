# Production rollout evidence — 2026-11-26

- Status: **HOLD**
- Release code: `979a03d756673da9ba38e4605e5062d0a8d74da9`
- CI: [run 45904384468](https://github.com/darkrei08/apt-cron-albo-pretorio/actions/runs/45904384468), job `test` PASS
- Host: `herdr`
- Operator sign-off time: `2026-11-26T22:51:16Z`

No credential, token, chat id or other secret value is recorded in this document.

## Authorization and decision sign-off

The operator authorized production work and publication of all acts from oldest to newest. The
follow-up authorization, translated from Italian as "Do everything to go to production", is recorded
as explicit pilot authorization for pre-GO production runs. The repository owner is the sign-off owner
and rollback owner recorded in ADR 0007.

ADR decision prerequisites were checked before any real send:

- Issues #5, #6, #7, #9, #11 and #12 are CLOSED.
- No unresolved `[INSERT DECISION]` marker was found in an ADR decision section. The two literal
  occurrences in ADR 0006 and ADR 0007 are explanatory prose about the marker, not open decisions.
- ADR 0007 part 1 is therefore PASS. No Telegram message was sent before this sign-off.

## Release installation

The protected checkout was installed from `origin/main` at the exact release commit:

```sh
git clone https://github.com/darkrei08/apt-cron-albo-pretorio.git /opt/apt-cron-pretorio
git -C /opt/apt-cron-pretorio fetch origin 979a03d756673da9ba38e4605e5062d0a8d74da9
git -C /opt/apt-cron-pretorio checkout --detach 979a03d756673da9ba38e4605e5062d0a8d74da9
git -C /opt/apt-cron-pretorio rev-parse HEAD
python3 --version
python3 -m py_compile apt_cron.py tests/test_apt_cron.py
python3 -m unittest discover -s tests -v
```

Recorded result: HEAD `979a03d756673da9ba38e4605e5062d0a8d74da9`, Python 3.13.5, compile PASS,
94 tests PASS, worktree clean. Protected paths exist: `/opt/apt-cron-pretorio`,
`/etc/apt-cron`, `/var/lib/apt-cron/state`, `/run/apt-cron` and `/var/log/apt-cron`.

## Credential gate

The protected environment file exists with metadata `0600 apt-cron:apt-cron`; its size is `0` bytes.
A metadata-only check reported both required values missing. The process environment also reported
both values missing.

**Exact missing data:** `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, rotated by the operator into
`/etc/apt-cron/albo.env` out of band. They were neither read nor written here. Rotation, private
HTML validation, real publication and the manual production run are blocked until those values
exist. The `MAILTO` operator alert address is also still required before cron activation.

**Current classification (ADR 0014/0015):** the statement above is the 2026-11-26 observation. The
scheduled publisher now uses the production-classified repository secrets
`APT_TEST_TELEGRAM_BOT_TOKEN` and `APT_TEST_TELEGRAM_CHAT_ID`; host-file names apply only to explicit
manual runs and no host cron is active. Record rotation metadata, never values, in
[production-credentials-evidence.md](production-credentials-evidence.md).

## Archive dry run and state preparation

Command, with no credentials and no Telegram traffic:

```sh
cd /opt/apt-cron-pretorio
export APT_ENV_FILE=/etc/apt-cron/albo.env
export APT_STATE_PATH=/var/lib/apt-cron/state/notices.json
export APT_INDEX_DIR=/opt/apt-cron-pretorio/public
export TZ=Europe/Rome
export APT_PAGE_SIZE=100
python3 apt_cron.py --backfill --dry-run
```

Window: `2026-11-26T22:37:26Z` to `2026-11-26T22:39:35Z`, exit code `0`. Result:
`{"attachment_errors": 725, "dry_run": true, "notices": 748, "published": 23}`.
The state file was absent before and after the dry run; no act was sent.

A read-only attachment-cache preparation using the existing `fetch_attachments` helper ran against
the archive with throttling and three retries. It was stopped at its 600-second budget. The resulting
version-2 state has 748 notice fingerprints, 23 cached attachment records, zero `sent_messages`
entries and zero `sent_documents` entries. It is owned by `apt-cron:apt-cron`, mode `0600`.
The high attachment-error count under sustained requests was observed but its root cause was not
diagnosed; no further archive requests were made.

`archive selection uses sent_messages, so seeded notices are still published`: with zero
`sent_messages` entries, all 748 archive notices remain eligible for the real backfill.

## Gate status

1. Decisions closed and approved: **PASS**.
2. CI on the exact release commit: **PASS**, run 45904384468.
3. Current private-channel HTML validation: **BLOCKED**, missing rotated credentials.
4. Operational readiness: **BLOCKED**, credentials absent and no manual production run.
5. Rollback rehearsal: **BLOCKED**, not performed while publication is blocked.

Cron is not installed and `systemctl is-active cron` is `active` as a service only. Both GitHub
Actions workflows are active. No Telegram message, document, act or duplicate was sent.
ADR 0007 and issue #32 remain **HOLD**; no GO is claimed.
