`EventBus` に購読解除と配信スナップショットを実装しました。

- [event_bus.py](<EVAL_WORKSPACE>/event_bus.py:9)
  - `off` は重複登録の先頭1件だけを解除
  - 未登録時は状態を作らず `False`
  - `emit` は開始時の購読者一覧をコピーして配信
  - 既存の登録順、戻り値、例外送出を維持
- 継続記録として `.agent/CONTINUITY.md` を作成

検証結果:

- 重複解除・未知イベント: 成功
- 配信中の `on` / `off`: 次回配信から反映
- handler例外: 後続を呼ばず送出
- 既存の登録順・結果リスト・未知イベント: 維持
- `python3 -m unittest discover -s tests`: **5件すべて成功**
- `git diff --check`: 問題なし

シェル起動フックが `parse error near 'end'` を表示しますが、テストは終了コード0で完了しています。
