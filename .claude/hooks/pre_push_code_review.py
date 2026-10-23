#!/usr/bin/env python3

from __future__ import annotations

import fnmatch
import sys

from claude_review import READ_ONLY_TOOLS, build_review_diff, parse_verdict, run_claude, tagged_lines
from git_range import changed_files_in_range, resolve_review_range

HOOK_ID = "code-review"
AGENT = "code-reviewer"
VERDICT_PREFIX = "CODE_REVIEW_VERDICT:"
REPORT_PREFIXES = ("BLOCKING:", "ADVISORY:")
SKIP_HINT = f"Bypass once with `SKIP={HOOK_ID} git push`."
EXCLUDED_PATTERNS = ("*.md", "uv.lock", "src/config/OMX_trade_strategies*.json")
BLOCKED_TOOLS = ("Bash", "Edit", "Write", "NotebookEdit")

PROMPT_TEMPLATE = """\
PRE-PUSH CODE REVIEW. Shell and file-editing tools are disabled; only Read, Grep, and Glob are available, so do not \
run validation. Review the code being pushed in the range {from_ref}..{to_ref}. The diff is below; read surrounding \
code in the working tree as needed. Only judge lines this range adds or changes; ignore pre-existing code.

Changed files in scope:
{files}

Diff of those files:
```diff
{diff}
```

Reply with only these lines and no other text:
- `BLOCKING: file:line - category - problem - smallest fix` for each blocking finding
- `ADVISORY: file:line - category - problem - smallest fix` for each advisory finding
- a final line, `{verdict} PASS` when there is no blocking finding, otherwise `{verdict} BLOCK`
"""


def select_review_files(paths: list[str]) -> list[str]:
    return sorted(path for path in paths if not any(fnmatch.fnmatch(path, glob) for glob in EXCLUDED_PATTERNS))


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
    files = select_review_files(changed_files_in_range(from_ref=from_ref, to_ref=to_ref))
    if not files:
        print(f"{HOOK_ID}: no reviewable code in this push; skipping.")
        return 0

    print(f"{HOOK_ID}: reviewing {len(files)} file(s) in {from_ref[:12]}..{to_ref[:12]}", flush=True)
    completed = run_claude(
        hook_id=HOOK_ID,
        prompt=build_prompt(from_ref=from_ref, to_ref=to_ref, files=files),
        agent=AGENT,
        allowed_tools=READ_ONLY_TOOLS,
        disallowed_tools=BLOCKED_TOOLS,
    )
    if completed is None:
        return 0

    report = tagged_lines(output=completed.stdout, prefixes=REPORT_PREFIXES)
    print("\n".join(report) if report else f"{HOOK_ID}: no findings.", flush=True)

    verdict = parse_verdict(output=completed.stdout, prefix=VERDICT_PREFIX)
    if completed.returncode != 0 or verdict is None:
        print(completed.stderr.strip(), file=sys.stderr)
        print(f"{HOOK_ID}: Claude run failed or returned no verdict. {SKIP_HINT}", file=sys.stderr)
        return 1

    if verdict != "PASS":
        print(f"{HOOK_ID}: blocking findings; fix them, commit, and push again. {SKIP_HINT}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
