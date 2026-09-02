結論として、リファクタリングは不要です。現状が最小かつ安全です。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

変更契約：

- `draft` は編集可能：`true`
- `published` は編集不可：`false`
- 未確定の `archived` や追加の分岐・抽象化は導入しない

検証結果：

- `draft: true`
- `published: false`
- 検証コマンドは終了コード `0`

`archived` が実際に型へ追加され、その編集可否が仕様として確定した時点で見直します。編集不可なら、この判定式は変更せずそのまま対応できます。
