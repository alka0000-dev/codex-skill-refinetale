EventBus の購読解除と配信スナップショットを実装しました。

- [event_bus.py](<EVAL_WORKSPACE>/event_bus.py:9)
  - `off` は最初の一致だけを削除して真偽値を返却
  - 未知イベントでは状態を作成しない
  - `emit` は開始時点の購読者リストを複製して配信
  - 例外は捕捉せず、そのまま送出
- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:5)
  - 重複登録の個別解除
  - 未知イベント・未登録handler
  - 配信中のon/offは次回反映
  - 例外後の配信停止
- [test_existing.py](<EVAL_WORKSPACE>/tests/test_existing.py:5)
  - `on` の戻り値、登録順、`emit` の結果を維持

検証結果:

- `python3 -m unittest discover -s tests`: **6件成功**
- Python構文コンパイル: 成功
- `git diff --check`: 成功

`refinetale` に従い、追加状態や配信中フラグ、遅延操作キューは導入していません。
