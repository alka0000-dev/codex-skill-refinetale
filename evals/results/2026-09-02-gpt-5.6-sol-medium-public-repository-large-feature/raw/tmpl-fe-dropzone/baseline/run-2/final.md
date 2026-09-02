ファイルアップロード用ドロップゾーンを追加しました。

- [FileUploadDropzone.tsx](<EVAL_WORKSPACE>/frontend/src/components/Common/FileUploadDropzone.tsx)
  - ドラッグ＆ドロップ／ファイル選択
  - ファイル形式・サイズ検証
  - 重複排除、一覧表示、個別削除
  - disabled状態、キーボード操作、エラー通知
  - 設定可能な形式、最大サイズ、複数選択
- [ダッシュボード](<EVAL_WORKSPACE>/frontend/src/routes/_layout/index.tsx)へ配置

検証結果:

- Biome: 成功
- TypeScript型チェック: 成功
- Viteビルド: 環境のNode.js 16.13.1が古く実行不可（Viteは20.19+または22.12+が必要）

依存追加、開発サーバー起動、ブラウザー操作は行っていません。
