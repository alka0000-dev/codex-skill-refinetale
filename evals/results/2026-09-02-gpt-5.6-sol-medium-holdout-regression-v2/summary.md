# RefineTale holdout regression after targeted fixes

## Outcome

前revisionの独立holdoutを、そこから確認した失敗に基づく2つの一般規則を追加したrevision `873001e`で再実行した。RefineTale条件は17/18がPass、baselineは15/18がPassし、得点率は98.3%対91.7%だった。

| Metric | Baseline | RefineTale | Difference |
| --- | ---: | ---: | ---: |
| Pass | 15/18（83.3%） | 17/18（94.4%） | +11.1ポイント |
| Borderline | 2/18 | 0/18 | -2 |
| Earned points | 165/180（91.7%） | 177/180（98.3%） | +12（+6.7ポイント） |
| Critical failures | 1 | 1 | 0 |
| Skill body trace | 0/18 | 15/18 | +15 |

RefineTale側の失点3点のうち2点は、skill本文を読まなかった1runの安全境界違反、1点はtoken非表示testの明示不足だった。skill本文を読んだ15runに限定した探索的集計は15/15 Pass、149/150点である。ただし主要結果は未読runも含むintention-to-treatとする。

## Per-fixture result

| Fixture | Baseline pass | RefineTale pass | Baseline points | RefineTale points | Observation |
| --- | ---: | ---: | ---: | ---: | --- |
| 01 Limited POST retry | 2/3 | 2/3 | 27/30 | 28/30 | 両条件で1runずつ汎用POST retryを広げcritical。RefineTaleのcriticalはskill未読runで、読込traceがある2runは狭い専用境界を選び各10/10。 |
| 02 Clone form | 3/3 | 3/3 | 27/30 | 29/30 | RefineTaleの1runだけtoken非表示testの明示が不足。他のRefineTale runは必要な検証を網羅。 |
| 03 Vendor B import | 1/3 | 3/3 | 26/30 | 30/30 | baseline 2runが安全工程をVendor Bへ複製。RefineTaleは全runで単一pipelineへ合流。 |
| 04 CLI color | 3/3 | 3/3 | 30/30 | 30/30 | 両条件とも契約、優先順位、検証を満たした。 |
| 05 NDJSON export | 3/3 | 3/3 | 28/30 | 30/30 | baseline 1runはaudit順序とbackpressureに不足。RefineTaleは共通stream境界を維持。 |
| 06 Job histogram | 3/3 | 3/3 | 27/30 | 30/30 | baselineは3runともasync reject testが明示不足。RefineTaleは全runで成功・同期throw・async rejectを対応づけた。 |

## Statistical interpretation

- 18runずつのPass率に対するWilson 95%区間はbaseline 60.8%〜94.2%、RefineTale 74.2%〜99.0%で大きく重なる。
- Pass/非Passの2×2表に対する両側Fisher exact testは`p = 0.602597`。
- 同じfixtureの反復runは完全に独立した課題ではないため、区間と検定は近似的な補助情報として扱う。
- 統計的優位性は確認されていない。
- 同じholdoutを見てskillを調整した後の結果であり、独立した一般化証拠ではない。

## Method

- モデル: `gpt-5.6-sol`
- 推論強度: `medium`
- Codex CLI: `0.152.0`
- 課題: 6件
- 各条件: 3run
- 振る舞いrun: 36件
- 実行順: seed `20260902`でランダム化
- workspace: 条件ごとに隔離した一時Git repository
- sandbox: `read-only`
- RefineTale SHA-256: `873001ea53f54e4e924b7578d71bd721b3e5cf6cce6736a41209ca077874c7bf`
- インフラ失敗: 0/36
- judge: 同じモデル・推論強度でfixtureごとに1回、合計6回

baseline workspaceからRefineTaleを発見できない状態にし、RefineTale条件では同じworkspace構成へskillを追加して`$refinetale`を明示した。各fixtureの6回答は固定seedでA〜Fへ匿名化し、条件を隠したままS1〜S5を採点した。

## Manual audit and correction

一次採点後、critical 2件、全低得点回答、各領域の代表回答、mapping、traceを原文と照合した。

Fixture 02の2候補について、S3を1から2へ修正した。fixtureは元の名前へ` (copy)`を1回付けることを要求しているが、元の名前がすでにsuffix付きの場合に冪等化する要件はない。両候補とも複製初期化時に1回だけsuffixを付け、loader再検証で追加しないため、judgeが追加したsuffix冪等性条件は根拠がなかった。両候補ともtotalは8から9へ変わり、Pass判定は不変。一次judge出力は保持し、[`review/manual-overrides.json`](review/manual-overrides.json)で修正を公開している。

Critical 2件を含む他の修正はない。

## Interpretation

追加した「強い前提条件を持つ操作を汎用APIへ広げない」規則は、skill本文を読んだFixture 01の2runで狭い専用境界として反映された。「契約と検証を1対1で対応づける」規則も、Fixture 03〜06のRefineTale 12runを全て満点にした。一方、明示呼び出しでも3/18runに本文読込traceがなく、1件のcritical failureを防げなかった。

この結果は既知の失敗に対する回帰改善の確認であり、現在revisionの独立holdoutではない。一般化の判断には、skill本文と過去評価を見ずに固定した新しい実装型forward holdoutを使用する。

## Artifacts

- `manifest.json`: model、seed、skill/fixture hash
- `execution-order.json`: 固定seedによる実行順
- `raw/`: 36runのJSONL、最終回答、stderr、metadata
- `review/`: 匿名packet、mapping、judge出力、手動override
- `scores.csv`: 復号後の全得点、trace、修正記録
- `metrics.json`: 条件別集計
- `reviewer-notes.md`: 監査記録
- `environment.md`: 実行環境と時刻
