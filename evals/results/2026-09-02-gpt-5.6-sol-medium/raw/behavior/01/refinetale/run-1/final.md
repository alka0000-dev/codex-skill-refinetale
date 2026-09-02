作業ツリーには対象ファイルやテスト設定がなく、さらに読み取り専用のため、実際の変更・テスト実行はできませんでした。適用すべき最小リファクタリングは次の形です。

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

テストでは、少なくとも両方の公開経路について以下を維持します。

```ts
describe.each([
  [
    "API",
    () => createApiBuckets({ from: "invalid", to: "2026-01-02" }),
    () => createApiBuckets({ from: "2026-01-02", to: "2026-01-01" }),
  ],
  [
    "CSV",
    () => createCsvBuckets({ startDate: "invalid", endDate: "2026-01-02" }),
    () =>
      createCsvBuckets({
        startDate: "2026-01-02",
        endDate: "2026-01-01",
      }),
  ],
])("%s range", (_name, createWithInvalidDate, createWithInvalidRange) => {
  it("無効な日付を拒否する", () => {
    expect(createWithInvalidDate).toThrow("invalid date");
  });

  it("開始日が終了日より後の範囲を拒否する", () => {
    expect(createWithInvalidRange).toThrow("invalid range");
  });
});

it("APIとCSVの範囲を同じ内部処理へ変換する", () => {
  expect(
    createApiBuckets({ from: "2026-01-01", to: "2026-01-02" }),
  ).toEqual(
    createCsvBuckets({
      startDate: "2026-01-01",
      endDate: "2026-01-02",
    }),
  );
});
```

外部フィールド名は維持し、違いを境界で吸収しています。日付解析、検証、`createBuckets` への経路は一つになり、新しい分岐や内部型は追加していません。
