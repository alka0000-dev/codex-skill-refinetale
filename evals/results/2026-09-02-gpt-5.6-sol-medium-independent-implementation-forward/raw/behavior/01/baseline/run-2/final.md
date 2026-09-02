タイムアウト設定を追加しました。

- `Client(transport, timeout=None)` に対応
- 優先順位: リクエスト指定 → Client指定 → `5.0`
- 正の有限な `int` / `float` のみ許可し、`bool` や無効値は `ValueError`
- transportへ `send(path, timeout=resolved_timeout)` で渡す
- 既存APIとの互換性を維持

変更: [client.py](<EVAL_WORKSPACE>/client.py)

検証結果:

```text
Ran 4 tests in 0.000s

OK
```

構文検査と `git diff --check` も成功しています。
