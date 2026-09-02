#!/usr/bin/env python3
"""Validate forward holdout structure and initial repository behavior."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


FORWARD_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-dir", type=Path, default=FORWARD_ROOT / "fixtures")
    parser.add_argument("--expected-count", type=int, default=8)
    args = parser.parse_args()

    fixtures = sorted(args.fixture_dir.resolve().glob("[0-9][0-9]-*"))
    if len(fixtures) != args.expected_count:
        raise SystemExit(
            f"Expected {args.expected_count} fixtures, found {len(fixtures)}"
        )

    failures = []
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    for fixture in fixtures:
        workspace = fixture / "workspace"
        verify_path = fixture / "verify.json"
        if not verify_path.is_file():
            verify_path = workspace / "verify.json"
        required = [fixture / "prompt.md", fixture / "rubric.md", verify_path]
        if not workspace.is_dir() or not all(path.is_file() for path in required):
            failures.append(f"{fixture.name}: missing required artifact")
            continue

        config = json.loads(verify_path.read_text(encoding="utf-8"))
        command = config.get("command")
        timeout = config.get("timeout_seconds", 60)
        if not isinstance(command, list) or not command or not all(
            isinstance(item, str) and item and not item.startswith("/") for item in command
        ):
            failures.append(f"{fixture.name}: invalid relative verification command")
            continue
        if not isinstance(timeout, int) or not 1 <= timeout <= 120:
            failures.append(f"{fixture.name}: invalid timeout")
            continue

        rubric = (fixture / "rubric.md").read_text(encoding="utf-8")
        if not all(f"S{index}" in rubric for index in range(1, 6)):
            failures.append(f"{fixture.name}: incomplete S1-S5 rubric")

        existing = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_existing.py",
            ],
            cwd=workspace,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        if existing.returncode != 0:
            failures.append(f"{fixture.name}: existing tests fail initially")

        full = subprocess.run(
            command,
            cwd=workspace,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        if full.returncode == 0:
            failures.append(f"{fixture.name}: new requirements already pass initially")

        print(
            f"{fixture.name}: existing={existing.returncode} requirements={full.returncode}"
        )

    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Validated {len(fixtures)} forward fixtures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
