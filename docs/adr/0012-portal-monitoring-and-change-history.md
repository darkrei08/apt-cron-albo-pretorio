# 0012 — Portal monitoring and change history

- Status: accepted

The operator needs an early warning when the Source register stops answering, when data or document
downloads fail, or when the portal's shape changes. Uptime Kuma covers availability with HTTP,
keyword and JSON-query monitors and Telegram notifications. changedetection.io covers content
diffs with CSS, XPath, JSONPath and jq filters plus notification hooks. This repository talks to a
JSON API, so it can reuse its existing source parser instead of running either service.

The decision is to add `portal_monitor.py`, a separate CLI that reads the current publication
window, probes the attachment-link endpoint and one document byte sample, then compares a normalized
Portal snapshot with the previous one. A change in response keys, notice keys, total pages, result
count, notice fingerprint, detail link or attachment link produces a Change event.

The history is JSON in `portal-history.json`, a generated runtime file that stays out of commits.
The repository documents its schema and retention here and in `docs/wiki/04-monitoraggio.md`; a
curated summary can be published through an issue or pull request when needed. The file keeps the
last snapshot and the latest 200 events to stay reviewable. Alerts
go to a dedicated Telegram chat from protected `APT_ALERT_TELEGRAM_*` variables; cron `MAILTO` keeps
receiving the redacted stderr line. Publication credentials, Notice state and the Generated index are
untouched. There is no real failover source: the monitor reports failure, it does not switch feeds.

References: [Uptime Kuma](https://github.com/louislam/uptime-kuma) for HTTP/keyword/JSON-query monitors and Telegram notifications; [changedetection.io](https://github.com/dgtlmoon/changedetection.io) for CSS/XPath/JSONPath/jq filters and content-diff notifications.
