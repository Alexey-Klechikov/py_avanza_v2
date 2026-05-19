---
description: "Use when deciding whether durable repository knowledge should update AGENTS.md, README.md, or both. Provides concrete examples for documentation updates."
applyTo:
  - "AGENTS.md"
  - "README.md"
---
# Documentation Update Examples

- Update both `AGENTS.md` and `README.md` when a change creates a durable contributor workflow and also changes runtime behavior or deployment expectations.
- Example for both: changing the strategy-file naming or storage path that contributors must preserve and operators must understand.
- Example for both: changing the cron or deploy layout, credential loading path, or live-trading safety defaults.
- Update only `AGENTS.md` when the fact mainly affects how contributors should work in the repo.
- Example for `AGENTS.md` only: a local-vs-remote path gotcha, integration-test credential requirement, generated-artifact pitfall, or hook workflow that changes how contributors should edit the repo.
- Example for `AGENTS.md` only: a watchlist naming constraint or dry-run default that mainly affects safe development and validation.
- Update only `README.md` when the fact mainly affects what the project does or how an operator or user runs it.
- Example for `README.md` only: a new task entry point, data source, deployment prerequisite, or runtime contract such as watchlist naming.
- If a change is temporary debugging noise, one-off migration detail, or implementation trivia with no lasting guidance value, do not update either document.
