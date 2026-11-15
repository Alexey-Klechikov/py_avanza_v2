#!/usr/bin/env python3

from __future__ import annotations

import fnmatch
import sys

from claude_review import (
    READ_ONLY_TOOLS,
    SELF_CHECK_INSTRUCTIONS,
    already_passed,
    blob_ids,
    build_review_diff,
    parse_verdict,
    paste_block,
    record_pass,
    review_fingerprint,
    run_claude,
    tagged_lines,
)
from git_range import REPOSITORY_ROOT, WORKING_TREE, changed_files_in_range, git_lines, resolve_review_range

HOOK_ID = "documentation-alignment"
AGENT = "documenter"
VERDICT_PREFIX = "DOCUMENTATION_VERDICT:"
BLOCKING_PREFIX = "BLOCKING:"
REPORT_PREFIXES = ("UPDATED:", BLOCKING_PREFIX, "ADVISORY:")
SKIP_HINT = f"Bypass once with `SKIP={HOOK_ID} git push`."
DOCUMENTATION_EDIT_RULES = (
    "Edit(./README.md)",
    "Edit(./**/CLAUDE.md)",
)
BLOCKED_TOOLS = ("Bash", "NotebookEdit")
DIFF_EXCLUDED_PATTERNS = ("uv.lock", "src/config/OMX_trade_strategies*.json")

PROMPT_TEMPLATE = """\
PRE-PUSH AUTOFIX MODE. Audit the documentation against the commits being pushed in the range \
{from_ref}..{to_ref}. Use the diff below and the files in the working tree; the working tree may contain \
uncommitted changes, so judge the diff. Verify that every surface in your routing is still accurate after this push \
and covers the durable facts it introduces, and fix every blocking finding in place. This is the only audit before \
the author pushes again: find every blocking gap now, and give each one you cannot fix a concrete fix.

Changed files in the push:
{files}

Diff (generated files such as `uv.lock` and strategy snapshots are listed above but omitted here):
```diff
{diff}
```

Reply with only these lines and no other text:
- `UPDATED: file - what changed - evidence` for each fix you made
- `BLOCKING: file - problem - evidence - concrete fix` for each blocking finding you could not fix
- `ADVISORY: file - problem - smallest fix` for each advisory finding
- a final line, `{verdict} PASS` when no blocking finding remains unfixed, otherwise `{verdict} BLOCK`
"""

FIX_PROMPT_TEMPLATE = """\
Fix these blocking pre-push documentation findings for {from_ref}..{to_ref} in one pass:
{findings}
{updated_note}
Verify each finding against the code before editing, and change only what it requires.
{self_check}
"""


def _snapshot_documentation() -> dict[str, bytes]:
    paths = git_lines(["ls-files", "--cached", "--others", "--exclude-standard", "--", "*.md"])
    file_paths = {path: REPOSITORY_ROOT / path for path in paths}
    return {path: file_path.read_bytes() for path, file_path in file_paths.items() if file_path.is_file()}


def _changed_documentation(before: dict[str, bytes]) -> list[str]:
    after = _snapshot_documentation()
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


def select_diff_files(paths: list[str]) -> list[str]:
    return [path for path in paths if not any(fnmatch.fnmatch(path, glob) for glob in DIFF_EXCLUDED_PATTERNS)]


def build_prompt(from_ref: str, to_ref: str, files: list[str], diff_files: list[str]) -> str:
    return PROMPT_TEMPLATE.format(
        from_ref=from_ref,
        to_ref=to_ref,
        files="\n".join(f"- {path}" for path in files),
        diff=build_review_diff(from_ref=from_ref, to_ref=to_ref, files=diff_files),
        verdict=VERDICT_PREFIX,
    )


def build_fix_prompt(from_ref: str, to_ref: str, findings: list[str], updated: list[str]) -> str:
    updated_note = f"The gate already edited {', '.join(updated)}; review those edits too.\n" if updated else ""
    return FIX_PROMPT_TEMPLATE.format(
        from_ref=from_ref[:12],
        to_ref=to_ref[:12],
        findings="\n".join(f"- {finding.removeprefix(BLOCKING_PREFIX).strip()}" for finding in findings),
        updated_note=updated_note,
        self_check=SELF_CHECK_INSTRUCTIONS,
    )


