---
name: documentation-skill
description: 'Update repository documentation from verified code and configuration changes. Use for README updates, AGENTS.md updates, copilot-instructions maintenance, instruction routing fixes, hook guidance updates, repo audits, and documentation drift after code or workflow changes.'
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
- AGENTS.md updates
- `.github/copilot-instructions.md` maintenance
- Instruction or hook guidance updates
- A docs pass after code or workflow changes
- A repository documentation audit

Typical triggers:
- "update the docs"
- "what documentation should change?"
- "sync AGENTS with the repo"
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
From the repository root, run `python3 .github/hooks/scripts/check_documentation_alignment.py` for the working tree. Treat its triggered rules and required documentation as the initial routing signal. When the hook routes work here, complete this pass before concluding and rerun the checker after documentation edits. Use `--staged` to inspect the exact staged change set when needed.

2. Map the relevant repo area.
Identify the smallest set of code, configuration, customization, and scripts that control the behavior or workflow being documented.

3. Verify the durable facts.
Prefer source code, executable configuration, tests, and scripts over comments when they disagree.

4. Route each finding to the right surface.
Use:
- `README.md` for externally useful runtime behavior, setup, deployment, or API changes
- `AGENTS.md` for contributor workflow, validation commands, repo topology, pitfalls, and documentation routing
- `.github/copilot-instructions.md` for always-on repo-wide agent behavior or engineering policy
- `.github/instructions/*.instructions.md` for stable path-specific rules
- `.github/hooks/` for deterministic reminder behavior and documentation-steering logic
- `.github/skills/` for reusable on-demand workflows like refactoring, review, and documentation passes
- `.github/agents/*.agent.md` only when the Linus entrypoint itself changes

5. Make the smallest documentation edits that close the verified gap.
Do not copy the same guidance into every file. Phrase the same fact differently when both contributor docs and external docs need it.

6. Validate consistency.
Re-read the edited documentation, rerun the alignment check, and make sure every changed statement matches verified repository behavior and the `Linus` naming contract.

## Decision Points

### README vs AGENTS
- Update `README.md` when the change matters to runtime users, setup, deployment, or public behavior.
- Update `AGENTS.md` when the change matters to contributors, validation workflow, repo map, or documentation routing.

### Instructions vs broad docs
- Use `.github/instructions/*.instructions.md` when the rule applies only to a path or layer.
- Use `.github/copilot-instructions.md` when the rule is always-on across the repo.

### Hook or skill update needed
- Update `.github/hooks/` when behavior must be enforced deterministically.
- Update `.github/skills/` when the workflow is reusable but should remain on-demand.
- Hooks cannot execute skills. A documentation hook may require `/documentation-skill`, but the skill performs the evidence gathering and edits.

### Evidence incomplete
- Document less, not more.
- State the ambiguity and the exact missing evidence.

## Completion Criteria

The documentation pass is complete when:
1. Each changed statement is backed by verified repository evidence
2. The guidance was written in the correct documentation surface
3. No unaffected documentation files were changed
4. `python3 .github/hooks/scripts/check_documentation_alignment.py` passes for the resulting working tree after any routed documentation update
5. Remaining uncertainty, if any, is explicit

## Output Format

Return:
1. What repo areas were analyzed
2. What documentation files were updated and why
3. What evidence those updates were based on
4. Any remaining documentation gaps or ambiguous areas

## Example Prompts

- `/documentation-skill Audit the repo docs after these runtime and workflow changes.`
- `/documentation-skill Update AGENTS.md and any relevant instructions based on the latest customization changes.`
- `/documentation-skill Verify whether this trading runtime change requires README updates or only contributor docs.`
