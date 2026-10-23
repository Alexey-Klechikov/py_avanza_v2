---
paths:
  - "pyproject.toml"
  - "uv.lock"
  - ".pre-commit-config.yaml"
  - ".flake8"
---

# Repository Tooling

- Manage dependencies with `uv`, not `pip` or `requirements.txt`. Keep `pyproject.toml` and `uv.lock` aligned whenever dependency definitions change; validate with `uv lock`.
- Preserve the current Python contract at `3.13` (`requires-python = "==3.13.*"`, pinned in `.python-version`) unless the task explicitly requires an upgrade. Note that `pyupgrade` in `.pre-commit-config.yaml` is pinned to `--py311-plus` and Black's `target-version` is `py311`; keep those pins and the `3.13` runtime target in sync if you change either.
- Keep formatting and linting settings centralized in `pyproject.toml` (`[tool.flake8]`, `[tool.isort]`, `[tool.black]`, `[tool.pytest.ini_options]`, `[tool.pylint]`). If a tool already reads its config from there, update the shared config instead of creating extra dotfiles. `.flake8` exists only as a legacy fallback; prefer `pyproject.toml`.
- `.pre-commit-config.yaml` runs formatter/linter hooks (`black`, `flake8`, `autoflake`, `isort`, `add-trailing-comma`, `pyupgrade`) at the default `pre-commit` stage, plus the blocking `documentation-alignment` and `code-review` gates at `pre-push` (local hooks backed by `.claude/hooks/pre_push_documentation.py` and `.claude/hooks/pre_push_code_review.py`, in that order). Keep `default_install_hook_types` including both `pre-commit` and `pre-push` so `pre-commit install` wires up both.
- When adding dependencies, update the correct `[dependency-groups]` or `[project.dependencies]` entry, refresh `uv.lock`, and avoid introducing duplicate tools that overlap with the existing Black, Flake8, isort, autoflake, pytest, and pyupgrade setup.
- Validate dependency changes with `uv lock`; validate tooling edits with `uv run python -m compileall src .claude/hooks` and `uv run pytest`.
