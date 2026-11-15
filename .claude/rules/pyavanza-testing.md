---
paths:
  - "src/**/*_test.py"
---

# Testing

- Tests sit next to their module as `<module>_test.py`, in `unittest.TestCase` style unless the surrounding tests differ.
- Default tests are deterministic with local fixtures: no credentials, network, or live account.
- Mark credential-dependent Avanza coverage `@pytest.mark.integration`; never run it by default.
