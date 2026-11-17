"""Layering contract for src/:

- apis/<name>: isolated adapters for one external API. They import only themselves, config and utils.
- services/<name>: isolated domain services. They import only themselves, config and utils.
- config, utils: foundations every layer may use; they import no layer above them.
- tasks/, task_*.py, development.py: the top layer, free to compose anything.
"""

import ast
from pathlib import Path
from unittest import TestCase

SRC = Path(__file__).resolve().parents[1] / "src"
LAYERS = ("apis", "services", "tasks")
FOUNDATIONS = ("config", "utils")


def _branch(module: str) -> str | None:
    """`apis.avanza.client.client` -> `apis.avanza`; `config.settings` -> `config`; third-party -> None."""
    parts = module.split(".")
    if parts[0] in ("apis", "services"):
        return ".".join(parts[:2])
    if parts[0] in ("tasks", *FOUNDATIONS):
        return parts[0]
    return None


def _imported_modules(path: Path) -> list[str]:
    modules = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.append(node.module)
        elif isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
    return modules


def _violations() -> list[str]:
    violations = []
    for path in sorted(SRC.rglob("*.py")):
        relative = path.relative_to(SRC).with_suffix("")
        own_branch = _branch(".".join(relative.parts))
        if own_branch is None or own_branch == "tasks":
            continue  # entry scripts and tasks sit on top

        for module in _imported_modules(path):
            imported_branch = _branch(module)
            if imported_branch is None or imported_branch == own_branch:
                continue
            if imported_branch in FOUNDATIONS and own_branch not in FOUNDATIONS:
                continue
            violations.append(f"{path.relative_to(SRC)} ({own_branch}) imports {module} ({imported_branch})")
    return violations


class Test_Architecture(TestCase):
    def test_branches_do_not_import_each_other(self):
        violations = _violations()

        assert not violations, "Cross-branch imports:\n" + "\n".join(violations)
