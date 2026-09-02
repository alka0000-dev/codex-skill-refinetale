ファイルアップロード用 `FileDropzone` を追加しました。

- [file-dropzone.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/file-dropzone.tsx)
- クリック選択とドラッグ＆ドロップを `onFilesSelected(File[])` に統一
- 単一・複数選択に対応
- ドラッグ中、フォーカス中、無効時の表示を実装
- 無効時・空ドロップではコールバックを抑止
- アップロード通信や選択ファイルの重複状態は追加していません

検証結果:

- TypeScript型チェック: 成功
- `git diff --check`: 成功
- Viteビルド: 環境のNode 16に対してNode 20.19以上が必要なため実行不可
- 全体リント: 既存SVGの8件とBiome設定・CLIバージョン差により失敗。新規UIディレクトリは既存設定でリント対象外
- ブラウザテスト: ブラウザを開かない指定と、ユニットテスト環境がないため未実施。必要な最小ケースはクリック選択、単一／複数ドロップ、無効時、空ドロップです。
