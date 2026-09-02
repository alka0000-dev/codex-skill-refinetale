`InvoiceService.publish_all` を [invoices.py](<EVAL_WORKSPACE>/invoices.py:14) に追加しました。

- 全件render完了後、入力順にpublishして結果を返す
- render失敗時はpublishせず、例外をそのまま送出
- publish失敗時は後続を停止し、成功済み公開は維持
- 空入力は `[]`、publisher呼び出しなし
- `publish_one` は変更なし
- 不要な条件分岐や例外変換は追加なし

検証結果:

```text
$ python3 -m unittest discover -s tests
.....
Ran 5 tests in 0.000s

OK
```

`git diff --check` も成功しています。
