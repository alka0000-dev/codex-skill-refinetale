現状のコードがすでに適切なので、リファクタリングは不要です。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

`archived` が追加されても、この許可リスト方式なら自動的に `false` になります。未確定の状態を先回りして分岐や抽象化へ追加する必要はありません。

なお、`referytale` が要求する対応表の保存は読み取り専用環境のため実施できませんでしたが、今回は新しい名称や概念を導入しない結論としました。
