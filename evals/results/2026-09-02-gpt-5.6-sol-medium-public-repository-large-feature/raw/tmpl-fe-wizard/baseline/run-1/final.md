マルチステップフォームウィザードを追加しました。

- [MultiStepFormWizard.tsx](<EVAL_WORKSPACE>/frontend/src/components/Common/MultiStepFormWizard.tsx:90)
  - 3ステップ構成
  - ステップ単位のZodバリデーション
  - 戻る／進む際の入力保持
  - キーボード操作、フォーカス移動、進捗表示
  - レスポンシブ・ダークモード・reduced motion対応
  - 完了／再開始状態と任意の`onComplete`コールバック
- [ダッシュボード](<EVAL_WORKSPACE>/frontend/src/routes/_layout/index.tsx:17)へ組み込みました。
- 依存関係の追加、サーバー起動、ブラウザ操作は行っていません。

検証結果：

- Biome: 成功
- TypeScript型チェック: 成功
- 本番ビルド: 型チェック後のVite起動時に停止
  - 環境のNode.js: `16.13.1`
  - Vite要件: `20.19+` または `22.12+`
