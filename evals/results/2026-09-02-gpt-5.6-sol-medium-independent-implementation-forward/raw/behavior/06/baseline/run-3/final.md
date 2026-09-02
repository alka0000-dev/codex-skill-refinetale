`EventBus` に購読解除を実装しました。

- `off(event, handler)` は最初の一致1件のみ解除し、成功可否を `bool` で返却
- 未知イベントでは状態を作成しない
- `emit` 開始時に購読者をコピーし、配信中の `on/off` は次回から反映
- 既存の `on/emit` の戻り値と例外伝播を維持

変更: [event_bus.py](<EVAL_WORKSPACE>/event_bus.py)

検証結果:

```text
Ran 5 tests in 0.000s

OK
```

`git diff --check` も成功しています。
