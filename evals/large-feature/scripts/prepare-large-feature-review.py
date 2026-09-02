#!/usr/bin/env python3
"""Create anonymized review packets for the large-feature benchmark."""

from __future__ import annotations

import argparse
import json
import random
import string
from pathlib import Path


BENCH_ROOT = Path(__file__).resolve().parents[1]


def candidate_ids(count: int) -> list[str]:
    alphabet = string.ascii_uppercase
    if count > len(alphabet):
        raise ValueError("Too many candidates for one task")
    return list(alphabet[:count])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=2026090204)
    args = parser.parse_args()

    result_root = args.result_dir.resolve()
    tasks_payload = json.loads((BENCH_ROOT / "tasks.json").read_text(encoding="utf-8"))
    rubric = json.loads((BENCH_ROOT / "rubric.json").read_text(encoding="utf-8"))
    manifest = json.loads((result_root / "manifest.json").read_text(encoding="utf-8"))
    runs = manifest["runs_per_condition"]
    selected_tasks = set(
        manifest.get(
            "selected_tasks", [task["id"] for task in tasks_payload["tasks"]]
        )
    )

    review_root = result_root / "review"
    if review_root.exists() and any(review_root.iterdir()):
        raise SystemExit(f"Review directory is not empty: {review_root}")
    review_root.mkdir(parents=True, exist_ok=True)

    for task_index, task in enumerate(tasks_payload["tasks"]):
        if task["id"] not in selected_tasks:
            continue
        identities = [
            {"mode": mode, "run": run}
            for run in range(1, runs + 1)
            for mode in ("baseline", "refinetale")
        ]
        random.Random(args.seed + task_index).shuffle(identities)
        labels = candidate_ids(len(identities))
        mapping = dict(zip(labels, identities, strict=True))
        task_dir = review_root / task["id"]
        task_dir.mkdir()
        (task_dir / "mapping.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        sections = [
            "# Blind implementation review",
            "",
            "## Ticket",
            "",
            task["prompt"],
            "",
            "## Rubric",
            "",
            rubric["instructions"],
            "",
        ]
        for name, scale in rubric["criteria"].items():
            sections.extend(
                [
                    f"### {name}",
                    "",
                    *[f"- {score}: {description}" for score, description in scale.items()],
                    "",
                ]
            )
        sections.extend(
            [
                "### critical_failure",
                "",
                rubric["critical_failure"],
                "",
                "## Candidates",
                "",
            ]
        )

        for label, identity in mapping.items():
            raw = (
                result_root
                / "raw"
                / task["id"]
                / identity["mode"]
                / f"run-{identity['run']}"
            )
            run_data = json.loads((raw / "run.json").read_text(encoding="utf-8"))
            build = json.loads((raw / "build.json").read_text(encoding="utf-8"))
            diff = (raw / "diff.patch").read_text(encoding="utf-8").rstrip()
            sections.extend(
                [
                    f"### Candidate {label}",
                    "",
                    f"- Agent completed: `{run_data['returncode'] == 0 and not run_data['timed_out']}`",
                    f"- Frontend build passed: `{build['returncode'] == 0 and not build['timed_out']}`",
                    "",
                    "```diff",
                    diff,
                    "```",
                    "",
                ]
            )
        sections.extend(
            [
                "## Output",
                "",
                "Return JSON matching the supplied schema. Include every candidate exactly once. "
                f"Use only these exact one-letter values for `id`: {', '.join(labels)}. ",
                "For evidence, cite concrete files or code choices from the diff and do not guess the hidden condition.",
                "",
            ]
        )
        (task_dir / "packet.md").write_text("\n".join(sections), encoding="utf-8")

    (review_root / "manifest.json").write_text(
        json.dumps(
            {
                "created_from_result": result_root.name,
                "seed": args.seed,
                "rubric_sha256": __import__("hashlib").sha256(
                    (BENCH_ROOT / "rubric.json").read_bytes()
                ).hexdigest(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
