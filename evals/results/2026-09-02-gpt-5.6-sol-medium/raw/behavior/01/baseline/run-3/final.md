作業ディレクトリが空で読み取り専用だったため、実ファイルへの反映とテスト実行はできませんでした。適用する最小差分は次のとおりです。

```ts
type ApiRange = { from: string; to: string };
type CsvRange = { startDate: string; endDate: string };

function createBucketsFromDateStrings(
  startDate: string,
  endDate: string,
) {
  const start = new Date(startDate);
  const end = new Date(endDate);

  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    throw new Error("invalid date");
  }

  if (start > end) {
    throw new Error("invalid range");
  }

  return createBuckets(start, end);
}

export function createApiBuckets(input: ApiRange) {
  return createBucketsFromDateStrings(input.from, input.to);
}

export function createCsvBuckets(input: CsvRange) {
  return createBucketsFromDateStrings(input.startDate, input.endDate);
}
```

Jestテストには、少なくとも以下を追加・維持します。

```ts
describe.each([
  {
    name: "API range",
    createBuckets: (startDate: string, endDate: string) =>
      createApiBuckets({ from: startDate, to: endDate }),
  },
  {
    name: "CSV range",
    createBuckets: (startDate: string, endDate: string) =>
      createCsvBuckets({ startDate, endDate }),
  },
])("$name", ({ createBuckets }) => {
  it.each([
    ["invalid start date", "invalid", "2026-01-02"],
    ["invalid end date", "2026-01-01", "invalid"],
  ])("rejects %s", (_, startDate, endDate) => {
    expect(() => createBuckets(startDate, endDate)).toThrow("invalid date");
  });

  it("rejects a start date later than the end date", () => {
    expect(() =>
      createBuckets("2026-01-02", "2026-01-01"),
    ).toThrow("invalid range");
  });

  it("accepts equal start and end dates", () => {
    expect(() =>
      createBuckets("2026-01-01", "2026-01-01"),
    ).not.toThrow();
  });
});

it("maps API and CSV contracts to the same date range", () => {
  expect(
    createApiBuckets({
      from: "2026-01-01",
      to: "2026-01-03",
    }),
  ).toEqual(
    createCsvBuckets({
      startDate: "2026-01-01",
      endDate: "2026-01-03",
    }),
  );
});
```

`ApiRange` と `CsvRange` は境界の型としてそのまま残し、共通化するのはフィールドを読み取った後の検証と生成処理だけです。エラー文言、検証順序、開始日と終了日が同日の場合に許可する挙動も維持されます。なお `referytale` の事前対応表は、読み取り専用環境のため保存できませんでした。
