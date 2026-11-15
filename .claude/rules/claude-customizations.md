---
paths:
  - "CLAUDE.md"
  - "**/CLAUDE.md"
  - ".claude/**"
  - ".pre-commit-config.yaml"
  - "README.md"
---

# Claude Code Customizations

## Layout and token budget
- Root `CLAUDE.md` loads on every request: keep it to always-on policy and the repo map. No nested `CLAUDE.md` today; add one only for a subtree a rule can't express.
- `.claude/rules/*.md` load only for matching `paths` (the only frontmatter field read there). Keep them narrow, avoid unscoped rules, keep overlapping scopes intentional, and never duplicate a fact across `CLAUDE.md`, rules, agents, or skills; reference the owner. `pyavanza-python.md` owns coding style for coding, refactoring, and review.
- Agents (`name`, `description`, `tools`, `model`; descriptions specific and discovery-oriented) own judgment: `documenter` owns doc routing, `code-reviewer` owns review standards and severity, `refactorer` owns the refactor workflow. Keep judgment out of hook prompts; the end-to-end request workflow lives in `CLAUDE.md`, not in an agent.
- Skills are thin `context: fork` wrappers (`agent:` frontmatter) so their exploration stays out of the main context: `code-review-skill` → `code-reviewer`, `documentation-skill` → `documenter`.

## Pre-push gates (`.pre-commit-config.yaml`, stage `pre-push`, documentation first, then code review)
- Hooks never modify the host, commit, or edit anything except documentation and their own pass records.
- One-round fixes: a blocked gate prints a paste-ready prompt (between `paste into Claude Code` markers, from `SELF_CHECK_INSTRUCTIONS` in `claude_review.py`) that fixes every listed blocking finding, reruns both gates with `--working-tree` until they exit 0, and commits. A pass writes a fingerprint (merge base, reviewed file blobs and deletions, prompt template, and the review standards: `CLAUDE.md`, the agent, `.claude/rules/*.md`, hook code) to `.git/claude-gates/<gate-id>`; a later run over identical content skips Claude. After autofix edits with a `PASS` verdict, the doc gate records the edited state, so committing those edits unchanged makes the next push skip it. Prompts tell each agent to report every blocking finding in a single pass.
- `documentation-alignment` → `.claude/hooks/pre_push_documentation.py`, `documenter` in autofix mode. Edits are limited to `README.md` and `CLAUDE.md` (`DOCUMENTATION_EDIT_RULES`); headless edits under `.claude/` are denied, so findings there come back as `BLOCKING:`. Diffs of `uv.lock` and `src/config/OMX_trade_strategies*.json` are omitted (names still listed); it skips when only those changed. Prints `UPDATED:`/`BLOCKING:`/`ADVISORY:` lines and parses `DOCUMENTATION_VERDICT: PASS|BLOCK`. Blocks when any Markdown file changed during the run or unfixed blocking findings remain. It fixes blocking findings only, so clean pushes stay edit-free.
- `code-review` → `.claude/hooks/pre_push_code_review.py`, `code-reviewer` read-only on changed files except Markdown, `uv.lock`, and `src/config/OMX_trade_strategies*.json`. Prints `BLOCKING:`/`ADVISORY:` lines and blocks on `CODE_REVIEW_VERDICT: BLOCK`.
- Both block when the Claude run fails or returns no verdict, and skip when the CLI is missing or there is no upstream. `--working-tree` checks upstream..working tree.
- Both use `.claude/hooks/claude_review.py` (CLI discovery, diff via `git diff --no-ext-diff --no-textconv` capped at 200,000 characters and embedded in the prompt, headless command). `Bash` is always blocked; `dontAsk`, project settings only, `disableAllHooks`. Keep output prefixes in sync with prompts, since only prefixed lines are printed.

## Standalone scripts (not run by `git push`)
- `check_documentation_alignment.py`: deterministic check that `README.md`/`CLAUDE.md` changed alongside routed paths; never edits.
- `pre_push_refactorer.py`: advisory read-only `refactorer` review of `src/` and `.claude/hooks/` Python.

## Maintenance
- Hook scripts are standard-library only; shared helpers live in `git_range.py` and `claude_review.py`. Validate with `uv run python -m compileall .claude/hooks` and `git diff --check`; exercise a changed gate through `.git/hooks/pre-push` with a test range on stdin.
- Update `CLAUDE.md` when customization, enforcement, or contributor workflow changes; `README.md` only for public behavior, setup, deployment, or externally useful validation.
