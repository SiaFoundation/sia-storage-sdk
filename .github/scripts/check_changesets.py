#!/usr/bin/env python3
"""Validate the change files Knope consumes, without third-party dependencies."""
from pathlib import Path
import sys


def validate(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ["must start with ---"]
    end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    if end is None:
        return ["missing closing ---"]
    # Knope parses colon-separated keys, not YAML: quoted keys are not default.
    if len(lines[1:end]) != 1:
        return ["must contain exactly one default: patch|minor|major entry"]
    key, separator, bump = lines[1].partition(":")
    problems = []
    if not separator or key.strip() != "default":
        problems.append("the package key must be default (unquoted)")
    if bump.strip() not in {"patch", "minor", "major"}:
        problems.append("the bump must be patch, minor, or major")
    if not "\n".join(lines[end + 1:]).strip():
        problems.append("missing change description")
    return problems


def main() -> int:
    failed = False
    files = sorted(Path(".changeset").glob("*.md"))
    for path in files:
        for problem in validate(path.read_text()):
            print(f"{path}: {problem}", file=sys.stderr)
            failed = True
    if not failed:
        print(f"{len(files)} valid changeset(s)")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
