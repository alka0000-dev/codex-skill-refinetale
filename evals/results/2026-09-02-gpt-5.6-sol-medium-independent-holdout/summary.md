# RefineTale independent holdout evaluation

## Outcome

既存の回帰fixtureと失敗分析を見ずに作成した6件のholdoutにおいて、RefineTale条件は18/18がPass、baselineは17/18がPassでした。得点率はRefineTale 95.0%、baseline 93.9%です。

| Metric | Baseline | RefineTale | Difference |
| --- | ---: | ---: | ---: |
| Pass | 17/18（94.4%） | 18/18（100%） | +5.6ポイント |
| Borderline | 1/18 | 0/18 | -1 |
| Earned points | 169/180（93.9%） | 171/180（95.0%） | +2（+1.1ポイント） |
| Critical failures | 0 | 0 | 0 |
| Skill body trace | 0/18 | 15/18 | +15 |

RefineTaleはbaselineの1件のBorderlineを解消しました。一方、baseline自体が非常に高得点で差は小さく、独立holdoutが支持するのは「この小標本で非劣化と小幅な記述的改善を確認した」までです。大幅な改善や一般的な優位性は示していません。

## Per-fixture result

| Fixture | Baseline pass | RefineTale pass | Baseline points | RefineTale points | Observation |
| --- | ---: | ---: | ---: | ---: | --- |
| 01 Limited POST retry | 3/3 | 3/3 | 27/30 | 26/30 | 両条件とも安全境界を維持。RefineTaleは汎用POST opt-in境界と非空key保証に軽微な不足が残った。 |
| 02 Clone form | 3/3 | 3/3 | 27/30 | 28/30 | RefineTaleの1runはtoken非表示のtestが弱かったが、全runが既存create経路へ合流した。 |
| 03 Vendor B import | 2/3 | 3/3 | 27/30 | 28/30 | baselineの1runだけ安全工程全体を複製しS1=0となった。RefineTaleは全runで単一pipelineを維持した。 |
| 04 CLI color | 3/3 | 3/3 | 30/30 | 30/30 | 両条件が優先順位、明示的false、command別defaultを完全に扱った。 |
| 05 NDJSON export | 3/3 | 3/3 | 30/30 | 30/30 | 両条件がtenant/public-row/queryを共有し、serializer差分だけを追加した。 |
| 06 Job histogram | 3/3 | 3/3 | 28/30 | 29/30 | 両条件が単一計測点を維持。いくつかのrunでasync rejection testが不足した。 |

## Statistical interpretation

- 18runずつのPass率に対するWilson 95%区間はbaseline 74.2%〜99.0%、RefineTale 82.4%〜100%で大きく重なる。
- Pass/非Passの2×2表に対する両側Fisher exact testは`p = 1.0`。
- したがって、観測差から統計的優位性は主張しない。
- 課題が詳細な契約を明示しているためbaselineも高得点となり、天井効果がある。

統計値は小標本の不確実性を示す補助情報であり、独立課題作成の品質や未知repositoryへの外的妥当性を保証するものではありません。

## Method

- モデル: `gpt-5.6-sol`
- 推論強度: `medium`
- Codex CLI: `0.152.0`
- 課題: 6件
- 各条件: 3run
- 振る舞いrun: 36件
- 実行順: seed `2026090202`でランダム化
- workspace: 条件ごとに隔離した一時Git repository
- sandbox: `read-only`
- RefineTale SHA-256: `ecc498cdf0753453be02ae98fb0e5df9ab6154e49a0ed7f8ecfeb95c1d5c7a89`
- インフラ失敗: 0/36（正式run）
- judge: 同じモデル・推論強度でfixtureごとに1回、合計6回

baseline workspaceからRefineTaleを発見できない状態にし、RefineTale条件では同じworkspace構成へskillを追加して`$refinetale`を明示しました。各fixtureの6回答は固定seedでA〜Fへ匿名化し、条件を隠したままS1〜S5を採点しました。

正式runの前にsandbox権限制約で36件すべてが開始前に失敗した試行が1回あります。この試行は回答を1件も生成しておらず、公開結果から除外して一時領域へ隔離しました。正式runは同じfixture、skill hash、seed、順序で再実行し、36/36件が成功しました。

## Independence protocol

holdout課題はfresh-contextの独立agentが作成しました。作成者にはRefineTaleの公開レベルの目的だけを伝え、`SKILL.md`本文、既存fixture、過去run、失敗分析を読まないよう明示しました。主担当は原案完成後に初めて内容を確認し、runner用の見出しへ整形してhashを固定しました。その後、RefineTale本体は変更していません。

詳細は[`../../holdout/authoring-protocol.md`](../../holdout/authoring-protocol.md)を参照してください。この独立性はprocess上の分離であり、第三者機関や独立した人間による検証ではありません。

## Manual audit and correction

一次採点後、全ての低得点回答、critical条件、代表的な満点回答、mapping、traceを原文と照合しました。

Fixture 02候補DはS3を1から2へ修正しました。fixtureは「元の名前へ` (copy)`を一度だけ付ける」と要求しており、既にsuffixがある名前を冪等化する要求はありません。候補Dは初期化時に一度だけ付けているため、一次judgeが追加した冪等性条件は根拠がありませんでした。totalは8から9へ変わり、Pass判定は変わりません。修正前のjudge出力は保持し、[`review/manual-overrides.json`](review/manual-overrides.json)で差分を公開しています。他の修正はありません。

## Skill-use fidelity

RefineTale条件の15/18runで`refinetale/SKILL.md`の読込traceを確認しました。3runは明示呼び出しにもかかわらずtraceがありませんでしたが、差し替えずintention-to-treatとしてRefineTale条件へ含めています。この3runもすべてPassで、合計29/30点でした。

## Known limitations

- 空のread-only workspaceで設計案とtest planを評価しており、生成コードのbuild、lint、型check、test成功は評価していない。
- 6課題×各条件3runの小標本で、単一model familyによる生成と採点である。
- 課題作成はfresh-context agentへ分離したが、外部の人間・組織による第三者評価ではない。
- 依頼文が詳細な契約と期待値を含むためbaselineの天井効果が強く、難しい曖昧要件や実repository上の差を十分に測れていない。
- RefineTale条件の3/18runはskill本文を読むtraceがなかった。
- 1回の匿名judgeと主担当の手動監査であり、複数judge間一致は測定していない。

## Supported publication claim

この結果が支持する表現は次です。

> 既存評価から分離して作成した6件の応答レベルholdoutで、RefineTaleは18/18、baselineは17/18がPassし、得点率は95.0%対93.9%だった。critical failureは双方0件だった。差は小さく、統計的優位性は確認されていない。

「未知のrepositoryで実装品質を改善すると証明した」「統計的に有意な効果がある」「第三者検証済み」とは表現しません。

## Artifacts

- `manifest.json`: model、seed、skill/fixture hash
- `execution-order.json`: 固定seedによる実行順
- `raw/`: 36runのJSONL、最終回答、stderr、metadata
- `review/`: 匿名packet、mapping、judge出力、手動override
- `scores.csv`: 復号後の全得点、trace、修正記録
- `metrics.json`: 条件別集計
- `reviewer-notes.md`: 監査記録
- `environment.md`: 実行環境と時刻