def _fingerprint(from_ref: str, to_ref: str, blobs: dict[str, str]) -> str | None:
    return review_fingerprint(
        hook_id=HOOK_ID,
        prompt_template=PROMPT_TEMPLATE,
        agent=AGENT,
        from_ref=from_ref,
        to_ref=to_ref,
        blobs=blobs,
    )


def main() -> int:
    if sys.argv[1:] not in ([], ["--working-tree"]):
        print(f"Usage: {sys.argv[0]} [--working-tree]", file=sys.stderr)
        return 64

    review_range = resolve_review_range(working_tree=sys.argv[1:] == ["--working-tree"])
    if review_range is None:
        print(f"{HOOK_ID}: no comparable remote ref for this push; skipping.")
        return 0

    from_ref, to_ref = review_range
    files = sorted(changed_files_in_range(from_ref=from_ref, to_ref=to_ref))
    diff_files = select_diff_files(files)
    if not diff_files:
        print(f"{HOOK_ID}: no documentation-relevant changes in this push; skipping.")
        return 0

    blobs = blob_ids(paths=files, to_ref=to_ref)
    if already_passed(hook_id=HOOK_ID, fingerprint=_fingerprint(from_ref=from_ref, to_ref=to_ref, blobs=blobs)):
        print(f"{HOOK_ID}: this exact change already passed the documentation audit; skipping.")
        return 0

    print(f"{HOOK_ID}: checking documentation for {len(files)} file(s) in {from_ref[:12]}..{to_ref[:12]}", flush=True)
    documentation_before = _snapshot_documentation()
    completed = run_claude(
        hook_id=HOOK_ID,
        prompt=build_prompt(from_ref=from_ref, to_ref=to_ref, files=files, diff_files=diff_files),
        agent=AGENT,
        allowed_tools=READ_ONLY_TOOLS + DOCUMENTATION_EDIT_RULES,
        disallowed_tools=BLOCKED_TOOLS,
    )
    if completed is None:
        return 0

    report = tagged_lines(output=completed.stdout, prefixes=REPORT_PREFIXES)
    if report:
        print("\n".join(report), flush=True)

    updated = _changed_documentation(documentation_before)
    edited = f" It edited {', '.join(updated)}; review those edits." if updated else ""
    verdict = parse_verdict(output=completed.stdout, prefix=VERDICT_PREFIX)
    if completed.returncode != 0 or verdict is None:
        print(completed.stderr.strip(), file=sys.stderr)
        print(f"{HOOK_ID}: Claude run failed or returned no verdict.{edited} {SKIP_HINT}", file=sys.stderr)
        return 1

    if verdict == "PASS":
        audited_blobs = blobs | blob_ids(paths=updated, to_ref=WORKING_TREE)
        record_pass(hook_id=HOOK_ID, fingerprint=_fingerprint(from_ref=from_ref, to_ref=to_ref, blobs=audited_blobs))
        if not updated:
            return 0
        paths = " ".join(updated)
        print(
            f"\n{HOOK_ID}: updated {', '.join(updated)} (not part of the pushed commits). Review with "
            f"`git diff -- {paths}`, then `git commit -m 'Update docs' -- {paths}` and push again; this audited "
            f"state is recorded, so the gate will skip that push. {SKIP_HINT}",
            file=sys.stderr,
        )
        return 1

    blocking = tagged_lines(output=completed.stdout, prefixes=(BLOCKING_PREFIX,))
    if not blocking:
        print(f"{HOOK_ID}: verdict BLOCK without findings; rerun the push.{edited} {SKIP_HINT}", file=sys.stderr)
        return 1

    print(f"\n{HOOK_ID}: blocked. Paste this into Claude Code, then push again:", flush=True)
    print(
        paste_block(build_fix_prompt(from_ref=from_ref, to_ref=to_ref, findings=blocking, updated=updated)),
        flush=True,
    )
    print(SKIP_HINT, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
