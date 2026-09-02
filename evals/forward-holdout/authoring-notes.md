# Forward-test authoring notes

## 課題一覧

1. `01-layered-timeout`: 階層設定の優先順位、明示無効値、既存送信経路。
2. `02-selective-retry`: 例外分類、試行上限、成功・恒久失敗での早期終了。
3. `03-atomic-ledger`: 一括更新の事前検証、入力順の制約、内部状態の原子性。
4. `04-versioned-profile`: 永続化形式のversion分岐、旧形式互換、domain error境界。
5. `05-prepared-publish`: 外部副作用前の全件準備、公開順、失敗後の停止。
6. `06-event-snapshot`: 重複購読、配信snapshot、配信中の状態変更。
7. `07-mounted-router`: 完全一致との共通挙動、segment境界、最長prefix差分。
8. `08-inventory-transfer`: 2状態間の移動、不足時の不変性、自己移動の早期終了。

## 使用ランタイム

- Python 3標準ライブラリのみ。
- テストは `unittest`、検証定義の読込はJSON標準形式を使用する。
- 外部パッケージ、サービス、ネットワークは使用しない。

## 検証方法

- 各fixture直下の `verify.json` を読み、同fixtureの `workspace/` をカレントディレクトリにして `command` を実行する。
- 既存回帰だけは `python3 -m unittest tests.test_existing` で独立して確認できる。
- 新要件は `tests/test_requirements.py` に分離する。初期状態では未実装を検出して総合検証が失敗し、解答後は既存・新要件を合わせて成功することを期待する。
- rubricは全課題でS1〜S5を各0〜2点とし、最終repositoryの差分、実挙動、設計境界、検証結果を採点する。

## 独立性制約

- 開示された高レベル目的と本依頼だけから新規作成した。
- この一時workspace外のファイル、既存skill本文、既存fixture、過去の評価結果、他の会話履歴は参照していない。ウェブ検索も行っていない。
- 課題間で同じ失敗の言い換えにならないよう、設定解決、制御フロー、内部transaction、schema evolution、外部副作用、observer semantics、path matching、複数aggregate間更新に主判定軸を分散した。
- 8件すべてが新しい公開挙動の実装を必要とし、変更不要を想定した課題は含めていない。
- 近接する既存APIを無条件に流用すると安全条件を壊す箇所と、既存APIを更新境界として再利用すべき箇所の両方を含めた。正解実装はfixtureに含めていない。
