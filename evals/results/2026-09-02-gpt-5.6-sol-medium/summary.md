# RefineTale evaluation — 2026-09-02

## Outcome

収録した5件の振る舞いfixtureにおいて、RefineTale条件はbaselineより高いrubric適合率を示しました。

| Metric | Baseline | RefineTale | Difference |
| --- | ---: | ---: | ---: |
| Full pass | 5/15（33.3%） | 7/15（46.7%） | +13.3ポイント |
| Applicable rubric points | 100 | 99 | -1 |
| Earned rubric points | 76 | 93 | +17 |
| Rubric rate | 76.0% | 93.9% | +17.9ポイント |
| Critical failures | 2 | 0 | -2 |
| Skill body trace | 0/15 | 14/15 | +14 |

この結果から、収録fixtureと実行条件の範囲では、RefineTaleによる記述統計上の改善を確認しました。ただし、全runが合格したわけではありません。

## Per-fixture full pass

| Fixture | Baseline | RefineTale | Observation |
| --- | ---: | ---: | --- |
| 01 Boundary normalization | 2/3 | 3/3 | RefineTale条件は全runで外部契約を維持し、共通経路と公開経路テストを提示した。 |
| 02 Single source of truth | 2/3 | 3/3 | 両条件とも状態の一本化は強かったが、baselineの1runには失敗するテスト案があった。 |
| 03 Real variation | 0/3 | 0/3 | RefineTale条件は3/3で共通経路を提示したが、全runでチャネル別テスト計画が不足した。 |
| 04 Safety boundaries | 1/3 | 0/3 | 全runで安全境界は維持したが、RefineTale条件は必須テストケースを列挙しなかった。 |
| 05 Stop when minimal | 0/3 | 1/3 | RefineTale条件は不要な変更を避けたが、2runで将来の見直し条件が明示不足だった。 |

## Routing

| Input | Expected | Result |
| --- | --- | ---: |
| A | RefineTaleを呼び出す | 3/3 |
| B | RefineTaleを呼び出さない | 3/3 |

ルーティングの成功は、JSONL内の`refinetale/SKILL.md`読込traceで確認しました。

## Method

- モデル: `gpt-5.6-sol`
- 推論強度: `medium`
- Codex CLI: `0.152.0`
- 各条件: 3run
- 振る舞いrun: 30件
- ルーティングrun: 6件
- 実行順: seed `20260902`でランダム化
- workspace: 条件ごとに隔離した一時Git repository
- sandbox: `read-only`
- RefineTale revision: `faad55f6063148266b442aa7f65021f6fb0ea59cd54b29bc98d6a6dc080c7722`
- インフラ失敗: 0/36

baseline workspaceからRefineTaleを発見できない状態にし、RefineTale条件では同じworkspace構成へskillを追加して`$refinetale`を明示しました。ルーティング評価ではskillを利用可能にしましたが、入力内では名前を明示していません。

各fixtureの6回答は、条件とrun番号を固定seedでA〜Fへ匿名化しました。一次採点は同じ`gpt-5.6-sol`・`medium`へ共通rubricとfixture固有条件を渡して実行しました。その後、生回答との手動照合を行い、一次採点からの修正はありませんでした。

## Known limitations

- 空の読み取り専用workspaceで回答方針を評価したため、提案コードのビルド、lint、型チェック、テスト実行は行っていない。
- 採点者は単一のCodex modelであり、独立した複数人の評価者間一致は測定していない。
- 5件を各条件3回実行した小標本であり、統計的有意差の検定は行っていない。
- RefineTale条件の1/15runはskill名へ言及したものの、skill本文を読むtraceがなかった。このrunは差し替えず結果へ含めた。
- 5件の小規模fixtureに限定され、実際の大規模repositoryや他モデルへ一般化できるとは限らない。
- Full passは46.7%であり、fixture 03・04を中心に検証計画の弱さが残った。

したがって、本結果が支持する表現は「収録した応答レベル評価で効果を確認した」です。「生成コードの実装品質を全面的に証明した」または「あらゆるrepositoryで効果がある」とは主張しません。

## Artifacts

- `manifest.json`: 実行条件、skill hash、fixture hash
- `execution-order.json`: 固定seedによる実行順
- `raw/`: 36runのJSONL、最終回答、stderr、run metadata。ローカル絶対パスは公開用プレースホルダーへ置換し、評価対象外のローカルskill本文は削除済み。
- `review/`: 匿名採点prompt、対応表、一次採点結果、出力schema
- `scores.csv`: 条件を復元した全rubric得点と証拠
- `metrics.json`: 集計値
- `routing.json`: ルーティングtraceの判定
- `reviewer-notes.md`: 採点手順と監査記録
