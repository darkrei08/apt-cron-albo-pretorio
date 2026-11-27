# Monitoraggio

> Lingua: italiano su richiesta esplicita dell'operatore; decisione registrata nel [wayfinder locale](../wayfinder.md) e nella [mappa GitHub](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1).

`portal_monitor.py` è un percorso di allarme separato. Non pubblica atti, non modifica lo Stato degli atti e non rigenera l'Indice generato.

## Cosa controlla

Una esecuzione:

1. legge la finestra corrente del Registro sorgente;
2. interroga l'endpoint allegati dell'atto più recente;
3. scarica un campione di un documento;
4. costruisce uno Snapshot del portale;
5. confronta lo snapshot con quello precedente.

Lo Snapshot del portale include chiavi della risposta, chiavi degli atti, pagine totali, conteggio risultati, impronte, link ufficiali e link degli allegati. Errori di raggiungibilità, errori di download e differenze producono un Evento di modifica.

## Cronologia

Il file `portal-history.json` contiene:

- ultimo Snapshot del portale;
- ultimi 200 Eventi di modifica;
- esito e impronta dello snapshot per ogni evento.

Il file è uno stato generato e non va committato. Git conserva la documentazione dello schema e della ritenzione; un riepilogo curato può essere pubblicato in una issue o in una pull request.

## Alert

L'alert usa il Canale di allerta configurato con `APT_ALERT_TELEGRAM_BOT_TOKEN` e `APT_ALERT_TELEGRAM_CHAT_ID`. In caso di errore, il comando stampa una riga redatta su stderr; cron `MAILTO` resta il canale secondario.

Opzioni per il bot degli errori:

- creare un nuovo bot dedicato;
- riutilizzare il bot storico di `uptimekuma`, previa conferma.

Dato fornito dall'operatore: `https://t.me/uptimeholobot`. La chat id resta nella configurazione protetta. Nessun token è nel repository.

Gli alert live sono disattivati. Il monitor rileva e registra, ma non avvisa Telegram finché le variabili dedicate non sono configurate.

## Confronto con altri strumenti

- [Uptime Kuma](https://github.com/louislam/uptime-kuma): monitor HTTP, keyword e JSON query con notifiche Telegram.
- [changedetection.io](https://github.com/dgtlmoon/changedetection.io): filtri CSS, XPath, JSONPath, jq e notifiche sui diff.

Questo repository riutilizza il parser JSON già presente. Non esiste un failover reale: il monitor segnala il guasto, non cambia fonte.

Decisione collegata: [ADR 0012](../adr/0012-portal-monitoring-and-change-history.md).

[Torna all'indice wiki](README.md).
