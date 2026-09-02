# RefineTale

> 必要なものだけを、既存の設計に沿って実装するためのCodex skill。

RefineTaleは、機能追加や修正が必要以上に大きくなるのを防ぎ、要件・既存契約・安全性を守った一貫した実装へ導きます。

単にコードを短くするskillではありません。既存の仕組みで解決できることは再利用し、本当に異なる部分だけを追加します。必要な構造整理や検証は残しながら、将来のためだけの型、設定、fallback、互換経路などを増やしません。

## こんなときに

- 大きめの機能を頼むと、依頼していない機能や設定まで実装されてしまう
- 同じ意味の状態や変数が増え、どれが正しい値なのか分かりにくくなる
- 既存機能と新機能で、ほぼ同じ処理が別々に作られてしまう
- 一時対応や将来対応のコードが、そのまま残り続けてしまう
- 実装を小さくしたいが、認証・入力検証・互換性までは削ってほしくない

## RefineTaleがすること

| 見るポイント | RefineTaleの動き |
| --- | --- |
| 変更範囲 | 変更する挙動と、変えてはいけない挙動を分ける |
| 既存設計 | 既存コード、標準機能、導入済みの仕組みから再利用できるものを探す |
| 状態とデータ | 同じ意味の値や処理経路を一つの正本へまとめる |
| 分岐 | 利用者から見て本当に挙動が異なる場所だけに置く |
| 安全性 | 認証、検証、データ保護、互換性、アクセシビリティを維持する |
| 停止条件 | 要件と必要な検証を満たしたら、隣接機能を作らず終了する |

RefineTaleは、次の整理をしてから実装を進めます。

```text
変更する挙動 ─┬─ 既存の仕組みで共通化できる部分
変更しない挙動 ┘
                 └─ 本当に異なる最小部分だけを実装
```

## インストール

Codexで `$skill-installer` に次のGitHubリポジトリURLを指定して、RefineTaleをインストールします。

```text
$skill-installer install https://github.com/alka0000-dev/codex-skill-refinetale
```

インストール後にskillが表示されない場合は、Codexを再起動します。

## 使い方

機能追加や修正の依頼で、プロンプトの先頭に`$refinetale`を付けます。

```text
$refinetale この機能を、既存の挙動を維持しながら実装してください。
```

過剰実装がないか確認するレビューにも使えます。

```text
$refinetale この差分に、不要な分岐、重複した状態、先行実装がないかレビューしてください。
```

実装方法を細かく指定しなくても、RefineTaleが既存コードと要件を確認し、共通部分と実際の差分を整理します。具体的な方式や完成形が決まっている場合は、その希望も一緒に伝えてください。

## 検証した効果

2026-09-02に、実在する公開リポジトリへ6種類のフロントエンド機能を追加する比較評価を行いました。RefineTaleなし・ありをそれぞれ3回、合計36回実装しています。

どちらも全18回でビルドと完成条件を満たしたうえで、RefineTaleは追加された実装コードを56.9%減らしました。

```text
追加された実装コード（合計）

RefineTaleなし  ████████████████████  4,118行
RefineTaleあり  █████████               1,777行
```

| 確認項目 | RefineTaleなし | RefineTaleあり |
| --- | ---: | ---: |
| ビルド・完成条件を満たした実装 | 18/18 | 18/18 |
| 追加された実装コード | 4,118行 | 1,777行 |
| 完成度・既存設計との一貫性・実装範囲の評価 | 87.5% | 98.6% |
| 重大な失敗 | 0件 | 0件 |

特に、date picker、file dropzone、multi-step formの実装で、依頼されていないAPI、独自の状態管理、追加画面などを抑える差が確認できました。

一方で、RefineTaleありの実行は平均時間が26.9%、生成した回答のtoken数が31.1%増えています。短い応答を得るためではなく、変更後に保守するコードと知識を減らすためのskillです。

この結果は、収録した6課題と同じ系列のモデルによる比較です。すべての言語・リポジトリ・機能で同じ効果を保証するものではありません。

### 評価の詳細

評価方法、課題別の結果、すべての実装差分、ビルド結果、匿名採点、統計上の制約、生データは`evals/`を正本として公開しています。

- [評価全体の案内](evals/README.md)
- [公開リポジトリを使った大きめ機能評価](evals/results/2026-09-02-gpt-5.6-sol-medium-public-repository-large-feature/summary.md)
- [評価の再現手順](evals/large-feature/README.md)
- [集計値](evals/results/2026-09-02-gpt-5.6-sol-medium-public-repository-large-feature/metrics.json)
- [全候補の採点結果](evals/results/2026-09-02-gpt-5.6-sol-medium-public-repository-large-feature/scores.csv)
- [追加した2規則を維持した判断](evals/results/2026-09-02-gpt-5.6-sol-medium-public-repository-large-feature/rule-retention.md)

安全境界や既存契約を維持できるかは、[独立実装型forward holdout](evals/results/2026-09-02-gpt-5.6-sol-medium-independent-implementation-forward/summary.md)と[応答レベル回帰評価](evals/results/2026-09-02-gpt-5.6-sol-medium-holdout-regression-v2/summary.md)でも確認しています。

## 詳しい動作ルール

実装時にCodexが読むルールの正本は[`SKILL.md`](SKILL.md)です。READMEには利用者向けの概要だけを記載し、実行規則は重複させていません。

## 対象外

RefineTaleは、一般的な技術説明、コードを扱わない文章作成、脆弱性の発見を目的としたセキュリティ監査には使用しません。

セキュリティに関係する通常の実装では、安全上必要な境界を維持するために利用できます。

## License

This skill is licensed under the MIT License.

Copyright (c) 2026 Shirafuji Anna
