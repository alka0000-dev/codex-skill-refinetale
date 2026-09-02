`Ledger.apply_batch(entries)` を実装しました。

- 全entryを事前検証し、不正形式は `ValueError`
- 複製残高で入力順にシミュレーションし、途中の負残高は `Overdraft`
- 検証失敗時は残高・監査ログとも無変更
- 成功時のみ既存の `apply` を入力順に呼び出し、戻り値のlistを返却
- 既存の `apply` 契約は変更なし

変更箇所:

- [ledger.py](<EVAL_WORKSPACE>/ledger.py:18)
- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:6)

検証結果:

- 正常系・同一account・入力順・戻り値・監査ログ: 成功
- 既存 `apply` 経路の利用: 成功
- 途中当座貸越時の原子性: 成功
- tuple形式、空／非文字列account、bool／非int deltaの拒否と原子性: 成功
- 既存 `apply` 契約: 成功
- `python3 -m unittest discover -s tests`: **5 tests passed**
- バイトコードコンパイル、`git diff --check`: 成功
