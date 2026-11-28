# External tooling evolution

## Specs

S1: `cli anything - api anythting - rust fast e rust anything`

S2: `quali miglioari apportatre e cosa poter melgio implemetare o aumenatre o integarre nuove features ed infine e creare una automazione n8n 8instalalndo in locale un container docker compose per n8n che legga pi agnet e chie possa anche riochiamare clianything trovare soluzione se esiste qualcosa di già fatto ricercando online)`

S3: `Primo: verifica l'endpoint JSON con api-anything; se manca, ferma subito il ramo.`

S4: `Secondo: contratto CLI esplicito, senza CLI-Anything: output macchina-leggibile e exit code stabili.`

S5: `Terzo: nessun port Rust; misura prima solo se necessario.`

S6: `Per "leggere pi agent", n8n legge file; non eseguire pi headless.`

## Tasks

T1 (S3): verify the Source register JSON endpoint. Result: already known in `apt_cron.py`; live read-only probe returned JSON with `results` and `totalPages`. Branch continues.

T2 (S4): document and test the CLI contract. Result: `docs/cli-contract.md` and `tests/test_cli_contract.py`. No CLI-Anything runtime wrapper.

T3 (S5): assess external performance tooling. Result: no Rust port; local `fast-anything` is v0.7.0, not the v0.8.6 note; historical 31 ms scan found no portable hot path; ADR 0013 records the boundary.

T4 (S2, S6): add local n8n automation host. Result: `docker-compose.yml`, `docs/automation/n8n.md` and ADR 0013. n8n reads repository files; it does not publish or run `pi` headless.

T5 (S2): search for an n8n community node for CLI-Anything. Result: none found; npm packages returned 404; HKUDS `cli-anything-n8n` is an external Python CLI, not an n8n node.

T6 (S1-S2): install or update only repository-supported tooling. Result: none installed or updated. The repo has no Python, npm, Cargo or Bun manifest; ADR 0002 forbids external tools in the runtime. Local inventory: `fast-anything` 0.7.0 global Bun package, no `api-anything` or `cli-anything` executable, Docker Compose 2.26.1-4. No runtime dependency was added.

T7 (S1-S2): complete external evidence. Result: source-backed findings in `docs/validation/external-tooling-evidence.md` with official README, manifest, release and package links for all four repositories. ADR 0013 links the evidence.

T8 (S4): apply the CLI-Anything registry pattern without the tool. Result: `docs/validation/cli-contract.json`, link from `docs/cli-contract.md` and `README.md`, and a registry test in `tests/test_cli_contract.py`. No generated harness, plugin or pip package was installed.

T9 (S5): apply the rust-anything golden gate pattern without a port. Result: exit-code and JSON exit assertions in `tests/test_cli_contract.py`; no Rust tool installed and no source rewritten.

## Log

L1: Original request recorded in S1-S2.

L2: Endpoint verified by a read-only POST to the source URL using the existing `apt_cron.UrllibTransport`; no api-anything CLI is installed locally.

L3: `docs/wiki/02-comandi.md`, `portal_monitor.py` and the 2026-11-22 fast-anything scan are present in PR #36 or outside this branch, not in the current `main` worktree; their relevant facts were read through GitHub/local read-only sources.

L4: n8n container was not pulled or started; workflow was not executed. This was true at the time of writing and was superseded by the later n8n proof in `odd/tasks/readable-message-spacing.md`.

L5: Trace completed in this session: `mem_search` for "CLI contract n8n automation external tooling" returned 0 results; `mem_save` stored observation #2843 with topic key `architecture/external-tooling-boundary`; the visible todo list was rewritten with four tasks and no open work.

L6: User correction: `Aggiorna il piano. POST /api/pap/filter risponde con results e totalPages. api-anything non è installato come CLI. La verifica usa il trasporto già presente nel repo.`

L7: User correction: `Mantieni: Nessun CLI-Anything runtime. Il contratto CLI del repo è documentato e testato. Mantieni: Nessun port Rust: nessuna misura o port eseguito. fast-anything locale è v0.7.0, non v0.8.6. Lo scan storico riporta 31 ms e nessun hotspot portabile.`

L8: User correction: `n8n locale: aggiunto come scheduler/allarme. Legge file del repo in sola lettura. Non esegue più headless e non pubblica atti.`

L9: User correction: `Nessuna modifica a apt_cron.py. Esegui o conferma. Probe JSON live: results presente, totalPages: 1. python3 -m unittest discover -s tests: PASS, 130 test. python3 -m py_compile ...: PASS. docker compose config: PASS, porta 127.0.0.1:5678, volume /home/node/.n8n, repo montato read_only: true. git diff --check: PASS. Link relativi dei nuovi documenti: 0 mancanti.`

L10: External evidence received from the `external-tool-evidence` researcher: CLI-Anything `v0.4.0` release, cli-anything-hub `0.4.1`, cli-anything-n8n `2.4.7`; rust-anything `v5.0.1`; fast-anything Cargo `0.8.11`, indexed npm `0.8.6`, indexed releases `v0.8.9`-`v0.8.11`; api-anything repository `0.5.0` with a publish-state conflict between README and INSTALL.md. None is supported as a repository dependency; installation is blocked by repository policy and recorded, not bypassed.

L11: Applied patterns: CLI-Anything machine-readable registry and rust-anything golden JSON/exit-code gate. fast-anything replay/switch and api-anything outcome enrichment were not applied because no behavior change or hot path is evidenced.

L12: Review-state correction: README step 8 now describes the hourly publish-and-report workflow, and the CLI contract distinguishes `apt_cron.py` JSON output from Markdown report builders. No runtime code changed.

L13: Independent verification returned FAIL for documentation and security consistency: ADR 0003/0007 still require separated production credentials, README still documents strict separation, and committed shared state is contradicted by `.gitignore` and the workflow. The tracker state and read-only checks passed. High findings are routed to Wayfinder tickets [Decide the production credential override and channel reclassification](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/37) and [Define the shared-state protocol for the two production schedulers](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/38). No completion is claimed.
