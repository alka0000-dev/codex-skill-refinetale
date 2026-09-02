日付選択コンポーネントを追加しました: [date-picker.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/date-picker.tsx:1)

- 既存 `Input` を再利用し、`type="date"` を実行時にも固定
- `value`、`min`、`max`、`disabled`、イベント、`ref` などはそのまま委譲
- 状態、分岐、日付変換、依存関係は追加なし
- 既存画面には組み込んでいないため、既存挙動は不変

検証結果:

- TypeScript strict check: 成功
- Vite build: Node.js 16.13.1 のため実行不可（Vite は 20.19+ または22.12+が必要）
- lint: UIディレクトリは既存設定の対象外。全体lintは既存SVGの8件とBiomeバージョン不一致で失敗
- ブラウザー確認: 明示された制約に従い未実施。最小確認ケースは、表示後に日付を選択し `YYYY-MM-DD` 値が変更イベントへ渡ることです。
