# Implementation forward holdout

このholdoutは、RefineTale revision `873001e`を、既存fixtureと過去の失点を見ない隔離sessionが作成した8件の小規模repositoryで評価する。

従来の応答レベル評価と異なり、各runでCodexが隔離されたrepositoryを実際に編集する。採点には次を使用する。

- 初期repository
- 最終diff
- fixture固有の検証コマンドと終了結果
- 最終回答
- fixture固有のS1〜S5 rubric

テストと`verify.json`は候補による変更前の状態へ戻してから検証し、テスト改変による見かけ上の成功を防ぐ。候補がテストを変更した場合、その変更自体は最終diffへ残して匿名採点の対象にする。

## 公開済み結果

`gpt-5.6-sol`、推論強度`medium`で各条件3回実行した結果、固定検証と匿名rubric Passはbaseline、RefineTaleとも24/24、critical failureは双方0件だった。得点は237/240対238/240で、RefineTaleの差は+1点だった。2回のblind judgeは45/48候補で完全一致し、critical判定は48/48一致した。

両条件が天井に達しており、実装成功率またはPass率の改善と統計的優位性は確認されていない。全run、diff、検証、採点、手動監査、制約は[`../results/2026-09-02-gpt-5.6-sol-medium-independent-implementation-forward/summary.md`](../results/2026-09-02-gpt-5.6-sol-medium-independent-implementation-forward/summary.md)を参照する。

## Fixture

各fixtureは次の構造を持つ。

```text
NN-short-name/
├── prompt.md
├── rubric.md
├── verify.json
└── workspace/
    ├── <implementation>.py
    └── tests/
        ├── test_existing.py
        └── test_requirements.py
```

8件の論点、使用ランタイム、初期検証は[`authoring-notes.md`](authoring-notes.md)、作成時の分離方法は[`authoring-protocol.md`](authoring-protocol.md)を参照する。

## 実行

最初にfixtureの構造と初期状態を確認する。

```text
python3 evals/forward-holdout/scripts/validate-forward-fixtures.py
```

baselineとRefineTale条件を各fixture 3回実行する。

```text
python3 evals/forward-holdout/scripts/run-forward-evals.py \
  --model gpt-5.6-sol \
  --effort medium \
  --runs 3 \
  --jobs 3 \
  --seed 20260902 \
  --result-dir evals/results/<run-name>
```

匿名採点packetを作成し、judgeを実行する。

```text
python3 evals/forward-holdout/scripts/prepare-forward-review.py \
  --result-dir evals/results/<run-name> \
  --seed 20260902

python3 evals/forward-holdout/scripts/run-forward-judges.py \
  --result-dir evals/results/<run-name> \
  --model gpt-5.6-sol \
  --effort medium \
  --judge-runs 2 \
  --jobs 4

python3 evals/forward-holdout/scripts/compare-forward-judges.py \
  --result-dir evals/results/<run-name>
```

採点後、条件を復元して集計する。

```text
python3 evals/forward-holdout/scripts/aggregate-forward-results.py \
  --result-dir evals/results/<run-name>
```

公開前に既存のsanitize scriptでローカル絶対パスと外部skill出力を除去する。

```text
python3 evals/scripts/sanitize-results.py \
  --result-dir evals/results/<run-name>
```

## 判定

各fixtureのS1〜S5を0〜2点で採点する。8〜10点かつ0点なしをPass、6〜7点または8点以上でも0点ありをBorderline、0〜5点をFailとする。fixture固有のcritical failureを最優先する。

主要指標は次の5つを分けて報告する。

- 匿名rubricのPass率
- rubric得点率
- fixture検証コマンドの成功率
- RefineTale本文の読込trace率
- 2回のblind judgeによるcriterion別一致率

Pass率だけでは天井効果を見落とすため、実テスト成功とcriterion別の失点も併記する。
