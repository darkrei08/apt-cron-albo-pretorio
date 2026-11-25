# Code Review Rules

- Keep changes narrowly scoped to the requested behavior.
- Preserve unrelated user changes and local configuration.
- Prefer standard-library APIs and existing dependencies.
- Keep code, comments, tests, and repository documentation in English. Exception: `odd/tasks/*.md` quotes the operator's original request and specs verbatim, including non-English text; those quotations are evidence and are never translated.
- Verify behavior through the public interface with simulated HTTP in tests.
- Never log credentials or commit runtime state.
- Run the relevant focused tests and the full suite when the runner is available; report unverified checks honestly.
