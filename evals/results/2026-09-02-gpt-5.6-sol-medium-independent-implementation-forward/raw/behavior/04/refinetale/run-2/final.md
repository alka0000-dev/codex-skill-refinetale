プロフィールcodecを新形式へ更新しました。

変更内容:

- `Profile(user_id, display_name=None)` を追加し、省略時は `user_id` を使用
- `encode` をversion 2形式へ変更
- `decode` はversion 1・2を共通の`Profile`へ正規化
- version不正、値の欠落・非文字列・空文字列を`InvalidProfile`化
- JSON構文エラーの元例外を外部へ露出しない
- 等価比較に`display_name`を追加
- 継続記録を作成・更新

対象: [profile_codec.py](<EVAL_WORKSPACE>/profile_codec.py:8)

検証結果:

- version 2 encode/decode・表示名省略: 成功
- version 1互換と`Profile("u")`: 成功
- version欠落・未知version: `InvalidProfile`
- 必須値の欠落・非文字列・空文字列: `InvalidProfile`
- JSON構文エラー: `InvalidProfile`、元例外のcauseなし
- `python3 -m unittest discover -s tests`: **4件すべて成功**
- `py_compile`: 成功
- `git diff --check`: 成功
