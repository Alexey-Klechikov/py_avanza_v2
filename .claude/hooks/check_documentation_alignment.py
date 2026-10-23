#!/usr/bin/env python3

from __future__ import annotations

import sys
from dataclasses import dataclass

from git_range import WORKING_TREE, changed_files_in_range, pushed_range_from_env, resolve_review_range


@dataclass(frozen=True)
class DocumentationRule:
    name: str
    prefixes: tuple[str, ...] = ()
    exact_paths: tuple[str, ...] = ()
    suffixes: tuple[str, ...] = ()
    required_docs: tuple[str, ...] = ()
    reason: str = ""

    def matches(self, path: str) -> bool:
        return path in self.exact_paths or path.startswith(self.prefixes) or path.endswith(self.suffixes)


RULES = (
    DocumentationRule(
        name="runtime-contract",
        exact_paths=(
            "src/apis/avanza/client/client.py",
            "src/config/settings.py",
            "src/services/storage/operators.py",
            "src/services/ta/strategies/operators.py",
            "src/task_end_of_day.py",
            "src/task_end_of_week.py",
            "src/task_trade.py",
            ".github/workflows/deploy.yaml",
        ),
        required_docs=("README.md", "CLAUDE.md"),
        reason="Runtime behavior, credentials, persistent artifacts, deployment, or live-trading workflow changed.",
    ),
    DocumentationRule(
        name="tooling-workflow",
        exact_paths=(
            "pyproject.toml",
            ".pre-commit-config.yaml",
        ),
        prefixes=(".claude/hooks/", ".claude/agents/", ".claude/skills/"),
        required_docs=("CLAUDE.md",),
        reason="Contributor workflow, agents, skills, or repository automation changed.",
    ),
    DocumentationRule(
        name="agent-policy",
        prefixes=(".claude/rules/",),
        suffixes=("/CLAUDE.md",),
        required_docs=("CLAUDE.md",),
        reason="Repository guidance or path-specific policy changed.",
    ),
)


def collect_changed_files(push_range: tuple[str, str] | None) -> set[str]:
    from_ref, to_ref = push_range or ("HEAD", WORKING_TREE)
    return set(changed_files_in_range(from_ref=from_ref, to_ref=to_ref))


def find_missing_documentation(changed_files: set[str]) -> list[str]:
    findings: list[str] = []

    for rule in RULES:
        triggering_paths = sorted(path for path in changed_files if rule.matches(path))
        missing_docs = [doc for doc in rule.required_docs if doc not in changed_files]
        if not triggering_paths or not missing_docs:
            continue

        findings.append(
            "\n".join(
                (
                    f"Rule: {rule.name}",
                    f"Reason: {rule.reason}",
                    f"Changed files: {', '.join(triggering_paths[:6])}",
                    f"Required docs not changed: {', '.join(missing_docs)}",
                ),
            ),
        )

    return findings


def _describe_change_source(push_range: tuple[str, str] | None) -> str:
    if push_range is None:
        return "working tree"
    from_ref, to_ref = push_range
    if to_ref == WORKING_TREE:
        return f"range {from_ref[:12]}..working tree (including uncommitted changes)"
    return f"pushed range {from_ref[:12]}..{to_ref[:12]}"


def build_success_message(changed_files: set[str], push_range: tuple[str, str] | None) -> str:
    checked = f"Checked {len(changed_files)} changed file(s) in the {_describe_change_source(push_range)}."
    triggered = [rule.name for rule in RULES if any(rule.matches(path) for path in changed_files)]
    if not triggered:
        return f"{checked} No documentation rule triggered."
    return f"{checked} Rules triggered: {', '.join(triggered)}. Required documentation is present."


def build_failure_message(findings: list[str], push_range: tuple[str, str] | None) -> str:
    return (
        f"Documentation alignment check failed. The {_describe_change_source(push_range)} "
        "requires a verified documentation pass.\n\n"
        "In Claude Code, run `/documentation-skill` to verify the triggering changes and update the listed "
        "documentation, commit the result, and push again. This deterministic check runs before the pre-push "
        "/documentation-skill review and never edits files.\n\n" + "\n\n".join(findings)
    )


def main() -> int:
    if sys.argv[1:]:
        print("Usage: check_documentation_alignment.py (upstream..working tree, or PRE_COMMIT_*_REF)", file=sys.stderr)
        return 64

    push_range = pushed_range_from_env() or resolve_review_range(working_tree=True)
    changed_files = collect_changed_files(push_range)
    findings = find_missing_documentation(changed_files)
    if not findings:
        print(build_success_message(changed_files=changed_files, push_range=push_range))
        return 0

    print(build_failure_message(findings=findings, push_range=push_range), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
