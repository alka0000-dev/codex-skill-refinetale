実装完了しました。

変更:

- [inventory.py](<EVAL_WORKSPACE>/inventory.py:18) に `Inventory.transfer_to` を追加
- 入力不正: `ValueError`、両倉庫無変更
- 同一倉庫: 在庫・監査ログ無変更で現在数を返却
- 在庫不足: `InsufficientStock`、両倉庫無変更
- 成功: source、destination の順で既存 `adjust` を呼び、更新後在庫数のタプルを返却
- [.agent/CONTINUITY.md](<EVAL_WORKSPACE>/.agent/CONTINUITY.md) に判断・検証結果を記録

検証結果:

- `python3 -m unittest discover -s tests`
  - 5件すべて成功
- 追加境界検証
  - 非文字列SKU、bool・ゼロ・負数・非整数quantityを拒否
  - 同一倉庫、不足時の状態・既存監査ログを維持
  - source → destination の `adjust` 呼び出し順を確認
- `py_compile`、`git diff --check` 成功
- 既存 `adjust` のテストも成功し、既存契約を維持しています。
