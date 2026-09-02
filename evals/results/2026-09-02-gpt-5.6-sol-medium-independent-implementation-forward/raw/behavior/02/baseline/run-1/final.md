実装完了しました。

変更内容:

- [delivery.py](<EVAL_WORKSPACE>/delivery.py)
  - `deliver(sender, message, max_attempts=3)` を追加
  - `TemporaryFailure` のみ最大回数まで再試行
  - その他の例外は即時送出
  - `max_attempts` を送信前に検証
  - 既存の成功時の挙動を維持

検証結果:

```text
Ran 5 tests
OK
```

`git diff --check` も問題ありません。
