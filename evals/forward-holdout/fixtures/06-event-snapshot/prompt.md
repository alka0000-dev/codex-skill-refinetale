# EventBusの購読解除

`workspace/` の `EventBus` に購読解除を追加し、配信中の変更について契約を明確に実装してください。

要件:

- `on(event, handler)` は従来どおり登録し、同じhandlerの複数登録も別々の購読として扱う。
- `off(event, handler)` は一致する登録のうち最初の1件だけを解除し、解除できたかをboolで返す。
- 未知eventまたは未登録handlerの解除は `False` で、状態を作らない。
- `emit` の開始時点の購読者を登録順に各1回呼ぶ。
- handler内で行ったon/offは次回emitから反映し、進行中のemitには影響させない。
- handler例外はそのまま送出し、以降のhandlerは呼ばない。
- 既存のon/emitの戻り値と呼出し契約を維持する。

`workspace/` を修正し、workspaceをカレントディレクトリとして `python3 -m unittest discover -s tests` を実行してください。
