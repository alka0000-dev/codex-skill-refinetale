コマンドパレットを実装しました。

- ヘッダーの検索ボタン、`⌘K` / `Ctrl+K` で開閉
- ページ名による絞り込みと該当なし表示
- `↑` / `↓`、Enter、クリックによる選択・遷移
- 非管理者には Admin を表示しない権限制御
- Dialogのフォーカス管理とARIA属性に対応
- サイドバー、Settings、パレットのナビゲーション定義を一元化

主な変更は [CommandPalette.tsx](<EVAL_WORKSPACE>/frontend/src/components/CommandPalette/CommandPalette.tsx:26)、[navigation.ts](<EVAL_WORKSPACE>/frontend/src/components/Sidebar/navigation.ts:4)、[_layout.tsx](<EVAL_WORKSPACE>/frontend/src/routes/_layout.tsx:24) です。

検証結果:

- TypeScript型検査: 成功
- 対象6ファイルのBiomeチェック: 成功
- `git diff --check`: 成功
- Viteビルド: 共有 `node_modules` に `@rollup/rollup-darwin-arm64` がなく実行不能。依存追加は禁止されているため修復していません
- ブラウザ/E2E確認: ブラウザを開かない指定に従い未実施。必要な手動確認は、一般ユーザー・管理者それぞれで開閉、検索、0件表示、矢印循環、Enter/クリック遷移を確認するケースです。
