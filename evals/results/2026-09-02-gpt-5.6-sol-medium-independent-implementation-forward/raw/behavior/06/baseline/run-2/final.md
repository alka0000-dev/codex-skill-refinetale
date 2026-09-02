`EventBus` に購読解除を実装しました。

- `off(event, handler)` は同一 handler の最初の登録だけを解除し、成否を `bool` で返します。
- 未知 event／未登録 handler では状態を変更しません。
- `emit` は開始時の購読者をスナップショット化し、配信中の変更を次回から反映します。
- 既存の `on`／`emit` の戻り値と例外伝播を維持しています。

変更: [event_bus.py](<EVAL_WORKSPACE>/event_bus.py:9)

検証結果:

- `python3 -m unittest discover -s tests`: **5件成功**
- `py_compile`: 成功
- `git diff --check`: 成功
