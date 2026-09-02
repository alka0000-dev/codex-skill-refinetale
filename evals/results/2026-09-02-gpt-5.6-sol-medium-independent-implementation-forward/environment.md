# Evaluation environment

| Field | Value |
| --- | --- |
| Behavior started | `2026-09-02T05:35:15.701216Z` |
| Behavior finished | `2026-09-02T06:18:16.658130Z` |
| Judge started | `2026-09-02T06:18:57.711979Z` |
| Judge finished | `2026-09-02T06:22:44.162492Z` |
| OS | `Darwin 25.5.0 arm64` |
| Codex CLI | `codex-cli 0.152.0` |
| Model | `gpt-5.6-sol` |
| Reasoning effort | `medium` |
| Fixtures | `8` |
| Runs per condition | `3` |
| Parallel jobs | `3` |
| Seed | `20260902` |
| Sandbox | `workspace-write` inside isolated temporary Git repositories |
| RefineTale SHA-256 | `873001ea53f54e4e924b7578d71bd721b3e5cf6cce6736a41209ca077874c7bf` |
| Frozen fixture tree SHA-256 | `a00cd15317c412c1991aa8f7ffd95a1f69c6b84950560cf8434aae767d00afa7` |

正式runは48/48件、固定検証は48/48件、judgeは16/16件がreturn code 0で完了した。fixture別SHA-256は`manifest.json`に記録している。`sanitize-results.py`を実行済みで、local absolute pathと評価対象外の外部skill出力を除去した。
