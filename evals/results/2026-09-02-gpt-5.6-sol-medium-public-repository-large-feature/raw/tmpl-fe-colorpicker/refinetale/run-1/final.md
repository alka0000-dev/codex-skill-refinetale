色選択コンポーネントを追加しました。

- [color-picker.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/color-picker.tsx)
- 標準の `input[type="color"]` を使用
- 既存 `Input` の focus・disabled・invalid・props 転送を継承
- 色固有の状態、分岐、依存関係は追加なし
- 画面への配置や保存処理は要件外のため既存画面を変更せず

検証結果:

- TypeScript 型検査: 成功
- Biome 検査: 成功
- Vite ビルド: 既存環境に Rollup の任意パッケージ `@rollup/rollup-darwin-arm64` がなく未完了
- 依存追加、開発サーバー起動、ブラウザー操作: 未実施
- 既存の追跡対象ファイルに変更なし。既存経路は維持されています。
