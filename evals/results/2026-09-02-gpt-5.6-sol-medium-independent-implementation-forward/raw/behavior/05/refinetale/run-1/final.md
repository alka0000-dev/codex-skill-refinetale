[invoices.py](<EVAL_WORKSPACE>/invoices.py:14) に `InvoiceService.publish_all` を追加しました。

検証結果:

- 入力順の結果・全件 render 後の publish: 成功
- render 失敗時に publish 0件: 成功
- publish 失敗時に後続を停止: 成功
- 空入力で空 list・publish 0件: 成功
- 既存 `publish_one` 契約: 成功
- `python3 -m unittest discover -s tests`: 5件成功
- 構文検証、`git diff --check`: 成功

例外処理や空入力専用分岐は追加せず、既存例外をそのまま伝播させる実装です。
