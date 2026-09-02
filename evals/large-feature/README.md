# Public-repository large-feature benchmark

RefineTaleが大きめの機能開発で過剰実装を抑えるかを、実際の公開repositoryへの実装差分で比較する評価です。

## 公開済み結果

2026-09-02の36runでは、baselineとRefineTaleの両方が18/18でfrontend buildとcorrectness gateを通過しました。追加source LOCは4,118から1,777へ56.9%減り、匿名judge得点率は87.5%から98.6%へ上がりました。全証拠、監査、制約は[`../results/2026-09-02-gpt-5.6-sol-medium-public-repository-large-feature/summary.md`](../results/2026-09-02-gpt-5.6-sol-medium-public-repository-large-feature/summary.md)を参照してください。

## 対象

- repository: `fastapi/full-stack-fastapi-template`
- commit: `cd83fc10ca20393e9ee50e3005e170c6929e047e`
- license: MIT
- 課題: Ponytailのagentic benchmarkで公開されているフロントエンド6課題

課題文は[`tasks.json`](tasks.json)に固定しています。RefineTale向けに書き換えず、上流の一文をそのまま使用します。

## 比較条件

- `baseline`: RefineTaleをrepositoryへ配置せず、課題文だけを渡す
- `refinetale`: 同じrepositoryへ評価対象の`SKILL.md`だけを配置し、repository内の相対pathを指定して全文読込を要求する

モデル、推論強度、実行上の注意、repository、依存、実行回数を揃えます。各runはfresh contextと独立した一時Git workspaceを使用します。

## 指標

変更量を比較する前に、次のcorrectness gateを通します。

1. Codex CLIが正常終了する。
2. 固定repositoryの`npm run build --workspace frontend`が成功する。
3. 匿名judgeが課題の中核を実装したと判定する。
4. critical failureがない。

過剰実装の代理指標は、Git差分に追加されたsource LOC、変更したsource file数、新規依存・lockfile変更の有無です。testは別集計とし、sourceの過剰実装へ数えません。生成済みclient、lockfile、build生成物もsource LOCから除外します。

匿名judgeは、完成度、既存・native機能の利用と責務のまとまり、依頼範囲、重複状態・経路の有無を採点します。少ないLOCだけで効果を主張せず、buildと完成度を併記します。

## 実行

Node依存を導入済みの固定template checkoutを用意します。

```text
git clone https://github.com/fastapi/full-stack-fastapi-template
git -C full-stack-fastapi-template checkout cd83fc1
npm --prefix full-stack-fastapi-template install --ignore-scripts
```

実装run、匿名packet、二重judge、集計の順に実行します。

```text
python3 scripts/run-large-feature-evals.py \
  --template-dir <full-stack-fastapi-template> \
  --result-dir <result-dir> \
  --runs 3

python3 scripts/prepare-large-feature-review.py --result-dir <result-dir>
python3 scripts/run-large-feature-judges.py --result-dir <result-dir> --judges 2
python3 scripts/aggregate-large-feature-results.py --result-dir <result-dir>
python3 ../scripts/sanitize-results.py --result-dir <result-dir>
```

ローカルに同名または名前が近いskillがある場合は、実装runとjudgeへ`--disable-skill-path <SKILL.md>`を繰り返し渡して無効化します。評価対象はrepository内へ置いたsnapshotだけです。

## 解釈上の制約

- 課題はPonytailの公開benchmarkから事前に存在したものを採用していますが、実行・採点はRefineTaleの作者側で行うため第三者評価ではありません。
- 一文の機能ticketは実務の詳細仕様を再現しません。
- buildは型とbundle整合性を確認しますが、browser上の操作性までは保証しません。
- 追加LOCは過剰実装の代理指標であり、それ自体が品質ではありません。
- 6課題×少数run×単一model familyの結果を、他のrepositoryや長期保守性へ一般化しません。
