from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WORKING_TREE = "working-tree"


def git_output(args: list[str]) -> str:
    completed = subprocess.run(["git", *args], check=False, capture_output=True, text=True, cwd=REPOSITORY_ROOT)
    if completed.returncode != 0:
        return ""
    return completed.stdout


def git_lines(args: list[str]) -> list[str]:
    return [line.strip() for line in git_output(args).splitlines() if line.strip()]


def pushed_range_from_env() -> tuple[str, str] | None:
    from_ref = os.environ.get("PRE_COMMIT_FROM_REF")
    if not from_ref:
        return None
    return from_ref, os.environ.get("PRE_COMMIT_TO_REF") or "HEAD"


def resolve_review_range(working_tree: bool) -> tuple[str, str] | None:
    push_range = pushed_range_from_env()
    if push_range is not None and not working_tree:
        return push_range

    upstream = git_lines(["rev-parse", "--verify", "--quiet", "@{upstream}"])
    if not upstream:
        return None
    return upstream[0], WORKING_TREE if working_tree else "HEAD"


def untracked_files() -> list[str]:
    return [path for path in git_lines(["ls-files", "--others", "--exclude-standard"]) if not path.endswith("/")]


def changed_files_in_range(from_ref: str, to_ref: str) -> list[str]:
    if to_ref != WORKING_TREE:
        return git_lines(["diff", "--name-only", "--diff-filter=ACMR", f"{from_ref}...{to_ref}"])

    tracked = git_lines(["diff", "--name-only", "--diff-filter=ACMR", from_ref, "--"])
    return sorted(set(tracked) | set(untracked_files()))
