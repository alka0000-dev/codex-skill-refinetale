`DatePicker` を追加しました。[date-picker.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/date-picker.tsx)

- 既存 `Input` のスタイル・disabled・invalid・focus 契約を再利用
- `type="date"` を固定し、呼び出し側からの上書きを型で禁止
- `value`、`onChange`、`min`、`max`、`required`、`aria-*` など標準 input props に対応
- 独自状態、日付変換、依存関係、条件分岐は追加なし

検証結果:

- TypeScript型検査: 成功
- `git diff --check`: 成功
- 状態・分岐・重複経路がないこと: 確認済み
- 本番ビルド: 型検査後、Node.js 16.13.1がViteの要件（20.19+）未満のため停止
- lint: 利用可能なBiomeと設定のバージョン差、および既存SVGの指摘により全体実行は失敗。対象の`ui`ディレクトリは既存設定でlint対象外
- ブラウザ操作確認: サーバー起動・ブラウザ使用禁止のため未実施。確認する最小ケースは日付選択時の`onChange`値、`min`/`max`制約、disabled・required表示です。
