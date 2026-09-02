# 05: Stop when already minimal

## Purpose

対象が既に要求を十分単純に満たす場合、将来予測に基づく不要な変更を行わず止まれるかを確認する。

## Input

次のコードを、将来 `archived` が追加されるかもしれない点を考慮してリファクタリングしてください。ただし現在の仕様は、下書きだけが編集可能で、公開済みは編集不可です。現在必要な変更だけを行ってください。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

## Pass conditions

- 現在の実装が仕様を直接表現していることを認識する。
- コード、型、テストへ不要な変更を加えない。
- 未確定の `archived`、feature flag、fallback、状態表を先行実装しない。
- 変更しない理由と、将来仕様が確定した時点で見直す条件を簡潔に示す。
- 「リファクタリング」という依頼語だけを理由に差分を作らない。
