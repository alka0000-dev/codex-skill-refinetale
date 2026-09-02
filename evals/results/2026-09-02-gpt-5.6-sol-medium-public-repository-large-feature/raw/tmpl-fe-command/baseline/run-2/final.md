コマンドパレットを追加しました。

- ヘッダーまたは `Ctrl/⌘ + K` で開閉
- コマンドの文字列検索
- 上下キー、Enter、Escによるキーボード操作
- Dashboard／Items／Settingsへの遷移
- 管理者のみAdminコマンドを表示
- 新規依存関係なし

変更箇所:

- [CommandPalette.tsx](<EVAL_WORKSPACE>/frontend/src/components/Common/CommandPalette.tsx)
- [_layout.tsx](<EVAL_WORKSPACE>/frontend/src/routes/_layout.tsx:3)

検証結果:

- Biome: 成功
- TypeScript型チェック: 成功
- Viteビルド: 環境のNode.jsが16.13.1のため実行不可（Viteは20.19+または22.12+が必要）

依存追加、開発サーバー起動、ブラウザー操作は行っていません。
