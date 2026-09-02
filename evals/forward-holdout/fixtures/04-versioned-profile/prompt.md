# プロフィール保存形式の更新

`workspace/` のプロフィールcodecを、表示名を持つ新形式へ更新してください。

要件:

- `encode(Profile)` は `{"version": 2, "user_id": ..., "display_name": ...}` をJSON化する。
- `Profile` は `user_id` と `display_name` を持つ。新規作成時にdisplay_nameを省略した場合はuser_idを使う。
- `decode` はversion 2を復元する。
- 既存のversion 1 (`{"version":1,"id":...}`) も読み込み、display_nameにはidを使う。
- version欠落、未知version、必須値の欠落または非文字列、空文字列は `InvalidProfile` にする。
- JSON構文エラーも `InvalidProfile` とし、元の例外を外へ漏らさない。
- `Profile("u")` と既存version 1読込の互換性を維持する。

`workspace/` を修正し、workspaceをカレントディレクトリとして `python3 -m unittest discover -s tests` を実行してください。
