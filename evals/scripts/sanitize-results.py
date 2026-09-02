#!/usr/bin/env python3
"""Remove local absolute paths from an evaluation result directory."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TEXT_SUFFIXES = {".csv", ".json", ".jsonl", ".log", ".md", ".txt"}
FORWARD_WORKSPACE_PATTERNS = (
    re.compile(
        r"/(?:private/)?var/folders/[^\s\"\\]+/T/"
        r"refinetale-forward-run-[^/\s\"\\]+/workspace"
    ),
    re.compile(r"/private/tmp/refinetale-forward-run-[^/\s\"\\]+/workspace"),
    re.compile(
        r"/(?:private/)?var/folders/[^\s\"\\]+/T/"
        r"refinetale-large-feature-[^/\s\"\\]+"
    ),
    re.compile(r"/(?:private/)?tmp/refinetale-[^/\s\"\\]+"),
)


def redact_external_skill_output(path: Path) -> None:
    if path.name != "events.jsonl":
        return
    redacted_lines = []
    changed = False
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            redacted_lines.append(line)
            continue
        item = event.get("item") or {}
        command = item.get("command", "")
        is_external_skill = any(
            marker in command
            for marker in (
                "<USER_HOME>/.agents/skills/",
                "<USER_HOME>/.codex/skills/",
                "<USER_HOME>/.codex/plugins/",
            )
        )
        if is_external_skill and item.get("aggregated_output"):
            item["aggregated_output"] = "<REDACTED_EXTERNAL_SKILL_OUTPUT>"
            changed = True
        redacted_lines.append(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
    if changed:
        path.write_text("\n".join(redacted_lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True, type=Path)
    args = parser.parse_args()
    root = args.result_dir.resolve()

    replacements = {
        str(Path.home()): "<USER_HOME>",
        Path.home().name: "<USER>",
        "/private/tmp": "<TMP_ROOT>",
        "/tmp": "<TMP_ROOT>",
    }
    for metadata_path in root.glob("raw/**/run.json"):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        workspace = metadata.get("workspace")
        if isinstance(workspace, str):
            workspace_root = str(Path(workspace).parent)
            replacements[workspace_root] = "<EVAL_WORKSPACE_ROOT>"
            if workspace_root.startswith("/var/"):
                replacements[f"/private{workspace_root}"] = "<EVAL_WORKSPACE_ROOT>"

    replacements["/private<EVAL_WORKSPACE_ROOT>"] = "<EVAL_WORKSPACE_ROOT>"
    replacements["/private<EVAL_WORKSPACE>"] = "<EVAL_WORKSPACE>"
    replacements["/private<EVAL_TEMP>"] = "<EVAL_TEMP>"
    replacements["/private<JUDGE_WORKSPACE>"] = "<JUDGE_WORKSPACE>"
    replacements["/private<JUDGE_TEMP>"] = "<JUDGE_TEMP>"

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        content = path.read_text(encoding="utf-8")
        sanitized = content
        for pattern in FORWARD_WORKSPACE_PATTERNS:
            sanitized = pattern.sub("<EVAL_WORKSPACE>", sanitized)
        for source, target in sorted(
            replacements.items(), key=lambda item: len(item[0]), reverse=True
        ):
            sanitized = sanitized.replace(source, target)
        if sanitized != content:
            path.write_text(sanitized, encoding="utf-8")
        redact_external_skill_output(path)


if __name__ == "__main__":
    main()
