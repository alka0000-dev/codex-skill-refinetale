実装しました。

変更内容:

- `Client(transport, timeout=None)` を追加
- `request(path, timeout=None)` を追加
- 優先順位: リクエスト指定 → Client指定 → `5.0`
- 正の有限な `int` / `float` のみ許可し、`bool` や無効値は `ValueError`
- transportへ `send(path, timeout=resolved_timeout)` として伝達
- 既存の呼び出し方との互換性を維持

変更ファイル: [client.py](<EVAL_WORKSPACE>/client.py)

検証結果:

```text
python3 -m unittest discover -s tests

Ran 4 tests in 0.000s
OK
```

構文検査も成功しています。
