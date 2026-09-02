実装完了しました。[delivery.py](<EVAL_WORKSPACE>/delivery.py) を更新しています。

- `deliver(sender, message, max_attempts=3)` を提供
- `TemporaryFailure` のみ最大 `max_attempts` 回まで再試行
- 成功時は即時終了
- その他の例外は即時送出
- bool以外の正のintのみ受理し、無効値は送信前に `ValueError`
- 従来の成功時の戻り値を維持

検証結果:

- 一時失敗後の成功・早期終了: 成功
- 試行回数上限での例外送出: 成功
- `PermanentFailure`／その他例外の即時送出: 成功
- 無効な試行回数でsender未呼び出し: 成功
- 既存の2引数成功経路: 成功
- `python3 -m unittest discover -s tests`: **5件すべて成功**
- 構文コンパイル、`git diff --check`: 成功

リント設定はプロジェクト内に存在しないため、個別のリンター実行対象はありません。
