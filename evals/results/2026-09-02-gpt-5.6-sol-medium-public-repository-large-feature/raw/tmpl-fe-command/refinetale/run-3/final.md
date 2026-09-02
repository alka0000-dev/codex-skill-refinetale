コマンドパレットを実装しました。

- ヘッダーまたは `⌘K / Ctrl+K` で開閉
- タイトル・パスによる検索、空結果表示
- Enter、上下キー、クリックで選択・遷移
- Escapeで閉じ、検索内容をリセット
- 一般ユーザーには Dashboard/Items、管理者には Admin も表示
- サイドバーとパレットでナビゲーション定義を共有

主な変更箇所:

- [CommandPalette.tsx](<EVAL_WORKSPACE>/frontend/src/components/Common/CommandPalette.tsx:19)
- [Main.tsx](<EVAL_WORKSPACE>/frontend/src/components/Sidebar/Main.tsx:13)
- [_layout.tsx](<EVAL_WORKSPACE>/frontend/src/routes/_layout.tsx:25)

検証結果:

- TypeScript型チェック: 成功
- Biome検査: 成功
- Vite本番ビルド: 成功
- `git diff --check`: 成功
- 認証リダイレクトと既存ページ実装は変更なし
- 検索不一致時は選択・遷移を実行しない

ブラウザー試験は指示に従い未実施です。最低限のUI確認ケースは「各起動方法」「検索一致・不一致」「Enter/上下キー/Escape」「一般・管理者のAdmin表示差」です。ビルド時に既存のNodeバージョン帯と大きなチャンクに関する警告は出ましたが、ビルドは正常終了しています。既存の未追跡 `node_modules` は変更していません。
