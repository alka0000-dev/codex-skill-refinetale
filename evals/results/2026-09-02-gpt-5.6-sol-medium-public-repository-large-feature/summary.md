# RefineTale public-repository large-feature benchmark

## Outcome

公開repository `fastapi/full-stack-fastapi-template` の固定commitへ、Ponytailが公開しているフロントエンド6課題を実装した。baselineとRefineTaleを各3回、合計36runで比較した結果、両条件とも18/18でfrontend buildとcorrectness gateを通過した。そのうえで、RefineTaleは追加source LOCの合計を4,118から1,777へ56.9%減らし、課題別LOC中央値の削減率は単純平均44.9%だった。

匿名rubricはbaseline 189/216点（87.5%）、RefineTale 213/216点（98.6%）だった。したがって、この評価では「未完成にして行数を減らした」のではなく、要求された機能とbuild成功を維持しながら、未要求のAPI、状態、独自機構、画面統合を抑えたことを確認した。

| Metric | Baseline | RefineTale | Difference |
| --- | ---: | ---: | ---: |
| Correctness gate | 18/18（100%） | 18/18（100%） | 0ポイント |
| Frontend build | 18/18（100%） | 18/18（100%） | 0ポイント |
| Judge points | 189/216（87.5%） | 213/216（98.6%） | +24（+11.1ポイント） |
| Added source LOC, sum | 4,118 | 1,777 | -2,341（-56.9%） |
| Added source LOC, mean | 228.8 | 98.7 | -56.9% |
| Source files, mean | 1.44 | 1.72 | +0.28 |
| Dependency changes | 0/18 | 0/18 | 0 |
| Critical failures | 0 | 0 | 0 |
| Target skill trace | 0/18 | 18/18 | +18 |
| Similar-skill trace | 0/18 | 0/18 | 0 |

ファイル数は減っていない。RefineTaleの効果は、責務を分ける必要がある課題では複数ファイルを許容しつつ、各ファイル内の不要な実装を減らした形で現れた。

## Per-task result

| Task | Baseline LOC | RefineTale LOC | Median reduction | Baseline points | RefineTale points |
| --- | --- | --- | ---: | ---: | ---: |
| Color picker | 24, 24, 26 | 23, 25, 23 | 4.2% | 33/36 | 35/36 |
| Command palette | 260, 263, 297 | 246, 192, 178 | 27.0% | 30/36 | 35/36 |
| Date picker | 480, 23, 11 | 12, 11, 9 | 52.2% | 31/36 | 36/36 |
| File dropzone | 277, 266, 262 | 106, 94, 136 | 60.2% | 27/36 | 36/36 |
| Star rating | 98, 124, 194 | 55, 57, 70 | 54.0% | 36/36 | 36/36 |
| Multi-step wizard | 526, 492, 471 | 284, 137, 119 | 72.2% | 32/36 | 35/36 |

特にbaselineの日付選択1runは、単純なcomponent追加に480 LOCの独自calendar、追加API、状態、focus管理を実装した。baselineのdropzone 3runも、未要求のvalidation、file list管理、設定API、demo画面統合などを含んだ。RefineTale条件では同じ課題の全runがbuildと完成度を維持しながら、既存componentまたはnative機能へ寄せた。

## Blind judge and manual audit

各課題の6候補をA〜Fへ匿名化し、生成条件、pair、skill traceを伏せて2回採点した。一次judgeを集計の正本、二次judgeを安定性監査に使用した。

| Agreement | Result |
| --- | ---: |
| All four criteria exactly equal | 18/36（50.0%） |
| Critical failure | 36/36（100%） |

不一致18候補は、すべて個別criterionの1点差だった。既存componentの再利用を必須とみなすか、軽微な追加機能をscope逸脱とみなすかなどの強度差で、critical判定とcorrectness gateは変わらなかった。一次judgeで2点未満のcriterionがあったのは、baselineの日付選択1件とdropzone 3件だけだった。diff、rubric、二次judgeを照合し、手動補正は0件とした。詳細は[`reviewer-notes.md`](reviewer-notes.md)に記録している。

