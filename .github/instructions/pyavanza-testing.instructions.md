---
description: "Use when adding or editing pyAvanza unit, model, integration, or hook tests. Covers colocated test conventions, Avanza credential safety, and focused validation commands."
applyTo:
  - "src/**/*_test.py"
  - ".github/hooks/scripts/test_documentation_alignment.py"
---
# Testing Guidelines

- Keep tests next to the code they cover and name them `<module>_test.py`. Use the existing `unittest.TestCase` style unless the surrounding test establishes a different pattern.
- Keep unit and model tests deterministic with local fixtures. Do not require Avanza credentials, a network connection, or a live account for the default test suite.
- Mark credential-dependent Avanza coverage with `@pytest.mark.integration`. Do not run that coverage by default; `src/apis/avanza/client/client_test.py` requires `src/config/.env` and may contact a live account.
- For a changed slice, run its focused test first. Use `uv run pytest` for the regular suite and `uv run python -m compileall src .github/hooks/scripts` as the repository-wide syntax check.
- Test hook behavior with its colocated `unittest` module and assert both positive routing and intentional non-trigger cases.