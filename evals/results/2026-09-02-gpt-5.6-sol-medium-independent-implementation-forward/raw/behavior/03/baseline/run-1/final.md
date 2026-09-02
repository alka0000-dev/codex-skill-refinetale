`Ledger.apply_batch(entries)` を [ledger.py](<EVAL_WORKSPACE>/ledger.py:17) に追加しました。

- 全entryを事前検証し、不正形式は `ValueError`
- 一時残高で入力順に試算し、途中で負になる場合は `Overdraft`
- 失敗時は残高・監査ログを変更しない
- 成功時のみ既存の `apply` を入力順に呼び、戻り値のリストを返す
- 空batch、生成器、非iterable入力も確認済み

検証結果:

```text
Ran 4 tests in 0.000s

OK
```

構文検査と `git diff --check` も成功しています。
