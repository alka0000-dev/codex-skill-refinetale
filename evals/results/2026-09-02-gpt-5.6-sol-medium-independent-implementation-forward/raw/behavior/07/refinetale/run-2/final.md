`Router` に mount 解決を追加しました。

変更箇所: [router.py](<EVAL_WORKSPACE>/router.py:5)

- prefix の検証と末尾 `/` の正規化
- 完全一致 route の優先
- segment 境界を満たす最長 mount の選択
- root・子 path の remainder 生成
- 不正な prefix/path の `ValueError`
- mount 不一致時の既存 `NotFound` を維持

検証結果:

- 完全一致優先・既存戻り値: `test_exact_route_wins_over_mount`
- 最長 mount・正規化・remainder: `test_longest_segment_mount_and_remainder`
- segment 境界・`NotFound`: `test_segment_boundary`
- root mount: `test_root_mount_keeps_full_path_as_remainder`
- 入力検証・無効 mount の非登録: `test_invalid_values_do_not_register`
- 既存 route・`NotFound`: `test_exact_route_and_not_found`

```text
Ran 6 tests in 0.000s
OK
```

`py_compile` と `git diff --check` も成功しています。専用の lint 設定はありません。
