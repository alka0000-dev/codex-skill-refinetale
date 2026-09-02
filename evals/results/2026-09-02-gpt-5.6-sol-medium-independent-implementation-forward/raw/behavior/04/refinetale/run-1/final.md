実装完了しました。

変更内容:

- [profile_codec.py](<EVAL_WORKSPACE>/profile_codec.py:8)
  - `Profile(user_id, display_name=None)` を追加
  - 表示名省略時は `user_id` を使用
  - `encode` をversion 2形式へ更新
  - `decode` でv1/v2を共通表現へ正規化
  - 欠落、非文字列、空文字列、不明version、JSONエラーを `InvalidProfile` に統一
- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:18)
  - v2の各必須値について、欠落・非文字列・空文字列の検証を補強
- [.agent/CONTINUITY.md](<EVAL_WORKSPACE>/.agent/CONTINUITY.md)
  - 変更契約と検証結果を記録

検証結果:

- v2保存・復元、表示名既定値: 成功
- v1読込と `Profile("u")` 互換: 成功
- 全不正入力とJSON構文エラーの拒否: 成功
- `python3 -m unittest discover -s tests`: **4件成功**
- Python構文コンパイル: 成功
- `git diff --check`: 成功
