コマンドパレットを追加しました。

- ヘッダーまたは `⌘K` / `Ctrl+K` で起動
- タイトル・説明・キーワードによる検索
- 上下キー、Enter、Esc、マウス操作に対応
- Dashboard、Items、User Settingsへ移動
- Adminコマンドは管理者だけに表示
- モバイル幅とアクセシビリティ属性に対応

変更箇所:

- [CommandPalette.tsx](<EVAL_WORKSPACE>/frontend/src/components/Common/CommandPalette.tsx:1)
- [_layout.tsx](<EVAL_WORKSPACE>/frontend/src/routes/_layout.tsx:24)

検証済み:

- TypeScript型チェック成功
- Biome全47ファイル成功
- Vite本番ビルド成功

既存環境のNode.js 21.7.3に対するViteのバージョン注意と、既存のバンドルサイズ警告のみ残っています。依存追加、開発サーバー起動、ブラウザー操作は行っていません。
