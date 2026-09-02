色ピッカーを追加しました: [color-picker.tsx](<EVAL_WORKSPACE>/frontend/src/components/ui/color-picker.tsx)

- ネイティブ `input[type="color"]` を使用
- controlled / uncontrolled の両方に対応
- `type` の上書きを型・実行時ともに防止
- focus、invalid、disabled、ブラウザ別スウォッチを既存UI規約に合わせて実装
- 依存関係や既存画面は変更なし

検証結果:

- TypeScript型チェック: 成功
- 空白エラーチェック: 成功
- Vite build: Node.js 16.13.1のため未完了（Viteは20.19以上が必要）
- lint: 既存のBiomeバージョン不一致とSVG 8件の既存エラーで失敗。新規UIファイルは設定上lint対象外
- ブラウザ確認: 指示に従い未実施。最小確認ケースは「色変更で`onChange`が発火し値が更新される」「disabled時は操作できない」です。
