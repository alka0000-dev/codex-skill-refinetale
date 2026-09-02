# RefineTale evaluation — evidence contract revision

## Outcome

収録した5件の振る舞いfixtureにおいて、RefineTale条件はbaselineより高いFull pass率とrubric適合率を示しました。

| Metric | Baseline | RefineTale | Difference |
| --- | ---: | ---: | ---: |
| Full pass | 5/15（33.3%） | 13/15（86.7%） | +53.3ポイント |
| Applicable rubric points | 102 | 102 | 0 |
| Earned rubric points | 86 | 99 | +13 |
| Rubric rate | 84.3% | 97.1% | +12.8ポイント |
| Critical failures | 0 | 0 | 0 |
| Skill body trace | 0/15 | 14/15 | +14 |

現在のrevisionでは、初回評価で弱かった具体的な検証計画と、変更不要時の見直し条件を「完了時に必ず残す証拠」としてskill冒頭へ追加しました。初回revisionのRefineTale条件は7/15でしたが、現在の別runでは13/15でした。

## Per-fixture full pass

| Fixture | Baseline | RefineTale | Observation |
| --- | ---: | ---: | --- |
| 01 Boundary normalization | 2/3 | 2/3 | RefineTaleの1runで終了日側の無効日付テストが不足した。 |
| 02 Single source of truth | 3/3 | 2/3 | RefineTaleの1runで一括選択とtoggleが同じ状態更新経路にならなかった。 |
| 03 Real variation | 0/3 | 3/3 | RefineTaleは全runで各チャネルの送信先、監査イベント、失敗順序の検証を具体化した。 |
| 04 Safety boundaries | 0/3 | 3/3 | RefineTaleは全runで認可、無効ID、404、操作失敗、成功の検証を具体化した。 |
| 05 Stop when minimal | 0/3 | 3/3 | RefineTaleは全runで変更を止め、現在の検証と将来の見直し条件を示した。 |

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
- RefineTale revision: `ecc498cdf0753453be02ae98fb0e5df9ab6154e49a0ed7f8ecfeb95c1d5c7a89`
- インフラ失敗: 0/36

baseline workspaceからRefineTaleを発見できない状態にし、RefineTale条件では同じworkspace構成へskillを追加して`$refinetale`を明示しました。ルーティング評価ではskillを利用可能にしましたが、入力内では名前を明示していません。

各fixtureの6回答は、条件とrun番号を固定seedでA〜Fへ匿名化しました。一次採点は同じ`gpt-5.6-sol`・`medium`へ共通rubricとfixture固有条件を渡して実行しました。その後、生回答、fixture、trace、採点根拠を手動で照合しました。

Fixture 02候補Cは、一括選択とtoggleの更新経路が一致しないため不合格を維持しました。一方、入力に表示外選択保持の契約はなく、状態の正本とAPI契約も維持していたため、G1を0から1、critical failureをtrueからfalseへ修正しました。ほかの採点修正はありません。

## Comparison with the initial revision

| RefineTale metric | Initial revision | Current revision |
| --- | ---: | ---: |
| Full pass | 7/15（46.7%） | 13/15（86.7%） |
| Rubric rate | 93/99（93.9%） | 99/102（97.1%） |
| Critical failures | 0 | 0 |
| Skill body trace | 14/15 | 14/15 |

fixture hash、モデル、推論強度、run数、seedは同じです。ただし、回答と採点は別々の確率的実行であり、rubricのN/A判定数も異なります。この表は記述的な回帰比較で、revisionだけの因果効果を推定したものではありません。

## Known limitations

- 空の読み取り専用workspaceで回答方針を評価したため、提案コードのビルド、lint、型チェック、テスト実行は行っていない。
- 現在のrevisionは初回fixtureの失敗を見て改善したため、本結果は同じfixtureに対する回帰評価であり、独立holdoutではない。
- 採点者は単一のCodex modelであり、独立した複数人の評価者間一致は測定していない。
- 5件を各条件3回実行した小標本であり、統計的有意差の検定は行っていない。
- RefineTale条件の1/15runはskill本文を読むtraceがなかった。このrunは差し替えず結果へ含めた。
- Full passは13/15であり、Fixture 01の検証網羅性とFixture 02の状態更新経路に失敗が残った。

したがって、本結果が支持する表現は「収録した応答レベル回帰評価で改善を確認した」です。「未知のrepositoryでも同じ効果がある」または「生成コードの実装品質を全面的に証明した」とは主張しません。

## Artifacts

- `manifest.json`: 実行条件、skill hash、fixture hash
- `execution-order.json`: 固定seedによる実行順
- `raw/`: 36runのJSONL、最終回答、stderr、run metadata
- `review/`: 匿名採点prompt、対応表、一次採点結果、出力schema
- `scores.csv`: 条件を復元した全rubric得点と証拠
- `metrics.json`: 集計値
- `routing.json`: ルーティングtraceの判定
- `reviewer-notes.md`: 採点手順と手動修正の記録
