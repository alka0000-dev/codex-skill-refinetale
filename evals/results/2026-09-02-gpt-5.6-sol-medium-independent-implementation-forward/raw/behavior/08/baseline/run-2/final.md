`Inventory.transfer_to` を [inventory.py](<EVAL_WORKSPACE>/inventory.py:18) に追加しました。

- 入力値を状態変更前に検証
- 同一倉庫は在庫・監査ログを変更せず現在庫を返却
- 在庫不足時の原子性を維持
- 成功時は source → destination の順に既存 `adjust` を使用
- 成功時は両倉庫の新在庫数を返却

検証結果:

- `python3 -m unittest discover -s tests`: 5件成功
- `py_compile`: 成功
- `git diff --check`: 成功
