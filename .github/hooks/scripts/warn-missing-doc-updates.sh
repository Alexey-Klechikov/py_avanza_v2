#!/bin/sh

cat >/dev/null

status_output=$(git status --porcelain --untracked-files=all 2>/dev/null || true)

if [ -z "$status_output" ]; then
  printf '%s\n' '{"continue":true}'
  exit 0
fi

if printf '%s\n' "$status_output" | awk '
{
  path = substr($0, 4)
  if (index(path, " -> ") > 0) {
    split(path, parts, " -> ")
    path = parts[2]
  }
  if (path ~ /^src\// || path ~ /^\.github\// || path == "pyproject.toml" || path == "uv.lock" || path == ".python-version" || path == ".flake8" || path == ".pre-commit-config.yaml" || path == ".gitignore") {
    code_changed = 1
  }
  if (path == "AGENTS.md" || path == "README.md") {
    docs_changed = 1
  }
}
END {
  exit !(code_changed && !docs_changed)
}
'; then
  printf '%s\n' '{"continue":true,"systemMessage":"Code or automation files changed under src/, .github/, or repo runtime/config files, but neither AGENTS.md nor README.md changed. If this work revealed durable repo knowledge, update the relevant documentation before ending the task."}'
  exit 0
fi

printf '%s\n' '{"continue":true}'
