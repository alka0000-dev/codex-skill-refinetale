変更は不要です。現状がすでに、現在の仕様を最も直接的に表現しています。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

- 変更する挙動: なし
- 維持する挙動: `draft` は編集可能、`published` は編集不可
- 正本: 編集可否は `canEdit` の許可条件 `status === "draft"`
- `archived` は仕様確定前なので型・分岐・テストへ追加しない
- 将来 `archived` が型へ追加されても、この許可リスト方式なら明示的に許可されない限り編集不可になる

検証環境が提示されていないため未実行ですが、必要な最小テストは `canEdit("draft") === true` と `canEdit("published") === false` です。`archived` の編集可否が正式に確定した時点で判断を見直します。
