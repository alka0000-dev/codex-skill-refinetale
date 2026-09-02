日付ピッカーを追加しました: [date-picker.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/date-picker.tsx)

- ブラウザ標準の `input[type="date"]` を使用
- 既存 `Input` のスタイルと `value`、`onChange`、`min`、`max`、`disabled`、`aria-*`、`ref` を継承
- `type` は上書き不能
- 状態、分岐、追加依存、既存画面の変更なし

検証:

- TypeScript全体型チェック: 成功
- 差分の空白チェック: 成功
- Biome: 共通UIディレクトリが設定上の除外対象のため0ファイル
- Viteビルド: 既存環境に `@rollup/rollup-darwin-arm64` がなく実行不可。依存追加禁止のためインストールせず停止
- ブラウザ確認: 指示に従い未実施。確認する場合は、日付選択時に `onChange` へ `YYYY-MM-DD` が渡り、`min`・`max`・`disabled` がネイティブUIへ反映されることが最小確認項目です。
