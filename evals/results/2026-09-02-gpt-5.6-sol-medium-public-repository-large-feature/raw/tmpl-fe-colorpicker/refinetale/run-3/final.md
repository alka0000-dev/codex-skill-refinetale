色ピッカーコンポーネントを追加しました。

- [color-picker.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/color-picker.tsx:1)
- ブラウザ標準の `input[type="color"]` を使用し、依存・内部状態・分岐を追加していません。
- `value`、`onChange`、`disabled`、`aria-*`、refなど標準 input propsを転送します。
- `type` は公開 props から除外し、常に色入力になることを型と実装で保証しています。
- 既存の `Input` に枠線、フォーカス、invalid、disabledの挙動を委譲しています。
- 既存画面やフォーム送信経路は変更していません。

検証結果:

- `npm run build`: 成功（TypeScript型チェック＋Viteビルド）
- `npm run lint`: 新規UIディレクトリは設定上対象外。既存SVGの8件の診断で失敗し、自動変更はありませんでした。
- テスト: 独自の状態・変換・非同期／失敗経路がなく、ブラウザを開かない指定のため追加・実行していません。
