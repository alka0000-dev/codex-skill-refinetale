#!/usr/bin/env python3
"""Create deterministic, condition-blinded holdout review packets."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


HOLDOUT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = HOLDOUT_ROOT / "fixtures"

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

Score each candidate independently using only its final answer and this fixture.
Do not guess its generation condition. The workspace intentionally contained no source files and
was read-only, so judge the proposed data flow, types, boundaries, failure behavior, and observable
test plan. Do not fail a candidate merely because it could not edit or execute code.

Score S1 through S5 from 0 to 2 exactly as defined by the fixture. `total` must equal their sum.
If any critical failure condition is met, set `critical_failure` to true and `outcome` to
`critical_failure`. Otherwise use: pass = total 8-10 with every S at least 1; borderline = total
6-7, or total 8-10 with any S equal to 0; fail = total 0-5. Evidence must name concrete satisfied
and missing behavior. Do not reward headings, verbosity, or terminology by itself.
"""


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
        json.dumps(SCHEMA, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    fixture_ids = sorted(
        path.name
        for path in (result_root / "raw" / "behavior").iterdir()
        if path.is_dir()
    )
    for fixture_id in fixture_ids:
        candidates = []
        for path in sorted(
            (result_root / "raw" / "behavior" / fixture_id).glob("*/run-*/final.md")
        ):
            mode = path.parts[-3]
            run = int(path.parts[-2].split("-")[1])
            candidates.append((mode, run, path.read_text(encoding="utf-8")))
        if len(candidates) != 6:
            raise SystemExit(f"Expected 6 candidates for fixture {fixture_id}")

        random.Random(args.seed + int(fixture_id)).shuffle(candidates)
        mapping = {}
        sections = []
        for label, (mode, run, content) in zip("ABCDEF", candidates, strict=True):
            mapping[label] = {"mode": mode, "run": run}
            sections.append(f"## Candidate {label}\n\n{content.strip()}")

        fixture_text = next(fixture_root.glob(f"{fixture_id}-*.md")).read_text(
            encoding="utf-8"
        )
        packet = (
            "You are grading six anonymized answers to an independent holdout evaluation. "
            "Return only the requested structured result.\n\n"
            + fixture_text
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
            json.dumps(mapping, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
