マルチステップフォームウィザードを実装しました。

- [MultiStepForm.tsx](<EVAL_WORKSPACE>/frontend/src/components/Common/MultiStepForm.tsx:13)
  - Back／Next／Submit の境界制御
  - 現在ステップのみネイティブ入力検証
  - 戻った際の入力値保持
  - レスポンシブな進捗表示
  - `fieldset`、`legend`、`aria-current`、live region によるアクセシビリティ対応
  - 既存フォーム属性と `onSubmit` をそのまま利用可能
- `.agent/CONTINUITY.md` に判断・検証結果を記録
- 既存ルート、API、フォーム、依存関係は変更していません。

検証結果:

- Biome: 成功
- TypeScript: 成功
- Viteビルド: 既存 `node_modules` に `@rollup/rollup-darwin-arm64` がないため未完了。指示に従い再インストールしていません。

ブラウザ操作禁止のため、以下の動作確認は未実施です。最小確認ケースは「必須項目が空ならNextで停止」「入力後は前後移動しても値を保持」「最終ステップだけSubmitが発火」「`noValidate` 指定時はネイティブ検証を省略」で、期待結果に対応する実装経路は静的に確認済みです。
