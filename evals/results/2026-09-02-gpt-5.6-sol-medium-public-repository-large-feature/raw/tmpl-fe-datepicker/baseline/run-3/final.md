日付ピッカーを追加しました。

- 追加: [date-picker.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/date-picker.tsx)
- 既存の `Input` を利用したネイティブ日付選択
- `min`、`max`、`required`、`disabled`、`ref`、ARIA属性に対応
- 依存関係の追加なし

検証結果:

- TypeScriptチェック: 成功
- 差分チェック: 成功
- Viteビルド: 環境のNode.js 16.13.1が古いため実行不可（Viteは20.19以上が必要）
- 開発サーバー・ブラウザは使用していません。
