在庫移動を実装しました。

- [inventory.py](<EVAL_WORKSPACE>/inventory.py:18)
  - destination・SKU・quantity を副作用前に検証
  - 同一倉庫は在庫数を返して無変更
  - 在庫不足は両倉庫・監査ログとも無変更
  - 成功時は source、destination の順で既存 `adjust` を使用
- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:26)
  - 非文字列SKU、負数quantity、destination側の不変条件を追加検証

検証結果:

- `python3 -m unittest discover -s tests`: 全5テスト成功
- 構文コンパイル: 成功
- `git diff --check`: 成功

入力不正、同一倉庫、在庫不足、成功時の戻り値・更新順序・監査ログ、既存 `adjust` 契約をそれぞれ確認済みです。
