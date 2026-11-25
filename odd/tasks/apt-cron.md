APT cron Wayfinder
Large ODD implementation on main; planning and tests precede source writes.

## Specs

S1. "io voreic reare uno script cron senza llm solo get post dal sito istituzionale al canale telegram"
S2. "questo deve essere il nome e il repo di destinazione https://github.com/darkrei08/apt-cron-albo-pretorio"
S3. "Con anno data" / "Soggetto vecchio che ricerca"
S4. "Telegram o wa capire se si vila qualcosa gdpr richieste dati conervazine semplice"
S5. "Cosa viola se un utente masisvamente scarica dati ? Alla fon è la stessa cosa farlo manalemnte ma per troppo tempo di lavoro"
S6. "puoi anceh usare la skills per creare una api utile epr il cron che scarica dati grezzi li trasofrma in json o e da li invia un mesaggio fomrattao correttamente seocnod le speficieh dete eprima (la skill sia chiama api anything  o trovala su github) direttiva da isnieire enlal mapap di wayfinder"
S7. "con api anythin ti sara faciel crare il corn"
S8. "api anything fast anything sono utili usali mpe,emnatli nelal mappa per facilitare etrsazioen dati meta dati link docuemtni della delibera delgia fficamenti eccetera"
S9. "e devi creare alla fine dellos viluppo di tutti i ticket anceh un bel file reamde descrittivo che responsaiblizza il fatto dis caricare"
S10. "solo get post" was relaxed by the operator: "Consenti POST di sola lettura al sito". Official OpenAPI exposes notice discovery only as POST /api/pap/filter; Telegram publishing is POST /sendMessage. No LLM at runtime.

## Tasks

T1 (S1,S10,S6-S8) research source contract and api-anything evidence — inline — commit: 3b638a1
T2 (S1,S3,S6) parse source JSON into minimal notice fields — inline, test-first — commit: 3b638a1
T3 (S1,S3,S6) format accessible Telegram text from notice JSON — inline, test-first — commit: 3b638a1
T4 (S1,S10) simulate source and Telegram HTTP requests; enforce no network in tests — inline, test-first — commit: 3b638a1
T5 (S1,S4,S5) seed/deduplicate notices safely and publish only new or changed ones — inline, test-first — commit: 3b638a1
T6 (S1,S9) expose cron configuration, README, and simulated end-to-end verification — inline — commit: 3b638a1

## Log

L1. "procedi con i ticket passo passo della mappa, io voreic reare uno script cron senza llm solo get post dal sito istituzionale al canale telegram"
L2. The operator chose to close Wayfinder tickets #3 and #4 before implementation and confirmed four TDD seams: HTML/JSON parsing, message composition, simulated HTTP, and temporary state deduplication.
L3. The official OpenAPI at https://siopi.publisys.it/kapi-aptbasilicata/v3/api-docs exposes only POST for /api/pap/filter; the operator authorized a read-only POST to the official site.
L4. The operator asked for api-anything and fast-anything directives in the Wayfinder map; api-anything is the extraction aid, fast-anything is a performance aid only.
