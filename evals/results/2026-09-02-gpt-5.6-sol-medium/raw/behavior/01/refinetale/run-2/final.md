作業ディレクトリには実装・テスト・`package.json` がなく、さらに読み取り専用のため、ファイルへの適用とテスト実行はできませんでした。適用すべき最小リファクタリングは次です。

```ts
type ApiRange = { from: string; to: string };
type CsvRange = { startDate: string; endDate: string };

function createBucketsFromRange(startValue: string, endValue: string) {
  const start = new Date(startValue);
  const end = new Date(endValue);

  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    throw new Error("invalid date");
  }

  if (start > end) {
    throw new Error("invalid range");
  }

  return createBuckets(start, end);
}

export function createApiBuckets(input: ApiRange) {
  return createBucketsFromRange(input.from, input.to);
}

export function createCsvBuckets(input: CsvRange) {
  return createBucketsFromRange(input.startDate, input.endDate);
}
```

テストは既存の正常系を残し、検証契約が両方の入口で維持されることを確認します。Jestなら次のように重複を抑えられます。

```ts
const bucketCreators: Array<
  [string, (start: string, end: string) => unknown]
> = [
  [
    "API range",
    (start, end) => createApiBuckets({ from: start, to: end }),
  ],
  [
    "CSV range",
    (start, end) =>
      createCsvBuckets({ startDate: start, endDate: end }),
  ],
];

describe.each(bucketCreators)("%s", (_, createBucketsForRange) => {
  it("rejects an invalid date", () => {
    expect(() =>
      createBucketsForRange("invalid", "2026-09-02"),
    ).toThrow("invalid date");
  });

  it("rejects a range whose start is after its end", () => {
    expect(() =>
      createBucketsForRange("2026-09-03", "2026-09-02"),
    ).toThrow("invalid range");
  });
});
```

外部フィールド名は維持し、新しい内部Range型も増やさず、異なる入力名だけを境界で位置引数へ変換しています。`.agent/CONTINUITY.md` も読み取り専用のため作成できませんでした。
