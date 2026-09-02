星評価入力コンポーネントを追加しました: [star-rating.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/star-rating.tsx)

- 1〜5の制御入力
- 選択値以下の星を塗り表示
- クリック・キーボード操作、フォーカス表示、無効状態に対応
- `name`、`required`、`form` などのRadix属性を透過
- 数値で `onValueChange` を通知
- 既存画面・API・依存関係は変更なし

検証結果:

- TypeScript型チェック: 成功
- 新規コンポーネントのBiome検査: 成功
- 全体ビルド: TypeScript完了後、Node.js 16.13.1がVite 7の要件（20.19+）を満たさず停止
- 全体lint: 新規ファイルとは無関係な既存SVG診断8件で失敗

ブラウザー禁止かつDOMテスト環境が未導入のため、操作テストは未実施です。最小の操作テストは「3を選択すると3が通知され先頭3星が塗られる」「矢印キーで隣へ移動」「disabledでは通知されない」「name付きで選択値がフォーム送信される」の4ケースです。
