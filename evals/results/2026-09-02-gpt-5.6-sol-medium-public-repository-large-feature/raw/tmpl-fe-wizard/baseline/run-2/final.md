複数ステップ式フォームウィザードを追加しました。

- 3ステップ構成：ワークスペース情報 → チーム設定 → 確認
- ステップ単位のZod検証と入力値保持
- 戻る・次へ・完了・リセット操作
- レスポンシブ表示とアクセシブルな進捗表示
- 保存処理を接続できる型付き `onComplete` コールバック
- ダッシュボードへ組み込み

変更箇所：

- [WorkspaceSetupWizard.tsx](<EVAL_WORKSPACE>/frontend/src/components/Common/WorkspaceSetupWizard.tsx:182)
- [index.tsx](<EVAL_WORKSPACE>/frontend/src/routes/_layout/index.tsx:30)

検証結果：

- TypeScript型チェック：成功
- 対象ファイルのBiomeチェック：成功
- `git diff --check`：成功
- Viteビルド：環境のNode.js 16.13.1が古いためバンドル段階のみ実行不可（Node.js 20.19+が必要）
- 指示どおり、依存追加・サーバー起動・ブラウザー操作は実施していません。
