実装完了しました。

- [delivery.py](<EVAL_WORKSPACE>/delivery.py:9) に `max_attempts=3` を追加
- `TemporaryFailure` のみ上限まで再試行
- 成功時は即時返却
- その他の例外は即時送出
- `bool` を除く正の `int` を送信前に検証
- 既存の2引数呼び出しを維持

検証結果:

```text
Ran 5 tests in 0.000s

OK
```

構文検証と `git diff --check` も成功しています。
