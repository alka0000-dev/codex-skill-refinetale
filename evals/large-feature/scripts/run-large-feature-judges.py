#!/usr/bin/env python3
"""Run repeated blind judges for large-feature implementations."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path


BENCH_ROOT = Path(__file__).resolve().parents[1]


def extract_final_message(events: str) -> str:
    messages: list[str] = []
    for line in events.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") or {}
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            value = item.get("text")
            if isinstance(value, str):
                messages.append(value)
    return messages[-1] if messages else ""


def disabled_skill_config(paths: tuple[str, ...]) -> str | None:
    if not paths:
        return None
    entries = []
    for raw_path in paths:
        escaped = raw_path.replace("\\", "\\\\").replace('"', '\\"')
        entries.append(f'{{path="{escaped}",enabled=false}}')
    return "skills.config=[" + ",".join(entries) + "]"


def run_with_input(
    command: list[str], prompt: str, cwd: Path, timeout: int
) -> tuple[int | None, str, str, bool]:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=os.name != "nt",
    )
    try:
        stdout, stderr = process.communicate(input=prompt, timeout=timeout)
        return process.returncode, stdout, stderr, False
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        stdout, stderr = process.communicate()
        return None, stdout, stderr, True


def validate_score(payload: dict, expected: set[str]) -> None:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("Judge output has no candidate list")
    for candidate in candidates:
        identifier = candidate.get("id")
        if isinstance(identifier, str) and identifier.startswith("Candidate "):
            candidate["id"] = identifier.removeprefix("Candidate ").strip()
    actual = {candidate.get("id") for candidate in candidates}
    if actual != expected or len(candidates) != len(expected):
        raise ValueError(f"Judge candidate mismatch: expected {expected}, got {actual}")
    for candidate in candidates:
        for field in ("completeness", "coherence", "scope_discipline", "single_path"):
            value = candidate.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 3:
                raise ValueError(f"Invalid {field}: {candidate}")
        if not isinstance(candidate.get("critical_failure"), bool):
            raise ValueError(f"Invalid critical_failure: {candidate}")
        if not isinstance(candidate.get("evidence"), str):
            raise ValueError(f"Invalid evidence: {candidate}")


def run_judge(
    task_dir: Path,
    judge_number: int,
    *,
    model: str,
    effort: str,
    timeout: int,
    disabled_paths: tuple[str, ...],
) -> tuple[str, int, bool]:
    mapping = json.loads((task_dir / "mapping.json").read_text(encoding="utf-8"))
    prompt = (task_dir / "packet.md").read_text(encoding="utf-8")
    command = [
        "codex",
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--json",
        "--model",
        model,
        "-c",
        f'model_reasoning_effort="{effort}"',
        "--sandbox",
        "read-only",
        "--output-schema",
        str(BENCH_ROOT / "judge-schema.json"),
    ]
    skill_config = disabled_skill_config(disabled_paths)
    if skill_config:
        command.extend(["-c", skill_config])
    command.append("-")

    with tempfile.TemporaryDirectory(prefix="refinetale-large-judge-") as temporary:
        workspace = Path(temporary) / "workspace"
        workspace.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
        started_at = dt.datetime.now(dt.timezone.utc)
        returncode, stdout, stderr, timed_out = run_with_input(
            command, prompt, workspace, timeout
        )
        finished_at = dt.datetime.now(dt.timezone.utc)

        replacements = [
            (str(workspace), "<JUDGE_WORKSPACE>"),
            (temporary, "<JUDGE_TEMP>"),
            (str(Path.home()), "<USER_HOME>"),
            (Path.home().name, "<USER>"),
        ]
        if temporary.startswith("/var/"):
            replacements.extend(
                [
                    (f"/private{workspace}", "<JUDGE_WORKSPACE>"),
                    (f"/private{temporary}", "<JUDGE_TEMP>"),
                ]
            )
        replacements.extend(
            (path, f"<DISABLED_SKILL_{index}>")
            for index, path in enumerate(disabled_paths, 1)
        )
        for source, target in sorted(replacements, key=lambda item: -len(item[0])):
            stdout = stdout.replace(source, target)
            stderr = stderr.replace(source, target)

    prefix = f"judge-{judge_number}"
    (task_dir / f"{prefix}.events.jsonl").write_text(stdout, encoding="utf-8")
    (task_dir / f"{prefix}.stderr.log").write_text(stderr, encoding="utf-8")
    metadata = {
        "task": task_dir.name,
        "judge": judge_number,
        "model": model,
        "reasoning_effort": effort,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "returncode": returncode,
        "timed_out": timed_out,
    }
    (task_dir / f"{prefix}.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    try:
        score = json.loads(extract_final_message(stdout))
        validate_score(score, set(mapping))
    except (json.JSONDecodeError, ValueError) as error:
        (task_dir / f"scores.blind.{prefix}.error.txt").write_text(
            f"{type(error).__name__}: {error}\n", encoding="utf-8"
        )
        succeeded = False
    else:
        (task_dir / f"scores.blind.{prefix}.json").write_text(
            json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        succeeded = returncode == 0 and not timed_out

    print(
        f"[{finished_at.isoformat()}] {task_dir.name}/{prefix}: "
        f"exit={returncode} valid={succeeded}",
        flush=True,
    )
    return task_dir.name, judge_number, succeeded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--judges", type=int, default=2)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--disable-skill-path", action="append", default=[])
    args = parser.parse_args()
    if args.judges < 1 or args.jobs < 1:
        raise SystemExit("--judges and --jobs must be positive")

    result_root = args.result_dir.resolve()
    review_root = result_root / "review"
    task_dirs = sorted(path for path in review_root.iterdir() if path.is_dir())
    if not task_dirs:
        raise SystemExit(f"No review packets found: {review_root}")
    disabled_paths = tuple(str(Path(path).resolve()) for path in args.disable_skill_path)
    tasks = [
        (task_dir, judge_number)
        for task_dir in task_dirs
        for judge_number in range(1, args.judges + 1)
    ]
    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = [
            executor.submit(
                run_judge,
                task_dir,
                judge_number,
                model=args.model,
                effort=args.effort,
                timeout=args.timeout_seconds,
                disabled_paths=disabled_paths,
            )
            for task_dir, judge_number in tasks
        ]
        for future in concurrent.futures.as_completed(futures):
            _, _, succeeded = future.result()
            failures += int(not succeeded)
    print(f"Completed {len(tasks)} judges with {failures} failures.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
