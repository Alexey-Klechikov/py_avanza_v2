---
paths:
  - "tests/**"
---

# Testing

- Tests live in `tests/`, next to `src/`, mirroring its layout: `src/<package>/<module>.py` is tested by `tests/<package>/test_<module>.py`, in `unittest.TestCase` style unless the surrounding tests differ. `tests/` is not deployed (deploy syncs only `src/`).
- Default tests are deterministic with local fixtures: no credentials, network, or live account.
- Mark credential-dependent Avanza coverage `@pytest.mark.integration`; never run it by default.
