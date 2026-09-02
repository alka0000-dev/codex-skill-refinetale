現状のコードは変更しないのが適切です。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

編集可能な状態を肯定条件で判定しているため、将来 `"archived"` を追加しても自動的に編集不可になります。今の段階で `archived`、状態一覧、`switch` などを追加するのは現行仕様に不要な先行実装です。

なお、`referytale` の対応表は作業環境が読み取り専用のため保存できませんでしたが、提示された仕様とコードだけを基に確認しました。
