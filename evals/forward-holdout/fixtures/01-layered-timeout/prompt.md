# タイムアウト設定の追加

`workspace/` の小さなHTTPクライアントに、リクエスト単位のタイムアウト指定を追加してください。

要件:

- `Client.request(path, timeout=None)` を利用可能にする。
- 有効なタイムアウトは正の有限な秒数（`int` または `float`。`bool` は不可）。
- 優先順位は、リクエスト指定、`Client` 作成時の指定、既定値 `5.0` の順。
- 明示された無効値は、下位の値へフォールバックせず `ValueError` にする。
- transportには従来どおりpathを渡し、解決済みタイムアウトをキーワード引数 `timeout` で渡す。
- 既存の `Client(transport)` と `request(path)` は互換に保つ。

`workspace/` 内の実装を修正し、最後にworkspaceをカレントディレクトリとして `python3 -m unittest discover -s tests` を実行してください。
