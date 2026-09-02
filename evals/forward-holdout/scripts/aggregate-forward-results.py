#!/usr/bin/env python3
"""Unblind implementation holdout scores and generate aggregates."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


TRACE_MARKER = "/refinetale/SKILL.md"


def wilson_interval(successes: int, total: int) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    z = 1.959963984540054
    rate = successes / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total))
        / denominator
    )
    return [round(center - margin, 4), round(center + margin, 4)]


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    row_one = a + b
    row_two = c + d
    column_one = a + c
    total = row_one + row_two

    def probability(value: int) -> float:
        return (
            math.comb(row_one, value)
            * math.comb(row_two, column_one - value)
            / math.comb(total, column_one)
        )

    observed = probability(a)
    lower = max(0, column_one - row_two)
    upper = min(row_one, column_one)
    return round(
        min(
            1.0,
            sum(
                probability(value)
                for value in range(lower, upper + 1)
                if probability(value) <= observed + 1e-12
            ),
        ),
        6,
    )


def expected_outcome(scores: list[int], critical: bool) -> str:
    if critical:
        return "critical_failure"
    total = sum(scores)
    if total >= 8 and min(scores) >= 1:
        return "pass"
    if total >= 6:
        return "borderline"
    return "fail"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True, type=Path)
    args = parser.parse_args()
    root = args.result_dir.resolve()
    overrides_path = root / "review" / "manual-overrides.json"
    overrides = (
        json.loads(overrides_path.read_text(encoding="utf-8"))
        if overrides_path.is_file()
        else {}
    )

    rows = []
    for review_dir in sorted((root / "review").glob("fixture-*")):
        fixture = review_dir.name[-2:]
        mapping = json.loads((review_dir / "mapping.json").read_text(encoding="utf-8"))
        scored = {
            candidate["id"]: candidate
            for candidate in json.loads(
                (review_dir / "scores.blind.judge-1.json").read_text(
                    encoding="utf-8"
                )
            )["candidates"]
        }
        for candidate, identity in mapping.items():
            score = dict(scored[candidate])
            override = overrides.get(review_dir.name, {}).get(candidate)
            adjustment_reason = ""
            if override:
                adjustment_reason = override["reason"]
                score.update(override["changes"])
            values = [score[f"S{index}"] for index in range(1, 6)]
            if score["total"] != sum(values):
                raise SystemExit(f"Invalid total: fixture {fixture} candidate {candidate}")
            expected = expected_outcome(values, score["critical_failure"])
            if score["outcome"] != expected:
                raise SystemExit(
                    f"Invalid outcome: fixture {fixture} candidate {candidate}: "
                    f"{score['outcome']} != {expected}"
                )
            mode = identity["mode"]
            run = identity["run"]
            raw_dir = root / "raw" / "behavior" / fixture / mode / f"run-{run}"
            events = (raw_dir / "events.jsonl").read_text(encoding="utf-8")
            verification = json.loads(
                (raw_dir / "verification.json").read_text(encoding="utf-8")
            )
            rows.append(
                {
                    "fixture": fixture,
                    "run": run,
                    "mode": mode,
                    "judge_candidate": candidate,
                    **score,
                    "verification_passed": verification["returncode"] == 0
                    and not verification["timed_out"],
                    "skill_trace": TRACE_MARKER in events,
                    "manual_adjustment": bool(override),
                    "adjustment_reason": adjustment_reason,
                }
            )

    rows.sort(key=lambda row: (row["fixture"], row["run"], row["mode"]))
    columns = [
        "fixture",
        "run",
        "mode",
        "judge_candidate",
        "S1",
        "S2",
        "S3",
        "S4",
        "S5",
        "total",
        "outcome",
        "critical_failure",
        "verification_passed",
        "skill_trace",
        "manual_adjustment",
        "adjustment_reason",
        "evidence",
    ]
    with (root / "scores.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    metrics = {}
    per_fixture_scores: dict[str, dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        per_fixture_scores[row["mode"]][row["fixture"]].append(row)

    for mode in ("baseline", "refinetale"):
        selected = [row for row in rows if row["mode"] == mode]
        metrics[mode] = {
            "runs": len(selected),
            "passed_runs": sum(row["outcome"] == "pass" for row in selected),
            "borderline_runs": sum(row["outcome"] == "borderline" for row in selected),
            "failed_runs": sum(row["outcome"] == "fail" for row in selected),
            "critical_failures": sum(row["critical_failure"] for row in selected),
            "verification_passed_runs": sum(
                row["verification_passed"] for row in selected
            ),
            "earned_points": sum(row["total"] for row in selected),
            "available_points": len(selected) * 10,
            "score_rate": round(
                sum(row["total"] for row in selected) / (len(selected) * 10), 4
            ),
            "pass_rate": round(
                sum(row["outcome"] == "pass" for row in selected) / len(selected), 4
            ),
            "verification_pass_rate": round(
                sum(row["verification_passed"] for row in selected) / len(selected), 4
            ),
            "skill_trace_runs": sum(row["skill_trace"] for row in selected),
            "criterion_points": {
                f"S{index}": sum(row[f"S{index}"] for row in selected)
                for index in range(1, 6)
            },
            "per_fixture": {
                fixture: {
                    "passed_runs": sum(row["outcome"] == "pass" for row in group),
                    "verification_passed_runs": sum(
                        row["verification_passed"] for row in group
                    ),
                    "points": sum(row["total"] for row in group),
                    "available_points": len(group) * 10,
                }
                for fixture, group in sorted(per_fixture_scores[mode].items())
            },
        }
    metrics["difference"] = {
        "pass_rate": round(
            metrics["refinetale"]["pass_rate"] - metrics["baseline"]["pass_rate"],
            4,
        ),
        "score_rate": round(
            metrics["refinetale"]["score_rate"] - metrics["baseline"]["score_rate"],
            4,
        ),
        "verification_pass_rate": round(
            metrics["refinetale"]["verification_pass_rate"]
            - metrics["baseline"]["verification_pass_rate"],
            4,
        ),
        "critical_failures": metrics["refinetale"]["critical_failures"]
        - metrics["baseline"]["critical_failures"],
    }
    baseline_passes = metrics["baseline"]["passed_runs"]
    treatment_passes = metrics["refinetale"]["passed_runs"]
    baseline_runs = metrics["baseline"]["runs"]
    treatment_runs = metrics["refinetale"]["runs"]
    baseline_verified = metrics["baseline"]["verification_passed_runs"]
    treatment_verified = metrics["refinetale"]["verification_passed_runs"]
    metrics["inference"] = {
        "baseline_pass_rate_wilson_95": wilson_interval(
            baseline_passes, baseline_runs
        ),
        "refinetale_pass_rate_wilson_95": wilson_interval(
            treatment_passes, treatment_runs
        ),
        "pass_rate_fisher_exact_two_sided_p": fisher_exact_two_sided(
            treatment_passes,
            treatment_runs - treatment_passes,
            baseline_passes,
            baseline_runs - baseline_passes,
        ),
        "baseline_verification_rate_wilson_95": wilson_interval(
            baseline_verified, baseline_runs
        ),
        "refinetale_verification_rate_wilson_95": wilson_interval(
            treatment_verified, treatment_runs
        ),
        "verification_rate_fisher_exact_two_sided_p": fisher_exact_two_sided(
            treatment_verified,
            treatment_runs - treatment_verified,
            baseline_verified,
            baseline_runs - baseline_verified,
        ),
    }
    (root / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
