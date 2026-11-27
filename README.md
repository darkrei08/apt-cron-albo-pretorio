# cron-albo-pretorio

> Lingua: italiano su richiesta esplicita dell'operatore; decisione registrata nel [wayfinder locale](docs/wayfinder.md) e nella [mappa GitHub](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1).

Pubblica gli atti del Registro sorgente APT Basilicata nel canale Telegram di destinazione e mantiene l'Indice generato nel repository. Un secondo comando controlla raggiungibilità, download e modifiche del portale.

## Scopo

- Legge gli atti pubblici dal Registro sorgente.
- Invia un messaggio HTML e tutti gli allegati ufficiali al canale di destinazione.
- Rigenera `public/index.json`, `public/index.md` e `public/index.html`.
- Registra impronte, link già inviati e stato degli atti.
- Rileva errori di accesso, download e modifiche della struttura del portale.

Il repository non copia i documenti ufficiali, non cancella messaggi e non invia nulla senza un comando esplicito. Usa solo la libreria standard di Python.

## Avvio rapido

```sh
python3 apt_cron.py --dry-run              # lettura, nessuna scrittura
python3 apt_cron.py --refresh-index        # solo indice, nessuna credenziale
python3 portal_monitor.py --dry-run        # monitoraggio senza alert
```

Per pubblicare serve un profilo Telegram configurato in un file di ambiente protetto. Vedi [Configurazione](docs/wiki/03-configurazione.md).

## Documentazione

| Documento | Contenuto |
| --- | --- |
| [Indice wiki](docs/wiki/README.md) | Accesso a tutta la documentazione operativa. |
| [Panoramica](docs/wiki/01-panoramica.md) | Scopo del repository e ruolo di questo README. |
| [Comandi](docs/wiki/02-comandi.md) | Comandi, opzioni, output e codici di uscita. |
| [Configurazione](docs/wiki/03-configurazione.md) | Variabili d'ambiente, profili e bot degli errori. |
| [Monitoraggio](docs/wiki/04-monitoraggio.md) | Snapshot del portale, cronologia e alert. |
| [Workflow](docs/wiki/05-workflow.md) | Esecuzione, cron, pubblicazione e verifiche. |
| [Wayfinder](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1) | Decisioni, rischi e prossime azioni. |
| [ADR 0012](docs/adr/0012-portal-monitoring-and-change-history.md) | Decisione sul monitoraggio del portale. |

## Comandi

| Comando | Credenziali | Effetto |
| --- | --- | --- |
| `python3 apt_cron.py --dry-run` | nessuna | Legge la finestra corrente e riporta i conteggi. |
| `python3 apt_cron.py --refresh-index` | nessuna | Rigenera solo `public/index.*`. |
| `python3 apt_cron.py --backfill --dry-run` | nessuna | Legge tutto l'archivio senza pubblicare. |
| `python3 apt_cron.py --backfill` | profilo Telegram | Pubblica l'archivio dal più vecchio al più recente. |
| `python3 apt_cron.py` | profilo Telegram | Pubblica gli atti nuovi o modificati e aggiorna l'indice. |
| `python3 portal_monitor.py --dry-run` | nessuna | Confronta il portale senza scrivere o avvisare. |
| `python3 portal_monitor.py` | variabili di allerta | Scrive la cronologia e avvisa su modifiche o errori. |

Opzioni e dettagli: [Comandi](docs/wiki/02-comandi.md).

## Configurazione essenziale

| Variabile | Uso |
| --- | --- |
| `APT_ENV_FILE` | File `KEY=VALUE` caricato prima di ogni impostazione. |
| `APT_TELEGRAM_PROFILE` | Profilo di pubblicazione: `production` o `test`. |
| `TELEGRAM_BOT_TOKEN` | Bot del canale di destinazione in produzione. |
| `TELEGRAM_CHAT_ID` | Chat del canale di destinazione in produzione. |
| `APT_TEST_TELEGRAM_BOT_TOKEN` | Bot del canale di validazione. |
| `APT_TEST_TELEGRAM_CHAT_ID` | Chat del canale di validazione. |
| `APT_ALERT_TELEGRAM_BOT_TOKEN` | Bot del canale di allerta. |
| `APT_ALERT_TELEGRAM_CHAT_ID` | Chat del canale di allerta. |
| `APT_STATE_PATH` | Stato degli atti e link già inviati. |
| `APT_INDEX_DIR` | Directory dell'Indice generato. |
| `APT_PORTAL_HISTORY_PATH` | Cronologia JSON del monitoraggio. |

Tabella completa e regole per i segreti: [Configurazione](docs/wiki/03-configurazione.md).

## Verifiche

```sh
python3 -m unittest discover -s tests
python3 -m py_compile apt_cron.py portal_monitor.py
git diff --check
```

Stato documentato: 121 test PASS, compilazione PASS, `git diff --check` PASS. Dettagli e elementi non verificati: [Workflow](docs/wiki/05-workflow.md) e [Wayfinder](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1).
