選択的な再試行を実装しました。

- [delivery.py](<EVAL_WORKSPACE>/delivery.py:9)
  - `deliver(sender, message, max_attempts=3)` を提供
  - `TemporaryFailure` のみ再試行
  - 成功時は即時返却
  - 最終失敗およびその他の例外は同じ例外を送出
  - bool・非int・0以下を送信前に `ValueError`
- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:18)
  - 成功後の停止、試行上限、既定3回、例外の同一性、無効値と送信抑止を検証
- `.agent/CONTINUITY.md` も更新済みです。

検証結果:

- `python3 -m unittest discover -s tests`: **6件成功**
- `compileall`: 成功
- `git diff --check`: 成功
- 既存の `deliver(sender, message)` 成功経路も維持されています。
