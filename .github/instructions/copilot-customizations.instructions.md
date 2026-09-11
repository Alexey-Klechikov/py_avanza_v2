---
description: "Use when editing Copilot instructions, agents, skills, hooks, or repository-wide AI guidance under .github/. Covers customization ownership, discovery, and deterministic documentation routing."
applyTo:
  - ".github/copilot-instructions.md"
  - ".github/agents/**"
  - ".github/hooks/**"
  - ".github/instructions/**"
  - ".github/skills/**"
---
# Copilot Customization Guidelines

- Keep `AGENTS.md` for concise contributor guidance and `.github/copilot-instructions.md` for repo-wide engineering behavior. Do not duplicate path-specific or task-specific rules in either file.
- Put rules tied to edited paths in one focused `.github/instructions/*.instructions.md` file with a narrow `applyTo` pattern and a keyword-rich `description` for on-demand discovery.
- Put repeatable, on-demand workflows in `.github/skills/<name>/SKILL.md`. The skill `name` must match its folder, and the body must describe a complete procedure without restating repository documentation.
- Keep `.github/agents/*.agent.md` focused on a single orchestration role with only the tools it needs. Use an explicit `description`, `argument-hint`, and clear completion criteria.
- Use `.github/hooks/` only for fast, deterministic commands. Hooks can direct an agent to load a skill but cannot execute a Copilot skill themselves.
- When customization policy, hook behavior, skill workflows, or validation commands change, update `AGENTS.md`, add or update focused regression coverage for executable hooks, and run the documentation alignment check.