コマンドパレットを追加しました。

- ヘッダーの検索ボタン、または `⌘K` / `Ctrl+K` で開閉
- Dashboard、Items、User Settings、管理者向けAdminを検索・遷移
- 矢印キー、Enter、Esc、マウス操作に対応
- ARIA属性、IME入力、レスポンシブ表示に対応
- 依存関係の追加なし

変更箇所:

- [CommandPalette.tsx](<EVAL_WORKSPACE>/frontend/src/components/Common/CommandPalette.tsx)
- [_layout.tsx](<EVAL_WORKSPACE>/frontend/src/routes/_layout.tsx:3)

検証済み:

- Biome: 成功
- TypeScript: 成功
- プロダクションビルド: 成功

Node.js 21.7.3がViteの推奨範囲外である警告と、既存のバンドルサイズ警告は残っています。
