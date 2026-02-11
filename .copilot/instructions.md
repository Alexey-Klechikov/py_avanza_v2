You are assisting in the pyAvanza_v2 codebase (Python 3.12). Keep guidance and changes aligned with the existing patterns and tools in this repository.

## Project shape
- Primary package root: src/
- API integrations live under src/apis (Avanza, Yahoo, Telegram).
- Domain operators live under src/**/operators.py and act as orchestration layers.
- Config lives under src/config (SETTINGS is the global config object).
- Technical analysis lives under src/services/ta with indicators and strategies.
- Logging utilities live under src/utils/logger.
- Data and logs are written under src/data and src/logs.

## Coding style
- Python typing is used throughout: use built-in generics (list[...], dict[...]) and PEP 604 unions (A | None).
- Follow Black/Flake8 constraints from pyproject.toml (line length 119).
- Keep imports grouped: standard library, third-party, local.
- Prefer short, focused methods; keep orchestration in operators.
- Avoid heavy inline comments; only add comments when logic is non-obvious.
- Default to ASCII; avoid introducing Unicode unless already used in a file.

## Method call style
- Prefer keyword arguments for non-logger method calls when supported.
- Do not force kwargs for built-ins or positional-only APIs.
- Do not change logger calls unless explicitly requested by the user.

## Error handling
- Known API failures use specific exceptions (e.g., OrderException).
- Prefer clear, user-facing log messages and return None where appropriate.
- Avoid broad exception handling unless the surrounding code already uses it.

## Logging
- Logger is retrieved via utils.logger.operators.get_logger().
- Logging format is centralized; do not reformat log handlers.
- Keep log message style consistent and concise.

## Data and side effects
- Functions that read or write data should log their intent.
- Favor idempotent reads; do not mutate shared state unless needed.
- Use SETTINGS for account filters, names, and feature toggles.

## Testing and tools
- Tests live near clients/models (e.g., chart_data_test.py). Add tests when behavior changes.
- Dependencies managed via PDM; do not modify tooling unless asked.

## When editing
- Prefer minimal, localized changes. Do not refactor unrelated code.
- Preserve public method signatures unless requested.
- Use keyword args in internal calls for clarity.
- Avoid changing external API call shapes unless required.

## When unsure
- Ask for clarification on trading logic, account filters, or strategy selection.
- Confirm whether a behavior change is desired vs a refactor.
