星評価入力コンポーネントを追加しました。

- [star-rating.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/star-rating.tsx:1)
- 1〜5段階の制御入力。値の正本は `value`、変更通知は `onValueChange`
- クリック、キーボード操作、フォームの `name` / `required`、無効化に対応
- Radio Groupと各星にアクセシブルなラベル、フォーカス・エラー表示を設定
- 既存画面、API、フォームスキーマは変更なし

検証結果:

- TypeScript型チェック: 成功
- Biome lint: 成功
- SSR確認: ラジオグループ1個、選択肢5個、選択状態1個、値3で塗りつぶし3個
- 値変換確認: `"5"` から数値 `5` をコールバックへ通知
- `name` / `required` / `disabled` の伝播: 確認済み
- Viteビルド: 環境のNode.js 16.13.1がVite 7の要件（20.19+または22.12+）を満たさないため未完了

ブラウザー操作は禁止されているため、実ブラウザー上のクリック・矢印キー・disabled時の入力抑止は実行していません。これらは既存のRadix Radio Groupへ委譲しています。
