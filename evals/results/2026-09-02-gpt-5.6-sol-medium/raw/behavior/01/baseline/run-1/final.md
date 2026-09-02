重複部分は、外部契約の内側で日付文字列を受け取る関数へ抽出できます。`new Date()` の挙動と例外メッセージも維持されます。

```ts
type ApiRange = { from: string; to: string };
type CsvRange = { startDate: string; endDate: string };

function createBucketsFromDateStrings(
  startDateString: string,
  endDateString: string,
) {
  const start = new Date(startDateString);
  const end = new Date(endDateString);

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

Jestであれば、両方の外部契約に同じ振る舞いを適用できます。

```ts
describe.each([
  {
    name: "API range",
    createBuckets: (start: string, end: string) =>
      createApiBuckets({ from: start, to: end }),
  },
  {
    name: "CSV range",
    createBuckets: (start: string, end: string) =>
      createCsvBuckets({ startDate: start, endDate: end }),
  },
])("$name", ({ createBuckets }) => {
  it.each([
    ["invalid", "2026-01-31"],
    ["2026-01-01", "invalid"],
  ])(
    "無効な日付を拒否する",
    (start, end) => {
      expect(() => createBuckets(start, end)).toThrow("invalid date");
    },
  );

  it("開始日が終了日より後の範囲を拒否する", () => {
    expect(() =>
      createBuckets("2026-02-01", "2026-01-31"),
    ).toThrow("invalid range");
  });
});
```

作業ディレクトリには対象ファイルやテストがなく、さらに読み取り専用だったため、実ファイルへの反映とテスト実行はできませんでした。