## Cost trade-off

RefineTale条件は実装量を減らした一方、平均実行時間は345.6秒から438.4秒へ26.9%増え、平均output tokenは9,914から12,995へ31.1%増えた。skillの読込、変更契約の整理、削除レビューに追加コストがある。この評価はコード量とrubric品質の改善を示すが、生成時間やtoken効率の改善は示さない。

## Method

- model: `gpt-5.6-sol`
- reasoning effort: `medium`
- Codex CLI: `0.152.0`
- repository: `fastapi/full-stack-fastapi-template`
- repository commit: `cd83fc10ca20393e9ee50e3005e170c6929e047e`
- task source: `DietrichGebert/ponytail` commit `2ed6c52c9d7e5e56942508591085fd45dea277d3`
- tasks: frontend feature tickets 6件
- runs per condition: 3
- implementation runs: 36
- execution order: seed `2026090203`で無作為化
- sandbox: runごとに隔離した一時Git workspaceの`workspace-write`
- RefineTale SHA-256: `873001ea53f54e4e924b7578d71bd721b3e5cf6cce6736a41209ca077874c7bf`
- infrastructure failures: 0/36
- judge: 同じmodel・推論強度、課題ごとに独立contextで2回、合計12回

baselineにはrepository-local RefineTaleを配置せず、RefineTale条件だけへ評価対象snapshotを配置し、その相対pathの全文読込を明示した。同名のglobal skillと類似する`referytale`を全条件で無効化した。trace監査はbaseline 0/18、RefineTale 18/18、類似skill 0/36だった。

## Rejected preliminary run

正式runより前の36runは、RefineTale条件で対象skillのtraceが0/18、類似するglobal `referytale`のtraceが18/18だった。条件汚染を採点前の監査で検出したため、その結果は集計・公開主張から除外し、公開directory外へ隔離した。正式runではrepository-local pathの明示とglobal skill無効化を追加し、同じ課題・commit・回数で最初から再実行した。

## Rule-retention decision

評価後も`SKILL.md`は変更していない。直前に追加した2規則は、大きめ機能評価で悪影響が見られず、既知回帰ではそれぞれ狭い安全境界と検証経路の網羅へ直接対応しているため維持した。今回のsuiteは2規則を個別に除いた統制ablationではないため、規則単体の因果効果は主張しない。削除しなかった根拠は[`rule-retention.md`](rule-retention.md)に分離した。

## Statistical interpretation and limitations

- correctness gateは両条件とも100%で、Wilson 95%区間はいずれも82.4%〜100%、両側Fisher exact testは`p = 1.0`だった。
- LOC差は記述統計であり、課題内の反復runを独立標本とみなした有意差検定は行っていない。
- 公開済みの一文ticketは、実務の詳細な受け入れ基準や長期変更を再現しない。
- buildは型とbundle整合性を確認するが、browser操作、視覚品質、自動E2E testは確認していない。
- 課題は外部の既存benchmark由来だが、選択、実行、採点、監査はRefineTale作者側であり第三者評価ではない。
- 6課題、各条件3run、単一model familyの結果を、他のrepository、backend機能、長期保守性、実運用へ一般化しない。

## Artifacts

- `manifest.json`: model、seed、skill/task/repository commit
- `execution-order.json`: 固定seedによる実行順
- `raw/`: 36runのJSONL、最終回答、diff、build結果、metadata
- `review/`: 匿名packet、mapping、2組のjudge出力
- `scores.csv`: 復号後の全得点、LOC、build、trace
- `metrics.json`: 条件別・課題別集計と補助統計
- `reviewer-notes.md`: 不一致と低得点の手動監査
- `rule-retention.md`: `SKILL.md`の2規則を維持した判断
- `environment.md`: 実行環境と時刻
