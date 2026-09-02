`EventBus` に購読解除と配信スナップショットを実装しました。

変更内容:

- [event_bus.py](<EVAL_WORKSPACE>/event_bus.py:9)
  - `off` は最初の一致だけを削除
  - 未登録時は状態を作らず `False`
  - `emit` 開始時に購読リストをコピー
  - handler例外は捕捉せず、そのまま送出
- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:6)
  - `on` の戻り値維持
  - 未登録handler解除時の状態維持を追加検証

検証結果:

- 重複登録・1件ずつの解除: 成功
- 未知event・未登録handler: `False`、副作用なし
- 配信中のon/off: 次回配信から反映
- 登録順・開始時点の各購読を1回配信: 成功
- handler例外後の配信停止: 成功
- 既存の`on` / `emit`戻り値: 維持
- `python3 -m unittest discover -s tests`: **7件成功**
- `git diff --check`: 成功

シェル初期化由来の `eval` 警告が表示されましたが、unittest自体は終了コード0で成功しています。
