# RefineTale evaluations

このディレクトリには、RefineTaleの公開repository大きめ機能評価、実装型forward holdout、応答レベル回帰評価、ルーティング評価を収録しています。同一の依頼に対するbaselineとskill明示条件を比較し、要求、既存契約、安全境界を維持しながら、状態、分岐、内部表現、責務の重複や推測による先行実装を減らせるかを確認します。

ルートの[README.md](../README.md)は利用者向けの概要です。評価条件、判定基準、課題別結果、匿名採点、統計上の制約、再現手順、生データはこのディレクトリを正本とします。

評価対象は、回答の行数や特定の言い回しではなく、観察可能な振る舞いです。現在revision用に公開repositoryのUI機能6件と実装型forward holdout 8件、回帰用に5件の振る舞い評価と1件のルーティング評価を定義しています。前revisionの独立holdout 6件も履歴として保持しています。ケースの定義だけでは、効果を実行済みまたは検証済みとは扱いません。

## 公開済み結果

### 公開repositoryの大きめ機能評価（現在revision）

`fastapi/full-stack-fastapi-template`の固定commitへ、Ponytailの公開benchmarkにあるフロントエンド6課題を変更せず使用し、revision `873001e`、`gpt-5.6-sol`、推論強度`medium`で各条件3回実装した。

| Metric | Baseline | RefineTale | Difference |
| --- | ---: | ---: | ---: |
| Correctness gate | 18/18（100%） | 18/18（100%） | 0ポイント |
| Frontend build | 18/18（100%） | 18/18（100%） | 0ポイント |
| Judge points | 189/216（87.5%） | 213/216（98.6%） | +11.1ポイント |
| Added source LOC | 4,118 | 1,777 | -56.9% |
| Critical failures | 0 | 0 | 0 |
| Target skill trace | 0/18 | 18/18 | +18 |

課題別LOC中央値の削減率は単純平均44.9%だった。2回のblind judgeはcriterion vectorが18/36候補で完全一致し、critical判定は36/36一致、手動補正は0件だった。詳細と全証拠は[`results/2026-09-02-gpt-5.6-sol-medium-public-repository-large-feature/summary.md`](results/2026-09-02-gpt-5.6-sol-medium-public-repository-large-feature/summary.md)、再現手順は[`large-feature/README.md`](large-feature/README.md)を参照する。

この評価は実装量とscope disciplineの記述的改善を確認した。一方で平均実行時間とoutput tokenは増加し、browser操作、長期保守性、統計的優位性は確認していない。

### 独立実装型forward holdout（現在revision）

既存fixture、過去結果、skill本文、直前に追加した規則を見ない隔離sessionが作成・固定した8件の小規模Python repositoryを、revision `873001e`、`gpt-5.6-sol`、推論強度`medium`で各条件3回実行しました。48runすべてで実際にコードを編集し、候補によるテスト変更を戻して固定検証しています。

| Metric | Baseline | RefineTale | Difference |
| --- | ---: | ---: | ---: |
| Rubric pass | 24/24（100%） | 24/24（100%） | 0ポイント |
| Fixed verification | 24/24（100%） | 24/24（100%） | 0ポイント |
| Points | 237/240（98.8%） | 238/240（99.2%） | +0.4ポイント |
| Critical failures | 0 | 0 | 0 |
| Skill body trace | 0/24 | 22/24 | +22 |

2回のblind judgeは45/48候補で完全一致し、critical判定は48/48一致しました。詳細は[`results/2026-09-02-gpt-5.6-sol-medium-independent-implementation-forward/summary.md`](results/2026-09-02-gpt-5.6-sol-medium-independent-implementation-forward/summary.md)、作成protocolと再現手順は[`forward-holdout/README.md`](forward-holdout/README.md)を参照してください。両条件が天井に達しており、実装成功率またはPass率の改善と統計的優位性は確認されていません。

### 応答レベル回帰評価（現在revision）

前revisionの独立holdout 6件を、既知の失敗に基づく2規則を追加したrevision `873001e`で各条件3回再実行しました。

| Metric | Baseline | RefineTale | Difference |
| --- | ---: | ---: | ---: |
| Pass | 15/18（83.3%） | 17/18（94.4%） | +11.1ポイント |
| Points | 165/180（91.7%） | 177/180（98.3%） | +6.7ポイント |
| Critical failures | 1 | 1 | 0 |
| Skill body trace | 0/18 | 15/18 | +15 |

詳細は[`results/2026-09-02-gpt-5.6-sol-medium-holdout-regression-v2/summary.md`](results/2026-09-02-gpt-5.6-sol-medium-holdout-regression-v2/summary.md)を参照してください。同じholdoutを見てskillを更新した後の結果であり、現在revisionに対する独立評価ではありません。

### 履歴

前revision `ecc498c`の独立holdoutはbaseline 17/18、RefineTale 18/18で、[`results/2026-09-02-gpt-5.6-sol-medium-independent-holdout/summary.md`](results/2026-09-02-gpt-5.6-sol-medium-independent-holdout/summary.md)に保持しています。さらに前の回帰結果は[`results/2026-09-02-gpt-5.6-sol-medium-evidence-contract/summary.md`](results/2026-09-02-gpt-5.6-sol-medium-evidence-contract/summary.md)、初回結果は[`results/2026-09-02-gpt-5.6-sol-medium/summary.md`](results/2026-09-02-gpt-5.6-sol-medium/summary.md)を参照してください。

