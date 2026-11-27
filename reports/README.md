# Publication reports

This directory is maintained by `.github/workflows/update-index.yml`.

- `latest.md`: last hourly publication report.
- `hourly/YYYY-MM-DD/HHMM.md`: one Markdown report per hourly run.
- `daily/YYYY-MM-DD.md`: aggregate report for the day.

The workflow writes these files to a temporary work area, then commits only the generated Markdown and the generated `public/index.*` files. No local state, token or document byte is committed.

The report distinguishes:

- `new_acts`: new acts appeared in the current window.
- `changed_acts`: existing act metadata changed.
- `removed_acts`: acts left the current window.
- `no_changes`: no index difference was observed.
