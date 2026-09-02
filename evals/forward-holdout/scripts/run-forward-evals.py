#!/usr/bin/env python3
"""Run implementation-based RefineTale forward holdout evaluations."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import random
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


FORWARD_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = FORWARD_ROOT / "fixtures"


@dataclass(frozen=True)
class EvalTask:
    fixture: str
    fixture_name: str
    mode: str
    run: int
    prompt: str


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


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


def discover_fixtures(root: Path) -> list[Path]:
    fixtures = []
    for path in sorted(root.glob("[0-9][0-9]-*")):
        required = [path / "prompt.md", path / "rubric.md"]
        verify_exists = (path / "verify.json").is_file() or (
            path / "workspace" / "verify.json"
        ).is_file()
        if (
            path.is_dir()
            and (path / "workspace").is_dir()
            and all(item.is_file() for item in required)
            and verify_exists
        ):
            fixtures.append(path)
    return fixtures


def read_verify_config(fixture_dir: Path) -> dict:
    config_path = fixture_dir / "verify.json"
    if not config_path.is_file():
        config_path = fixture_dir / "workspace" / "verify.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    command = config.get("command")
    if not isinstance(command, list) or not command or not all(
        isinstance(item, str) and item for item in command
    ):
        raise ValueError(f"Invalid verification command: {fixture_dir}")
    timeout = config.get("timeout_seconds", 60)
    if not isinstance(timeout, int) or not 1 <= timeout <= 120:
        raise ValueError(f"Invalid verification timeout: {fixture_dir}")
    return config


def initialize_git(workspace: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
    subprocess.run(["git", "add", "-A"], cwd=workspace, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=RefineTale Eval",
            "-c",
            "user.email=eval@example.invalid",
            "commit",
            "-qm",
            "fixture baseline",
        ],
        cwd=workspace,
        check=True,
    )


def install_skill(workspace: Path) -> None:
    skill_dir = workspace / ".agents" / "skills"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "refinetale").symlink_to(SKILL_ROOT, target_is_directory=True)


def run_verification(workspace: Path, config: dict) -> dict:
    started_at = dt.datetime.now(dt.timezone.utc)
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        completed = subprocess.run(
            config["command"],
            cwd=workspace,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=config.get("timeout_seconds", 60),
        )
        result = {
            "command": config["command"],
            "returncode": completed.returncode,
            "timed_out": False,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as error:
        result = {
            "command": config["command"],
            "returncode": None,
            "timed_out": True,
            "stdout": error.stdout or "",
            "stderr": error.stderr or "",
        }
    result["started_at"] = started_at.isoformat()
    result["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    return result


def collect_diff(workspace: Path) -> str:
    subprocess.run(["git", "add", "-N", "-A"], cwd=workspace, check=True)
    completed = subprocess.run(
        [
            "git",
            "diff",
            "--no-ext-diff",
            "--binary",
            "--",
            ".",
            ":(exclude).agents",
            ":(glob,exclude)**/__pycache__/**",
            ":(glob,exclude)**/*.pyc",
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def restore_verification_assets(workspace: Path) -> None:
    paths = ["tests"]
    if (workspace / "verify.json").exists():
        paths.append("verify.json")
    subprocess.run(
        ["git", "restore", "--source=HEAD", "--", *paths],
        cwd=workspace,
        check=True,
    )


def run_task(
    task: EvalTask,
    fixture_root: Path,
    result_root: Path,
    model: str,
    effort: str,
) -> tuple[EvalTask, int]:
    fixture_dir = fixture_root / task.fixture_name
    output_dir = (
        result_root / "raw" / "behavior" / task.fixture / task.mode / f"run-{task.run}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    verify_config = read_verify_config(fixture_dir)

    with tempfile.TemporaryDirectory(prefix="refinetale-forward-run-") as temporary:
        workspace = Path(temporary) / "workspace"
        shutil.copytree(fixture_dir / "workspace", workspace)
        initialize_git(workspace)
        if task.mode == "refinetale":
            install_skill(workspace)

        prompt = task.prompt
        if task.mode == "refinetale":
            prompt = f"$refinetale\n\n{prompt}"
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
            "workspace-write",
            prompt,
        ]
        started_at = dt.datetime.now(dt.timezone.utc)
        completed = subprocess.run(
            command,
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        finished_at = dt.datetime.now(dt.timezone.utc)
        diff = collect_diff(workspace)
        restore_verification_assets(workspace)
        verification = run_verification(workspace, verify_config)

    (output_dir / "events.jsonl").write_text(completed.stdout, encoding="utf-8")
    (output_dir / "stderr.log").write_text(completed.stderr, encoding="utf-8")
    (output_dir / "final.md").write_text(
        extract_final_message(completed.stdout).rstrip() + "\n", encoding="utf-8"
    )
    (output_dir / "diff.patch").write_text(diff, encoding="utf-8")
    (output_dir / "verification.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "verify.stdout.log").write_text(
        verification["stdout"], encoding="utf-8"
    )
    (output_dir / "verify.stderr.log").write_text(
        verification["stderr"], encoding="utf-8"
    )
    metadata = {
        **asdict(task),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "model": model,
        "reasoning_effort": effort,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "returncode": completed.returncode,
        "verification_returncode": verification["returncode"],
        "verification_timed_out": verification["timed_out"],
        "diff_sha256": hashlib.sha256(diff.encode("utf-8")).hexdigest(),
    }
    (output_dir / "run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"[{finished_at.isoformat()}] behavior/{task.fixture}/{task.mode}/"
        f"run-{task.run}: codex={completed.returncode} "
        f"verify={verification['returncode']}",
        flush=True,
    )
    return task, completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--result-dir", required=True, type=Path)
    args = parser.parse_args()

    result_root = args.result_dir.resolve()
    fixture_root = args.fixture_dir.resolve()
    fixtures = discover_fixtures(fixture_root)
    if not fixtures:
        raise SystemExit(f"No forward fixtures found: {fixture_root}")
    if result_root.exists() and any(result_root.iterdir()):
        raise SystemExit(f"Result directory is not empty: {result_root}")
    result_root.mkdir(parents=True, exist_ok=True)

    cli_version = subprocess.run(
        ["codex", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    manifest = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "codex_cli": cli_version,
        "model": args.model,
        "reasoning_effort": args.effort,
        "runs_per_condition": args.runs,
        "jobs": args.jobs,
        "execution_seed": args.seed,
        "skill_sha256": sha256(SKILL_ROOT / "SKILL.md"),
        "fixtures": {path.name: tree_hash(path) for path in fixtures},
        "notes": [
            "Fixtures were frozen before the evaluated skill revision was inspected by the author.",
            "Baseline runs cannot discover the RefineTale project skill.",
            "Treatment runs explicitly invoke $refinetale.",
            "Codex edits an isolated copy and the fixture verification command runs afterward.",
            "All run slots are retained; failed infrastructure runs are not replaced.",
        ],
    }
    (result_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    tasks = [
        EvalTask(
            fixture=path.name[:2],
            fixture_name=path.name,
            mode=mode,
            run=run,
            prompt=(path / "prompt.md").read_text(encoding="utf-8").strip(),
        )
        for path in fixtures
        for run in range(1, args.runs + 1)
        for mode in ("baseline", "refinetale")
    ]
    random.Random(args.seed).shuffle(tasks)
    (result_root / "execution-order.json").write_text(
        json.dumps([asdict(task) for task in tasks], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = [
            executor.submit(
                run_task,
                task,
                fixture_root,
                result_root,
                args.model,
                args.effort,
            )
            for task in tasks
        ]
        for future in concurrent.futures.as_completed(futures):
            _, returncode = future.result()
            failures += int(returncode != 0)

    print(f"Completed {len(tasks)} runs with {failures} infrastructure failures.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
