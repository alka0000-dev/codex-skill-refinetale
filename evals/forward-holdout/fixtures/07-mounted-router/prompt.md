# Routerへのmount追加

`workspace/` の完全一致routerに、path prefixによるmountを追加してください。

要件:

- `mount(prefix, handler)` を追加する。prefixは `/` で始まり、末尾 `/` はroot以外では正規化して扱う。
- `resolve(path)` は完全一致routeを最優先し、なければ一致する最長のmountを選ぶ。
- mountの一致はpath segment境界に限る。`/api` は `/api` と `/api/users` に一致するが `/apix` には一致しない。
- mountが選ばれた場合は `(handler, remainder)` を返す。remainderはprefix自身なら `/`、子pathなら先頭 `/` を含む。
- 完全一致routeの戻り値と、見つからない場合の `NotFound` を維持する。
- mountのprefixまたはresolveのpathが非str、空、`/` 始まりでない場合は `ValueError`。無効mountで状態を変えない。

`workspace/` を修正し、workspaceをカレントディレクトリとして `python3 -m unittest discover -s tests` を実行してください。
