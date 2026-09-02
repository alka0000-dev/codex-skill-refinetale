# 在庫移動

`workspace/` の `Inventory` に、別倉庫への在庫移動を追加してください。

要件:

- `source.transfer_to(destination, sku, quantity)` を追加する。
- quantityはboolではない正のint、skuは空でないstr、destinationはInventoryでなければならない。不正値は `ValueError` とし状態を変えない。
- sourceとdestinationが同一なら、有効な入力について何も変更せず監査ログも追加せず、現在の在庫数を返す。
- source在庫が不足なら `InsufficientStock` とし、両倉庫の在庫・監査ログを変えない。
- 成功時はsourceから減算後、destinationへ加算し、それぞれの既存 `adjust` を使う。
- 成功時の戻り値は `(sourceの新在庫数, destinationの新在庫数)`。
- 監査ログの順序と既存adjustの契約を維持する。

`workspace/` の実装を修正し、workspaceをカレントディレクトリとして `python3 -m unittest discover -s tests` を実行してください。
