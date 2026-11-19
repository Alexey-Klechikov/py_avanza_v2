---
paths:
  - "src/**/*.py"
  - ".claude/hooks/*.py"
---

# Python Style, Nesting, Complexity

Single owner of coding style. Applies when writing code, refactoring (`refactorer`), and reviewing (`code-reviewer`).

## Style
- Black + isort (profile black) at 119 columns; flake8 (`pflake8`) ignores W503, E203, F401; `add-trailing-comma`; `pyupgrade --py311-plus`, so use `list[str]`, `dict[str, int]`, `X | None`.
- Import each symbol from the module that owns it (flat roots, see `CLAUDE.md`), never via re-exports.
- File order: models/classes, module constants, private `_helpers`, public entrypoints. File-local helpers start with `_`.
- Stable shapes are typed (Pydantic, `NamedTuple`, frozen `dataclass`) like `client/models/` and `services/ta/strategies/models/`, not `Any`, `object`, or nested untyped `dict`.
- In `src/`, log through `get_logger()` from `utils/logger/operators.py`; never `print` or ad hoc loggers. Hook scripts are stdlib-only and report via `print`.
- Descriptive names over comments. Keep a comment only when the name cannot say it: it explains why (a constraint, a trade-off, a library bug, a calibration result), never what the code does. Complex logic (formulas, time alignment, look-ahead guards) may keep a short what-comment. Exception: indicator methods in `services/ta/indicators/` keep their full docstrings (what the indicator measures, defaults, references) and each indicator module keeps its `import pandas_ta as ta` (registers the `DataFrame.ta` accessor).
- Names are conclusive: the subject (what it is) plus any qualifier that changes its meaning (`sorted_trades`, `closed_history`, `train_rows`), units where they matter (`move_bp`, `hold_bars`), and an `is_`/`has_` prefix for booleans and boolean masks. No `data`, `tmp`, `res`, `df`, or single letters outside comprehensions and math.
- No speculative parameters, extension points, or pattern ceremony; use a pattern only when it removes repeated branching, unstable conditionals, or hard-to-test wiring; prefer plain code when it only adds indirection. No one-line forwarding helpers or wrapper chains: one indented block beats a wrapper chain three files deep. Grow functions horizontally (clear sequential steps), not vertically (helper layers that only pass data through).

## Nesting (max two levels in a function body)
Flatten in this order:
1. Guard clauses: invert and `return`/`continue`/`raise` early; happy path at the lowest indent.
2. Comprehensions for pure filter/map: one `for`, at most one `if`, one line; otherwise a loop.
3. `dict` lookup of values/callables instead of `if`/`elif` chains on one discriminator; `match` for destructuring.
4. Extract a `_verb_noun` helper only for one cohesive job that makes the caller flatter.
5. Combine conditions or name them as a local boolean instead of stacking `if`s.

## Complexity
- No nested scans or `x in list` inside loops: build a `dict`/`set` keyed by symbol, resolution, or strategy name once.
- Hoist loop-invariant work: indicator parameter, date, and resolution parsing, sorting; regexes as module constants. Compute per-symbol or per-resolution values once, not per (symbol, strategy) pair.
- Read each OHLCV pickle or the weighted model once per run via `services/storage/operators.py` or `tasks/shared/weighted_model.py`; never fix repeated I/O with module-level mutable caches.
- Sort rankings once; top-N via `heapq.nlargest`/`min`/`max`; no `list.pop(0)`, `insert(0, …)`, or string `+=` in loops; `set`/`dict.fromkeys` for membership and dedup.
- pandas: vectorize instead of `DataFrame.apply` on large frames; collect frames and `pd.concat` once; no needless `.copy()`.
- Avanza calls stay sequential: no threads or `asyncio` around trade, order, or watchlist calls; the client holds session/auth state and the live loop's timing is deliberate.
