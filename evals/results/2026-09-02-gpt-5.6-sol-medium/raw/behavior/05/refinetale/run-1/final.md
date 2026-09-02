リファクタリング不要です。現状の実装がすでに最小で、将来 `archived` が追加されても自然に編集不可になります。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

`archived` が正式な仕様になった時点で、型だけを変更します。

```ts
type ArticleStatus = "draft" | "published" | "archived";
```

`canEdit` は変更不要です。現時点で `archived`、分岐、許可状態の配列などを追加すると、未確定仕様の先行実装になるため行いません。
