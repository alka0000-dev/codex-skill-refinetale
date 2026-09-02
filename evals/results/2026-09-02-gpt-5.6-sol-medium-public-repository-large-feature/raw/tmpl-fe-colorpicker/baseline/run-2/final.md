カラーピッカーコンポーネントを追加しました。

- [color-picker.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/color-picker.tsx)
- controlled／uncontrolled、フォーム属性、ARIA、disabled／invalid 状態に対応
- Chrome・Firefox のカラースウォッチを既存UIに合わせてスタイリング
- TypeScriptチェック、Biomeチェック成功

フルビルドは環境の Node.js 16.13.1 が Vite の要件（20.19+）未満のため、TypeScript成功後のVite工程で停止しました。依存関係の変更はありません。
