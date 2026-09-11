---
name: code-review-skill
description: "Review pyAvanza changes before a production deploy or pull request. Use for correctness, live-account safety, performance, architecture, validation, and documentation-drift reviews."
argument-hint: "Describe the change set, risk area, and whether you want findings only or deploy-ready validation."
---

# Code Review Skill

## When to Use

Use for a code review, production-readiness pass, security review, performance review, or before opening a pull request or deploying.

## Procedure

1. Classify the change surface and read `AGENTS.md`, `.github/copilot-instructions.md`, and the matching path-specific instruction.
2. Inspect correctness first, then live-account safety, secret handling, persistent-file compatibility, performance, and architecture.
3. For Avanza, Yahoo, and Telegram changes, confirm that client payload adaptation remains in `client/`, repository workflows remain in `operators/`, credentials stay environment-backed, and tests do not place orders.
4. For strategy changes, keep technical analysis free of broker side effects, preserve the ranked-strategy JSON contract, and assess both backtest and live-loop behavior.
5. For deployment, settings, paths, storage, or entry-point changes, verify the local `src/` and deployed-root layouts remain compatible and that `DRY_RUN` cannot be bypassed accidentally.
6. Run the narrowest relevant validation. Start with a colocated test when one exists; use `uv run pytest` for the regular suite and `uv run python -m compileall src .github/hooks/scripts` for repository-wide syntax validation. Run integration coverage only when credentials and explicit approval make live API access safe.
7. Run `python3 .github/hooks/scripts/check_documentation_alignment.py`. When it requires a documentation pass, load and execute `documentation-skill`, then rerun the checker.

## Review Focus

- Correctness: signal-to-order flow, exit behavior, data resolution, ranking, and generated-artifact compatibility.
- Safety: `DRY_RUN`, order placement, watchlist mutation, credentials, alert delivery, and no secret exposure.
- Reliability: retry bounds, missing data, local/deployed paths, persistent-state writes, and cron assumptions.
- Architecture: thin entry points, client versus operator boundaries, side-effect-free services, and no speculative helper layers.
- Performance: repeated broker or data calls, polling work, strategy-combination growth, and unnecessary DataFrame copies.

## Completion Criteria

Report findings first, ordered by severity and with concrete file references. Then state the validation run, documentation outcome, residual risk, and one of: `ready`, `ready with follow-up`, or `not ready`.