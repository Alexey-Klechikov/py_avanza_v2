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
from git_range import changed_files_in_range, resolve_review_range

HOOK_ID = "code-review"
AGENT = "code-reviewer"
VERDICT_PREFIX = "CODE_REVIEW_VERDICT:"
BLOCKING_PREFIX = "BLOCKING:"
REPORT_PREFIXES = (BLOCKING_PREFIX, "ADVISORY:")
SKIP_HINT = f"Bypass once with `SKIP={HOOK_ID} git push`."
EXCLUDED_PATTERNS = ("*.md", "uv.lock", "src/config/*_weighted_model.json")
BLOCKED_TOOLS = ("Bash", "Edit", "Write", "NotebookEdit")

PROMPT_TEMPLATE = """\
PRE-PUSH CODE REVIEW. Shell and file-editing tools are disabled; only Read, Grep, and Glob are available, so do not \
run validation. Review the code being pushed in the range {from_ref}..{to_ref}. The diff is below; read surrounding \
code in the working tree as needed. Only judge lines this range adds or changes; ignore pre-existing code.

This is the only review before the author fixes and pushes again: report every blocking finding now, each with a fix \
concrete enough to apply without further investigation.

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

FIX_PROMPT_TEMPLATE = """\
Fix these blocking pre-push code-review findings for {from_ref}..{to_ref} in one pass:
{findings}

For each finding: confirm it against the code, then apply the smallest fix that follows CLAUDE.md and the matching \
.claude/rules. Do not refactor beyond the findings or act on advisory findings. If a fix changes documented behavior, \
update README.md or CLAUDE.md too.
{self_check}
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


def build_fix_prompt(from_ref: str, to_ref: str, findings: list[str]) -> str:
    return FIX_PROMPT_TEMPLATE.format(
        from_ref=from_ref[:12],
        to_ref=to_ref[:12],
        findings="\n".join(f"- {finding.removeprefix(BLOCKING_PREFIX).strip()}" for finding in findings),
        self_check=SELF_CHECK_INSTRUCTIONS,
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

    fingerprint = review_fingerprint(
        hook_id=HOOK_ID,
        prompt_template=PROMPT_TEMPLATE,
        agent=AGENT,
        from_ref=from_ref,
        to_ref=to_ref,
        blobs=blob_ids(paths=files, to_ref=to_ref),
    )
    if already_passed(hook_id=HOOK_ID, fingerprint=fingerprint):
        print(f"{HOOK_ID}: this exact change already passed review; skipping.")
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

    if verdict == "PASS":
        record_pass(hook_id=HOOK_ID, fingerprint=fingerprint)
        return 0

    blocking = tagged_lines(output=completed.stdout, prefixes=(BLOCKING_PREFIX,))
    if not blocking:
        print(f"{HOOK_ID}: verdict BLOCK without findings; rerun the push. {SKIP_HINT}", file=sys.stderr)
        return 1

    print(f"\n{HOOK_ID}: blocked. Paste this into Claude Code, then push again:", flush=True)
    print(paste_block(build_fix_prompt(from_ref=from_ref, to_ref=to_ref, findings=blocking)), flush=True)
    print(SKIP_HINT, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
