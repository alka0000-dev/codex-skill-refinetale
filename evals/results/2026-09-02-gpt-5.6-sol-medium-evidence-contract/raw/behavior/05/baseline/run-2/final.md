現状のコードはすでに「編集可能な状態を許可リストで判定」しているため、変更不要です。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

将来 `"archived"` を追加しても、自動的に編集不可になります。

```ts
type ArticleStatus = "draft" | "published" | "archived";
```

未確定の将来仕様に備えた `switch` や編集可能状態の配列は、現時点では過剰な抽象化です。今回はリファクタリングしないことが、最小かつ安全な変更です。
