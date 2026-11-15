---
name: documentation-skill
description: "Verified documentation pass for pyAvanza: README, CLAUDE.md, .claude rules/agents/hooks guidance, doc drift after code or workflow changes, repo doc audits, fixing blocked documentation-alignment pushes."
argument-hint: "Changed area, suspected stale docs, docs-only or follow-up to code changes."
context: fork
agent: documenter
---

Run a documentation pass for: $ARGUMENTS

If no range is given, use upstream..working tree. Follow your procedure, including the push-gate rerun when this resolves a blocked push, and return your interactive output.
