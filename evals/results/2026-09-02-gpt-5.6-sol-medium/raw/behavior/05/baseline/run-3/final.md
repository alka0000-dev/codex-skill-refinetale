現状のコードがすでに要件を満たしているため、変更は不要です。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

許可する状態を `draft` に限定しているため、将来 `archived` が追加されても自動的に `false` になります。現時点で `archived` の追加や `switch`、編集可能ステータス一覧などを導入するのは先回りした実装です。
