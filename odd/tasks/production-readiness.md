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

## Tasks

- T1 (S1,S4,S5): Decide and implement the `sent_messages` migration and duplicate-PDF acceptance contract from Wayfinder ticket 33; route: developer + tests/reviewer; commits: `aad3360`, `1bcda80`; ticket 33 closed with evidence.
- T2 (S1,S4): Reconcile the current implementation with the open readable-message/archive-backfill map from ticket 27; route: architect/reviewer; commits: `eaf5b97`, `1bcda80`; ticket 27 closed with explicit separate-scope dispositions.
- T3 (S1,S2,S7): Select the production host, index destination and operational owner from ticket 26; route: operator decision; blocked until host details exist; commit: N/A.
- T4 (S1,S2,S5,S7): Rotate credentials, define protected paths, install, validate, monitor and rehearse rollback through tickets 28-31; route: release/sre/security; blocked by T3 and operator-only actions; commit: pending.
- T5 (S1,S2,S5,S6,S7): Make the final release-gate decision from ticket 32 only after T1-T4 evidence; route: release + independent verifier; commit: pending.

## Log

- L1: "procedi in autonomia a risolvere tutti i tikcet della mappa facendo appunto corretta delegazioen epr ruoli ai task dche tiservono per procedere a rendere il progetto in produzione seocnod le bets practies del ciclo dis viluppo del software"
- L2: Current repository state: `main` at `cef13761aed1f33d9847395588763a656e1a8a98` with pre-existing uncommitted `sent_messages` implementation and documentation changes; preserve them until ownership and integration are decided.
- L3: Wayfinder ticket 34 is closed with reconciled evidence; production remains blocked by host/operator, current HTML validation, installation, monitoring and final release-gate evidence.
- L4: `aad3360` passed 77 unit tests and GGA; `eaf5b97` passed 80 unit tests and GGA; `1bcda80`, `0a56613` and `a0d2ff5` passed GGA documentation review. The five local commits total 1041 authored changed lines, with the first slice at 562 lines. Delivery shape is retained as five reviewable local commits; a chained PR is required before publication because the aggregate exceeds the review budget.
- L5: Current workflow capability is available through PiWorkflow; delegated roles used were reviewer/security synthesis and developer/TDD implementation. The workflow verifier could not start because its configured model alias was unavailable; the direct verifier setup was blocked by the shell safety guard. Parent-local compile, 80-test, diff-check and GGA evidence is recorded without claiming an independent verifier PASS.
