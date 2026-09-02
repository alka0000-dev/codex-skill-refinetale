# RefineTale independent holdout

このディレクトリには、既存の回帰fixtureとその失敗分析を見ずに作成した6件のholdout課題を収録しています。課題作成後はRefineTale本体を変更せず、baselineと`$refinetale`明示条件を同じ入力・モデル・推論強度・read-only workspaceで比較します。

独立性の作成手順と限界は[`authoring-protocol.md`](authoring-protocol.md)を参照してください。

## 評価対象

- 冪等性を伴う限定POST retry
- 複製画面のフォーム再利用
- 新しい取引file形式の安全な取り込み
- CLI設定優先順位の共通化
- tenant分離を維持したNDJSON export
- bounded labelを保つduration histogram

各fixtureは固有のS1〜S5を0〜2点で採点します。8〜10点かつ0点なしをPass、6〜7点または0点を含む8点以上をBorderline、0〜5点をFailとし、critical failure条件を最優先します。

## 実行

```text
python3 evals/scripts/run-evals.py \
  --model gpt-5.6-sol \
  --effort medium \
  --runs 3 \
  --jobs 3 \
  --seed 2026090202 \
  --fixture-dir evals/holdout/fixtures \
  --skip-routing \
  --result-dir evals/results/<holdout-run-name>
```

```text
python3 evals/holdout/scripts/prepare-holdout-review.py \
  --result-dir evals/results/<holdout-run-name> \
  --fixture-dir evals/holdout/fixtures \
  --seed 2026090202

python3 evals/holdout/scripts/run-holdout-judges.py \
  --result-dir evals/results/<holdout-run-name> \
  --model gpt-5.6-sol \
  --effort medium \
  --jobs 3

python3 evals/holdout/scripts/aggregate-holdout-results.py \
  --result-dir evals/results/<holdout-run-name>
```

結果公開前に既存の`evals/scripts/sanitize-results.py`でlocal pathと外部skill出力を除去します。

## 現在の結果

2026-09-02の結果は[`../results/2026-09-02-gpt-5.6-sol-medium-independent-holdout/summary.md`](../results/2026-09-02-gpt-5.6-sol-medium-independent-holdout/summary.md)にあります。baseline 17/18に対してRefineTale 18/18、得点は169/180に対して171/180でした。差は小さく、統計的優位性を示す結果ではありません。
