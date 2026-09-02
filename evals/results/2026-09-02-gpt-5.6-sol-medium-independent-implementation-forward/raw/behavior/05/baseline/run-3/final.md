`InvoiceService.publish_all(invoices)` を追加しました。

- 全件の render 成功後に publish を開始
- 入力順で公開し、結果を list で返却
- render / publish の例外をそのまま送出
- publish 失敗後は後続処理を停止
- 空入力では publisher を呼ばず `[]` を返却
- `publish_one` は変更なし

変更: [invoices.py](<EVAL_WORKSPACE>/invoices.py:13)

検証結果:

```text
Ran 5 tests in 0.000s

OK
```

`py_compile` と `git diff --check` も成功しています。
