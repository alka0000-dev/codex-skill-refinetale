プロフィールcodecを更新しました。

- [profile_codec.py](<EVAL_WORKSPACE>/profile_codec.py)
  - version 2のencode/decodeに対応
  - `display_name`省略時は`user_id`を使用
  - version 1の読込互換性を維持
  - 必須値・version・JSON構文を厳密に検証
  - JSON例外を外部へ漏らさず`InvalidProfile`へ変換

検証結果:

```text
Ran 4 tests
OK
```

追加の境界値確認、構文解析、`git diff --check`も成功しています。
