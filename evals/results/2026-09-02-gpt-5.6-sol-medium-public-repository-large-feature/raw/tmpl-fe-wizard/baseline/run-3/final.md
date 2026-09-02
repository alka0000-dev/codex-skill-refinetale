複数ステップのフォームウィザードを追加しました。

- 3ステップ構成：プロジェクト情報 → 設定 → 確認
- ステップ単位のZodバリデーション
- 入力値保持、戻る／次へ、Enterキー対応
- 進捗表示、完了画面、リセット、成功トースト
- レスポンシブ・アクセシビリティ・軽減モーション対応
- ダッシュボードへ配置

変更箇所：

- [MultiStepFormWizard.tsx](<EVAL_WORKSPACE>/frontend/src/components/Common/MultiStepFormWizard.tsx:46)
- [index.tsx](<EVAL_WORKSPACE>/frontend/src/routes/_layout/index.tsx:17)

検証結果：

- TypeScript型チェック：成功
- Biome lint／format：成功
- `git diff --check`：成功
- Viteビルド：環境のNode.js 16.13.1が、Viteの要求する20.19+／22.12+未満のため実行不可

依存関係の追加、開発サーバー起動、ブラウザー操作は行っていません。
