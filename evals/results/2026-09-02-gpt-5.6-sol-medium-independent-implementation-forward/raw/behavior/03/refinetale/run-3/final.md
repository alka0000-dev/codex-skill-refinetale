`Ledger.apply_batch(entries)` を実装しました。[ledger.py](<EVAL_WORKSPACE>/ledger.py:17)

- 不正entry → `ValueError`、状態・監査ログ変更なし
- 途中残高が負 → `Overdraft`、状態・監査ログ変更なし
- 同一accountを含め入力順に仮残高を検証
- 成功時のみ既存 `apply` 経路で順番に反映
- 空batchは `[]`
- 既存 `apply` の契約を維持

検証結果:

- 指定コマンド: `python3 -m unittest discover -s tests`
- 4テストすべて成功
- 既存apply、成功順序、不正entryの原子性、途中当座貸越の原子性を確認
- 追加境界確認、`py_compile`、`git diff --check` も成功しました。
