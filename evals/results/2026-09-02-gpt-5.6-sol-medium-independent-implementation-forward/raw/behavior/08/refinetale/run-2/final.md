在庫移動を実装しました。

- [inventory.py](<EVAL_WORKSPACE>/inventory.py:18)
  - destination・sku・quantityを副作用前に検証
  - 同一倉庫は在庫・監査ログを変更せず現在値を返却
  - 不足時は既存 `adjust` の `InsufficientStock` により両倉庫を変更しない
  - 成功時は source、destination の順で既存 `adjust` を実行し、新在庫の組を返却
- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:26)
  - 非str・空sku、非正数・非int・bool quantity、不正destinationについて、両倉庫が変更されないことを検証

検証結果:

- `python3 -m compileall -q inventory.py tests`: 成功
- `python3 -m unittest discover -s tests`: **5 tests、すべて成功**
- `git diff --check`: 成功
- 既存 `adjust` の契約と監査ログ形式は未変更です。
