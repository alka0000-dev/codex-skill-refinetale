`InvoiceService.publish_all` を追加しました。[invoices.py](<EVAL_WORKSPACE>/invoices.py:14)

- 全件render完了後に入力順でpublish
- render／publish例外をそのまま送出
- publish失敗後の処理を停止
- 空入力は空list
- `publish_one` は変更なし

検証結果:

```text
Ran 5 tests
OK
```

`py_compile` と `git diff --check` も成功しています。
