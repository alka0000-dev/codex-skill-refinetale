実装完了しました。

変更内容:

- [client.py](<EVAL_WORKSPACE>/client.py)
  - `Client.request(path, timeout=None)` を追加
  - 優先順位をリクエスト指定 → Client指定 → `5.0` で解決
  - 正の有限な `int` / `float` のみ許可し、`bool` 等は `ValueError`
  - 無効値ではtransportを呼び出さず、フォールバックもしない
  - `transport.send(path, timeout=resolved_timeout)` で転送
  - 既存の呼び出し方と戻り値を維持

検証結果:

- リクエスト値・Client値・既定値: 成功
- 無効なリクエスト値の拒否と送信抑止: 成功
- 無効なClient値の拒否: 成功
- path、戻り値、既存API互換: 成功
- 構文検査: 成功
- Ruff: 未導入、lint設定なし
- 指定コマンド: **4テストすべて成功**

```text
Ran 4 tests in 0.000s

OK
```
