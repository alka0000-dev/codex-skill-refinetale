# RefineTale independent implementation forward holdout

## Outcome

既存fixture、過去結果、skill本文、直前に追加した規則を見ない隔離sessionが作成・固定した8件の小規模Python repositoryで、RefineTale revision `873001e`を評価した。各runではCodexが実際にrepositoryを編集し、候補によるテスト変更を戻したうえで固定済みの検証を実行した。

baselineとRefineTaleはどちらも24/24runで検証に成功し、匿名rubricでも24/24がPass、critical failureは0件だった。得点率はbaseline 98.8%、RefineTale 99.2%で、差は1点（+0.4ポイント）だった。

| Metric | Baseline | RefineTale | Difference |
| --- | ---: | ---: | ---: |
| Rubric pass | 24/24（100%） | 24/24（100%） | 0ポイント |
| Fixed verification | 24/24（100%） | 24/24（100%） | 0ポイント |
| Earned points | 237/240（98.8%） | 238/240（99.2%） | +1（+0.4ポイント） |
| Critical failures | 0 | 0 | 0 |
| Skill body trace | 0/24 | 22/24 | +22 |

この評価では両条件が天井に達しており、RefineTaleによる実装成功率またはPass率の改善は確認できなかった。少なくとも収録した8課題では非劣化だったが、一般的な優位性や統計的優位性を示す結果ではない。

## Per-fixture result

| Fixture | Baseline verification | RefineTale verification | Baseline points | RefineTale points | Observation |
| --- | ---: | ---: | ---: | ---: | --- |
| 01 Layered timeout | 3/3 | 3/3 | 29/30 | 29/30 | 両条件の各1runが、極端に大きい正のintを`math.isfinite`へ渡して`OverflowError`にするためS2=1。 |
| 02 Selective retry | 3/3 | 3/3 | 30/30 | 30/30 | 両条件とも試行上限、例外分類、早期終了を満たした。 |
| 03 Atomic ledger | 3/3 | 3/3 | 30/30 | 30/30 | 全runで入力順、原子性、既存`apply`境界を維持した。例外の優先順位だけjudge間で解釈差があった。 |
| 04 Versioned profile | 3/3 | 3/3 | 28/30 | 29/30 | baseline 2runはversion別の生成経路が共通化されずS3=1。RefineTale 1runはJSON例外をcauseに残してS4=1。 |
| 05 Prepared publish | 3/3 | 3/3 | 30/30 | 30/30 | 全件準備後の公開と失敗後の停止を両条件が満たした。 |
| 06 Event snapshot | 3/3 | 3/3 | 30/30 | 30/30 | 重複購読、開始時snapshot、配信中変更を両条件が満たした。 |
| 07 Mounted router | 3/3 | 3/3 | 30/30 | 30/30 | 完全一致優先、segment境界、最長prefixを両条件が満たした。 |
| 08 Inventory transfer | 3/3 | 3/3 | 30/30 | 30/30 | 不足時の不変性、更新順、自己移動を両条件が満たした。 |

## Blind judge agreement and manual audit

fixtureごとに候補6件をA〜Fへ匿名化し、同じmodel・推論強度のjudgeを独立contextで2回実行した。一次judgeを集計の正本とし、二次judgeを採点安定性の監査に使用した。

| Agreement | Result |
| --- | ---: |
| Candidate total and all criteria | 45/48（93.8%） |
| Critical failure | 48/48（100%） |
| S1 | 48/48（100%） |
| S2 | 45/48（93.8%） |
| S3 | 48/48（100%） |
| S4 | 48/48（100%） |
| S5 | 48/48（100%） |

3件の不一致はすべてFixture 03のS2だった。先行entryでOverdraftになり、後続entryの形式も不正なbatchについて、二次judgeは後続の不正を優先して`ValueError`にすべきと解釈した。promptとrubricは失敗時の状態不変を要求する一方、複数エラーが競合する場合の例外優先順位を指定していない。3実装はいずれも状態変更前に各entryを検証し、最初に観測した入力順のOverdraftで停止するため、一次judgeのS2=2を維持した。

全5件の一次低得点、3件のjudge不一致、全critical判定を差分、固定テスト、rubricと照合した。根拠のない採点修正はなく、[`review/manual-overrides.json`](review/manual-overrides.json)は空である。詳細は[`reviewer-notes.md`](reviewer-notes.md)に記録した。

## Statistical interpretation

- Pass率と固定検証成功率は両条件とも100%で、Wilson 95%区間はいずれも86.2%〜100%。
- Pass/非Passと検証成功/失敗の両側Fisher exact testはいずれも`p = 1.0`。
- 得点率差は+0.4ポイントだが、同一fixture内の反復runは独立した課題ではなく、点数にも天井効果がある。
- 統計的優位性は確認されていない。区間と検定は小標本かつclusterを無視した補助情報として扱う。

## Method

- モデル: `gpt-5.6-sol`
- 推論強度: `medium`
- Codex CLI: `0.152.0`
- 課題: 8件の小規模Python repository
- 各条件: 3run
- 実装run: 48件
- 実行順: seed `20260902`でランダム化
- workspace: 条件・runごとに隔離した一時Git repository
- sandbox: `workspace-write`
- RefineTale SHA-256: `873001ea53f54e4e924b7578d71bd721b3e5cf6cce6736a41209ca077874c7bf`
- 固定fixture tree SHA-256: `a00cd15317c412c1991aa8f7ffd95a1f69c6b84950560cf8434aae767d00afa7`
- インフラ失敗: 0/48
- judge: 同じモデル・推論強度、fixtureごとに2回、合計16回

baselineからRefineTaleを発見できない状態にし、RefineTale条件だけにskillを配置して`$refinetale`を明示した。候補が変更したテストはdiffへ残したが、検証時にはfixture固定時のテストへ戻した。RefineTale条件の2/24run（Fixture 07 run 2、Fixture 08 run 1）はskill本文の読込traceがなかったが、差し替えずintention-to-treat集計へ含めた。

## Independence and limitations

課題作成者はプロジェクト外のephemeral sessionで作業し、skill本文、追加規則、既存fixture、既存run、採点結果、失敗分析を見ていない。fixtureをhashで固定した後は評価完了まで`SKILL.md`を変更していない。したがって、現在revisionに対する課題作成process上のforward holdoutである。

ただし、これは第三者機関による検証ではない。課題作成、回答生成、匿名採点はいずれも同じmodel familyを使う。8件はいずれもPython標準ライブラリだけの小規模repositoryで、各条件3runの小標本である。固定テストが観測しない境界欠陥も実際に残った。未知の言語、framework、大規模repository、長期保守性、実運用での効果へ一般化しない。

この結果を見てRefineTaleを変更した場合、本評価は次revisionに対して独立ではなくなり、回帰評価としてのみ扱う。

## Artifacts

- `manifest.json`: model、seed、skill/fixture hash
- `execution-order.json`: 固定seedによる実行順
- `raw/`: 48runのJSONL、最終回答、diff、検証結果、metadata
- `review/`: 匿名packet、mapping、2組のjudge出力、一致度、手動監査記録
- `scores.csv`: 復号後の全得点、固定検証、trace
- `metrics.json`: 条件別集計と補助統計
- `reviewer-notes.md`: 採点差と低得点の監査記録
- `environment.md`: 実行環境と時刻
