# 01: Normalize at the boundary

## Purpose

外部形式を維持したまま境界で正規化し、内部の検証と処理を1本化できるかを確認する。

## Input

次のTypeScriptコードをリファクタリングしてください。`ApiRange` と `CsvRange` は外部契約なので、フィールド名を変更してはいけません。無効な日付と開始日が終了日より後の範囲は、これまでどおり拒否してください。必要なテストも更新してください。

```ts
type ApiRange = { from: string; to: string };
type CsvRange = { startDate: string; endDate: string };

export function createApiBuckets(input: ApiRange) {
  const start = new Date(input.from);
  const end = new Date(input.to);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    throw new Error("invalid date");
  }
  if (start > end) throw new Error("invalid range");
  return createBuckets(start, end);
}

export function createCsvBuckets(input: CsvRange) {
  const start = new Date(input.startDate);
  const end = new Date(input.endDate);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    throw new Error("invalid date");
  }
  if (start > end) throw new Error("invalid range");
  return createBuckets(start, end);
}
```

## Pass conditions

- `ApiRange` と `CsvRange` の外部フィールド名を維持する。
- 境界で共通の内部表現へ正規化する。
- 日付変換、検証、bucket生成の共通経路を1つにする。
- `invalid date` と `invalid range` の契約を維持する。
- 公開経路の振る舞いを確認するテストを残し、内部helperごとの重複テストを増やさない。
