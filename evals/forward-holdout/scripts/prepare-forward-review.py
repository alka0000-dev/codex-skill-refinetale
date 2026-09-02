#!/usr/bin/env python3
"""Create condition-blinded review packets for implementation holdouts."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


FORWARD_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = FORWARD_ROOT / "fixtures"

SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "minItems": 6,
            "maxItems": 6,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "enum": list("ABCDEF")},
                    "S1": {"type": "integer", "minimum": 0, "maximum": 2},
                    "S2": {"type": "integer", "minimum": 0, "maximum": 2},
                    "S3": {"type": "integer", "minimum": 0, "maximum": 2},
                    "S4": {"type": "integer", "minimum": 0, "maximum": 2},
                    "S5": {"type": "integer", "minimum": 0, "maximum": 2},
                    "total": {"type": "integer", "minimum": 0, "maximum": 10},
                    "outcome": {
                        "type": "string",
                        "enum": ["pass", "borderline", "fail", "critical_failure"],
                    },
                    "critical_failure": {"type": "boolean"},
                    "evidence": {"type": "string"},
                },
                "required": [
                    "id",
                    "S1",
                    "S2",
                    "S3",
                    "S4",
                    "S5",
                    "total",
                    "outcome",
                    "critical_failure",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["candidates"],
    "additionalProperties": False,
}

JUDGE_RULES = """\
## Judge instructions

Score each candidate independently using the initial repository, final diff, verification output,
final answer, and fixture rubric. Do not guess its generation condition. Repository behavior and
the actual diff take precedence over claims in the final answer. A nonzero verification result is
evidence of an incomplete result, but apply the fixture's S1-S5 and critical conditions rather than
inventing new requirements.

Score S1 through S5 from 0 to 2 exactly as defined by the fixture. `total` must equal their sum.
If any critical failure condition is met, set `critical_failure` to true and `outcome` to
`critical_failure`. Otherwise use: pass = total 8-10 with every S at least 1; borderline = total
6-7, or total 8-10 with any S equal to 0; fail = total 0-5. Evidence must name concrete satisfied
and missing behavior from the diff or verification. Do not reward headings, verbosity, identifier
spelling, or terminology by itself.
"""


def render_workspace(root: Path) -> str:
    sections = []
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = path.relative_to(root).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            sections.append(f"### {relative}\n\n`<binary file>`")
            continue
        sections.append(f"### {relative}\n\n````text\n{content.rstrip()}\n````")
    return "\n\n".join(sections)


def candidate_section(label: str, raw_dir: Path) -> str:
    verification = json.loads((raw_dir / "verification.json").read_text(encoding="utf-8"))
    command = " ".join(verification["command"])
    return (
        f"## Candidate {label}\n\n"
        f"### Final answer\n\n{(raw_dir / 'final.md').read_text(encoding='utf-8').strip()}\n\n"
        f"### Final diff\n\n````diff\n{(raw_dir / 'diff.patch').read_text(encoding='utf-8').rstrip()}\n````\n\n"
        f"### Verification\n\n"
        f"- Command: `{command}`\n"
        f"- Exit: `{verification['returncode']}`\n"
        f"- Timed out: `{verification['timed_out']}`\n\n"
        f"````text\n{verification['stdout'].rstrip()}\n{verification['stderr'].rstrip()}\n````"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--seed", type=int, default=20260902)
    args = parser.parse_args()

    result_root = args.result_dir.resolve()
    fixture_root = args.fixture_dir.resolve()
    review_root = result_root / "review"
    review_root.mkdir(parents=True, exist_ok=True)
    (review_root / "score-schema.json").write_text(
        json.dumps(SCHEMA, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    fixture_ids = sorted(
        path.name
        for path in (result_root / "raw" / "behavior").iterdir()
        if path.is_dir()
    )
    for fixture_id in fixture_ids:
        fixture_dir = next(fixture_root.glob(f"{fixture_id}-*"))
        candidates = []
        for path in sorted(
            (result_root / "raw" / "behavior" / fixture_id).glob("*/run-*")
        ):
            if not path.is_dir():
                continue
            mode = path.parts[-2]
            run = int(path.name.split("-")[1])
            candidates.append((mode, run, path))
        if len(candidates) != 6:
            raise SystemExit(f"Expected 6 candidates for fixture {fixture_id}")

        random.Random(args.seed + int(fixture_id)).shuffle(candidates)
        mapping = {}
        sections = []
        for label, (mode, run, raw_dir) in zip("ABCDEF", candidates, strict=True):
            mapping[label] = {"mode": mode, "run": run}
            sections.append(candidate_section(label, raw_dir))

        packet = (
            "You are grading six anonymized implementations from an independent forward holdout. "
            "Return only the requested structured result.\n\n"
            "# User request\n\n"
            + (fixture_dir / "prompt.md").read_text(encoding="utf-8").strip()
            + "\n\n# Fixture rubric\n\n"
            + (fixture_dir / "rubric.md").read_text(encoding="utf-8").strip()
            + "\n\n# Initial repository\n\n"
            + render_workspace(fixture_dir / "workspace")
            + "\n\n"
            + JUDGE_RULES
            + "\n\n"
            + "\n\n".join(sections)
            + "\n"
        )

        target = review_root / f"fixture-{fixture_id}"
        target.mkdir(parents=True, exist_ok=True)
        (target / "prompt.md").write_text(packet, encoding="utf-8")
        (target / "mapping.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
