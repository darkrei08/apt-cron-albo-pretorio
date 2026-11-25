APT notice index and PDF delivery
Large ODD implementation on main; issue https://github.com/darkrei08/apt-cron-albo-pretorio/issues/8.

## Specs

S1. "Altro tiCket da implementaree per evitare di reinviare tutti i juovi link messaggi e pdff, infatti avere un sistema di controllo ech einvia solo innuovi atti trovare soluzione pe rimplemattr cintrollo e dire fatto quindintenere traccia ?"
S2. "Prendere il link diretto del PDF da inserire nel corpo del messaggio e successivamente al corpo del messaggio inviare l'allegato PDF. Cosa ci vuole? È semplice."
S3. "HTML, JSON, altro indice, markdown pure, tutto da iniettare ogni volta all'interno del repo git come se fosse un report che crea in automatico ovviamente non ci deve essere nessuna chiamata API a nessun LLM, tutto deve essere eseguito attraverso uno script."
S4. "Tutti i dati possibili, ovviamente non bisogna violare nulla. Alla fine io cittadino, invece di scaricarli manualmente e aprire con tanti clic i file del portale, mi sono creato un sistema che mi autodocumenta e mi indicizza le informazioni cosa cambia non sto violando nulla"
S5. "non targetizzare, informare, dire chi sono i gruppi, i responsabili, i soggetti non pubblici"
S6. "Usa un identificativo stabile dell'atto; altrimenti usa link del pdf e dell'atto e l'allegato PDF."
S7. "Aggiungi test per primo invio, nessuna novità, nuovo atto e allegato PDF."

## Tasks

T1 (S1,S6) stable notice identity and versioned persistent state — inline, test-first — commit: 719f5ae
T2 (S1,S2,S7) fetch public PDF links and send PDF as Telegram document once — inline, test-first — commit: 719f5ae
T3 (S3,S4,S5) generate JSON, Markdown and HTML public index from safe fields — inline, test-first — commit: 719f5ae
T4 (S1,S3) integrate enrichment, index generation and CLI configuration — inline — commit: 719f5ae
T5 (S2-S5) update README and Wayfinder references — inline — commit: 719f5ae
T6 (S1-S7) review and commit the work unit — inline — commit: 719f5ae

## Log

L1. "Altro tiCket da implementaree per evitare di reinviare tutti i juovi link messaggi e pdff, infatti avere un sistema di controllo ech einvia solo innuovi atti trovare soluzione pe rimplemattr cintrollo e dire fatto quindintenere traccia ? Organizza il lavoro su GitHub ..."
L2. The operator clarified: "non targetizzare, informare, dire chi sono i gruppi, i responsabili, i soggetti non pubblici"; the message must contain the direct PDF link and then send the PDF as a Telegram document, and the public index must be generated into the Git repository by a script with no LLM.
L3. No CLAI Anything, Rust Anything or Rust Fast implementation is installed. Use Python standard library; api-anything was a planning aid and fast-anything is performance-only.
