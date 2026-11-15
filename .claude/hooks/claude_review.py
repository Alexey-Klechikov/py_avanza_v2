from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

from git_range import REPOSITORY_ROOT, WORKING_TREE, git_lines, git_output, untracked_files

VSCODE_BINARY_GLOB = "anthropic.claude-code-*/resources/native-binary/claude"
READ_ONLY_TOOLS = ("Read", "Grep", "Glob")
MAX_DIFF_CHARS = 200_000
TIMED_OUT_RETURN_CODE = 124
DEFAULT_TIMEOUT_SECONDS = 900
PASS_RECORD_DIRECTORY = "claude-gates"
SELF_CHECK_INSTRUCTIONS = """\
Then validate with `uv run python -m compileall src .claude/hooks` and the focused `uv run pytest <path>` for each \
touched module. Commit the untracked files that belong to this change and ask before deleting any, since untracked \
files change the reviewed set. Finally run both push gates in the background (each can take several minutes), \
in this order: \
`python3 .claude/hooks/pre_push_documentation.py --working-tree`, then \
`python3 .claude/hooks/pre_push_code_review.py --working-tree`. Verify and fix anything they report, and rerun until \
both exit 0; a passing run records the reviewed state so the next `git push` of exactly this content skips review. \
Commit all resulting changes, including any documentation edits made by the gate, and do not push."""
PASTE_MARKER = "-" * 30 + " paste into Claude Code " + "-" * 30


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


def blob_ids(paths: list[str], to_ref: str) -> dict[str, str]:
    if not paths:
        return {}
    if to_ref == WORKING_TREE:
        ids = git_lines(["hash-object", "--", *paths])
    else:
        ids = git_lines(["rev-parse", *(f"{to_ref}:{path}" for path in paths)])
    if len(ids) != len(paths):
        print("Could not fingerprint the reviewed files; this pass will not be cached.", file=sys.stderr)
        return {}
    return dict(zip(paths, ids))


def _review_standards(agent: str) -> list[str]:
    hooks = REPOSITORY_ROOT / ".claude" / "hooks"
    standard_files = [
        REPOSITORY_ROOT / "CLAUDE.md",
        REPOSITORY_ROOT / ".claude" / "agents" / f"{agent}.md",
        *sorted((REPOSITORY_ROOT / ".claude" / "rules").glob("*.md")),
        *sorted(hooks.glob("*.py")),
    ]
    return [path.read_text(encoding="utf-8") for path in standard_files if path.is_file()]


def review_fingerprint(
    hook_id: str,
    prompt_template: str,
    agent: str,
    from_ref: str,
    to_ref: str,
    blobs: dict[str, str],
) -> str | None:
    merge_base = git_lines(["merge-base", from_ref, "HEAD" if to_ref == WORKING_TREE else to_ref])
    if not blobs or not merge_base:
        return None
    revision = [merge_base[0]] if to_ref == WORKING_TREE else [merge_base[0], to_ref]
    deleted = git_lines(["diff", "--name-only", "--diff-filter=D", *revision, "--"])
    reviewed = [f"{path}:{blobs[path]}" for path in sorted(blobs)] + [f"{path}:deleted" for path in deleted]
    entries = [hook_id, prompt_template, *_review_standards(agent), merge_base[0], *reviewed]
    return hashlib.sha256("\n".join(entries).encode()).hexdigest()


def _pass_record_path(hook_id: str) -> Path | None:
    git_path = git_lines(["rev-parse", "--git-path", f"{PASS_RECORD_DIRECTORY}/{hook_id}"])
    return REPOSITORY_ROOT / git_path[0] if git_path else None


def already_passed(hook_id: str, fingerprint: str | None) -> bool:
    record = _pass_record_path(hook_id)
    if fingerprint is None or record is None or not record.is_file():
        return False
    return record.read_text(encoding="utf-8").strip() == fingerprint


def record_pass(hook_id: str, fingerprint: str | None) -> None:
    record = _pass_record_path(hook_id)
    if fingerprint is None or record is None:
        return
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(fingerprint + "\n", encoding="utf-8")


def paste_block(prompt: str) -> str:
    return f"{PASTE_MARKER}\n{prompt.strip()}\n{PASTE_MARKER}"
