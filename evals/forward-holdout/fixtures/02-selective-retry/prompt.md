# 選択的な再試行

`workspace/` の配信処理に、一時的な失敗だけを再試行する機能を追加してください。

要件:

- `deliver(sender, message, max_attempts=3)` の公開形を提供する。
- `TemporaryFailure` のときだけ、合計 `max_attempts` 回まで同じsenderで再試行する。
- 成功したら直ちに結果を返し、それ以上呼ばない。
- `PermanentFailure` を含む他の例外は直ちにそのまま送出する。
- `max_attempts` はboolではない正のintだけを受理し、無効ならsenderを呼ぶ前に `ValueError` にする。
- 既存の `deliver(sender, message)` の成功時の挙動を維持する。

`workspace/` を修正し、workspaceをカレントディレクトリとして `python3 -m unittest discover -s tests` を実行してください。
