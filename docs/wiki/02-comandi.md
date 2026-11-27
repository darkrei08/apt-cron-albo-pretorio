# Comandi

> Lingua: italiano su richiesta esplicita dell'operatore; decisione registrata nel [wayfinder locale](../wayfinder.md) e nella [mappa GitHub](https://github.com/darkrei08/apt-cron-albo-pretorio/issues/1).

Questa pagina elenca tutti i comandi eseguibili e le opzioni presenti nel codice.

## Pubblicazione

| Comando | Credenziali | Effetto |
| --- | --- | --- |
| `python3 apt_cron.py --dry-run` | nessuna | Legge la finestra corrente e riporta i conteggi. |
| `python3 apt_cron.py --refresh-index` | nessuna | Rigenera solo `public/index.*`. |
| `python3 apt_cron.py --backfill --dry-run` | nessuna | Legge tutto l'archivio e riporta quanti atti verrebbero pubblicati. |
| `python3 apt_cron.py --backfill` | profilo Telegram selezionato | Pubblica l'archivio dal più vecchio al più recente. |
| `python3 apt_cron.py` | profilo Telegram selezionato | Pubblica atti nuovi o modificati e aggiorna l'indice. |

`--refresh-index` e `--backfill` non possono essere usati insieme.

## Monitoraggio

| Comando | Credenziali | Effetto |
| --- | --- | --- |
| `python3 portal_monitor.py --dry-run` | nessuna | Legge il portale, confronta lo snapshot, non scrive e non avvisa. |
| `python3 portal_monitor.py` | variabili di allerta | Scrive la cronologia e invia l'alert su modifiche o errori. |

## Opzioni

### `apt_cron.py`

| Opzione | Default | Effetto |
| --- | --- | --- |
| `--dry-run` | disattivata | Nessuna pubblicazione e nessuna scrittura di stato. |
| `--refresh-index` | disattivata | Solo rigenerazione dell'Indice generato. |
| `--backfill` | disattivata | Lettura di tutte le pagine dell'archivio. |
| `--source-url` | valore di `APT_SOURCE_URL` | Base dell'API del Registro sorgente. |
| `--state-path` | valore di `APT_STATE_PATH` | File dello Stato degli atti. |
| `--attachments-base` | valore di `APT_ATTACHMENTS_BASE` | Base dell'endpoint allegati. |
| `--index-dir` | valore di `APT_INDEX_DIR` | Directory dell'Indice generato. |

### `portal_monitor.py`

| Opzione | Default | Effetto |
| --- | --- | --- |
| `--dry-run` | disattivata | Nessuna cronologia e nessun alert. |
| `--history-path` | valore di `APT_PORTAL_HISTORY_PATH` | File JSON della cronologia. |
| `--source-url` | valore di `APT_SOURCE_URL` | Base dell'API del Registro sorgente. |
| `--attachments-base` | valore di `APT_ATTACHMENTS_BASE` | Base dell'endpoint allegati. |
| `--detail-base` | valore di `APT_DETAIL_BASE` | Base dei link ufficiali degli atti. |

## Output e uscita

Entrambi i comandi stampano una riga JSON su successo e una riga `error: ...` redatta su stderr in caso di errore.

| Codice | Significato |
| --- | --- |
| `0` | Esecuzione riuscita. |
| `1` | Errore runtime; il token selezionato viene redatto. |
| `2` | Argomenti non validi, profilo sconosciuto o `APT_PAGE_SIZE` non positivo. |

Esempi di output:

```json
{"notices": 748, "published": 0, "dry_run": true}
{"notices": 23, "changes": 1, "status": "changed", "alerted": false, "dry_run": true}
```

## Verifica

```sh
python3 -m unittest discover -s tests
python3 -m py_compile apt_cron.py portal_monitor.py
git diff --check
```

[Torna all'indice wiki](README.md).
