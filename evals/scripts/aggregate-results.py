#!/usr/bin/env python3
"""Unblind scored RefineTale evals and generate machine-readable aggregates."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


TRACE_MARKER = "/refinetale/SKILL.md"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True, type=Path)
    args = parser.parse_args()
    root = args.result_dir.resolve()

    rows = []
    for review_dir in sorted((root / "review").glob("fixture-*")):
        fixture = review_dir.name[-2:]
        mapping = json.loads((review_dir / "mapping.json").read_text(encoding="utf-8"))
        scored = {
            candidate["id"]: candidate
            for candidate in json.loads(
                (review_dir / "scores.blind.json").read_text(encoding="utf-8")
            )["candidates"]
        }
        for candidate, identity in mapping.items():
            mode = identity["mode"]
            run = identity["run"]
            events_path = (
                root
                / "raw"
                / "behavior"
                / fixture
                / mode
                / f"run-{run}"
                / "events.jsonl"
            )
            rows.append(
                {
                    "fixture": fixture,
                    "run": run,
                    "mode": mode,
                    "judge_candidate": candidate,
                    **scored[candidate],
                    "skill_trace": TRACE_MARKER
                    in events_path.read_text(encoding="utf-8"),
                }
            )

    rows.sort(key=lambda row: (row["fixture"], row["run"], row["mode"]))
    columns = [
        "fixture",
        "run",
        "mode",
        "judge_candidate",
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
        "skill_trace",
        "evidence",
    ]
    with (root / "scores.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    metrics = {}
    for mode in ("baseline", "refinetale"):
        selected = [row for row in rows if row["mode"] == mode]
        applicable = sum(
            row[f"G{index}"] != -1 for row in selected for index in range(1, 8)
        )
        earned = sum(
            row[f"G{index}"] == 1 for row in selected for index in range(1, 8)
        )
        per_fixture = defaultdict(int)
        for row in selected:
            per_fixture[row["fixture"]] += int(row["overall_pass"])
        metrics[mode] = {
            "runs": len(selected),
            "passed_runs": sum(row["overall_pass"] for row in selected),
            "pass_rate": round(
                sum(row["overall_pass"] for row in selected) / len(selected), 4
            ),
            "critical_failures": sum(row["critical_failure"] for row in selected),
            "earned_rubric_points": earned,
            "applicable_rubric_points": applicable,
            "rubric_rate": round(earned / applicable, 4),
            "per_fixture_passed_runs": dict(sorted(per_fixture.items())),
            "skill_trace_runs": sum(row["skill_trace"] for row in selected),
        }
    metrics["difference"] = {
        "pass_rate": round(
            metrics["refinetale"]["pass_rate"] - metrics["baseline"]["pass_rate"],
            4,
        ),
        "rubric_rate": round(
            metrics["refinetale"]["rubric_rate"]
            - metrics["baseline"]["rubric_rate"],
            4,
        ),
        "critical_failures": metrics["refinetale"]["critical_failures"]
        - metrics["baseline"]["critical_failures"],
    }
    (root / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    routing = {}
    if (root / "raw" / "routing").is_dir():
        for label, mode, expected in (
            ("A", "invoke", True),
            ("B", "do-not-invoke", False),
        ):
            event_paths = sorted(
                (root / "raw" / "routing" / label / mode).glob("run-*/events.jsonl")
            )
            observations = [
                TRACE_MARKER in path.read_text(encoding="utf-8")
                for path in event_paths
            ]
            routing[label] = {
                "expected_skill_trace": expected,
                "observed": observations,
                "passed": sum(observed == expected for observed in observations),
                "runs": len(observations),
            }
    (root / "routing.json").write_text(
        json.dumps(routing, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
