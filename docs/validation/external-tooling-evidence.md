# External tooling evidence

Date: 2026-11-27

This document records source-backed evidence from the four repositories named by the operator. It does not change the runtime. The repository still uses Python's standard library only; no external tool is imported, called by `apt_cron.py`, or required by GitHub Actions.

## HKUDS CLI-Anything

Repository: https://github.com/HKUDS/CLI-Anything
Release: `v0.4.0`
Evidence: https://github.com/HKUDS/CLI-Anything/releases
Plugin install reference: https://github.com/HKUDS/CLI-Anything/blob/main/cli-anything-plugin/README.md
Hub reference: https://github.com/HKUDS/CLI-Anything/blob/main/cli-hub/README.md
Registry reference: https://github.com/HKUDS/CLI-Anything/blob/main/public_registry.json
n8n harness reference: https://github.com/HKUDS/CLI-Anything/blob/main/skills/cli-anything-n8n/SKILL.md

CLI-Anything generates an agent-facing CLI harness around existing software. Its documented install surfaces are `/plugin marketplace add HKUDS/CLI-Anything`, `/plugin install cli-anything`, `pip install cli-anything-hub`, `cli-hub install <name>`, `cli-hub update <name>` and `pip install cli-anything-n8n`. The generator writes or updates tracked files in the target project; the pip installs add environment packages.

Applicable pattern: publish a checked-in machine-readable command registry with explicit entry points and contract references. Applied through [`cli-contract.json`](cli-contract.json) and tested in `tests/test_cli_contract.py`. No generated harness is installed because this repository already owns its CLI and exit-code contract.

`cli-anything-n8n` is a Python CLI for the n8n REST API, not an n8n community node. No public evidence was found for an n8n community node named `n8n-nodes-cli-anything` or equivalent. Absence cannot be proven exhaustively.

## erkamyaman rust-anything

Repository: https://github.com/erkamyaman/rust-anything
Release: `v5.0.1`
Evidence: https://github.com/erkamyaman/rust-anything/releases/latest
Manifest: https://github.com/erkamyaman/rust-anything/blob/main/Cargo.toml
Package: https://www.npmjs.com/package/rust-anything

rust-anything is a Rust CLI and MCP server for incremental ports with `record`, `bridge`, `diff`, `gate`, `fuzz` and `map` stages. Documented setup is `cargo install rust-anything` or `npm install -g rust-anything`, followed by `rust-anything setup`. `setup` registers agent MCP entries and skills and can create backups. It is global tooling, not a repository dependency.

Applicable pattern: use golden JSON and exit-code fixtures as a gate before behavior changes, and keep source-field mapping drift explicit. The existing suite already tests field sets and fingerprints. No port is performed: ADR 0013 records the boundary, and no measured problem justifies a second runtime.

## EL4CTEO fast-anything

Repository: https://github.com/EL4CTEO/fast-anything
Manifest: https://github.com/EL4CTEO/fast-anything/blob/main/Cargo.toml
Changelog: https://github.com/EL4CTEO/fast-anything/blob/main/CHANGELOG.md
Release v0.8.9: https://github.com/EL4CTEO/fast-anything/releases/tag/v0.8.9
Release v0.8.10: https://github.com/EL4CTEO/fast-anything/releases/tag/v0.8.10
Release v0.8.11: https://github.com/EL4CTEO/fast-anything/releases/tag/v0.8.11
Package: https://www.npmjs.com/package/@el4cteo/fast-anything

fast-anything is a Rust profiling and acceleration CLI that ports selected functions and verifies recorded calls. Documented install commands are `npm i -g @el4cteo/fast-anything` and `cargo install fast-anything`. Installing does not rewrite the target repository; applying a port does and is designed to be reversible.

Upstream evidence is inconsistent: the Cargo manifest is `0.8.11`, indexed releases include `v0.8.9`, `v0.8.10` and `v0.8.11`, and the indexed npm profile showed `0.8.6`. The local installed CLI remains `0.7.0`, as recorded in ADR 0013. No update was applied. The canonical latest release could not be verified.

Applicable pattern: replay recorded inputs before enabling a behavior change and keep the change switchable. This repository has no demonstrated hot path and no port is enabled, so no replay or switch is added.

## goodnight000 api-anything

Repository: https://github.com/goodnight000/api-anything
README: https://github.com/goodnight000/api-anything/blob/main/README.md
Install: https://github.com/goodnight000/api-anything/blob/main/INSTALL.md
Quickstart: https://github.com/goodnight000/api-anything/blob/main/docs/QUICKSTART.md
Reference: https://github.com/goodnight000/api-anything/blob/main/docs/REFERENCE.md
Manifest: https://github.com/goodnight000/api-anything/blob/main/package.json
Releases: https://github.com/goodnight000/api-anything/releases

api-anything is a CLI, MCP server and library system that learns reusable website operations as JSON specs and executes them through tiered HTTP or browser operations. The README documents `npx -y api-anything setup` and `npx -y api-anything call <site> <op> ...`; the manual install is `npm install -g api-anything`. `INSTALL.md` also says the package is not yet published and gives clone, `npm ci`, `npm pack` and install-archive steps. That conflict is unresolved. The repository manifest is `0.5.0`; no GitHub release and no verified published npm version were found.

`setup` edits agent MCP configuration, installs or updates a skill, creates `~/.api-anything/key.json` and writes settings, with backups and `--dry-run` or `--local-only` controls. This is outside the repository and not supported by any repository manifest, so no setup was run.

Applicable pattern: stable outcome classes and machine-readable reason fields. The Source register response already carries `results` and `totalPages`; a live read-only probe on 2026-11-27 returned 25 results and `totalPages: 1` using `apt_cron.UrllibTransport`. No runtime change was made.

## Installation decision

No tool was installed or updated. `README.md` and ADR 0002 require a Python standard library runtime with no third-party Python package. ADR 0013 keeps all four tools outside the runtime. The repository has no `requirements*.txt`, `pyproject.toml`, `package.json`, `Cargo.toml`, lockfile or tool manifest that authorizes these global installs. The install is therefore recorded as blocked by repository policy, while the applicable patterns are applied without new dependencies.
