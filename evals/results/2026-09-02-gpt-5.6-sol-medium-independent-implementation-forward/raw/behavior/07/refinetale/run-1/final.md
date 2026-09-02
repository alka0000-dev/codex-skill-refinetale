Router に prefix mount を追加し、要件どおり動作することを確認しました。

変更:

- [router.py](<EVAL_WORKSPACE>/router.py:5)
  - prefix の検証・末尾 `/` 正規化
  - 完全一致 route の優先
  - segment 境界を守った最長 mount 選択
  - root／子 path の remainder 生成
  - 未解決時の `NotFound` 維持
- [tests/test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:5)
  - 非文字列を含む無効入力と、登録状態が変化しないことを補強

検証結果:

- 完全一致優先: 成功
- 最長 mount・正規化・remainder: 成功
- `/api` と `/apix` の境界: 成功
- root mount: 成功
- 無効入力の `ValueError`・状態維持: 成功
- 既存 route・`NotFound`: 成功
- `python3 -m unittest discover -s tests`: **6 tests、すべて成功**
- `git diff --check`: 成功

独立したビルド／lint 設定はないため、追加実行対象はありません。
