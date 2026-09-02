実ファイルには反映できませんでした。作業ツリーが空で、環境も読み取り専用だったためです。提示コードに対する最小のリファクタリングは次の形です。

```ts
type ApiRange = { from: string; to: string };
type CsvRange = { startDate: string; endDate: string };

function createValidatedBuckets(startValue: string, endValue: string) {
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
  return createValidatedBuckets(input.from, input.to);
}

export function createCsvBuckets(input: CsvRange) {
  return createValidatedBuckets(input.startDate, input.endDate);
}
```

テストでは両方の外部契約を通して、共通の不変条件を確認します。

```ts
const rangeCases = [
  [
    "ApiRange",
    (start: string, end: string) =>
      createApiBuckets({ from: start, to: end }),
  ],
  [
    "CsvRange",
    (start: string, end: string) =>
      createCsvBuckets({ startDate: start, endDate: end }),
  ],
] as const;

describe.each(rangeCases)("%s", (_name, createBucketsForRange) => {
  it("有効な範囲を受理する", () => {
    expect(() =>
      createBucketsForRange("2026-01-01", "2026-01-02"),
    ).not.toThrow();
  });

  it("無効な日付を拒否する", () => {
    expect(() =>
      createBucketsForRange("invalid", "2026-01-02"),
    ).toThrow("invalid date");
  });

  it("開始日が終了日より後の範囲を拒否する", () => {
    expect(() =>
      createBucketsForRange("2026-01-02", "2026-01-01"),
    ).toThrow("invalid range");
  });
});

it("APIとCSVで同じ期間から同じバケットを生成する", () => {
  expect(
    createCsvBuckets({
      startDate: "2026-01-01",
      endDate: "2026-01-02",
    }),
  ).toEqual(
    createApiBuckets({
      from: "2026-01-01",
      to: "2026-01-02",
    }),
  );
});
```

検証用の自己完結した実行では、`ApiRange` と `CsvRange` それぞれについて正常系、無効日付、逆転範囲の計6ケースが成功しました。実プロジェクトのビルド・リント・テストは、対象ファイルと設定が存在しないため未実施です。
