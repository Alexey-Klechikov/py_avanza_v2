from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from git_range import REPOSITORY_ROOT, WORKING_TREE, git_output, untracked_files

VSCODE_BINARY_GLOB = "anthropic.claude-code-*/resources/native-binary/claude"
READ_ONLY_TOOLS = ("Read", "Grep", "Glob")
MAX_DIFF_CHARS = 200_000
TIMED_OUT_RETURN_CODE = 124
DEFAULT_TIMEOUT_SECONDS = 900


def _find_claude_binary() -> str | None:
    configured = os.environ.get("CLAUDE_BIN") or shutil.which("claude")
    if configured:
        return configured

    candidates = sorted((Path.home() / ".vscode" / "extensions").glob(VSCODE_BINARY_GLOB))
    return str(candidates[-1]) if candidates else None


def _build_untracked_diff(paths: list[str]) -> str:
    sections = []
    for path in paths:
        file_path = REPOSITORY_ROOT / path
        if file_path.is_symlink() or not file_path.is_file():
            continue
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        sections.append(f"diff --git a/{path} b/{path}\nnew untracked file\n+++ b/{path}\n")
        sections.extend(f"+{line}\n" for line in lines)
    return "".join(sections)


def build_review_diff(from_ref: str, to_ref: str, files: list[str]) -> str:
    revision = from_ref if to_ref == WORKING_TREE else f"{from_ref}...{to_ref}"
    diff = git_output(
        ["diff", "--no-ext-diff", "--no-textconv", "--no-color", "--unified=5", revision, "--"] + files,
    )
    if to_ref == WORKING_TREE:
        untracked = set(untracked_files())
        diff += _build_untracked_diff([path for path in files if path in untracked])
    if len(diff) <= MAX_DIFF_CHARS:
        return diff
    return diff[:MAX_DIFF_CHARS] + f"\n[diff truncated to {MAX_DIFF_CHARS} characters; Read the files for the rest]"


def tagged_lines(output: str, prefixes: tuple[str, ...]) -> list[str]:
    stripped_lines = (line.strip() for line in output.splitlines())
    return [line for line in stripped_lines if line.startswith(prefixes)]


def parse_verdict(output: str, prefix: str) -> str | None:
    verdict_lines = tagged_lines(output=output, prefixes=(prefix,))
    if not verdict_lines:
        return None
    return verdict_lines[-1].removeprefix(prefix).strip()


def build_command(
    claude_binary: str,
    prompt: str,
    agent: str | None,
    allowed_tools: tuple[str, ...],
    disallowed_tools: tuple[str, ...],
) -> list[str]:
    command = [claude_binary, "-p", prompt]
    if agent:
        command.extend(["--agent", agent])
    command.extend(
        [
            "--permission-mode",
            "dontAsk",
            "--setting-sources",
            "project",
            "--allowed-tools",
            *allowed_tools,
            "--disallowed-tools",
            *disallowed_tools,
            "--settings",
            '{"disableAllHooks": true}',
            "--output-format",
            "text",
        ],
    )
    max_budget = os.environ.get("CLAUDE_REVIEW_MAX_BUDGET_USD")
    if max_budget:
        command.extend(["--max-budget-usd", max_budget])
    return command


def run_claude(
    hook_id: str,
    prompt: str,
    agent: str | None,
    allowed_tools: tuple[str, ...],
    disallowed_tools: tuple[str, ...],
) -> subprocess.CompletedProcess[str] | None:
    claude_binary = _find_claude_binary()
    if claude_binary is None:
        print(f"{hook_id}: Claude Code CLI not found (set CLAUDE_BIN); skipping.", file=sys.stderr)
        return None

    command = build_command(
        claude_binary=claude_binary,
        prompt=prompt,
        agent=agent,
        allowed_tools=allowed_tools,
        disallowed_tools=disallowed_tools,
    )
    raw_timeout = os.environ.get("CLAUDE_REVIEW_TIMEOUT_SECONDS", "")
    timeout_seconds = int(raw_timeout) if raw_timeout.isdigit() else DEFAULT_TIMEOUT_SECONDS
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            cwd=REPOSITORY_ROOT,
            stdin=subprocess.DEVNULL,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=command,
            returncode=TIMED_OUT_RETURN_CODE,
            stdout="",
            stderr=f"timed out after {timeout_seconds}s",
        )
