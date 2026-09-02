# 台帳への一括記帳

`workspace/` の `Ledger` に一括記帳APIを追加してください。

要件:

- `apply_batch(entries)` を追加する。各entryは `(account, delta)` の2要素tupleで、accountは空でないstr、deltaはboolではないint。
- 同一accountが複数回現れ得る。入力順に適用した途中を含め、残高が一度でも0未満になるbatchは `Overdraft` にする。
- entry形式が不正なら `ValueError` にする。
- 失敗したbatchでは、残高と監査ログを一切変更しない。
- 成功時は各entryを入力順に既存の `apply` 経路で反映し、その戻り値のlistを返す。
- `apply` と既存の公開状態の契約を維持する。

`workspace/` のファイルを修正し、workspaceをカレントディレクトリとして `python3 -m unittest discover -s tests` を実行してください。
