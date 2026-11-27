# Workflow

> Lingua: italiano su richiesta esplicita dell'operatore; decisione registrata nel [wayfinder locale](../wayfinder.md) e nella [mappa GitHub](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1).

Questa pagina descrive esecuzione, pubblicazione, pianificazione e verifiche.

## Esecuzione ordinaria

1. Il comando `apt_cron.py` legge la finestra corrente del Registro sorgente.
2. La prima esecuzione semina lo Stato degli atti senza pubblicare.
3. Gli atti nuovi o modificati ricevono un messaggio HTML e tutti i documenti disponibili.
4. Lo stato viene salvato dopo ogni pubblicazione riuscita.
5. L'Indice generato viene rigenerato dagli stessi Campi pubblicati.

Il messaggio segue [ADR 0009](../adr/0009-readable-telegram-act-message.md). La frontiera di pubblicazione segue [ADR 0005](../adr/0005-publication-boundary.md) e [ADR 0011](../adr/0011-publish-procedural-responsible.md).

## Backfill

`--backfill` legge tutte le pagine dell'archivio e pubblica dal più vecchio al più recente. Non scrive l'indice. Una interruzione riprende dallo stato salvato. Un riesecuzione su atti invariati non pubblica di nuovo.

## Download

- Elenco atti: `POST /api/pap/filter` con `User-Agent: apt-cron/1.0` e timeout di 20 secondi.
- Allegati: `GET /api/pap/files/{id}`.
- Documenti: byte letti in memoria, inviati come `sendDocument` multipart, mai salvati su disco.
- Limite: 50 MB per documento.
- Telegram non scarica direttamente l'URL ufficiale: una prova live ha restituito `400 Bad Request: failed to get HTTP URL content`.

## Pianificazione

Esempio per la pubblicazione oraria:

```cron
CRON_TZ=Europe/Rome
MAILTO=operator@example.invalid
0 * * * * cd /path/to/cron-albo-pretorio && TZ=Europe/Rome APT_ENV_FILE=/etc/apt-cron/albo.env APT_TELEGRAM_PROFILE=production /usr/bin/flock -n /tmp/apt-cron.lock /usr/bin/python3 apt_cron.py
```

Esempio per il monitoraggio:

```cron
CRON_TZ=Europe/Rome
MAILTO=operator@example.invalid
30 * * * * cd /path/to/cron-albo-pretorio && TZ=Europe/Rome APT_ENV_FILE=/etc/apt-cron/albo.env /usr/bin/python3 portal_monitor.py
```

Sostituire percorsi e indirizzo email. Non inserire credenziali nella riga cron.

## Controlli

- `APT_PAGE_SIZE` deve essere un intero positivo.
- Gli errori runtime stampano una riga redatta su stderr.
- Telegram HTTP `429` e reset di connessione vengono ritentati fino a sei tentativi, con attesa massima di 60 secondi.
- Il messaggio HTML è limitato a 4096 caratteri; le didascalie a 1024.
- Ogni valore dinamico viene escapato.
- `.github/workflows/ci.yml` compila ed esegue i test. `.github/workflows/update-index.yml` aggiorna l'indice ogni ora.

## Responsabilità dell'operatore

L'operatore fornisce credenziali, percorsi protetti, pianificazione, monitoraggio e risposte sui dati. Il ritiro di un atto non viene automatizzato: l'atto resta nel canale e esce dall'indice al successivo aggiornamento, secondo [ADR 0004](../adr/0004-withdrawal-and-retention.md).

## Verifiche eseguite

- 121 test PASS.
- `py_compile` PASS.
- `git diff --check` PASS.
- Matrice container PASS su Debian 13, Fedora 42, Arch Linux, Alpine 3.20 e openSUSE Tumbleweed.

Non verificati: alert Telegram reale, Windows e macOS, conteggio manuale dei 748 messaggi in chat. Il conteggio è verificato tramite stato e dry-run.

[Torna all'indice wiki](README.md).
