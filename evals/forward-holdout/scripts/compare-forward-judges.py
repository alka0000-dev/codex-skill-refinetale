#!/usr/bin/env python3
"""Measure blind-judge agreement and list score disagreements."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_scores(path: Path) -> dict[str, dict]:
    scores = {
        candidate["id"]: candidate
        for candidate in json.loads(path.read_text(encoding="utf-8"))["candidates"]
    }
    for candidate in scores.values():
        values = [candidate[f"S{index}"] for index in range(1, 6)]
        if candidate["total"] != sum(values):
            raise SystemExit(f"Invalid total in {path}: {candidate['id']}")
        if candidate["critical_failure"]:
            expected = "critical_failure"
        elif candidate["total"] >= 8 and min(values) >= 1:
            expected = "pass"
        elif candidate["total"] >= 6:
            expected = "borderline"
        else:
            expected = "fail"
        if candidate["outcome"] != expected:
            raise SystemExit(f"Invalid outcome in {path}: {candidate['id']}")
    return scores


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True, type=Path)
    args = parser.parse_args()
    root = args.result_dir.resolve()

    criterion_agreements = {f"S{index}": 0 for index in range(1, 6)}
    comparisons_per_criterion = 0
    exact_candidate_agreements = 0
    critical_agreements = 0
    candidates = []

    for review_dir in sorted((root / "review").glob("fixture-*")):
        primary = load_scores(review_dir / "scores.blind.judge-1.json")
        secondary = load_scores(review_dir / "scores.blind.judge-2.json")
        if primary.keys() != secondary.keys():
            raise SystemExit(f"Candidate mismatch: {review_dir}")
        for candidate_id in sorted(primary):
            first = primary[candidate_id]
            second = secondary[candidate_id]
            differences = {}
            for key in [f"S{index}" for index in range(1, 6)]:
                if first[key] == second[key]:
                    criterion_agreements[key] += 1
                else:
                    differences[key] = [first[key], second[key]]
            if first["critical_failure"] == second["critical_failure"]:
                critical_agreements += 1
            else:
                differences["critical_failure"] = [
                    first["critical_failure"],
                    second["critical_failure"],
                ]
            if first["outcome"] != second["outcome"]:
                differences["outcome"] = [first["outcome"], second["outcome"]]
            if first["total"] != second["total"]:
                differences["total"] = [first["total"], second["total"]]
            if not differences:
                exact_candidate_agreements += 1
            candidates.append(
                {
                    "fixture": review_dir.name[-2:],
                    "candidate": candidate_id,
                    "differences": differences,
                    "judge_1_evidence": first["evidence"],
                    "judge_2_evidence": second["evidence"],
                }
            )
            comparisons_per_criterion += 1

    result = {
        "summary": {
            "candidates": comparisons_per_criterion,
            "exact_candidate_agreements": exact_candidate_agreements,
            "exact_candidate_agreement_rate": round(
                exact_candidate_agreements / comparisons_per_criterion, 4
            ),
            "critical_agreements": critical_agreements,
            "critical_agreement_rate": round(
                critical_agreements / comparisons_per_criterion, 4
            ),
            "criterion_agreements": criterion_agreements,
            "criterion_agreement_rates": {
                key: round(value / comparisons_per_criterion, 4)
                for key, value in criterion_agreements.items()
            },
        },
        "disagreements": [
            candidate for candidate in candidates if candidate["differences"]
        ],
    }
    (root / "review" / "judge-agreement.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
