在庫移動を [inventory.py](<EVAL_WORKSPACE>/inventory.py:17) に実装しました。

- 入力値を変更前に検証
- 同一倉庫は無変更・監査ログなし
- 在庫不足時は両倉庫とも無変更
- 成功時は source→destination の順で既存 `adjust` を使用
- 成功時は両倉庫の新在庫数を返却

検証結果:

```text
Ran 5 tests in 0.000s
OK
```

`py_compile` と `git diff --check` も成功しています。
