星評価入力コンポーネントを追加しました。

- 追加: [star-rating.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/star-rating.tsx)
- `value` / `defaultValue` / `onValueChange` に対応
- 最大星数、無効・必須状態、フォーム送信に対応
- ホバープレビュー、矢印キー操作、スクリーンリーダー向けラベルを実装
- TypeScript型チェック、Biome検証、空白チェック成功

フルビルドは環境の Node.js 16.13.1 がVite 7の要件（Node.js 20.19+）を満たさないため、Vite処理のみ実行できませんでした。TypeScriptコンパイルは成功しています。
