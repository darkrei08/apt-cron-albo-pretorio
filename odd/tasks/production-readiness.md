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

- T1 (S1,S4,S5): Decide and implement the `sent_messages` migration and duplicate-PDF acceptance contract from Wayfinder ticket 33; route: developer + tests/reviewer; commit: `aad3360` (implementation and tests), documentation evidence pending.
- T2 (S1,S4): Reconcile the current implementation with the open readable-message/archive-backfill map from ticket 27; route: architect/reviewer; commit: `eaf5b97` (attachment cache invalidation and tests), documentation evidence pending.
- T3 (S1,S2,S7): Select the production host, index destination and operational owner from ticket 26; route: operator decision; blocked until host details exist; commit: N/A.
- T4 (S1,S2,S5,S7): Rotate credentials, define protected paths, install, validate, monitor and rehearse rollback through tickets 28-31; route: release/sre/security; blocked by T3 and operator-only actions; commit: pending.
- T5 (S1,S2,S5,S6,S7): Make the final release-gate decision from ticket 32 only after T1-T4 evidence; route: release + independent verifier; commit: pending.

## Log

- L1: "procedi in autonomia a risolvere tutti i tikcet della mappa facendo appunto corretta delegazioen epr ruoli ai task dche tiservono per procedere a rendere il progetto in produzione seocnod le bets practies del ciclo dis viluppo del software"
- L2: Current repository state: `main` at `cef13761aed1f33d9847395588763a656e1a8a98` with pre-existing uncommitted `sent_messages` implementation and documentation changes; preserve them until ownership and integration are decided.
- L3: Wayfinder ticket 34 is closed with reconciled evidence; production remains blocked by host/operator, current HTML validation, installation, monitoring and final release-gate evidence.
- L4: `aad3360` passed 77 unit tests and GGA; `eaf5b97` passed 80 unit tests and GGA. The first slice exceeded the 400-line review budget (562 authored lines), so the delivery shape must be recorded before publication.
- L5: Current workflow capability is available through PiWorkflow; delegated roles used were reviewer/security synthesis and developer/TDD implementation. The runtime capability script was inspected but could not be executed by the safety gate; no capability was invented.
