配信処理に選択的な再試行を追加しました。

- [`delivery.py`](<EVAL_WORKSPACE>/delivery.py:9)
  - `deliver(sender, message, max_attempts=3)` を提供
  - `TemporaryFailure` のみ最大回数まで再試行
  - 成功時は即座に結果を返却
  - その他の例外は即時送出
  - boolを除く正のint以外は、送信前に `ValueError`

検証結果:

```text
Ran 5 tests in 0.000s
OK
```

`py_compile` と `git diff --check` も成功しています。継続記録は [`.agent/CONTINUITY.md`](<EVAL_WORKSPACE>/.agent/CONTINUITY.md) に作成しました。
