# 請求書の一括公開

`workspace/` の請求書サービスに、一括公開を追加してください。

要件:

- `InvoiceService.publish_all(invoices)` を追加し、公開結果を入力順のlistで返す。
- 各invoiceは既存の `render` で生成し、既存publisherの `publish(invoice_id, body)` で公開する。
- 全invoiceのrenderが成功した後にだけ、最初のpublishを行う。
- render失敗時は例外をそのまま送出し、1件もpublishしない。
- publish失敗時は例外をそのまま送出し、後続invoiceをpublishしない（既に成功した外部公開は取り消さない）。
- 空入力は空listを返し、publisherを呼ばない。
- 既存の `publish_one` の契約を維持する。

`workspace/` の実装を修正し、workspaceをカレントディレクトリとして `python3 -m unittest discover -s tests` を実行してください。
