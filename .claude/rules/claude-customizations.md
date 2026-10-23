---
paths:
  - "CLAUDE.md"
  - "**/CLAUDE.md"
  - ".claude/**"
  - ".pre-commit-config.yaml"
  - "README.md"
---

# Claude Code Customizations

- Keep always-on repository policy in the root `CLAUDE.md`. This repo has no nested `CLAUDE.md` files today because `src/` has no independently-owned subtree; add one only if a future subtree needs isolated policy a `.claude/rules/*.md` file can't express. Put rules that span directories in `.claude/rules/*.md` with narrow `paths` globs; `paths` is the only frontmatter field Claude Code reads there. Avoid unscoped rules and keep overlapping scopes intentional.
- `CLAUDE.md` is the single contributor baseline; there is no `AGENTS.md` or Copilot configuration. Do not duplicate one rule across `CLAUDE.md` and `.claude/rules/*.md`; cross-reference the owning file instead.
- Agents need YAML frontmatter with a specific, discovery-oriented `description` and Claude Code field names (`name`, `description`, `tools`, `model`).
- The repo has three agents and no skills. `documenter` owns documentation judgment and routing, `code-reviewer` owns review standards and severity, and `refactorer` owns the refactoring workflow and coding-style guidance for `src/**`. The end-to-end request workflow lives in the root `CLAUDE.md`, not in an agent. Keep judgment in the agents, not in hook prompts.
- Hooks must never modify the host, commit, or edit anything except documentation. The only repository hooks are two blocking gates that run at `pre-push` through `.pre-commit-config.yaml`:
  - `documentation-alignment` runs `.claude/hooks/pre_push_documentation.py` with the `documenter` agent in autofix mode on every push with changed files. `DOCUMENTATION_EDIT_RULES` scopes edits to `README.md` and `CLAUDE.md` files. Claude Code denies headless edits under `.claude/` even with an allow rule, so findings there are reported as `BLOCKING:` instead. It prints only `UPDATED:`, `BLOCKING:`, and `ADVISORY:` lines and parses `DOCUMENTATION_VERDICT: PASS|BLOCK`. It blocks when any Markdown file changed during the run, because those edits are not part of the pushed commits, and when unfixed blocking findings remain.
  - `code-review` runs `.claude/hooks/pre_push_code_review.py` with the `code-reviewer` agent read-only on every changed file except Markdown, `uv.lock`, and `src/config/OMX_trade_strategies*.json`. It prints only `BLOCKING:` and `ADVISORY:` lines and blocks on `CODE_REVIEW_VERDICT: BLOCK`.
  - Both gates block when the Claude run fails or returns no verdict, and skip when the Claude CLI is not found or there is no upstream to compare against. Run either with `--working-tree` to check upstream..working tree before committing.
  - Both go through `.claude/hooks/claude_review.py`, which owns CLI discovery, the diff, and the headless command. The hook computes the diff itself (`git diff --no-ext-diff --no-textconv`, capped at 200,000 characters) and embeds it in the prompt. Each hook passes its own allowed and blocked tools; `Bash` is always blocked. Permissions are `dontAsk`, only project settings load, and all hooks are off (`disableAllHooks`). Keep each output prefix in sync with its prompt, because the hooks print only prefixed lines.
- The documentation gate fixes only blocking findings, never advisory ones, so a clean push does not keep producing edits. When it reports `BLOCKING:` findings it could not fix, run the `documenter` agent interactively, update the listed documentation, commit, and push again.
- Keep hook scripts standard-library only, with shared git helpers in `.claude/hooks/git_range.py` and shared Claude-run helpers in `.claude/hooks/claude_review.py`. Validate customization changes with `uv run python -m compileall .claude/hooks` and `git diff --check`, and exercise a changed gate through `.git/hooks/pre-push` with a test push range on stdin.
- Update the root `CLAUDE.md` (instruction map, validation, documentation routing) whenever customization, enforcement, or contributor workflow changes. Update `README.md` only when public behavior, setup, deployment, or externally useful validation guidance changes.
