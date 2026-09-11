#!/usr/bin/env python3

from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import check_documentation_alignment as checker


class DocumentationAlignmentTests(unittest.TestCase):
    def test_runtime_contract_covers_all_documented_owners(self) -> None:
        runtime_rule = next(rule for rule in checker.RULES if rule.name == "runtime-contract")

        self.assertEqual(
            set(runtime_rule.exact_paths),
            {
                "src/apis/avanza/client/client.py",
                "src/config/settings.py",
                "src/services/storage/operators.py",
                "src/services/ta/strategies/operators.py",
                "src/task_end_of_day.py",
                "src/task_end_of_week.py",
                "src/task_trade.py",
            },
        )

    def test_runtime_contract_requires_readme_and_agents(self) -> None:
        findings = checker.find_missing_documentation(
            {"src/config/settings.py"},
        )

        self.assertEqual(len(findings), 1)
        self.assertIn("Rule: runtime-contract", findings[0])
        self.assertIn("Required docs not changed: README.md, AGENTS.md", findings[0])

    def test_runtime_contract_accepts_both_documentation_updates(self) -> None:
        findings = checker.find_missing_documentation(
            {"src/services/ta/strategies/operators.py", "README.md", "AGENTS.md"},
        )

        self.assertEqual(findings, [])

    def test_deployment_contract_requires_readme_and_agents(self) -> None:
        findings = checker.find_missing_documentation(
            {".github/workflows/deploy.yaml"},
        )

        self.assertEqual(len(findings), 1)
        self.assertIn("Rule: deployment-contract", findings[0])
        self.assertIn("Required docs not changed: README.md, AGENTS.md", findings[0])

    def test_customization_policy_requires_agents_update(self) -> None:
        findings = checker.find_missing_documentation(
            {".github/instructions/pyavanza-testing.instructions.md"},
        )

        self.assertEqual(len(findings), 1)
        self.assertIn("Rule: customization-policy", findings[0])

    def test_customization_policy_covers_python_tooling(self) -> None:
        findings = checker.find_missing_documentation({"pyproject.toml"})

        self.assertEqual(len(findings), 1)
        self.assertIn("Rule: customization-policy", findings[0])

    def test_generated_artifacts_do_not_require_documentation(self) -> None:
        self.assertEqual(
            checker.find_missing_documentation(
                {"src/config/OMX_trade_strategies_dev_8.json", "src/data/OMX_2m.pickle", "src/logs/task.log"},
            ),
            [],
        )

    def test_unrelated_change_requires_no_documentation(self) -> None:
        self.assertEqual(
            checker.find_missing_documentation({"src/services/ta/indicators/momentum.py"}),
            [],
        )

    @patch("check_documentation_alignment._run_git_command")
    def test_worktree_mode_includes_tracked_and_untracked_files(self, run_git_command) -> None:
        run_git_command.side_effect = [
            ["src/config/settings.py"],
            [".github/instructions/new-rule.instructions.md"],
        ]

        changed_files = checker.collect_changed_files(staged=False)

        self.assertEqual(
            changed_files,
            {"src/config/settings.py", ".github/instructions/new-rule.instructions.md"},
        )
        self.assertEqual(run_git_command.call_count, 2)

    @patch("check_documentation_alignment._run_git_command")
    def test_staged_mode_uses_only_index_changes(self, run_git_command) -> None:
        run_git_command.return_value = [".github/hooks/update-documentation.json"]

        changed_files = checker.collect_changed_files(staged=True)

        self.assertEqual(changed_files, {".github/hooks/update-documentation.json"})
        run_git_command.assert_called_once_with(
            ["diff", "--cached", "--name-only", "--diff-filter=ACMR", "--"],
        )

    def test_failure_response_requires_documentation_skill(self) -> None:
        response = checker.build_failure_response(["Rule: agent-policy"], staged=True)

        self.assertFalse(response["continue"])
        self.assertIn("/documentation-skill", response["systemMessage"])
        self.assertIn("Before concluding, load and execute", response["systemMessage"])
        self.assertIn("cannot execute skills directly", response["systemMessage"])
        self.assertIn("staged change set", response["systemMessage"])

    @patch("check_documentation_alignment.collect_changed_files")
    def test_main_returns_hook_payload_for_missing_documentation(self, collect_changed_files) -> None:
        collect_changed_files.return_value = {"src/task_trade.py"}
        original_argv = sys.argv
        original_stdin = sys.stdin
        sys.argv = ["check_documentation_alignment.py"]
        sys.stdin = io.StringIO("{}")
        stdout = io.StringIO()
        try:
            with redirect_stdout(stdout):
                exit_code = checker.main()
        finally:
            sys.argv = original_argv
            sys.stdin = original_stdin

        response = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertFalse(response["continue"])
        self.assertIn("runtime-contract", response["systemMessage"])


if __name__ == "__main__":
    unittest.main()
