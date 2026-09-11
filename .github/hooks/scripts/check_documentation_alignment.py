#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TypedDict

HookResponse = TypedDict(
    "HookResponse",
    {
        "continue": bool,
        "stopReason": str,
        "systemMessage": str,
    },
)


@dataclass(frozen=True)
class DocumentationRule:
    name: str
    prefixes: tuple[str, ...] = ()
    exact_paths: tuple[str, ...] = ()
    suffixes: tuple[str, ...] = ()
    required_docs: tuple[str, ...] = ()
    reason: str = ""

    def matches(self, path: str) -> bool:
        normalized = path.strip()
        return (
            normalized in self.exact_paths
            or normalized.startswith(self.prefixes)
            or normalized.endswith(self.suffixes)
        )


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
        ),
        required_docs=("README.md", "AGENTS.md"),
        reason="Runtime behavior, credentials, persistent artifacts, or live-trading workflow changed.",
    ),
    DocumentationRule(
        name="deployment-contract",
        exact_paths=(".github/workflows/deploy.yaml",),
        required_docs=("README.md", "AGENTS.md"),
        reason="Deployment layout, credentials, or cron contract changed.",
    ),
    DocumentationRule(
        name="customization-policy",
        exact_paths=(
            ".github/copilot-instructions.md",
            "pyproject.toml",
        ),
        prefixes=(
            ".github/hooks/",
            ".github/agents/",
            ".github/skills/",
            ".github/instructions/",
        ),
        required_docs=("AGENTS.md",),
        reason="Contributor workflow or repository automation changed.",
    ),
)


def _run_git_command(args: list[str]) -> list[str]:
    completed = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return []

    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _collect_worktree_changed_files() -> set[str]:
    tracked = set(_run_git_command(["diff", "--name-only", "--diff-filter=ACMR", "HEAD", "--"]))
    untracked = set(_run_git_command(["ls-files", "--others", "--exclude-standard"]))
    return {path for path in tracked | untracked if not path.endswith("/")}


def _collect_staged_changed_files() -> set[str]:
    staged = _run_git_command(["diff", "--cached", "--name-only", "--diff-filter=ACMR", "--"])
    return {path for path in staged if not path.endswith("/")}


def collect_changed_files(staged: bool) -> set[str]:
    if staged:
        return _collect_staged_changed_files()
    return _collect_worktree_changed_files()


def _normalize_doc_path(path: str) -> str:
    return PurePosixPath(path).as_posix()


def _changed_doc_targets(changed_files: set[str]) -> set[str]:
    doc_targets: set[str] = set()
    for path in changed_files:
        normalized = _normalize_doc_path(path)
        if normalized in {"README.md", "AGENTS.md", ".github/copilot-instructions.md"}:
            doc_targets.add(normalized)
            continue
        if normalized.startswith((".github/instructions/", ".github/agents/", ".github/hooks/")):
            doc_targets.add(normalized)
    return doc_targets


def find_missing_documentation(changed_files: set[str]) -> list[str]:
    changed_docs = _changed_doc_targets(changed_files)
    findings: list[str] = []

    for rule in RULES:
        triggering_paths = sorted(path for path in changed_files if rule.matches(path))
        if not triggering_paths:
            continue

        missing_docs = [doc for doc in rule.required_docs if doc not in changed_docs]
        if not missing_docs:
            continue

        findings.append(
            "\n".join(
                (
                    f"Rule: {rule.name}",
                    f"Reason: {rule.reason}",
                    f"Changed files: {', '.join(triggering_paths[:6])}",
                    f"Required docs not changed: {', '.join(missing_docs)}",
                )
            )
        )

    return findings


def build_failure_response(findings: list[str], staged: bool) -> HookResponse:
    change_source = "staged change set" if staged else "working tree"
    message = (
        "Documentation alignment check failed. The latest "
        f"{change_source} requires a verified documentation pass.\n\n"
        "Before concluding, load and execute `/documentation-skill` to verify the triggering changes, "
        "update the listed documentation, and rerun this check. The hook cannot execute skills directly; "
        "it is the deterministic backstop for that workflow.\n\n" + "\n\n".join(findings)
    )
    return {
        "continue": False,
        "stopReason": "Documentation updates are required for the latest change set.",
        "systemMessage": message,
    }


def main() -> int:
    _ = sys.stdin.read()
    arguments = sys.argv[1:]
    if any(argument != "--staged" for argument in arguments) or arguments.count("--staged") > 1:
        print("Usage: check_documentation_alignment.py [--staged]", file=sys.stderr)
        return 64

    staged = "--staged" in arguments
    changed_files = collect_changed_files(staged=staged)
    if not changed_files:
        print(json.dumps({"continue": True}))
        return 0

    findings = find_missing_documentation(changed_files)
    if not findings:
        print(json.dumps({"continue": True}))
        return 0

    print(json.dumps(build_failure_response(findings=findings, staged=staged)))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
