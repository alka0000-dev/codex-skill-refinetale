# Evaluation environment

| Field | Value |
| --- | --- |
| Implementation started | `2026-09-02T09:20:49.890036Z` |
| Implementation finished | `2026-09-02T10:24:33.058607Z` |
| Judge started | `2026-09-02T10:25:27.202955Z` |
| Judge finished | `2026-09-02T10:30:43.392048Z` |
| OS | `Darwin 25.5.0 arm64` |
| Codex CLI | `codex-cli 0.152.0` |
| Model | `gpt-5.6-sol` |
| Reasoning effort | `medium` |
| Public repository | `fastapi/full-stack-fastapi-template` |
| Repository commit | `cd83fc10ca20393e9ee50e3005e170c6929e047e` |
| Task source commit | `DietrichGebert/ponytail@2ed6c52c9d7e5e56942508591085fd45dea277d3` |
| Tasks | `6` |
| Runs per condition | `3` |
| Parallel jobs | `4` |
| Seed | `2026090203` |
| Sandbox | `workspace-write` inside isolated temporary Git repositories |
| Node.js | `v21.7.3` |
| npm | `10.5.0` |
| RefineTale SHA-256 | `873001ea53f54e4e924b7578d71bd721b3e5cf6cce6736a41209ca077874c7bf` |

正式runは36/36件、frontend buildは36/36件、judgeは12/12件がreturn code 0で完了した。実行前に固定repositoryのfrontend buildが成功することを確認した。依存は固定checkoutへ事前導入し、各workspaceから同じtreeをsymlinkで参照した。

正式run前の汚染runはtrace監査で失格とし、正式結果へ含めていない。`sanitize-results.py`を実行済みで、local absolute path、local user名、評価対象外の外部skill出力を除去した。
