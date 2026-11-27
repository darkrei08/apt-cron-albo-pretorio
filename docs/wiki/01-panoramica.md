# Panoramica

> Lingua: italiano su richiesta esplicita dell'operatore; decisione registrata nel [wayfinder locale](../wayfinder.md) e nella [mappa GitHub](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1).

`cron-albo-pretorio` legge il Registro sorgente degli atti pubblici APT Basilicata. Pubblica gli atti nel canale Telegram di destinazione e mantiene l'Indice generato nel repository. `portal_monitor.py` controlla il portale senza pubblicare atti.

## Superfici di pubblicazione

| Superficie | Contenuto |
| --- | --- |
| Canale di destinazione | Messaggio HTML, PDF ufficiale e ogni allegato scaricabile. |
| Indice generato | `public/index.json`, `public/index.md`, `public/index.html`. |

Entrambe usano lo stesso Insieme dei campi pubblicati. I documenti ufficiali non vengono copiati nel repository.

## README attuale

Il README è l'ingresso operativo breve. Offre:

- scopo del repository in cinque punti;
- avvio rapido con i tre comandi senza credenziali;
- indice linkabile alla wiki;
- tabella completa dei comandi;
- configurazione essenziale;
- comandi di verifica.

I dettagli lunghi sono in questa wiki. Le decisioni architetturali sono negli [ADR](../adr/).

## Termini

I termini canonici sono in [GLOSSARY.md](../../GLOSSARY.md). I più usati sono:

- **Registro sorgente**: fonte ufficiale dei dati.
- **Atto pubblico**: singolo atto identificato da numero, anno e link ufficiale.
- **Impronta dell'atto**: valore che determina nuovo, modificato o invariato.
- **Stato degli atti**: memoria durevole di impronte e link inviati.
- **Indice generato**: pubblicazione derivata degli atti correnti.
- **Snapshot del portale**: vista normalizzata usata dal monitoraggio.
- **Evento di modifica**: differenza o errore registrato nella cronologia.

[Torna all'indice wiki](README.md).
