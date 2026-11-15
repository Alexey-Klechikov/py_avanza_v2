---
name: code-review-skill
description: "Pre-PR or pre-deploy review of pyAvanza changes: correctness, security, live-account safety, performance, style/architecture, validation, doc drift, PR readiness."
argument-hint: "Change set or risk areas; findings only or deploy-ready validation."
context: fork
agent: code-reviewer
---

Review this change set: $ARGUMENTS

If no range is given, review upstream..working tree (`git diff @{upstream}` plus untracked files). Run the narrowest validation and the documentation alignment check, then return findings, open questions, and the PR-readiness verdict in your standard output format.
