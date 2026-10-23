#!/usr/bin/env python3

from __future__ import annotations

import sys

from claude_review import READ_ONLY_TOOLS, build_review_diff, parse_verdict, run_claude, tagged_lines
from git_range import REPOSITORY_ROOT, changed_files_in_range, git_lines, resolve_review_range

HOOK_ID = "documentation-alignment"
AGENT = "documenter"
VERDICT_PREFIX = "DOCUMENTATION_VERDICT:"
REPORT_PREFIXES = ("UPDATED:", "BLOCKING:", "ADVISORY:")
SKIP_HINT = f"Bypass once with `SKIP={HOOK_ID} git push`."
DOCUMENTATION_EDIT_RULES = (
    "Edit(./README.md)",
    "Edit(./**/CLAUDE.md)",
)
BLOCKED_TOOLS = ("Bash", "NotebookEdit")

PROMPT_TEMPLATE = """\
PRE-PUSH AUTOFIX MODE. Audit the documentation against the commits being pushed in the range \
{from_ref}..{to_ref}. Use the diff below and the files in the working tree; the working tree may contain \
uncommitted changes, so judge the diff. Verify that every surface in your routing is still accurate after this push \
and covers the durable facts it introduces, and fix every blocking finding in place.

Changed files in the push:
{files}

Diff:
```diff
{diff}
```

Reply with only these lines and no other text:
- `UPDATED: file - what changed - evidence` for each fix you made
- `BLOCKING: file - problem - evidence` for each blocking finding you could not fix
- `ADVISORY: file - problem - smallest fix` for each advisory finding
- a final line, `{verdict} PASS` when no blocking finding remains unfixed, otherwise `{verdict} BLOCK`
"""


def _snapshot_documentation() -> dict[str, bytes]:
    paths = git_lines(["ls-files", "--cached", "--others", "--exclude-standard", "--", "*.md"])
    file_paths = {path: REPOSITORY_ROOT / path for path in paths}
    return {path: file_path.read_bytes() for path, file_path in file_paths.items() if file_path.is_file()}


def _changed_documentation(before: dict[str, bytes]) -> list[str]:
    after = _snapshot_documentation()
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


def build_prompt(from_ref: str, to_ref: str, files: list[str]) -> str:
    return PROMPT_TEMPLATE.format(
        from_ref=from_ref,
        to_ref=to_ref,
        files="\n".join(f"- {path}" for path in files),
        diff=build_review_diff(from_ref=from_ref, to_ref=to_ref, files=files),
        verdict=VERDICT_PREFIX,
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
    if not files:
        print(f"{HOOK_ID}: no changed files in this push; skipping.")
        return 0

    print(f"{HOOK_ID}: checking documentation for {len(files)} file(s) in {from_ref[:12]}..{to_ref[:12]}", flush=True)
    documentation_before = _snapshot_documentation()
    completed = run_claude(
        hook_id=HOOK_ID,
        prompt=build_prompt(from_ref=from_ref, to_ref=to_ref, files=files),
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
    if updated:
        print(
            f"{HOOK_ID}: updated {', '.join(updated)}. Review the edits, commit them, and push again. {SKIP_HINT}",
            file=sys.stderr,
        )
        return 1

    verdict = parse_verdict(output=completed.stdout, prefix=VERDICT_PREFIX)
    if completed.returncode != 0 or verdict is None:
        print(completed.stderr.strip(), file=sys.stderr)
        print(f"{HOOK_ID}: Claude run failed or returned no verdict. {SKIP_HINT}", file=sys.stderr)
        return 1

    if verdict != "PASS":
        print(f"{HOOK_ID}: blocking findings remain; fix them, commit, and push again. {SKIP_HINT}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
