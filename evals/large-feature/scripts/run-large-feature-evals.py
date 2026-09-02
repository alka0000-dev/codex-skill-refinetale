#!/usr/bin/env python3
"""Run RefineTale against public-repository feature tickets."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import random
import re
import shutil
import signal
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


BENCH_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = Path(__file__).resolve().parents[3]
TASKS_PATH = BENCH_ROOT / "tasks.json"
CODE_EXTENSIONS = {".css", ".html", ".js", ".jsx", ".ts", ".tsx"}
GENERATED_MARKERS = (".gen.ts", "routeTree.gen", "/client/")
TEST_PARTS = {"test", "tests", "__tests__"}
NEUTRAL_NOTE = (
    "Work in the existing repository and implement the requested change. "
    "Do not install dependencies, start a development server, or open a browser. "
    "You may run the existing build or type checks. Tests are optional when they "
    "are appropriate for this change."
)


@dataclass(frozen=True)
class EvalTask:
    task_id: str
    mode: str
    run: int
    ticket: str


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_tasks() -> dict:
    payload = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks.json has no tasks")
    seen: set[str] = set()
    for task in tasks:
        if not isinstance(task.get("id"), str) or not isinstance(
            task.get("prompt"), str
        ):
            raise ValueError("Every task needs string id and prompt")
        if task["id"] in seen:
            raise ValueError(f"Duplicate task id: {task['id']}")
        seen.add(task["id"])
    return payload


def run_command(
    command: list[str],
    *,
    cwd: Path,
    timeout: int,
    environment: dict[str, str] | None = None,
) -> tuple[int | None, str, str, bool]:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=os.name != "nt",
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
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


def copy_template(template: Path, workspace: Path) -> None:
    ignored = shutil.ignore_patterns(
        ".git",
        ".agents",
        ".agent",
        "node_modules",
        "dist",
        "dist-ssr",
        ".vite",
        "package-lock.json",
        "*.log",
        "__pycache__",
        ".pytest_cache",
        ".venv",
        "venv",
    )
    shutil.copytree(template, workspace, ignore=ignored)


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
            "pinned template",
        ],
        cwd=workspace,
        check=True,
    )


def install_dependencies_link(template: Path, workspace: Path) -> None:
    source = template / "node_modules"
    if not source.is_dir():
        raise ValueError(
            "Template node_modules is missing; install the pinned frontend dependencies first"
        )
    (workspace / "node_modules").symlink_to(source, target_is_directory=True)


def install_skill(workspace: Path) -> None:
    destination = workspace / ".agents" / "skills" / "refinetale"
    destination.mkdir(parents=True)
    shutil.copy2(SKILL_ROOT / "SKILL.md", destination / "SKILL.md")
    metadata = SKILL_ROOT / "agents" / "openai.yaml"
    if metadata.is_file():
        (destination / "agents").mkdir()
        shutil.copy2(metadata, destination / "agents" / "openai.yaml")


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


def extract_usage(events: str) -> dict[str, int]:
    for line in reversed(events.splitlines()):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "turn.completed" and isinstance(
            event.get("usage"), dict
        ):
            return {
                key: int(value)
                for key, value in event["usage"].items()
                if isinstance(value, int)
            }
    return {}


def sanitize_text(text: str, replacements: list[tuple[str, str]]) -> str:
    sanitized = text
    for source, target in sorted(replacements, key=lambda item: -len(item[0])):
        sanitized = sanitized.replace(source, target)
    return sanitized


def collect_diff(workspace: Path) -> str:
    subprocess.run(["git", "add", "-N", "-A"], cwd=workspace, check=True)
    completed = subprocess.run(
        [
            "git",
            "diff",
            "--no-ext-diff",
            "--binary",
            "HEAD",
            "--",
            ".",
            ":(exclude).agents/**",
            ":(exclude).agent/**",
            ":(exclude)node_modules",
            ":(glob,exclude)**/node_modules",
            ":(glob,exclude)**/dist/**",
            ":(glob,exclude)**/node_modules/**",
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def is_test_path(path: str) -> bool:
    parts = {part.lower() for part in Path(path).parts}
    name = Path(path).name.lower()
    return bool(parts & TEST_PARTS) or name.endswith(
        (".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")
    )


def is_generated_path(path: str) -> bool:
    normalized = f"/{path.replace(os.sep, '/')}"
    return any(marker in normalized for marker in GENERATED_MARKERS)


def diff_metrics(workspace: Path) -> dict:
    subprocess.run(["git", "add", "-N", "-A"], cwd=workspace, check=True)
    numstat = subprocess.run(
        ["git", "diff", "--numstat", "HEAD", "--", "."],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    statuses = subprocess.run(
        ["git", "diff", "--name-status", "HEAD", "--", "."],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    source_added = source_deleted = test_added = test_deleted = 0
    source_paths: set[str] = set()
    test_paths: set[str] = set()
    dependency_paths: set[str] = set()
    for line in numstat.splitlines():
        fields = line.split("\t")
        if len(fields) != 3 or fields[0] == "-":
            continue
        added, deleted, path = int(fields[0]), int(fields[1]), fields[2]
        if path.startswith((".agents/", ".agent/")) or "node_modules/" in path:
            continue
        if Path(path).name in {"package.json", "bun.lock", "package-lock.json"}:
            dependency_paths.add(path)
        if Path(path).suffix not in CODE_EXTENSIONS or is_generated_path(path):
            continue
        if is_test_path(path):
            test_added += added
            test_deleted += deleted
            test_paths.add(path)
        else:
            source_added += added
            source_deleted += deleted
            source_paths.add(path)

    new_source_paths: set[str] = set()
    for line in statuses.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        status, path = fields[0], fields[-1]
        if (
            status.startswith("A")
            and Path(path).suffix in CODE_EXTENSIONS
            and not is_test_path(path)
            and not is_generated_path(path)
        ):
            new_source_paths.add(path)

    return {
        "source_added_loc": source_added,
        "source_deleted_loc": source_deleted,
        "source_files": len(source_paths),
        "new_source_files": len(new_source_paths),
        "test_added_loc": test_added,
        "test_deleted_loc": test_deleted,
        "test_files": len(test_paths),
        "dependency_manifest_changed": bool(dependency_paths),
        "dependency_paths": sorted(dependency_paths),
        "source_paths": sorted(source_paths),
        "new_source_paths": sorted(new_source_paths),
    }


def feature_signal(task_id: str, diff: str) -> dict:
    lowered = diff.lower()
    rules: dict[str, list[tuple[str, str]]] = {
        "tmpl-fe-datepicker": [
            ("date-input", r"type\s*=\s*(?:[\"']date[\"']|\{[\"']date[\"']\})")
        ],
        "tmpl-fe-colorpicker": [
            ("color-input", r"type\s*=\s*(?:[\"']color[\"']|\{[\"']color[\"']\})")
        ],
        "tmpl-fe-command": [
            ("search", r"search|query"),
            ("keyboard", r"keydown|onkeydown|keyboard"),
        ],
        "tmpl-fe-dropzone": [
            ("file-input", r"type\s*=\s*(?:[\"']file[\"']|\{[\"']file[\"']\})"),
            ("drop", r"ondrop|drop"),
        ],
        "tmpl-fe-wizard": [
            ("step-state", r"currentstep|usestate|usereducer"),
            ("navigation", r"next|previous|prev"),
        ],
        "tmpl-fe-rating": [
            ("star", r"star|★|☆"),
            ("change", r"onchange|setrating|setvalue"),
        ],
    }
    checks = {
        name: bool(re.search(pattern, lowered)) for name, pattern in rules[task_id]
    }
    return {"checks": checks, "all_present": all(checks.values())}


def build_frontend(workspace: Path) -> dict:
    started_at = dt.datetime.now(dt.timezone.utc)
    environment = {
        **os.environ,
        "CI": "1",
        "NO_COLOR": "1",
        "npm_config_cache": str(Path(tempfile.gettempdir()) / "refinetale-npm-cache"),
    }
    returncode, stdout, stderr, timed_out = run_command(
        ["npm", "run", "build", "--workspace", "frontend"],
        cwd=workspace,
        timeout=240,
        environment=environment,
    )
    return {
        "command": ["npm", "run", "build", "--workspace", "frontend"],
        "started_at": started_at.isoformat(),
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "returncode": returncode,
        "timed_out": timed_out,
        "stdout": stdout,
        "stderr": stderr,
    }


def disabled_skill_config(paths: tuple[str, ...]) -> str | None:
    if not paths:
        return None
    entries = []
    for raw_path in paths:
        escaped = raw_path.replace("\\", "\\\\").replace('"', '\\"')
        entries.append(f'{{path="{escaped}",enabled=false}}')
    return "skills.config=[" + ",".join(entries) + "]"


def run_task(
    task: EvalTask,
    *,
    template: Path,
    result_root: Path,
    model: str,
    effort: str,
    timeout: int,
    disabled_skill_paths: tuple[str, ...],
) -> tuple[EvalTask, bool]:
    output_dir = (
        result_root
        / "raw"
        / task.task_id
        / task.mode
        / f"run-{task.run}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="refinetale-large-feature-") as temp:
        temporary_root = Path(temp)
        workspace = temporary_root / "workspace"
        copy_template(template, workspace)
        initialize_git(workspace)
        install_dependencies_link(template, workspace)
        if task.mode == "refinetale":
            install_skill(workspace)

        common_prompt = f"{task.ticket}\n\n{NEUTRAL_NOTE}"
        prompt = (
            "Use the repository-local $refinetale skill. Read "
            ".agents/skills/refinetale/SKILL.md completely before working, then "
            f"follow it for this task.\n\n{common_prompt}"
            if task.mode == "refinetale"
            else common_prompt
        )
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
            "workspace-write",
        ]
        skill_config = disabled_skill_config(disabled_skill_paths)
        if skill_config:
            command.extend(["-c", skill_config])
        command.append(prompt)

        started_at = dt.datetime.now(dt.timezone.utc)
        returncode, stdout, stderr, timed_out = run_command(
            command,
            cwd=workspace,
            timeout=timeout,
        )
        finished_at = dt.datetime.now(dt.timezone.utc)
        build = build_frontend(workspace)
        diff = collect_diff(workspace)
        metrics = diff_metrics(workspace)
        signal_result = feature_signal(task.task_id, diff)
        usage = extract_usage(stdout)
        skill_trace = ".agents/skills/refinetale/SKILL.md" in stdout
        global_refinetale_trace = "codex-skill-refinetale/SKILL.md" in stdout
        referytale_trace = "codex-skill-referytale/SKILL.md" in stdout

        replacements = [
            (str(workspace), "<EVAL_WORKSPACE>"),
            (str(temporary_root), "<EVAL_TEMP>"),
            (str(template), "<TEMPLATE_CHECKOUT>"),
            (str(SKILL_ROOT), "<REFINETALE_SOURCE>"),
            (str(Path.home()), "<USER_HOME>"),
            (Path.home().name, "<USER>"),
        ]
        if str(temporary_root).startswith("/var/"):
            replacements.extend(
                [
                    (f"/private{workspace}", "<EVAL_WORKSPACE>"),
                    (f"/private{temporary_root}", "<EVAL_TEMP>"),
                ]
            )
        replacements.extend(
            (path, f"<DISABLED_SKILL_{index}>")
            for index, path in enumerate(disabled_skill_paths, 1)
        )
        sanitized_stdout = sanitize_text(stdout, replacements)
        sanitized_stderr = sanitize_text(stderr, replacements)
        sanitized_diff = sanitize_text(diff, replacements)
        build_stdout = sanitize_text(build.pop("stdout"), replacements)
        build_stderr = sanitize_text(build.pop("stderr"), replacements)

    (output_dir / "events.jsonl").write_text(sanitized_stdout, encoding="utf-8")
    (output_dir / "stderr.log").write_text(sanitized_stderr, encoding="utf-8")
    (output_dir / "final.md").write_text(
        sanitize_text(extract_final_message(stdout), replacements).rstrip() + "\n",
        encoding="utf-8",
    )
    (output_dir / "diff.patch").write_text(sanitized_diff, encoding="utf-8")
    (output_dir / "build.stdout.log").write_text(build_stdout, encoding="utf-8")
    (output_dir / "build.stderr.log").write_text(build_stderr, encoding="utf-8")
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "feature-signal.json").write_text(
        json.dumps(signal_result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "build.json").write_text(
        json.dumps(build, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    metadata = {
        **asdict(task),
        "model": model,
        "reasoning_effort": effort,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "returncode": returncode,
        "timed_out": timed_out,
        "build_passed": build["returncode"] == 0 and not build["timed_out"],
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "diff_sha256": hashlib.sha256(diff.encode("utf-8")).hexdigest(),
        "skill_trace": skill_trace,
        "global_refinetale_trace": global_refinetale_trace,
        "referytale_trace": referytale_trace,
        "usage": usage,
    }
    (output_dir / "run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"[{finished_at.isoformat()}] {task.task_id}/{task.mode}/run-{task.run}: "
        f"codex={returncode} build={build['returncode']} "
        f"loc={metrics['source_added_loc']}",
        flush=True,
    )
    return task, returncode == 0 and not timed_out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template-dir", required=True, type=Path)
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument(
        "--task",
        action="append",
        help="Run only the named task; repeat this option to select multiple tasks",
    )
    parser.add_argument("--seed", type=int, default=2026090203)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--disable-skill-path", action="append", default=[])
    args = parser.parse_args()

    if args.runs < 1 or args.jobs < 1:
        raise SystemExit("--runs and --jobs must be positive")
    template = args.template_dir.resolve()
    result_root = args.result_dir.resolve()
    if result_root.exists() and any(result_root.iterdir()):
        raise SystemExit(f"Result directory is not empty: {result_root}")
    if not (template / ".git").exists():
        raise SystemExit(f"Template is not a Git checkout: {template}")
    payload = load_tasks()
    if args.task:
        requested = set(args.task)
        available = {task["id"] for task in payload["tasks"]}
        unknown = requested - available
        if unknown:
            raise SystemExit(f"Unknown tasks: {sorted(unknown)}")
        payload["tasks"] = [
            task for task in payload["tasks"] if task["id"] in requested
        ]
    expected_commit = payload["template"]["commit"]
    actual_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=template,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if actual_commit != expected_commit:
        raise SystemExit(
            f"Template commit mismatch: expected {expected_commit}, got {actual_commit}"
        )
    if not (template / "node_modules").is_dir():
        raise SystemExit("Install template frontend dependencies before running")

    result_root.mkdir(parents=True, exist_ok=True)
    cli_version = subprocess.run(
        ["codex", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    node_version = subprocess.run(
        ["node", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    npm_version = subprocess.run(
        ["npm", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    disabled_paths = tuple(str(Path(path).resolve()) for path in args.disable_skill_path)
    disabled_hashes = {
        f"disabled-{index}": sha256(Path(path))
        for index, path in enumerate(disabled_paths, 1)
        if Path(path).is_file()
    }
    manifest = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "codex_cli": cli_version,
        "model": args.model,
        "reasoning_effort": args.effort,
        "runs_per_condition": args.runs,
        "jobs": args.jobs,
        "execution_seed": args.seed,
        "timeout_seconds": args.timeout_seconds,
        "skill_sha256": sha256(SKILL_ROOT / "SKILL.md"),
        "tasks_sha256": sha256(TASKS_PATH),
        "template": payload["template"],
        "task_source": payload["source"],
        "selected_tasks": [task["id"] for task in payload["tasks"]],
        "node": node_version,
        "npm": npm_version,
        "disabled_skill_hashes": disabled_hashes,
        "neutral_execution_note": NEUTRAL_NOTE,
        "notes": [
            "Tasks are unchanged from the pinned Ponytail agentic benchmark source.",
            "Every cell uses a fresh copy and a fresh Codex context.",
            "Baseline has no repository-local RefineTale skill.",
            "Treatment installs only the evaluated SKILL.md snapshot, names its repository-local path, and requires reading it completely.",
            "All run slots are retained; infrastructure or build failures are not replaced.",
            "The build uses one preinstalled dependency tree shared read-only by symlink.",
        ],
    }
    (result_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    tasks = [
        EvalTask(task["id"], mode, run, task["prompt"])
        for task in payload["tasks"]
        for run in range(1, args.runs + 1)
        for mode in ("baseline", "refinetale")
    ]
    random.Random(args.seed).shuffle(tasks)
    (result_root / "execution-order.json").write_text(
        json.dumps([asdict(task) for task in tasks], ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )

    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = [
            executor.submit(
                run_task,
                task,
                template=template,
                result_root=result_root,
                model=args.model,
                effort=args.effort,
                timeout=args.timeout_seconds,
                disabled_skill_paths=disabled_paths,
            )
            for task in tasks
        ]
        for future in concurrent.futures.as_completed(futures):
            _, succeeded = future.result()
            failures += int(not succeeded)

    print(f"Completed {len(tasks)} runs with {failures} infrastructure failures.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
