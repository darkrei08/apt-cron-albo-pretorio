Production hardening
Workflow audit run 89d7cf23-b992-4a78-88f2-adad2dd7ba65 on main ahead 4.

## Specs

S1. "Prowegui con lo wvikippo per renderelo in poduzionw faintutti inpassaggi usa do piworjflow extensible dev reviw tets audit security ecceera"
S2. "Cerca \"wvikippo\" nel repository e nella documentazione per primo. Se il termine non esiste, segnalalo nel report e prosegui con build, test, audit e security già configurati."
S3. "Aggiungi o aggiorna test per ogni correzione rilevante."
S4. "Correggi problemi di build, configurazione, CI, dipendenze e sicurezza che trovi."
S5. "Se serve una decisione esterna, lascia il valore irrisolto e riportalo nel report."

## Tasks

T1 (S1,S3,S4) validate runtime configuration and add regression tests — inline, test-first — commit: f0c2373
T2 (S1,S3,S4) redact Telegram credentials from runtime failures — inline, test-first — commit: f0c2373
T3 (S1,S3) bound message length to Telegram limit — inline, test-first — commit: f0c2373
T4 (S1,S4) add CI workflow for compile and full test suite — inline — commit: f0c2373
T5 (S1-S5) review, commit and report unresolved checks — inline — commit: f0c2373

## Log

L1. The operator asked to make the project production-ready using the requested extensible workflow, development, review, tests, audit and security sequence.
L2. The literal term "wvikippo" has no match in the repository. It is treated as a typo for workflow; the deterministic PiWorkflow audit ran with development, test, audit and security phases.
