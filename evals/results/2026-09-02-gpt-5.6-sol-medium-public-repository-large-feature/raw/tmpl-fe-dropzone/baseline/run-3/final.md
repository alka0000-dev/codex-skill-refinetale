ファイルアップロード用ドロップゾーンを追加しました。

- ドラッグ＆ドロップ／クリック選択
- 複数ファイル、重複排除、個別削除
- ファイル形式・サイズ検証
- `onFilesChange` コールバック
- キーボード操作とスクリーンリーダー対応
- ダッシュボードへ配置（上限10MB）

変更箇所:

- [FileUploadDropzone.tsx](<EVAL_WORKSPACE>/frontend/src/components/Common/FileUploadDropzone.tsx:1)
- [ダッシュボード](<EVAL_WORKSPACE>/frontend/src/routes/_layout/index.tsx:20)

検証:

- Biome: 成功
- TypeScript型チェック: 成功
- Viteビルド: 実行環境のNode.js 16.13.1が要件（20.19+または22.12+）未満のため、バンドル開始前に停止

バックエンドにアップロードAPIがないため、実際の送信処理は含めていません。
