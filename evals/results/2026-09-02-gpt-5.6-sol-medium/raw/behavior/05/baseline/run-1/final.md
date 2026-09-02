将来状態が追加された際に判断漏れをコンパイルエラーで検出できるよう、現在の2状態だけを明示します。`archived` 自体はまだ追加しません。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  switch (status) {
    case "draft":
      return true;
    case "published":
      return false;
    default: {
      const exhaustiveCheck: never = status;
      return exhaustiveCheck;
    }
  }
}
```

将来 `ArticleStatus` に `archived` を追加すると `exhaustiveCheck` で型エラーになり、その時点で編集可否を明示的に決められます。

なお、`referytale` の事前表は環境が読み取り専用のため保存できず、今回は新しい抽象名を導入しない最小変更として整理しました。
