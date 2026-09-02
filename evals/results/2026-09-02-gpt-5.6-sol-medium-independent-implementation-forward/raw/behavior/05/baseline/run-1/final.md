`InvoiceService.publish_all(invoices)` を [invoices.py](<EVAL_WORKSPACE>/invoices.py:14) に追加しました。

- 全件render完了後、入力順にpublish
- render／publish例外はそのまま送出
- publish失敗後の後続処理を停止
- 空入力は `[]`
- `publish_one` は変更なし

検証結果:

```text
python3 -m unittest discover -s tests
Ran 5 tests
OK
```

Python構文コンパイルと `git diff --check` も成功しています。
