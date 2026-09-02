実装完了しました。

- [router.py](<EVAL_WORKSPACE>/router.py) に `mount(prefix, handler)` を追加
- prefix の末尾 `/` を正規化
- 完全一致 route を優先
- segment 境界を満たす最長 mount を解決
- `(handler, remainder)` を返却
- mount／resolve の不正入力を `ValueError` に統一
- 不正な mount では状態を変更しない

検証結果:

```text
python3 -m unittest discover -s tests
Ran 6 tests
OK
```

`py_compile` と `git diff --check` も成功しています。
