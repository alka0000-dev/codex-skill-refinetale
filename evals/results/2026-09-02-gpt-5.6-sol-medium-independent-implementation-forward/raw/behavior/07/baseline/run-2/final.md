実装完了しました。

- [`router.py`](<EVAL_WORKSPACE>/router.py:12)
  - `mount(prefix, handler)` を追加
  - 末尾 `/` の正規化
  - 完全一致 route の優先
  - segment 境界を考慮した最長 mount 選択
  - remainder の返却
  - 不正入力の `ValueError`
- [`tests/test_requirements.py`](<EVAL_WORKSPACE>/tests/test_requirements.py:22)
  - 複数末尾スラッシュ、非文字列、無効 mount 時の状態不変性を追加検証

検証結果:

```text
Ran 7 tests
OK
```

`py_compile` と `git diff --check` も成功しています。
