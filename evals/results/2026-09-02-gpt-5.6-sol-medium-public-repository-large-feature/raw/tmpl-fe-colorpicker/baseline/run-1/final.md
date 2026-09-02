カラーピッカーを追加しました。

- [color-picker.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/color-picker.tsx)
- ネイティブ `input[type="color"]` を利用
- フォーム属性、disabled、invalid、フォーカス表示に対応
- 依存関係の追加なし
- TypeScript型チェック、`git diff --check` 成功

Viteビルドは、既存依存に `@rollup/rollup-darwin-arm64` が欠けているため完走できませんでした。指定どおり依存の再インストールは行っていません。
