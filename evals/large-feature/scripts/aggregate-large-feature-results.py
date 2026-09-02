#!/usr/bin/env python3
"""Unblind and aggregate large-feature benchmark results."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


SCORE_FIELDS = ("completeness", "coherence", "scope_discipline", "single_path")


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


def rounded_mean(values: list[float | int]) -> float | None:
    return round(statistics.mean(values), 3) if values else None


def rounded_median(values: list[float | int]) -> float | None:
    return round(statistics.median(values), 3) if values else None


def parse_duration_seconds(started_at: str, finished_at: str) -> float:
    started = dt.datetime.fromisoformat(started_at)
    finished = dt.datetime.fromisoformat(finished_at)
    return round((finished - started).total_seconds(), 3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True, type=Path)
    args = parser.parse_args()
    result_root = args.result_dir.resolve()
    review_root = result_root / "review"
    overrides_path = review_root / "manual-overrides.json"
    overrides = (
        json.loads(overrides_path.read_text(encoding="utf-8"))
        if overrides_path.is_file()
        else {}
    )

    rows: list[dict] = []
    for task_dir in sorted(path for path in review_root.iterdir() if path.is_dir()):
        mapping = json.loads((task_dir / "mapping.json").read_text(encoding="utf-8"))
        judge_one = {
            candidate["id"]: candidate
            for candidate in json.loads(
                (task_dir / "scores.blind.judge-1.json").read_text(encoding="utf-8")
            )["candidates"]
        }
        judge_two = {
            candidate["id"]: candidate
            for candidate in json.loads(
                (task_dir / "scores.blind.judge-2.json").read_text(encoding="utf-8")
            )["candidates"]
        }
        for candidate_id, identity in mapping.items():
            raw = (
                result_root
                / "raw"
                / task_dir.name
                / identity["mode"]
                / f"run-{identity['run']}"
            )
            run_data = json.loads((raw / "run.json").read_text(encoding="utf-8"))
            build = json.loads((raw / "build.json").read_text(encoding="utf-8"))
            size = json.loads((raw / "metrics.json").read_text(encoding="utf-8"))
            signal = json.loads(
                (raw / "feature-signal.json").read_text(encoding="utf-8")
            )
            primary = dict(judge_one[candidate_id])
            secondary = dict(judge_two[candidate_id])
            override = overrides.get(task_dir.name, {}).get(candidate_id)
            adjustment_reason = ""
            if override:
                adjustment_reason = override["reason"]
                primary.update(override["changes"])
            primary_total = sum(primary[field] for field in SCORE_FIELDS)
            secondary_total = sum(secondary[field] for field in SCORE_FIELDS)
            agent_completed = run_data["returncode"] == 0 and not run_data["timed_out"]
            build_passed = build["returncode"] == 0 and not build["timed_out"]
            correctness_gate = (
                agent_completed
                and build_passed
                and primary["completeness"] >= 2
                and not primary["critical_failure"]
            )
            rows.append(
                {
                    "task": task_dir.name,
                    "mode": identity["mode"],
                    "run": identity["run"],
                    "candidate_id": candidate_id,
                    "agent_completed": agent_completed,
                    "build_passed": build_passed,
                    "correctness_gate": correctness_gate,
                    "feature_signal": signal["all_present"],
                    **{field: primary[field] for field in SCORE_FIELDS},
                    "judge_total": primary_total,
                    "critical_failure": primary["critical_failure"],
                    "judge_2_total": secondary_total,
                    "judge_exact_match": all(
                        primary[field] == secondary[field] for field in SCORE_FIELDS
                    )
                    and primary["critical_failure"] == secondary["critical_failure"],
                    "judge_critical_match": primary["critical_failure"]
                    == secondary["critical_failure"],
                    "manual_adjustment": bool(override),
                    "adjustment_reason": adjustment_reason,
                    "source_added_loc": size["source_added_loc"],
                    "source_deleted_loc": size["source_deleted_loc"],
                    "source_files": size["source_files"],
                    "new_source_files": size["new_source_files"],
                    "test_added_loc": size["test_added_loc"],
                    "test_files": size["test_files"],
                    "dependency_manifest_changed": size[
                        "dependency_manifest_changed"
                    ],
                    "skill_trace": run_data["skill_trace"],
                    "global_refinetale_trace": run_data[
                        "global_refinetale_trace"
                    ],
                    "referytale_trace": run_data.get("referytale_trace", False),
                    "duration_seconds": parse_duration_seconds(
                        run_data["started_at"], run_data["finished_at"]
                    ),
                    "input_tokens": run_data.get("usage", {}).get("input_tokens", 0),
                    "cached_input_tokens": run_data.get("usage", {}).get(
                        "cached_input_tokens", 0
                    ),
                    "output_tokens": run_data.get("usage", {}).get("output_tokens", 0),
                    "evidence": primary["evidence"],
                    "judge_2_evidence": secondary["evidence"],
                }
            )

    rows.sort(key=lambda row: (row["task"], row["run"], row["mode"]))
    columns = list(rows[0])
    with (result_root / "scores.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    by_mode: dict[str, list[dict]] = defaultdict(list)
    by_mode_task: dict[str, dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        by_mode[row["mode"]].append(row)
        by_mode_task[row["mode"]][row["task"]].append(row)

    metrics: dict[str, dict] = {}
    for mode in ("baseline", "refinetale"):
        selected = by_mode[mode]
        accepted = [row for row in selected if row["correctness_gate"]]
        metrics[mode] = {
            "runs": len(selected),
            "agent_completed_runs": sum(row["agent_completed"] for row in selected),
            "build_passed_runs": sum(row["build_passed"] for row in selected),
            "correctness_gate_runs": len(accepted),
            "feature_signal_runs": sum(row["feature_signal"] for row in selected),
            "critical_failures": sum(row["critical_failure"] for row in selected),
            "source_added_loc_all": {
                "sum": sum(row["source_added_loc"] for row in selected),
                "mean": rounded_mean([row["source_added_loc"] for row in selected]),
                "median": rounded_median([row["source_added_loc"] for row in selected]),
            },
            "source_added_loc_gate_passed": {
                "sum": sum(row["source_added_loc"] for row in accepted),
                "mean": rounded_mean([row["source_added_loc"] for row in accepted]),
                "median": rounded_median([row["source_added_loc"] for row in accepted]),
            },
            "source_files_gate_passed": {
                "mean": rounded_mean([row["source_files"] for row in accepted]),
                "median": rounded_median([row["source_files"] for row in accepted]),
            },
            "dependency_manifest_changed_runs": sum(
                row["dependency_manifest_changed"] for row in selected
            ),
            "test_written_runs": sum(row["test_added_loc"] > 0 for row in selected),
            "judge_points": sum(row["judge_total"] for row in selected),
            "available_judge_points": len(selected) * len(SCORE_FIELDS) * 3,
            "criterion_points": {
                field: sum(row[field] for row in selected) for field in SCORE_FIELDS
            },
            "skill_trace_runs": sum(row["skill_trace"] for row in selected),
            "global_refinetale_trace_runs": sum(
                row["global_refinetale_trace"] for row in selected
            ),
            "referytale_trace_runs": sum(row["referytale_trace"] for row in selected),
            "duration_seconds": {
                "mean": rounded_mean([row["duration_seconds"] for row in selected]),
                "median": rounded_median([row["duration_seconds"] for row in selected]),
            },
            "output_tokens": {
                "sum": sum(row["output_tokens"] for row in selected),
                "mean": rounded_mean([row["output_tokens"] for row in selected]),
            },
            "per_task": {},
        }
        for task, group in sorted(by_mode_task[mode].items()):
            accepted_group = [row for row in group if row["correctness_gate"]]
            metrics[mode]["per_task"][task] = {
                "runs": len(group),
                "build_passed_runs": sum(row["build_passed"] for row in group),
                "correctness_gate_runs": len(accepted_group),
                "source_added_loc_all": [row["source_added_loc"] for row in group],
                "source_added_loc_gate_passed_median": rounded_median(
                    [row["source_added_loc"] for row in accepted_group]
                ),
                "judge_points": sum(row["judge_total"] for row in group),
            }

    comparisons = {}
    reductions = []
    baseline_accepted_total = refinetale_accepted_total = 0
    for task in sorted(by_mode_task["baseline"]):
        baseline_values = [
            row["source_added_loc"]
            for row in by_mode_task["baseline"][task]
            if row["correctness_gate"]
        ]
        refinetale_values = [
            row["source_added_loc"]
            for row in by_mode_task["refinetale"][task]
            if row["correctness_gate"]
        ]
        baseline_median = rounded_median(baseline_values)
        refinetale_median = rounded_median(refinetale_values)
        reduction = (
            round((baseline_median - refinetale_median) / baseline_median, 4)
            if baseline_median not in (None, 0) and refinetale_median is not None
            else None
        )
        if reduction is not None:
            reductions.append(reduction)
        baseline_accepted_total += sum(baseline_values)
        refinetale_accepted_total += sum(refinetale_values)
        comparisons[task] = {
            "baseline_gate_passed_loc": baseline_values,
            "refinetale_gate_passed_loc": refinetale_values,
            "baseline_median": baseline_median,
            "refinetale_median": refinetale_median,
            "median_reduction": reduction,
        }

    baseline_gate = metrics["baseline"]["correctness_gate_runs"]
    refinetale_gate = metrics["refinetale"]["correctness_gate_runs"]
    baseline_runs = metrics["baseline"]["runs"]
    refinetale_runs = metrics["refinetale"]["runs"]
    metrics["comparison"] = {
        "per_task": comparisons,
        "task_balanced_mean_of_median_reductions": rounded_mean(reductions),
        "pooled_gate_passed_loc_reduction": (
            round(
                (baseline_accepted_total - refinetale_accepted_total)
                / baseline_accepted_total,
                4,
            )
            if baseline_accepted_total
            else None
        ),
        "correctness_gate_rate_difference": round(
            refinetale_gate / refinetale_runs - baseline_gate / baseline_runs, 4
        ),
        "correctness_gate_fisher_exact_two_sided_p": fisher_exact_two_sided(
            refinetale_gate,
            refinetale_runs - refinetale_gate,
            baseline_gate,
            baseline_runs - baseline_gate,
        ),
        "baseline_correctness_gate_wilson_95": wilson_interval(
            baseline_gate, baseline_runs
        ),
        "refinetale_correctness_gate_wilson_95": wilson_interval(
            refinetale_gate, refinetale_runs
        ),
    }
    metrics["judge_agreement"] = {
        "exact_score_vector_runs": sum(row["judge_exact_match"] for row in rows),
        "critical_match_runs": sum(row["judge_critical_match"] for row in rows),
        "runs": len(rows),
        "manual_adjustments": sum(row["manual_adjustment"] for row in rows),
    }
    (result_root / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
