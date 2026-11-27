# Production readiness implementation

Source of truth for the authorized production-readiness work tracked by Wayfinder map 24.
Implementation stays bounded by the map; operator-only evidence remains blocked rather than invented.

## Specs

- S1: "Risolvi tutti i ticket presenti nella mappa."
- S2: "Porta il progetto in produzione secondo le best practices del ciclo di sviluppo del software."
- S3: "Delega correttamente i task ai ruoli più adatti, usando gli strumenti disponibili."
- S4: "Non introdurre funzionalità non richieste."
- S5: "Esegui i test, i controlli di qualità e le verifiche di sicurezza disponibili."
- S6: "Non dichiarare completato un ticket non verificato."
- S7: "Segnala chiaramente eventuali blocchi o informazioni mancanti."
- S8: "Token e chat sono per orvare doponlo rioto ora vai i in roiduzine".
- S9: "Indica nel reamde anche cos afa il repo test temolate dle nesaggio cone e dove sceivere i dati s esibili token eccetera e quali coma di cli poter eseguire e oerisnalizzare il corn eccetra".

## Tasks

- T1 (S1,S4,S5): Decide and implement the `sent_messages` migration and duplicate-PDF acceptance contract from Wayfinder ticket 33; route: developer + tests/reviewer; commits: `aad3360`, `1bcda80`; ticket 33 closed with evidence.
- T2 (S1,S4): Reconcile the current implementation with the open readable-message/archive-backfill map from ticket 27; route: architect/reviewer; commits: `eaf5b97`, `1bcda80`; ticket 27 closed with explicit separate-scope dispositions.
- T3 (S1,S2,S7): Select the production host, index destination and operational owner from ticket 26; route: operator decision; blocked until host details exist; commit: N/A.
- T4 (S1,S2,S5,S7): Rotate credentials, define protected paths, install, validate, monitor and rehearse rollback through tickets 28-31; route: release/sre/security; blocked by T3 and operator-only actions; commit: pending.
- T5 (S1,S2,S5,S6,S7): Make the final release-gate decision from ticket 32 only after T1-T4 evidence; route: release + independent verifier; commit: pending.
- T6 (S1,S2,S7): Provide a concrete installation, validation, monitoring and rollback runbook for tickets 28-31 without claiming host execution; route: release/SRE documentation; commit: `0fab591`.
- T7 (S1,S2,S7): Provision the local `herdr` host without reading credentials and keep cron disabled until the exact candidate is approved; route: release/SRE operations; evidence: `docs/validation/local-host-provisioning-2026-11-26.md`; commit: `a2e58e4`.
- T8 (S1,S2,S5,S6,S7): Harden archive seeding, fail closed on malformed source data, isolate attachment failures per notice, and align the private Telegram checklist with all-attachment delivery; route: developer/tests/reviewer; commit: `23b8649`.
- T9 (S2,S4,S5,S7): Add an explicit Telegram profile so test credentials cannot replace production credentials; route: developer/tests/security reviewer; commit: pending.
- T10 (S2,S7): Expand README with repository purpose, test message template, secret locations, CLI commands and cron customization; route: technical writer; commit: pending.

## Log

- L1: "procedi in autonomia a risolvere tutti i tikcet della mappa facendo appunto corretta delegazioen epr ruoli ai task dche tiservono per procedere a rendere il progetto in produzione seocnod le bets practies del ciclo dis viluppo del software"
- L2: Current repository state: `main` at `cef13761aed1f33d9847395588763a656e1a8a98` with pre-existing uncommitted `sent_messages` implementation and documentation changes; preserve them until ownership and integration are decided.
- L3: Wayfinder ticket 34 is closed with reconciled evidence; production remains blocked by host/operator, current HTML validation, installation, monitoring and final release-gate evidence.
- L4: `aad3360` passed 77 unit tests and GGA; `eaf5b97` passed 80 unit tests and GGA; `1bcda80`, `0a56613`, `a0d2ff5` and `0fab591` passed GGA documentation review. The seven local commits total 1147 authored changed lines, with the first slice at 562 lines. Delivery shape is retained as seven reviewable local commits; a chained PR is required before publication because the aggregate exceeds the review budget.
- L5: Current workflow capability is available through PiWorkflow; delegated roles used were researcher/explorer, reviewer/security synthesis and developer/TDD implementation. The workflow verifier could not start because its configured model alias was unavailable; the direct verifier setup was blocked by the shell safety guard. Parent-local compile, 80-test, diff-check and GGA evidence is recorded without claiming an independent verifier PASS.
- L6: The production runbook defines the recommended protected paths, seed/validation/activation order, monitoring evidence and rollback procedure. It does not claim a host, credentials, operator or production approval; tickets 26, 28, 30, 31 and 32 remain external gates.
- L7: The user selected the current local host `herdr` (Debian 13, Python 3.13.5) and the repository owner as operational owner. The exact alert address was confirmed from repository-owner metadata without writing it to the repository.
- L8: Local host provisioning is complete for non-secret infrastructure: service user, protected directories, empty credential file, lock and disabled cron template. `/etc/apt-cron` is `root:apt-cron` mode `0750`, and service-user traversal/readability was checked without reading file contents. The application candidate was not copied because the user chose to wait for PR publication; seed, live validation, manual run, monitoring and rollback remain pending.
- L9: The provisioning evidence slice is recorded in `a2e58e4` and linked in `6c16a99`; the branch remains above the review-size threshold and requires a chained PR delivery shape before publication.
- L10: "Correggi il comportamento seed/backfill. Rifiuta risposte sorgente o allegati malformate, senza interpretarle come risultati vuoti. Impedisci che un errore nel recupero allegati blocchi l’intero archivio. Aggiorna la checklist Telegram: ora gli allegati non PDF vengono inviati." T8 was committed as `23b8649`, passed GGA, and the merged branch has CI run `45904384468`.
- L11: "doponlo rioto" was clarified as "dopo la rotazione": the supplied token and chat id are test values for use after rotation, not production credentials. No supplied secret is written to this repository, a log or a report. T9 keeps that test path explicit; T10 documents repository scope, message template, secret locations, CLI commands and cron customization.
- L12: The live archive probe showed that many old notices legitimately return `documentoUnico: null`; treating null as malformed skipped them during backfill. `fetch_attachments` now accepts null document/files as absent values while still rejecting other malformed shapes. `test_absent_attachment_fields_are_empty_not_errors` reproduces the API shape with a fake transport.
- L13: BrowserOS proved that `/albo-pretorio/dettaglio/<id>` returns `Nessuna pubblicazione in corso` for both old and new acts, while `/albo-pretorio/dettaglio/<id>/dettaglio-pap` shows the act and its documents. `build_detail_url` now appends `DETAIL_PATH_SUFFIX`, and the exact message-link assertion was updated. Old archived acts expose no documents in either the API or the browser page, so no PDF or attachment can be sent for them.
