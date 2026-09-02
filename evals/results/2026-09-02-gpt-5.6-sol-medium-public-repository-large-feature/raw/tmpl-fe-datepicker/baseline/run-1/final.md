日付ピッカーを追加しました。

- [date-picker.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/date-picker.tsx)
- 制御／非制御モード対応
- 月移動、Today、Clear
- `minDate`／`maxDate`、ロケール、週開始曜日に対応
- キーボード操作、Escape、外側クリック、フォーカス管理
- フォーム用の`name`と`YYYY-MM-DD`値をサポート
- 依存関係の追加なし

検証結果:

- TypeScript型チェック: 成功
- `git diff --check`: 成功
- Viteビルド: 環境のNode.js 16.13.1がVite 7の要件（20.19+または22.12+）未満のため実行不可
