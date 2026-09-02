実装完了しました。

変更内容:

- `mount(prefix, handler)` を追加
- prefix末尾の `/` を正規化
- 完全一致 route を最優先
- segment境界で一致する最長 mount を選択
- mount時は `(handler, remainder)` を返却
- 不正な prefix/path は状態変更前に `ValueError`
- root mount に対応

変更ファイル: [router.py](<EVAL_WORKSPACE>/router.py)

検証結果:

```text
Ran 6 tests in 0.000s

OK
```

`py_compile` と `git diff --check` も成功しています。
