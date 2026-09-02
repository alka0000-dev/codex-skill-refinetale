#!/usr/bin/env python3
"""Create deterministic, condition-blinded review packets for RefineTale evals."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


EVAL_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = EVAL_ROOT / "fixtures"

RUBRIC = """\
## Scoring rules

Score each item as `1` (satisfied), `0` (not satisfied), or `-1` (not applicable).

- G1 Contract fidelity: preserves requested external contracts, inputs, outputs, errors, and events.
- G2 Change contract: clearly handles what changes, what must not change, and allowed variation.
- G3 Canonical ownership: keeps one source of truth for the same state or decision.
- G4 Variation isolation: isolates only real differences and does not duplicate common processing.
- G5 No speculative implementation: adds no unrequested future extension, fallback, flag, or abstraction.
- G6 Safety preservation: does not weaken authorization, validation, audit, or failure behavior.
- G7 Verification and stop: identifies necessary verification and stops when no change is needed.

Use only evidence present in the candidate's final answer. Do not reward a promise to finish later.
The workspace intentionally lacked source files and was read-only. Do not fail a candidate merely
for reporting that limitation if it still provides the requested concrete solution and verification
plan. Missing implementation guidance or missing required test coverage can still fail the relevant
criterion. `overall_pass` requires every applicable G score and the fixture-specific conditions to
equal 1. G1 is always critical; G6 is critical when applicable.
"""

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
                    "G1": {"type": "integer", "enum": [-1, 0, 1]},
                    "G2": {"type": "integer", "enum": [-1, 0, 1]},
                    "G3": {"type": "integer", "enum": [-1, 0, 1]},
                    "G4": {"type": "integer", "enum": [-1, 0, 1]},
                    "G5": {"type": "integer", "enum": [-1, 0, 1]},
                    "G6": {"type": "integer", "enum": [-1, 0, 1]},
                    "G7": {"type": "integer", "enum": [-1, 0, 1]},
                    "fixture_specific": {"type": "integer", "enum": [0, 1]},
                    "overall_pass": {"type": "boolean"},
                    "critical_failure": {"type": "boolean"},
                    "evidence": {"type": "string"},
                },
                "required": [
                    "id",
                    "G1",
                    "G2",
                    "G3",
                    "G4",
                    "G5",
                    "G6",
                    "G7",
                    "fixture_specific",
                    "overall_pass",
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_ROOT)
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
        candidate_sections = []
        for label, (mode, run, content) in zip("ABCDEF", candidates, strict=True):
            mapping[label] = {"mode": mode, "run": run}
            candidate_sections.append(f"## Candidate {label}\n\n{content.strip()}")

        fixture_text = next(fixture_root.glob(f"{fixture_id}-*.md")).read_text(
            encoding="utf-8"
        )
        packet = (
            "You are grading six anonymized answers to one coding-skill evaluation. "
            "Apply the rubric strictly and return only the requested structured result. "
            "Do not guess which condition produced an answer.\n\n"
            + fixture_text
            + "\n\n"
            + RUBRIC
            + "\n\n"
            + "\n\n".join(candidate_sections)
            + "\n"
        )

        fixture_review = review_root / f"fixture-{fixture_id}"
        fixture_review.mkdir(parents=True, exist_ok=True)
        (fixture_review / "prompt.md").write_text(packet, encoding="utf-8")
        (fixture_review / "mapping.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
