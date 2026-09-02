変更は不要です。現在の実装は許可する状態を `draft` に限定しているため、将来 `archived` が追加されても自動的に編集不可になります。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

`switch` や編集不可ステータスの列挙を追加すると、未確定の将来仕様を先回りすることになります。現状の許可リスト方式が、現在の仕様を最小かつ安全に表現しています。新しい名称も不要だったため、`referytale` による対応表の作成対象にはしていません。
