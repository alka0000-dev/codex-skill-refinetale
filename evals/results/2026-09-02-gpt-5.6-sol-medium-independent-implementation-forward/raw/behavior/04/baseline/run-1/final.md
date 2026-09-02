プロフィールcodecを新形式へ更新しました。

- `Profile`に`display_name`を追加し、省略時は`user_id`を使用
- `encode`をversion 2形式へ変更
- version 1／2の復元に対応
- 欠損、不正型、空文字列、未知version、不正JSONを`InvalidProfile`へ統一
- `Profile("u")`とversion 1の互換性を維持

変更: [profile_codec.py](<EVAL_WORKSPACE>/profile_codec.py:8)

検証結果:

```text
Ran 4 tests in 0.000s

OK
```

`py_compile`と`git diff --check`も成功しています。
