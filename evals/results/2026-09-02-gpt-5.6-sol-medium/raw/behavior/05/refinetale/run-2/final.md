リファクタリングは不要です。現在の実装がすでに最小かつ適切です。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

`draft` だけを許可する許可リスト方式なので、将来 `archived` が型へ追加されても自動的に編集不可になります。現時点で `archived`、`switch`、設定マップなどを先行追加する必要はありません。
