`Ledger.apply_batch(entries)` を実装しました。

- 全entryを事前検証し、不正形式は `ValueError`
- 入力順で仮計算し、途中で負残高なら `Overdraft`
- 失敗時は残高・監査ログを完全復元
- 成功時は既存の `self.apply` 経路で反映し、戻り値をリスト化
- `bool` はdeltaとして拒否

変更ファイル: [ledger.py](<EVAL_WORKSPACE>/ledger.py)

検証結果:

```text
Ran 4 tests in 0.000s
OK
```

`python3 -m py_compile` と `git diff --check` も成功しています。