公開repository評価とforward holdoutはいずれも各条件3runの小標本で、回答生成と採点は単一model family、実行と監査は作者側です。第三者検証や未知repository全体への一般化を意味しません。

## 比較条件

- baselineとskill明示時で、同じモデルID、推論強度、プロジェクト指示を使用する。
- 各runは新しいタスクまたは隔離した一時ワークスペースで実行する。
- baselineではRefineTaleを使用しない。
- skill明示時は、入力の先頭で `$refinetale` を明示する。
- 2条件間で変更する要素は、RefineTaleの適用有無だけにする。
- ばらつきを測る場合は、各条件を3回以上実行する。
- 実行時は各fixtureの `## Input` の内容だけを依頼として送る。
- 実行日、モデルID、推論強度、RefineTaleのrevisionを記録する。

## 実行手順

1. 対象fixtureを選ぶ。
2. baseline条件で `## Input` を実行し、応答、差分、検証結果を保存する。
3. 同じ入力をskill明示条件で実行し、同じ情報を保存する。
4. 共通rubricとfixture固有の合格条件を採点する。
5. 結果を `results-template.md` の複製へ記録する。
6. 失敗した項目は、単なる文体差ではなく、観察可能な失敗として分類する。

## 自動実行

公開repository評価の実行、build、二重匿名採点、集計は[`large-feature/README.md`](large-feature/README.md)、実装型forward holdoutは[`forward-holdout/README.md`](forward-holdout/README.md)にまとめています。以下は応答レベル評価の手順です。

収録runnerは、baselineとRefineTale条件を隔離し、実行順を固定seedでシャッフルしてJSONL、生の最終回答、stderr、metadataを保存します。

```text
python3 evals/scripts/run-evals.py \
  --model gpt-5.6-sol \
  --effort medium \
  --runs 3 \
  --jobs 3 \
  --seed 20260902 \
  --result-dir evals/results/<run-name>
```

匿名採点packetは次で生成します。

```text
python3 evals/scripts/prepare-blind-review.py \
  --result-dir evals/results/<run-name> \
  --seed 20260902
```

採点後、次のコマンドで条件を復元し、`scores.csv`、`metrics.json`、`routing.json`を生成します。

```text
python3 evals/scripts/aggregate-results.py \
  --result-dir evals/results/<run-name>
```

GitHubへ公開する前に、ローカルの絶対パスを置換します。

```text
python3 evals/scripts/sanitize-results.py \
  --result-dir evals/results/<run-name>
```

## 共通rubric

各項目を `1`（満たす）、`0`（満たさない）、`N/A`（対象外）で採点します。

| ID | 観点 | 合格条件 |
| --- | --- | --- |
| G1 | Contract fidelity | 依頼で指定された外部契約、入力、出力、エラー、イベント名を維持する。 |
| G2 | Change contract | 変更対象、変更禁止対象、許容差分を回答内で明確に扱う。 |
| G3 | Canonical ownership | 同じ意味を持つ状態や判断の正本を1か所に置く。 |
| G4 | Variation isolation | 本当に異なる差分だけを境界へ隔離し、共通処理を重複させない。 |
| G5 | No speculative implementation | 現在の要求にない将来拡張、fallback、flag、抽象化を追加しない。 |
| G6 | Safety preservation | 認可、検証、監査、失敗時の扱いなど既存の安全境界を弱めない。 |
| G7 | Verification and stop | 必要な検証を示し、既に十分単純なら変更しない判断をする。 |

G1は常にcriticalです。安全境界を含むfixtureではG6もcriticalです。合格には、すべての適用可能な共通項目とfixture固有の条件を満たす必要があります。

## Fixture固有の判定

各fixtureの `## Pass conditions` は、共通rubricだけでは識別しにくい失敗を補います。採点時は、次の証拠を優先してください。

- 提案または実装された差分
- 追加・更新されたテスト
- 実行された検証とその結果
- 変更しなかった対象の明示
- 安全境界や外部契約が維持されたこと

## 比較と失敗シグネチャ

skillの効果は、単独の合否だけでなくbaselineとの差で確認します。とくに次の失敗数を比較します。

- 契約の欠落
- 安全境界の削除または順序変更
- 同じ意味を持つ状態の二重管理
- 同じ差分の複数層への伝播
- 要求にない先行実装
- 既に単純な対象への不要な変更
- 実装詳細に密結合した過剰または重複したテスト

## ルーティング評価

`06-routing-boundaries.md` は振る舞い評価と分けて実行します。入力に `$refinetale` を含めず、Codexのtraceでskillの呼び出し有無を確認してください。呼び出すべき入力と呼び出すべきでない入力は、必ず別タスクで実行します。

## 収録fixture

- `fixtures/01-normalize-at-boundary.md`
- `fixtures/02-single-source-of-truth.md`
- `fixtures/03-isolate-real-variation.md`
- `fixtures/04-preserve-safety-boundaries.md`
- `fixtures/05-stop-when-already-minimal.md`
- `fixtures/06-routing-boundaries.md`

現在revisionの公開repository課題は`large-feature/tasks.json`に6件、実装型forward holdoutは`forward-holdout/fixtures/`に8件収録しています。前revision用の独立holdoutは`holdout/fixtures/`に6件保持しており、現在は回帰用途です。応答レベル回帰として実行する場合は、通常fixtureと混ぜず`--fixture-dir evals/holdout/fixtures --skip-routing`を指定します。
