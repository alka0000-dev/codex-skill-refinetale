#!/usr/bin/env python3
"""Run RefineTale behavior and routing evaluations with Codex CLI."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import random
import re
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


EVAL_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = EVAL_ROOT.parent
FIXTURE_ROOT = EVAL_ROOT / "fixtures"


@dataclass(frozen=True)
class EvalTask:
    category: str
    fixture: str
    mode: str
    run: int
    prompt: str
    workspace: str


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_behavior_prompt(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    match = re.search(
        r"^## Input\n\n(.*?)\n\n## Pass conditions\n",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise ValueError(f"Input section not found: {path}")
    return match.group(1).strip()


def extract_routing_prompts(path: Path) -> dict[str, str]:
    content = path.read_text(encoding="utf-8")
    match = re.search(
        r"^### A: expected invocation\n\n(.*?)\n\n"
        r"### B: expected non-invocation\n\n(.*?)\n\n## Pass conditions\n",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise ValueError(f"Routing inputs not found: {path}")
    return {"A": match.group(1).strip(), "B": match.group(2).strip()}


def extract_final_message(events: str) -> str:
    messages: list[str] = []
    for line in events.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") or {}
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            text = item.get("text")
            if isinstance(text, str):
                messages.append(text)
    return messages[-1] if messages else ""


def run_task(
    task: EvalTask,
    result_root: Path,
    model: str,
    effort: str,
) -> tuple[EvalTask, int]:
    output_dir = (
        result_root
        / "raw"
        / task.category
        / task.fixture
        / task.mode
        / f"run-{task.run}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

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
        task.prompt,
    ]
    started_at = dt.datetime.now(dt.timezone.utc)
    completed = subprocess.run(
        command,
        cwd=task.workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    finished_at = dt.datetime.now(dt.timezone.utc)

    (output_dir / "events.jsonl").write_text(completed.stdout, encoding="utf-8")
    (output_dir / "stderr.log").write_text(completed.stderr, encoding="utf-8")
    (output_dir / "final.md").write_text(
        extract_final_message(completed.stdout).rstrip() + "\n",
        encoding="utf-8",
    )
    metadata = {
        **asdict(task),
        "prompt_sha256": hashlib.sha256(task.prompt.encode("utf-8")).hexdigest(),
        "model": model,
        "reasoning_effort": effort,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "returncode": completed.returncode,
    }
    (output_dir / "run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"[{finished_at.isoformat()}] {task.category}/{task.fixture}/"
        f"{task.mode}/run-{task.run}: exit={completed.returncode}",
        flush=True,
    )
    return task, completed.returncode


def initialize_workspace(path: Path, with_skill: bool) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    if with_skill:
        skill_dir = path / ".agents" / "skills"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "refinetale").symlink_to(SKILL_ROOT, target_is_directory=True)


def discover_behavior_fixtures(fixture_root: Path) -> list[Path]:
    fixtures = []
    for path in sorted(fixture_root.glob("[0-9][0-9]-*.md")):
        content = path.read_text(encoding="utf-8")
        if "\n## Input\n" in content and "\n### A: expected invocation\n" not in content:
            fixtures.append(path)
    return fixtures


def build_tasks(
    baseline: Path,
    treatment: Path,
    runs: int,
    fixture_root: Path,
    include_routing: bool,
) -> list[EvalTask]:
    tasks: list[EvalTask] = []
    for fixture_path in discover_behavior_fixtures(fixture_root):
        fixture = fixture_path.name[:2]
        prompt = extract_behavior_prompt(fixture_path)
        for run in range(1, runs + 1):
            tasks.append(
                EvalTask("behavior", fixture, "baseline", run, prompt, str(baseline))
            )
            tasks.append(
                EvalTask(
                    "behavior",
                    fixture,
                    "refinetale",
                    run,
                    f"$refinetale\n\n{prompt}",
                    str(treatment),
                )
            )

    if include_routing:
        routing = extract_routing_prompts(fixture_root / "06-routing-boundaries.md")
        for label, prompt in routing.items():
            expected = "invoke" if label == "A" else "do-not-invoke"
            for run in range(1, runs + 1):
                tasks.append(
                    EvalTask("routing", label, expected, run, prompt, str(treatment))
                )
    return tasks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--skip-routing", action="store_true")
    parser.add_argument("--result-dir", required=True, type=Path)
    args = parser.parse_args()

    result_root = args.result_dir.resolve()
    fixture_root = args.fixture_dir.resolve()
    behavior_fixtures = discover_behavior_fixtures(fixture_root)
    if not behavior_fixtures:
        raise SystemExit(f"No behavior fixtures found: {fixture_root}")
    if not args.skip_routing and not (fixture_root / "06-routing-boundaries.md").is_file():
        raise SystemExit(f"Routing fixture not found: {fixture_root}")
    if result_root.exists() and any(result_root.iterdir()):
        raise SystemExit(f"Result directory is not empty: {result_root}")
    result_root.mkdir(parents=True, exist_ok=True)

    cli_version = subprocess.run(
        ["codex", "--version"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    fixture_paths = sorted(fixture_root.glob("*.md"))
    manifest = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "codex_cli": cli_version,
        "model": args.model,
        "reasoning_effort": args.effort,
        "runs_per_condition": args.runs,
        "jobs": args.jobs,
        "execution_seed": args.seed,
        "skill_sha256": sha256(SKILL_ROOT / "SKILL.md"),
        "fixtures": {path.name: sha256(path) for path in fixture_paths},
        "notes": [
            "Smoke runs are excluded.",
            "Behavior baseline runs cannot discover the RefineTale project skill.",
            "Behavior treatment runs explicitly invoke $refinetale.",
            "All run slots are retained; failed infrastructure runs are not replaced.",
        ],
    }
    if args.skip_routing:
        manifest["notes"].append("Routing is outside this evaluation scope.")
    else:
        manifest["notes"].append(
            "Routing runs have RefineTale available but do not name it."
        )
    (result_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with tempfile.TemporaryDirectory(prefix="refinetale-eval-") as temporary:
        temporary_root = Path(temporary)
        baseline = temporary_root / "baseline"
        treatment = temporary_root / "treatment"
        initialize_workspace(baseline, with_skill=False)
        initialize_workspace(treatment, with_skill=True)

        tasks = build_tasks(
            baseline,
            treatment,
            args.runs,
            fixture_root,
            include_routing=not args.skip_routing,
        )
        random.Random(args.seed).shuffle(tasks)
        (result_root / "execution-order.json").write_text(
            json.dumps([asdict(task) for task in tasks], ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )

        failures = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
            futures = [
                executor.submit(run_task, task, result_root, args.model, args.effort)
                for task in tasks
            ]
            for future in concurrent.futures.as_completed(futures):
                _, returncode = future.result()
                failures += int(returncode != 0)

    print(f"Completed {len(tasks)} runs with {failures} infrastructure failures.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
