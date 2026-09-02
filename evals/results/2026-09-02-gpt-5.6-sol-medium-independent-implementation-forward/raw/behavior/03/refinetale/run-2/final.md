実装完了しました。

- [ledger.py](<EVAL_WORKSPACE>/ledger.py:18)
  - 全entryを副作用前に検証
  - 入力順の途中残高を事前計算し、負数なら `Overdraft`
  - 成功時のみ既存 `apply` 経路で順次反映し、戻り値をリスト化
- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:6)
  - 成功時の順序・戻り値・監査ログ
  - 途中当座貸越の原子性
  - tuple、account、deltaの不正形式と原子性
  - 空batch
  - 既存 `apply` 経路の利用
- `.agent/CONTINUITY.md` も作成・更新済みです。

検証結果:

```text
python3 -m unittest discover -s tests
Ran 6 tests in 0.000s
OK
```

既存 `apply` の当座貸越時の残高・監査ログ契約も既存テストで維持されています。`git diff --check` も成功しました。
