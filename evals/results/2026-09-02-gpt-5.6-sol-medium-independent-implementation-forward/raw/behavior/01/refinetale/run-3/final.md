実装しました。

変更内容:

- [client.py](<EVAL_WORKSPACE>/client.py)
  - `Client(transport, timeout=None)` を追加
  - `Client.request(path, timeout=None)` を追加
  - 優先順位を request → Client → `5.0` で解決
  - 正の有限な `int` / `float` のみ許可し、`bool`・非数値・0以下・NaN・無限値は `ValueError`
  - 検証後に `transport.send(path, timeout=...)` を実行
  - 無効値では transport を呼び出さない

- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py)
  - 明示的な `None` のフォールバックを検証
  - 数値型以外の拒否を検証

検証結果:

```text
python3 -m unittest discover -s tests

Ran 4 tests in 0.000s
OK
```

優先順位、有効値、無効値の早期拒否、path・timeout の送信、既存 API の互換性をそれぞれテストで確認済みです。
