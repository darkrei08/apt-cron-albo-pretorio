# Configurazione

> Lingua: italiano su richiesta esplicita dell'operatore; decisione registrata nel [wayfinder locale](../wayfinder.md) e nella [mappa GitHub](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1).

Tutta la configurazione arriva da variabili d'ambiente o da un file `KEY=VALUE`. Il repository non contiene token né chat id.

## Variabili

| Variabile | Obbligatoria | Default | Uso |
| --- | --- | --- | --- |
| `APT_ENV_FILE` | no | `.env` nella root | File `KEY=VALUE` caricato prima delle impostazioni. |
| `APT_TELEGRAM_PROFILE` | no | `production` | Profilo di pubblicazione: `production` o `test`. |
| `TELEGRAM_BOT_TOKEN` | sì in `production`, salvo `--dry-run` e `--refresh-index` | nessuno | Bot del canale di destinazione. |
| `TELEGRAM_CHAT_ID` | sì in `production`, salvo `--dry-run` e `--refresh-index` | nessuno | Chat del canale di destinazione. |
| `APT_TEST_TELEGRAM_BOT_TOKEN` | sì in `test`, salvo `--dry-run` e `--refresh-index` | nessuno | Bot del canale di validazione. |
| `APT_TEST_TELEGRAM_CHAT_ID` | sì in `test`, salvo `--dry-run` e `--refresh-index` | nessuno | Chat del canale di validazione. |
| `APT_SOURCE_URL` | no | `https://siopi.publisys.it/kapi-aptbasilicata/api/pap/filter` | Base dell'API del Registro sorgente. |
| `APT_NATURE_ID` | no | `200152` | Identificatore della natura dell'atto. |
| `APT_PAGE_SIZE` | no | `20` | Atti richiesti per pagina. |
| `APT_DETAIL_BASE` | no | `https://siopi.publisys.it/sito-aptbasilicata/albo-pretorio/dettaglio` | Base dei link ufficiali. |
| `APT_ATTACHMENTS_BASE` | no | `https://siopi.publisys.it/kapi-aptbasilicata/api/pap/files` | Base dell'endpoint allegati. |
| `APT_INDEX_DIR` | no | `public` | Directory dell'Indice generato. |
| `APT_STATE_PATH` | no | `state/notices.json` | File dello Stato degli atti. |
| `APT_ALERT_TELEGRAM_BOT_TOKEN` | sì per `portal_monitor.py`, salvo `--dry-run` | nessuno | Bot del canale di allerta. |
| `APT_ALERT_TELEGRAM_CHAT_ID` | sì per `portal_monitor.py`, salvo `--dry-run` | nessuno | Chat del canale di allerta. |
| `APT_PORTAL_HISTORY_PATH` | no | `portal-history.json` | File della cronologia del portale. |

## Profili

| Profilo | Variabili richieste | Posizione consigliata |
| --- | --- | --- |
| `production` | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | File protetto `/etc/apt-cron/albo.env`, modo `0600`. |
| `test` | `APT_TEST_TELEGRAM_BOT_TOKEN`, `APT_TEST_TELEGRAM_CHAT_ID` | File locale ignorato, modo `0600`. |

I profili non usano credenziali dell'altro profilo. Un profilo sconosciuto termina con codice `2`.

## File di ambiente

`APT_ENV_FILE` punta a un file `KEY=VALUE`. Il caricamento accetta righe vuote, commenti `#`, prefisso `export ` e virgolette. I valori già presenti nell'ambiente prevalgono. `.env` e `.env.*` sono ignorati da Git.

Non scrivere token in comandi, crontab, issue, log o file tracciati. Non usare codifica base64 come protezione.

## Bot degli errori

Il canale di allerta è distinto dal canale di destinazione. Due opzioni:

| Opzione | Azione |
| --- | --- |
| Nuovo bot dedicato | Creare il bot in futuro e scrivere i suoi valori solo nel file protetto. |
| Riutilizzo del bot storico di `uptimekuma` | Valutare il riutilizzo, previa conferma di proprietà e permessi. |

Dato fornito dall'operatore per il bot storico: `https://t.me/uptimeholobot`. La chat id resta nella configurazione protetta e non nel repository.

Le variabili richieste restano `APT_ALERT_TELEGRAM_BOT_TOKEN` e `APT_ALERT_TELEGRAM_CHAT_ID`. Nessun token è presente nel repository. Gli alert live sono disattivati finché le variabili non vengono configurate.

[Torna all'indice wiki](README.md).
