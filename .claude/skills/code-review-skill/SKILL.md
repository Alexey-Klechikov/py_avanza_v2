---
name: code-review-skill
description: 'Review pyAvanza changes before a production deploy or pull request. Use for strict security review, live-account safety, performance evaluation, style and architecture checks, pre-commit validation, documentation drift checks, and PR readiness.'
argument-hint: 'Describe the change set, risk areas, and whether you want findings only or deploy-ready validation.'
---

# Code Review Skill

## What This Produces

This skill produces a strict pre-PR review that prioritizes correctness, security, performance, and repository convention drift before a pull request is generated.

Expected outputs:
- Findings ordered by severity, with concrete file references when issues are found
- A PR-readiness decision: ready, ready with minor follow-up, or not ready
- Validation summary for the relevant checks that were run
- Documentation update check across `CLAUDE.md`, `.claude/`, and `README.md`

## When to Use

Use this skill when the user asks for:
- A code review or pre-PR review
- Security or performance review of a change
- Style or architecture conformance review
- A final pass before generating a pull request
- Validation that pre-commit hooks and repo documentation were considered

Typical triggers:
- "review this change"
- "is this PR ready?"
- "do a security pass"
- "check performance regressions"
- "validate before opening a PR"

## Review Standard

Apply these priorities in order:
1. Correctness and behavioral regressions
2. Security risks and unsafe assumptions
3. Performance regressions and unnecessary complexity
4. Violations of repo conventions and style guidance
5. Missing validation or missing documentation updates

Do not block PR readiness for purely cosmetic issues unless the repo explicitly depends on that style rule for maintainability or correctness.

## Procedure

1. Classify the change surface.
Determine whether the change touches Avanza/Yahoo/Telegram integrations, strategy/trading-loop logic, runtime services, config, entry points, repository tooling, or a mixed change.

2. Read the governing instructions before judging the change.
Always consider:
- root `CLAUDE.md`

Read additional path-specific rules when relevant:
- `src/apis/**` -> `.claude/rules/pyavanza-apis.md`
- `src/config/**` -> `.claude/rules/pyavanza-config.md`
- `.github/workflows/deploy.yaml` -> `.claude/rules/pyavanza-deploy.md`
- `src/task_*.py`, `src/development.py`, `src/print_logs.sh` -> `.claude/rules/pyavanza-entrypoints.md`
- `src/services/storage/**`, `src/services/calendar/**` -> `.claude/rules/pyavanza-services.md`
- `src/services/ta/**`, `src/tasks/**` -> `.claude/rules/pyavanza-strategies.md`
- `src/**/*_test.py` -> `.claude/rules/pyavanza-testing.md`
- `src/utils/**` -> `.claude/rules/pyavanza-utils.md`
- `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml`, `.flake8` -> `.claude/rules/pyavanza-tooling.md`
- `CLAUDE.md`, `.claude/**`, `README.md` -> `.claude/rules/claude-customizations.md`

3. Inspect the change with a findings-first mindset.
Look for:
- Security: credential handling (`src/config/.env`, `src/apis/avanza/client/client.py`), secret leakage into logs or Telegram alerts, unsafe input handling in strategy/indicator parsing, dangerous defaults around `DRY_RUN` or order placement
- Performance: repeated Avanza/Yahoo API calls, unnecessary DataFrame copies or re-parses, avoidable disk I/O on cached OHLCV data, hot-path branching in the live loop, strategy-combination growth in the backtest engine
- Style and architecture: client/operator boundary violations, broker side effects leaking into `src/services/ta/**`, helpers that only forward data, barrel imports via `__init__.py`, `src.`-prefixed imports instead of the flat `apis`/`config`/`services`/`tasks`/`utils` roots
- Reliability: broken local/deployed path duality, generated strategy-file schema drift, cron/entry-point assumptions, missing retry bounds around broker calls

4. Run the narrowest relevant validation before declaring PR-ready.
Choose based on the touched area:
- A colocated `*_test.py` for the touched module: `uv run pytest <path>`
- Repository-wide syntax check: `uv run python -m compileall src .claude/hooks`
- The regular suite: `uv run pytest` (skip `-m integration` unless credentials and explicit approval make live Avanza access safe)
- Dependency changes: `uv lock`
- Never validate a review by running `src/task_trade.py` directly; it can place live orders when `DRY_RUN` is `False`

5. Check documentation drift before PR generation.
Ask whether the change should also update:
- `README.md` for externally visible behavior, setup, deployment, or runtime changes
- root `CLAUDE.md` for contributor workflow, validation commands, repo topology, documentation routing, or repo-wide engineering policy changes
- `.claude/rules/*.md` for durable path-specific rules discovered during the work

Run `python3 .claude/hooks/check_documentation_alignment.py` from the repository root. If it reports a requirement, apply `documentation-skill` and rerun the check before declaring the change PR-ready.

6. Decide PR readiness.
Use one of these outcomes:
- Ready: no blocking findings, validation appropriate to the change passed, docs are aligned
- Ready with follow-up: only minor non-blocking issues remain, and they are explicitly called out
- Not ready: any correctness, security, significant performance, validation, or documentation blocker remains

## Decision Points

### Security finding found
- Treat as blocking unless proven non-exploitable in this environment.
- Prefer concrete exploit or failure reasoning over generic warnings.

### Performance concern found
- Treat as blocking when it affects hot paths, repeated polling, data-heavy transforms, or user-visible latency.
- Otherwise mark as non-blocking but explain the scale assumption.

### Style issue found
- Escalate only when it breaks a repository rule, makes the code harder to verify, or hides real behavior.
- Do not drown out higher-signal findings with nits.

### Validation unavailable
- State exactly which command could not be run and why.
- Do not claim PR readiness without calling out the missing check.

### Documentation uncertainty
- If runtime behavior, public behavior, or contributor workflow changed, assume a doc update is needed unless the diff proves otherwise.

## Output Format

When findings exist:
1. List findings first, ordered by severity, with file references.
2. Then state assumptions or open questions.
3. End with PR readiness and the validation summary.

When no findings exist:
1. State that no blocking findings were identified.
2. Mention residual risks or unrun checks.
3. End with PR readiness and documentation status.

## Repo-Specific Guardrails

- Keep `src/apis/*/client/` limited to third-party payload adaptation and retries; keep repo-facing workflows in `src/apis/*/operators/`.
- Keep `src/services/ta/**` free of broker/account side effects; live trading stays in `src/tasks/main.py` and `src/apis/avanza/trade/operator.py`.
- Preserve the `OMX_trade_strategies*.json` schema and the `DT_<direction>_<instrument>_<instrument_type>` watchlist naming contract.
- Import Python symbols from the flat package roots under `src/` (`apis`, `config`, `services`, `tasks`, `utils`), never through `__init__.py` barrels or a `src.` prefix.
- Treat any change near `DRY_RUN`, order placement, or exit-rule timing in `src/task_trade.py` and `src/tasks/main.py` as high risk.

## Example Prompts

- `/code-review-skill Review the current branch for security, performance, and PR readiness.`
- `/code-review-skill Check whether these Avanza API changes are ready for a PR and whether docs need updates.`
- `/code-review-skill Do a strict pre-deploy pass on the strategy ranking and live-loop changes.`
