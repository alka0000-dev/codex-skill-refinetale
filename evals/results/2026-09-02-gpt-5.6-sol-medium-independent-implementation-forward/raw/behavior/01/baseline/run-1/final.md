タイムアウト設定を [client.py](<EVAL_WORKSPACE>/client.py) に追加しました。

- 優先順位: リクエスト指定 → Client指定 → `5.0`
- 正の有限な `int` / `float` のみ許可（`bool` は拒否）
- 無効な明示値は `ValueError`
- transportへ `send(path, timeout=resolved_timeout)` として送信
- 既存APIとの互換性を維持

検証結果:

```text
Ran 4 tests in 0.000s

OK
```

構文チェックと `git diff --check` も成功しています。
