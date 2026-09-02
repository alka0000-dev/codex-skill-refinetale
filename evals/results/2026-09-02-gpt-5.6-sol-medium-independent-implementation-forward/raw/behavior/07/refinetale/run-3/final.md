実装完了しました。[router.py](<EVAL_WORKSPACE>/router.py) に以下を追加しています。

- `mount(prefix, handler)` と末尾 `/` の正規化
- 完全一致 route の優先
- segment 境界による mount 判定
- 最長 prefix の選択と remainder 返却
- `mount`／`resolve` の入力検証
- 無効 mount 時の状態不変
- 既存の handler 単体返却と `NotFound` の維持

検証結果：

- 完全一致優先：成功
- 最長 mount・remainder：成功
- `/api` と `/apix` の境界：成功
- root mount：成功
- 不正入力・状態不変：成功
- 既存 route・`NotFound`：成功
- `python3 -m unittest discover -s tests`：**6件成功**
- 構文コンパイル、`git diff --check`：成功

継続記録も [.agent/CONTINUITY.md](<EVAL_WORKSPACE>/.agent/CONTINUITY.md) に作成しました。
