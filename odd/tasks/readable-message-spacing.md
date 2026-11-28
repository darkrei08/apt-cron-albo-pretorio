# Readable message spacing

## Specs

S1: `Migliora la formattazione del testo e della descrizione di ogni atto, perché ok va bene inserire il grassetto e poi le informazioni, però avere tutto un corpo molto vicino non permette all'utente di leggerlo facilmente perché poi sembra che tutti i campi siano e tutti i testi siano vicini creando un muro testuale. Quali formattazioni, righe, spazi possiamo implementare?`

S2: `Applica righe, spazi e separazioni tra campi e testi vicini.`

S3: `ovviamente le emoji non sono molto utili per capire esattamente quali telegram supporta per avere una facile lettura all'uomo all'umano`

S4: `Verifica che tutti i test passino e tutti i tech siano stati risolti.`

S5: `Verifica che lo script sia impostato, organizzato e funzionante.`

S6: `Esegui una prova end-to-end in n8n secondo tutti i ticket e le implementazioni.`

## Tasks

T1 (S4-S5): verify baseline tests, tickets, script and working tree. Result: 131 baseline tests PASS; 7 open Wayfinder child tickets plus two open maps; PR #36 is open and conflicting; no n8n container running.

T2 (S1-S3): define Telegram-safe spacing and grouping. Result: four visible sections separated by blank lines, bold section headings, plain field values and no emoji.

T3 (S1-S3): implement renderer and update exact-layout tests. Result: RED observed on the new layout, then GREEN on 17 focused tests and 131 full tests.

T4 (S1-S3): update README template and ADR for the new layout. Result: README template and ADR 0009 now document blank lines, headings and numbered attachments.

T5 (S6): run bounded local n8n file-read proof with built-in nodes, no secrets and no external alarm. Result: Compose image `2.49.8` pulled; proof workflow imported and executed with `N8N_RESTRICT_FILE_ACCESS_TO`; file-read output PASS with 20 notices and `acts_to_publish`; documentation workflow checked in. Telegram rendering and publication were not exercised by n8n.

T6 (S4-S6): final verification and report. Result: 131 tests PASS, focused renderer tests PASS, dry-run PASS, n8n file-read proof PASS with 20 notices and `acts_to_publish`, Compose config PASS and `git diff --check` PASS. Telegram rendering is verified by unit tests, not by the n8n proof.

## Log

L1: User request recorded verbatim in S1-S6.

L2: User examples requested human-readable grouping with links, price/responsibility lines, bullet fields and compact separators; emoji usefulness was explicitly questioned.

L3: Test-first evidence: the exact-layout and synthetic HTML tests were changed first and failed against the old renderer (1 error, 5 failures), then passed after the renderer change (17 focused tests PASS). The full suite returned 131 PASS after one final assertion adjustment.

L4: The chosen layout uses standard Telegram HTML tags only: `b`, `u`, `a`, `blockquote`. It adds blank lines between `Collegamenti`, `Titolo`, `Date e responsabile`, `Classificazione e stato` and the expandable technical quote. When more than one attachment exists, links are numbered to avoid identical adjacent labels.

L5: n8n proof: the first attempt failed because n8n 2.x denies `/workspace` until `N8N_RESTRICT_FILE_ACCESS_TO` is set. The second attempt failed because `readWriteFile` uses filesystem-v2 binary storage, not inline base64. The corrected workflow uses `extractFromFile` and passed with no credentials or external calls.
