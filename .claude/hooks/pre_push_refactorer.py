#!/usr/bin/env python3

from __future__ import annotations

import sys

from claude_review import READ_ONLY_TOOLS, build_review_diff, run_claude, tagged_lines
from git_range import changed_files_in_range, resolve_review_range

HOOK_ID = "refactorer-review"
REVIEW_PREFIXES = ("src/", ".claude/hooks/")
REVIEW_SUFFIXES = (".py",)
FINDING_PREFIX = "FINDING:"
BLOCKED_TOOLS = ("Bash", "Edit", "Write", "NotebookEdit")

PROMPT_TEMPLATE = """\
ADVISORY REVIEW (git pre-push hook). Do not edit files and do not run validation or the documentation checker; \
shell and file-editing tools are disabled for this run. Only Read, Grep, and Glob are available.

Review the code being pushed in the range {from_ref}..{to_ref} against your complexity, nesting, dead-code, \
style, and security standards. The diff is below; read surrounding code in the working tree as needed. Only judge \
lines this range adds or changes; ignore pre-existing code.

Changed files in scope:
{files}

Diff of those files:
```diff
{diff}
```

Report only findings you would confidently change under your ground rules: a worse complexity class, nesting \
deeper than two levels that a guard clause or lookup would flatten, a forwarding-only helper, dead code proven by \
references, a repository style or layer rule violation, or a local security issue.

Reply with one line per finding, `{finding} file:line - category - problem - smallest fix`, and nothing else: no \
verdict, summary, praise, checks you ran, or notes on code that is fine. Reply with nothing when there are no \
findings.
"""


def select_review_files(paths: list[str]) -> list[str]:
    return sorted(path for path in paths if path.startswith(REVIEW_PREFIXES) and path.endswith(REVIEW_SUFFIXES))


def build_prompt(from_ref: str, to_ref: str, files: list[str]) -> str:
    return PROMPT_TEMPLATE.format(
        from_ref=from_ref,
        to_ref=to_ref,
        files="\n".join(f"- {path}" for path in files),
        diff=build_review_diff(from_ref=from_ref, to_ref=to_ref, files=files),
        finding=FINDING_PREFIX,
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
    files = select_review_files(changed_files_in_range(from_ref=from_ref, to_ref=to_ref))
    if not files:
        print(f"{HOOK_ID}: no Python source or hook code in this push; skipping.")
        return 0

    print(f"{HOOK_ID}: reviewing {len(files)} file(s) in {from_ref[:12]}..{to_ref[:12]}", flush=True)
    prompt = build_prompt(from_ref=from_ref, to_ref=to_ref, files=files)
    completed = run_claude(
        hook_id=HOOK_ID,
        prompt=prompt,
        agent="refactorer",
        allowed_tools=READ_ONLY_TOOLS,
        disallowed_tools=BLOCKED_TOOLS,
    )
    if completed is None:
        return 0
    if completed.returncode != 0:
        print(f"{HOOK_ID}: Claude run failed ({completed.stderr.strip()}); no review for this push.", file=sys.stderr)
        return 0

    findings = tagged_lines(output=completed.stdout, prefixes=(FINDING_PREFIX,))
    print("\n".join(findings) if findings else f"{HOOK_ID}: no findings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
