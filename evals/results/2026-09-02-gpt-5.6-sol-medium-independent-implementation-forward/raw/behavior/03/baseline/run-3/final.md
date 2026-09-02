`Ledger.apply_batch(entries)` を追加しました。

- 全entryを事前検証し、不正形式は `ValueError`
- 入力順で途中残高を計算し、負残高は `Overdraft`
- 検証失敗時は残高・監査ログを変更しない
- 成功時は既存の `apply` 経由で反映し、戻り値をリスト化

変更: [ledger.py](<EVAL_WORKSPACE>/ledger.py:18)

検証結果:

```text
Ran 4 tests in 0.000s
OK
```

構文コンパイルと `git diff --check` も成功しています。
