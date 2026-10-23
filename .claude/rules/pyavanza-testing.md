---
paths:
  - "src/**/*_test.py"
---

# Testing

- Keep tests next to the code they cover and name them `<module>_test.py`. Use the existing `unittest.TestCase` style unless the surrounding test establishes a different pattern.
- Keep unit and model tests deterministic with local fixtures. Do not require Avanza credentials, a network connection, or a live account for the default test suite.
- Mark credential-dependent Avanza coverage with `@pytest.mark.integration`. Do not run that coverage by default; `src/apis/avanza/client/client_test.py` requires `src/config/.env` and may contact a live account.
- For a changed slice, run its focused test first. Use `uv run pytest` for the regular suite and `uv run python -m compileall src .claude/hooks` as the repository-wide syntax check.
