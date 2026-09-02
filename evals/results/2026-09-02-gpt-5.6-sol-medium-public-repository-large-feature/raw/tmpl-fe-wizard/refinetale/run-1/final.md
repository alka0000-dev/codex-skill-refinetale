フォームウィザードをダッシュボードへ追加しました。

- 3ステップ構成：基本情報 → 勤務情報 → 確認
- ステップ単位の Zod バリデーション
- 戻る操作でも入力値を保持
- 進捗表示と `aria-current` によるアクセシビリティ対応
- 完了時にコールバックを実行し、フォームを初期化
- 外部 API や依存パッケージは追加していません

主な変更：

- [MultiStepForm.tsx](<EVAL_WORKSPACE>/frontend/src/components/Common/MultiStepForm.tsx:28)
- [index.tsx](<EVAL_WORKSPACE>/frontend/src/routes/_layout/index.tsx:21)

検証結果：

- TypeScript型検査：成功
- 変更対象のBiomeチェック：成功
- `git diff --check`：成功
- 本番ビルド：実行したものの、環境のNode.js 16.13.1がViteの要求する20.19以上を満たさず停止
- 全体リント：今回未変更の既存SVGとBiome CLI／設定バージョン差により失敗

ブラウザー操作は禁止されているため、UI操作テストは未実施です。必要な最小ケースは「不正入力では進まない」「正常入力で次へ進む」「戻っても値を保持する」「最終送信で通知後に初期状態へ戻る」で、実装上それぞれ現在ステップ検証、単一フォーム状態、完了コールバックに対応しています。
