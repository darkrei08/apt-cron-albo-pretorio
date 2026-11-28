# 0013 — External tooling boundary

- Status: accepted
- Evidence: [docs/validation/external-tooling-evidence.md](../validation/external-tooling-evidence.md)

The Source register already exposes JSON through the read-only `POST /api/pap/filter` request discovered with `api-anything` during planning and implemented in `apt_cron.py`. A live read-only probe confirmed the response has `results` and `totalPages`; therefore the JSON branch does not stop.

The runtime stays Python standard library only. CLI-Anything is not adopted because the repository already has an explicit CLI contract with machine-readable stdout and stable exit codes. `api-anything` remains a planning aid per ADR 0002. `fast-anything` is not adopted: the local CLI is version 0.7.0, the measured historical scan ran in 31 ms and found no portable hot path, and `fast-anything port` rewrites tracked source and requires generated Rust crates. `rust-anything` has no verifiable local evidence and is not adopted. No Rust port is attempted.

n8n is adopted only as a local automation host and alarm surface through `docker-compose.yml`. It reads repository files from a read-only mount and never runs `pi` headless or publishes acts. `apt_cron.py` remains the only publisher and GitHub Actions remains the publication scheduler. No n8n community node for CLI-Anything was found; HKUDS `cli-anything-n8n` is an external Python CLI for the n8n API, not an n8n node.

The checked-in registry at `docs/validation/cli-contract.json` applies the CLI-Anything registry pattern without adopting CLI-Anything. Golden JSON and exit-code tests apply the rust-anything gate pattern without a Rust port. No upstream tool was installed or updated because no repository manifest authorizes a global tool and ADR 0002 forbids runtime dependencies. The fast-anything upstream version evidence is inconsistent (`0.8.11` Cargo, `0.8.6` npm profile, `0.8.9`-`0.8.11` releases); the local CLI remains `0.7.0`.
