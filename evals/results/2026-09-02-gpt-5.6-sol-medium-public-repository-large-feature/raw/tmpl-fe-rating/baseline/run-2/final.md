星評価入力コンポーネントを追加しました。

- [star-rating.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/star-rating.tsx)
- 制御・非制御入力に対応
- 星数、必須、無効状態、フォーム送信に対応
- ホバー表示、キーボード操作、アクセシブルなラジオグループを実装
- 依存関係の追加なし

検証: `npm run build` 成功。既存環境の Node 21 非推奨とバンドルサイズ警告のみです。既存の未追跡 `node_modules` は変更していません。
