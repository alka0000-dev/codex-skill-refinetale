実装完了です。

変更:

- [delivery.py](<EVAL_WORKSPACE>/delivery.py:9)
  - `deliver(sender, message, max_attempts=3)` を追加
  - `TemporaryFailure` のみ同じ sender で再試行
  - 成功時は即時返却
  - その他の例外は即時送出
  - bool以外の正のintだけを受理し、送信前に検証

検証結果:

- 一時失敗後の成功: 2回で停止
- 試行回数超過: 最後の `TemporaryFailure` を送出
- `PermanentFailure`／その他例外: 1回で送出
- 無効な `max_attempts`: sender呼び出し0回で `ValueError`
- 既存の成功経路: 戻り値と1回送信を維持

```text
python3 -m unittest discover -s tests
Ran 5 tests in 0.000s
OK
```

`py_compile` と `git diff --check` も成功しています。
