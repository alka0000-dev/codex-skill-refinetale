タイムアウト指定を追加しました。

- [client.py](<EVAL_WORKSPACE>/client.py:7)
  - 優先順位: リクエスト指定 → Client指定 → `5.0`
  - 正の有限な `int` / `float` のみ許可（`bool` は拒否）
  - 無効な明示値は transport 呼び出し前に `ValueError`
  - `send(path, timeout=resolved_timeout)` で送信

- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:15)
  - 優先順位と既定値
  - `None` の未指定扱い
  - 数値境界・非数値・`bool` の拒否
  - 無効時にフォールバック・送信しないこと
  - 既存呼び出しの互換性

検証結果:

```text
python3 -m unittest discover -s tests
Ran 4 tests
OK
```

`git diff --check` も成功しています。プロジェクトには個別のビルド・lint設定はありません。
