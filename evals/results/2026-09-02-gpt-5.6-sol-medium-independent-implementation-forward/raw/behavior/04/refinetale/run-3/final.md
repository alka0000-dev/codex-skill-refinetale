実装完了しました。

変更:

- [profile_codec.py](<EVAL_WORKSPACE>/profile_codec.py)
  - `Profile(user_id, display_name=None)`へ更新
  - 省略時は`display_name = user_id`
  - `encode`をversion 2形式へ更新
  - version 1/2を共通内部形式へ正規化して復元
  - 欠落・未知version・非文字列・空文字列・JSONエラーを`InvalidProfile`化
- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py)
  - 各必須値の欠落・型違反・空文字列を追加検証

検証結果:

- version 2保存・復元: 成功
- `Profile("u")`の互換性: 成功
- version 1読込と表示名補完: 成功
- 全無効入力の`InvalidProfile`化: 成功
- `python3 -m unittest discover -s tests`: 4件成功
- `py_compile`: 成功
- `git diff --check`: 成功
