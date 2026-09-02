#!/usr/bin/env python3
"""Run structured blind judges for implementation holdout packets."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import subprocess
import tempfile
from pathlib import Path


def run_judge(review_dir: Path, judge_run: int, model: str, effort: str) -> int:
    prompt = (review_dir / "prompt.md").read_text(encoding="utf-8")
    schema = review_dir.parent / "score-schema.json"
    suffix = f"judge-{judge_run}"
    output = review_dir / f"scores.blind.{suffix}.json"
    started_at = dt.datetime.now(dt.timezone.utc)
    with tempfile.TemporaryDirectory(prefix="refinetale-forward-judge-") as temporary:
        workspace = Path(temporary)
        subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
        command = [
            "codex",
            "exec",
            "--ephemeral",
            "--json",
            "--model",
            model,
            "-c",
            f'model_reasoning_effort="{effort}"',
            "--sandbox",
            "read-only",
            "--output-schema",
            str(schema),
            "--output-last-message",
            str(output),
            "-",
        ]
        completed = subprocess.run(
            command,
            cwd=workspace,
            input=prompt,
            capture_output=True,
            text=True,
            check=False,
        )
    finished_at = dt.datetime.now(dt.timezone.utc)
    (review_dir / f"judge-events.{suffix}.jsonl").write_text(
        completed.stdout, encoding="utf-8"
    )
    (review_dir / f"judge-stderr.{suffix}.log").write_text(
        completed.stderr, encoding="utf-8"
    )
    (review_dir / f"judge-run.{suffix}.json").write_text(
        json.dumps(
            {
                "model": model,
                "reasoning_effort": effort,
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "returncode": completed.returncode,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"{review_dir.name}/{suffix}: exit={completed.returncode}", flush=True
    )
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--judge-runs", type=int, default=2)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()

    review_dirs = sorted(args.result_dir.resolve().glob("review/fixture-*"))
    tasks = [
        (path, judge_run)
        for path in review_dirs
        for judge_run in range(1, args.judge_runs + 1)
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = [
            executor.submit(run_judge, path, judge_run, args.model, args.effort)
            for path, judge_run in tasks
        ]
        returncodes = [future.result() for future in futures]
    failures = sum(code != 0 for code in returncodes)
    print(f"Completed {len(tasks)} judges with {failures} failures.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
