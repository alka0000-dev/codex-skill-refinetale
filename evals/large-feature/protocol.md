# Protocol

1. Ponytailの公開agentic benchmarkから、`full-stack-fastapi-template`を対象にしたフロントエンド6課題を変更せず採用する。
2. `tasks.json`と評価scriptを実装runより先に固定する。
3. templateはcommit `cd83fc10ca20393e9ee50e3005e170c6929e047e`へ固定し、元の状態でfrontend buildが成功することを確認する。
4. 全条件で同じ実行上の注意を課題文へ付加する。
5. 各runはtemplateの独立コピーとfresh Codex contextを使う。
6. baselineではRefineTaleを配置しない。RefineTale条件では`SKILL.md` snapshotだけを`.agents/skills/refinetale/`へ配置し、その相対pathを指定して全文読込を要求する。ローカルの同名skillと`referytale`は全条件で無効化する。
7. 実装終了後にGit差分を保存し、同じ導入済み依存でfrontend buildを実行する。
8. 条件名を伏せて候補を無作為なIDへ割り当て、同一rubricで2回採点する。
9. judge不一致、build失敗、低完成度、極端なLOCを手動監査し、修正する場合は一次出力を保持したoverrideを残す。
10. 全run slotをintention-to-treatで保持し、失敗runを都合よく差し替えない。
11. 結果を確認した後に`SKILL.md`を変更した場合、この評価は変更後revisionの独立証拠として扱わない。

## Neutral execution note

次の文を全条件へ同一に追加する。

> Work in the existing repository and implement the requested change. Do not install dependencies, start a development server, or open a browser. You may run the existing build or type checks. Tests are optional when they are appropriate for this change.

## Frozen rubric

機械可読な正本は[`rubric.json`](rubric.json)とする。

各候補を次の4軸で0〜3点評価する。

- `completeness`: 0は未実装、1は中核欠落、2は主要機能を実装、3はticketを完全に実装。
- `coherence`: 0は既存設計と衝突、1は大きな不要層・依存、2は小さな余分を含むが一貫、3は既存またはnative機能を使う最小の責務へ収まる。
- `scope_discipline`: 0は依頼外が中心、1は大きな先行実装、2は軽微な余分、3はticketに必要な範囲だけ。
- `single_path`: 0は重複状態・経路が支配的、1は大きな重複、2は軽微な重複、3は状態・値・経路の正本が一つ。

critical failureは、ticket未実装、危険な既存契約の削除、repository全体を壊す変更、またはbuild失敗を隠す行為とする。correctness gateはCodex正常終了、実build成功、`completeness >= 2`、criticalなしをすべて満たす場合に通過する。
