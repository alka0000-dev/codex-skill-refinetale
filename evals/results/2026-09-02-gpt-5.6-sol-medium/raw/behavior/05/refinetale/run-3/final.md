リファクタリングは不要です。現在の実装が「編集可能な状態だけを許可する」という最小の許可リストになっています。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

将来 `archived` を型へ追加しても、自動的に編集不可になります。

```ts
type ArticleStatus = "draft" | "published" | "archived";
```

`switch`、編集不可状態の一覧、将来用の分岐などは現時点では不要です。現在のコードが要件を満たしつつ、安全側へ閉じる最小実装です。
