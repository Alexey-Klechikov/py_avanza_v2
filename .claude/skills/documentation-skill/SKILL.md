---
name: documentation-skill
description: 'Update repository documentation from verified code and configuration changes. Use for README updates, CLAUDE.md and `.claude/rules` maintenance, instruction routing fixes, hook guidance updates, repo audits, and documentation drift after code or workflow changes.'
argument-hint: 'Describe the changed area, what documentation may be stale, and whether this is a docs-only task or a follow-up to code changes.'
---

# Documentation Skill

## What This Produces

This skill produces verified documentation updates that keep repository guidance aligned with code, configuration, hooks, and contributor workflow.

Expected outputs:
- A concise map of the repo areas reviewed
- Small documentation edits in the correct surfaces
- A summary of the evidence used for each update
- Any remaining gaps or ambiguous areas that still need manual review

## When to Use

Use this skill when the user asks for:
- README updates
- `CLAUDE.md` and `.claude/rules/` maintenance
- Instruction or hook guidance updates
- A docs pass after code or workflow changes
- A repository documentation audit

Typical triggers:
- "update the docs"
- "what documentation should change?"
- "sync CLAUDE.md with the repo"
- "fix stale customization guidance"
- "audit the docs after this change"

## Documentation Standard

Apply these priorities in order:
1. Verify durable facts from code, configuration, tests, scripts, or existing automation before writing
2. Put each fact in the narrowest correct documentation surface
3. Update only the files materially affected by verified findings
4. Keep contributor guidance, runtime guidance, and agent guidance separate
5. State uncertainty instead of guessing when evidence is incomplete

Do not make product-code changes unless the task explicitly asks for them.

## Procedure

1. Run the documentation alignment check.
From the repository root, run `python3 .claude/hooks/check_documentation_alignment.py`, which checks upstream..working tree. Treat its triggered rules and required documentation as the initial routing signal. When resolving a blocked push, rerun it with `PRE_COMMIT_FROM_REF=<remote sha> PRE_COMMIT_TO_REF=HEAD` to inspect the exact pushed range.

2. Map the relevant repo area.
Identify the smallest set of code, configuration, customization, and scripts that control the behavior or workflow being documented.

3. Verify the durable facts.
Prefer source code, executable configuration, tests, and scripts over comments when they disagree.

4. Route each finding to the right surface.
Use:
- `README.md` for externally useful runtime behavior, setup, deployment, or API changes
- root `CLAUDE.md` for contributor workflow, validation commands, repo topology, pitfalls, documentation routing, and always-on repo-wide agent behavior or engineering policy
- `.claude/rules/*.md` with `paths` for path-scoped rules that span directories (API/client/operator boundaries, config, deploy, entry points, services, strategies, testing, utils, tooling)
- `.claude/hooks/` and `.pre-commit-config.yaml` for pre-push gates, both the deterministic routing rules and the Claude-based reviews
- `.claude/skills/` for reusable on-demand workflows like review and documentation passes
- `.claude/agents/refactorer.md` only when the refactor workflow or coding-style expectations change

5. Make the smallest documentation edits that close the verified gap.
Do not copy the same guidance into every file. Phrase the same fact differently when both contributor docs and external docs need it.
Check every sentence you add or change against the code or configuration it describes before keeping it, including sentences written only to resolve a review finding. Never extend a verified fact to neighboring items, such as applying one endpoint's restriction to its siblings, without checking each item.

6. Validate consistency.
Re-read the edited documentation, rerun the alignment check, and make sure every changed statement matches verified repository behavior and the `refactorer` agent name.

7. Rerun the push gate locally before handing back.
Run `python3 .claude/hooks/pre_push_documentation.py --working-tree`. It applies the same routing rules, prompt, and verdict as `git push`, over upstream..working tree including uncommitted and untracked files. It may fix blocking findings itself: check every `UPDATED:` edit against the source as in step 5. Treat any `BLOCKING:` line as new input to steps 3–6. Rerun until it passes without editing anything. Hand the change back for commit only after that pass, and say that it passed.

## Decision Points

### README vs CLAUDE.md
- Update `README.md` when the change matters to runtime users, setup, deployment, or public behavior.
- Update the root `CLAUDE.md` when the change matters to contributors, validation workflow, repo map, or documentation routing.

### Instructions vs broad docs
- Use a `paths`-scoped `.claude/rules/*.md` when the rule applies only to a path or layer.
- Use the root `CLAUDE.md` when the rule is always-on across the repo.

### Hook or skill update needed
- Update `.claude/hooks/` when behavior must be enforced at push time: the routing rules for deterministic path requirements, and the gate prompts for judgment-based review.
- Update `.claude/skills/` when the workflow is reusable but should remain on-demand.
- The `documentation-alignment` pre-push hook runs this skill headlessly in autofix mode, with the diff embedded in the prompt, no shell, and edits allowed only on `README.md` and `CLAUDE.md` files. In that mode, fix blocking findings only, report findings under `.claude/` as `BLOCKING:` because edits there are denied, reply with just the requested `UPDATED:`, `BLOCKING:`, and `ADVISORY:` lines, and end with the `DOCUMENTATION_VERDICT` line. The hook blocks the push whenever it edited something so the edits get reviewed and committed.

### Fixing pre-push gate findings
- The gate reviews the whole unpushed range, so sentences you add while fixing one finding are reviewed on the next push too. Verify them as carefully as the original finding.
- Verify each reported finding against the source before acting on it. Fix blocking findings; fix an advisory finding only when it is cheap and verified.
- Treat the hook's own `UPDATED:` edits the same way: verify them before committing.
- Close the loop with step 7. Never hand back an unverified fix for the user to discover at push time.

### Evidence incomplete
- Document less, not more.
- State the ambiguity and the exact missing evidence.

## Completion Criteria

The documentation pass is complete when:
1. Each changed statement is backed by verified repository evidence
2. The guidance was written in the correct documentation surface
3. No unaffected documentation files were changed
4. `python3 .claude/hooks/check_documentation_alignment.py` passes for the resulting working tree, and `python3 .claude/hooks/pre_push_documentation.py --working-tree` passes without editing anything
5. Remaining uncertainty, if any, is explicit

## Output Format

Return:
1. What repo areas were analyzed
2. What documentation files were updated and why
3. What evidence those updates were based on
4. Any remaining documentation gaps or ambiguous areas

## Example Prompts

- `/documentation-skill Audit the repo docs after these runtime and workflow changes.`
- `/documentation-skill Update CLAUDE.md and any relevant rules based on the latest customization changes.`
- `/documentation-skill Verify whether this trading runtime change requires README updates or only contributor docs.`
