実装しました。[invoices.py](<EVAL_WORKSPACE>/invoices.py:14) に `InvoiceService.publish_all` を追加しています。

検証結果:

- 入力順の結果返却・全render後のpublish開始: 成功
- render失敗時にpublish 0件・例外伝播: 成功
- publish失敗時に後続停止・既存公開は維持: 成功
- 空入力で空list・publish 0件: 成功
- 既存`publish_one`契約: 成功
- `python3 -m unittest discover -s tests`: 5件成功
- `py_compile`、`git diff --check`: 成功

既存テストが全要件を直接検証していたため、テストコードの追加変更はありません。
