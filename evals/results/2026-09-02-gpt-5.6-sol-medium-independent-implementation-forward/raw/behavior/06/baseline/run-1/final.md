`EventBus` の購読解除と配信中の変更契約を実装しました。

- `off(event, handler)` は最初の一致のみ解除し、成功可否を `bool` で返却
- 未知のイベントでは状態を作成しない
- `emit` 開始時の購読者をコピーし、配信中の `on` / `off` は次回から反映
- 既存の戻り値・例外送出契約を維持

変更: [event_bus.py](<EVAL_WORKSPACE>/event_bus.py:1)

検証結果:

```text
Ran 5 tests in 0.000s

OK
```

構文確認と `git diff --check` も成功しています。
