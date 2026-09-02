変更不要です。現状がすでに最小で、現在の仕様を正確に表現しています。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

検証結果：

- `draft` → `true`
- `published` → `false`

`archived` は未確定なので、型・分岐・テストへ先行追加しません。将来 `archived` が正式に追加されても、この許可リスト方式なら既定で編集不可になります。仕様が「archived は編集可能」と確定した場合にのみ、`canEdit` の変更を検討します。

提示された断片にはテスト環境がないため実行テストは未実施ですが、必要な最小ケースは上記2件です。追加の抽象化や `switch` は、現時点では保守対象を増やすだけです。
