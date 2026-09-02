星評価入力コンポーネントを追加しました。

- 追加: [star-rating.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/star-rating.tsx)
- 制御／非制御モード対応
- クリック、ホバー、矢印キー、Home／End対応
- ARIA radio group、無効・読み取り専用状態に対応
- `name` 指定時はフォーム値として送信可能
- `max`、`value`、`defaultValue` 対応
- 既存のLucideアイコンとテーマ色のみ使用

検証:

- TypeScript型チェック成功
- Viteビルドは環境のNode.js 16.13.1が要件（20.19以上）を満たさないため実行不可
- 依存追加、開発サーバー起動、ブラウザー操作は行っていません
