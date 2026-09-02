ファイルアップロード用ドロップゾーンを追加しました。

- 実装: [file-upload-dropzone.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/file-upload-dropzone.tsx)
- クリック／キーボード選択とドラッグ＆ドロップに対応
- `accept`、`multiple`、`disabled` をサポート
- 両入力経路を同じ `File[]` に正規化
- 同一ファイルの再選択に対応
- アップロード通信や選択済みファイルの状態は親コンポーネントが所有

検証結果:

- TypeScript型チェック: 成功
- Viteビルド: 共有依存にRollupのdarwin-arm64バイナリがなく実行不可
- Biome: 共有依存側との設定ルート競合で実行不可
- Playwrightテスト: ブラウザ使用禁止のため未実施

最小の実操作確認項目は、ファイル選択／ドロップでコールバックが1回呼ばれること、`accept` 不一致が除外されること、単一選択では先頭1件のみになること、無効時はコールバックが呼ばれないこと、同一ファイルを再選択できることです。

継続記録も [.agent/CONTINUITY.md](<EVAL_WORKSPACE>/.agent/CONTINUITY.md) に更新しました。既存の未追跡 `node_modules` には触れていません。
