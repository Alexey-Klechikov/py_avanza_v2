---
description: "Use when updating AGENTS.md or README.md after code, configuration, deployment, or Copilot workflow changes. Routes durable facts to the correct documentation surface."
applyTo:
  - "AGENTS.md"
  - "README.md"
---
# Documentation Routing

- Put contributor-facing guidance in `AGENTS.md`: fast start, where to look first, codebase conventions, validation notes, deployment gotchas, generated artifact expectations, and reusable pitfalls discovered while editing the repo.
- Put project-facing documentation in `README.md`: project purpose, runtime tasks, architecture, external dependencies, setup, deployment, and externally useful operational context.
- When one change matters to both audiences, update both files but phrase them differently.
- Update both files for durable runtime or deployment contracts, including strategy-file naming, persistent path layout, credential-loading paths, cron scheduling, and live-trading safety defaults.
- Update only `AGENTS.md` for contributor workflow, test prerequisites, generated-artifact pitfalls, and Copilot customization or hook behavior.
- Update only `README.md` for a new task entry point, data source, deployment prerequisite, or other operator-facing runtime behavior.
- Do not copy one-off debugging notes into `README.md` or project overview material into `AGENTS.md` unless it changes how contributors work in this repository.
