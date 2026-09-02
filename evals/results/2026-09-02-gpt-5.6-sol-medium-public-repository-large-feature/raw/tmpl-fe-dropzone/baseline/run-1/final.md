ファイルアップロード用ドロップゾーンを追加しました。

- [file-upload-dropzone.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/file-upload-dropzone.tsx)
- ドラッグ＆ドロップ／クリック選択
- 単一・複数ファイル対応
- ファイル形式、サイズ、件数制限
- 選択一覧、個別削除、一括クリア
- controlled／uncontrolled API
- 無効状態、キーボード操作、エラー通知対応

検証結果:

- TypeScript型チェック: 成功
- Vite本番ビルド: 成功
- 既存のNode.jsバージョン警告とバンドルサイズ警告のみ発生
- 依存追加、開発サーバー起動、ブラウザ操作は未実施

継続記録も [.agent/CONTINUITY.md](<EVAL_WORKSPACE>/.agent/CONTINUITY.md) に追加しています。
