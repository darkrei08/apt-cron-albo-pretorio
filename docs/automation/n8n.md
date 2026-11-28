# n8n automation

The local n8n stack is an automation host and alarm surface. It is not a publication surface. `apt_cron.py` remains the only publisher to the Destination channel; the GitHub workflow remains the scheduler for publication and committed reports.

## Start

```sh
docker compose up -d
```

Open `http://127.0.0.1:5678`. The service binds only to loopback. Workflow data is stored in the `n8n_data` named volume mounted at `/home/node/.n8n`. The repository is mounted read-only at `/workspace/cron-albo-pretorio`.

No credential is placed in `docker-compose.yml`. Configure alarm endpoints in n8n itself and keep their values out of the repository.

`N8N_RESTRICT_FILE_ACCESS_TO` allows only `public/` and `reports/` for n8n file nodes. The repository
stays read-only.

## Suggested workflow

1. `Schedule Trigger`: hourly or daily.
2. `Read/Write Files from Disk`: read `/workspace/cron-albo-pretorio/public/index.json`.
3. `Read/Write Files from Disk`: read `/workspace/cron-albo-pretorio/reports/latest.md`.
4. `Code`: summarize the Generated index and the last report.
5. `IF`: route `no_changes`, `new_acts`, `changed_acts`, `removed_acts` or errors.
6. `HTTP Request` or an alarm node: send the summary to the configured alarm destination.

The committed Compose configuration allows file nodes only under `public/` and `reports/`. To read
project instructions for a Pi agent, first add `/workspace/cron-albo-pretorio`,
`/workspace/cron-albo-pretorio/docs` and `/workspace/cron-albo-pretorio/odd` to
`N8N_RESTRICT_FILE_ACCESS_TO`, then add file-reading nodes for `GLOSSARY.md`, `docs/wiki/*.md`,
`docs/adr/*.md` and `odd/tasks/*.md`. Do not run `pi` headless inside the n8n container.

## CLI-Anything node search

No n8n community node for CLI-Anything was found. Searches for `n8n-nodes-cli-anything` and `cli-anything-n8n` in the npm registry returned HTTP 404. The HKUDS repository has `cli-anything-n8n`, a Python CLI for the n8n Public API, not an n8n community node. Official n8n docs describe community-node installation for self-hosted n8n, but no matching CLI-Anything package was found.

Do not install an unverified node. Use n8n built-in file, HTTP and schedule nodes. Source-backed details and version evidence are in [../validation/external-tooling-evidence.md](../validation/external-tooling-evidence.md).

## Scope

- n8n schedules checks, reads reports and raises alarms.
- GitHub Actions publishes acts and commits generated reports.
- Python owns publication and the machine-readable CLI contract.
- CLI-Anything, api-anything, fast-anything and rust-anything are not runtime dependencies.

## Reproducible proof

The checked-in [proof workflow](apt-cron-proof-workflow.json) uses only built-in nodes. It reads
`public/index.json`, extracts the JSON, reads `reports/latest.md`, extracts the text and emits:

```json
{"check":"n8n-builtin-file-read","index_notices":20,"report_outcome":"acts_to_publish","source":"public/index.json,reports/latest.md","status":"PASS"}
```

`PASS` requires a populated index and a non-error report outcome from the known set: `acts_to_publish`,
`no_new_acts_to_publish`, `new_acts`, `changed_acts`, `removed_acts`, `no_changes` or `seeded`.

The image was pulled, the workflow was imported and executed through the n8n CLI with no credentials
and no external call. The image is `docker.n8n.io/n8nio/n8n` version `2.49.8`. This proves built-in
file reading and JSON/text extraction only. It does not prove Telegram rendering or act publication.

## Not verified

- Telegram rendering and act publication were not exercised by n8n; unit tests cover the renderer.
- Alarm endpoint configuration is operator-owned and not stored in this repository.
- No scheduled trigger or HTTP alarm was executed; the proof used a manual trigger.
- The proof used the repository as mounted by Compose; it did not publish acts or write to the repository.
