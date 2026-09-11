---
name: refactoring-skill
description: "Refactor pyAvanza code safely while preserving behavior. Use for simplifying trading, API, storage, or utility code; checking references; and validating documentation drift."
argument-hint: "Describe the target code, desired simplification, behavior constraints, and validation requirements."
---

# Refactoring Skill

## When to Use

Use for requested simplification, extraction, de-duplication, dead-code removal, or an architecture cleanup that must preserve behavior.

## Procedure

1. Start from the controlling code path and state one falsifiable reason the current implementation is too complex, duplicated, risky, or wasteful. Do not refactor without that evidence.
2. Read `AGENTS.md`, `.github/copilot-instructions.md`, and the matching path-specific instruction before editing.
3. Choose the smallest behavior-preserving change. Keep API payload adaptation in clients, repository workflows in operators, technical analysis free of broker side effects, and entry points thin.
4. Before removing code, inspect references and runtime registration or serialization use. Keep code when dynamic use cannot be ruled out.
5. Make one focused edit, then immediately run the narrowest relevant test or validation. Repair that same slice before expanding the refactor.
6. Recheck live-account boundaries, generated strategy-file compatibility, local/deployed paths, retry behavior, and repeated polling or DataFrame work in the touched area.
7. Run `python3 .github/hooks/scripts/check_documentation_alignment.py`. When it reports a requirement, load and execute `documentation-skill`, then rerun the checker.

## Guardrails

- Preserve behavior unless the request explicitly changes it.
- Do not introduce generic extension points, forwarding helpers, or design-pattern ceremony without a demonstrated maintenance benefit.
- Never validate a refactor by running live trade entry points. Prefer colocated tests, `uv run pytest`, and `uv run python -m compileall src .github/hooks/scripts`.
- Run credential-dependent integration tests only with explicit approval and configured credentials.

## Completion Criteria

Report the concrete simplification, reference evidence for any removal, focused validation, documentation outcome, and remaining risk or intentionally skipped cleanup.