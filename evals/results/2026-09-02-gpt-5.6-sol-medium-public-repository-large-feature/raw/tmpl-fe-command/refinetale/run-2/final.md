コマンドパレットを追加しました。

- ヘッダーボタンまたは `⌘/Ctrl + K` で開閉
- コマンド名の部分一致検索
- 矢印キー、Tab、Enterで操作可能
- 該当なし表示、Escape・外側クリックで閉じる
- 管理者だけに `Admin` を表示
- サイドバーとパレットでナビゲーション定義を共有

主な変更箇所:

- [CommandPalette.tsx](<EVAL_WORKSPACE>/frontend/src/components/Common/CommandPalette.tsx:26)
- [navigation.ts](<EVAL_WORKSPACE>/frontend/src/components/Sidebar/navigation.ts:9)
- [_layout.tsx](<EVAL_WORKSPACE>/frontend/src/routes/_layout.tsx:24)
- [CONTINUITY.md](<EVAL_WORKSPACE>/.agent/CONTINUITY.md)

検証結果:

- TypeScriptコンパイル: 成功
- 変更した5ファイルのBiome検査: 成功
- `git diff --check`: 成功
- Viteビルド: TypeScript通過後、既存依存に `@rollup/rollup-darwin-arm64` がないため停止。依存追加は禁止されているため未修復
- リポジトリ全体lint: 今回未変更の既存SVGにある8件の警告で失敗
- ブラウザ確認: 指示に従い未実施。必要な確認ケースは、ボタン／ショートカットでの開閉、検索結果の絞り込み、選択時の遷移、空結果、一般ユーザーからのAdmin除外、Escapeによる早期終了です

依存インストール、開発サーバー起動、ブラウザ操作は行っていません。作業開始時から存在した未追跡の `node_modules` にも変更を加えていません。
