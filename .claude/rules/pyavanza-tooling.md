---
paths:
  - "pyproject.toml"
  - "uv.lock"
  - ".pre-commit-config.yaml"
  - ".flake8"
---

# Repository Tooling

- Dependencies via `uv` only (no `pip`/`requirements.txt`): edit the right `[project.dependencies]` or `[dependency-groups]` entry, then `uv lock`. Don't add tools overlapping Black, Flake8, isort, autoflake, pytest, pyupgrade.
- Runtime stays `requires-python = "==3.13.*"` (`.python-version`) unless explicitly upgraded; `pyupgrade --py311-plus` and Black `target-version = py311` must move together with it.
- Tool config lives in `pyproject.toml` (`[tool.flake8]`, `[tool.isort]`, `[tool.black]`, `[tool.pytest.ini_options]`, `[tool.pylint]`); `.flake8` is a legacy fallback, add no new dotfiles.
- `.pre-commit-config.yaml`: formatters/linters at `pre-commit`, the two Claude gates at `pre-push`; keep `default_install_hook_types` with both.
