重複していた「文字列から日付へ変換 → 妥当性検証」を共通化できます。外部契約と例外メッセージは変更しません。

```ts
type ApiRange = { from: string; to: string };
type CsvRange = { startDate: string; endDate: string };

function parseAndValidateRange(
  startValue: string,
  endValue: string,
): [Date, Date] {
  const start = new Date(startValue);
  const end = new Date(endValue);

  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    throw new Error("invalid date");
  }

  if (start > end) {
    throw new Error("invalid range");
  }

  return [start, end];
}

export function createApiBuckets(input: ApiRange) {
  const [start, end] = parseAndValidateRange(input.from, input.to);
  return createBuckets(start, end);
}

export function createCsvBuckets(input: CsvRange) {
  const [start, end] = parseAndValidateRange(
    input.startDate,
    input.endDate,
  );
  return createBuckets(start, end);
}
```

Jest/Vitestでは、両方の外部契約について次の振る舞いを維持するテストを追加できます。

```ts
describe.each([
  {
    contract: "ApiRange",
    createValidBuckets: () =>
      createApiBuckets({
        from: "2026-01-01",
        to: "2026-01-02",
      }),
    createBucketsWithInvalidDate: () =>
      createApiBuckets({
        from: "not-a-date",
        to: "2026-01-02",
      }),
    createBucketsWithInvalidRange: () =>
      createApiBuckets({
        from: "2026-01-02",
        to: "2026-01-01",
      }),
  },
  {
    contract: "CsvRange",
    createValidBuckets: () =>
      createCsvBuckets({
        startDate: "2026-01-01",
        endDate: "2026-01-02",
      }),
    createBucketsWithInvalidDate: () =>
      createCsvBuckets({
        startDate: "not-a-date",
        endDate: "2026-01-02",
      }),
    createBucketsWithInvalidRange: () =>
      createCsvBuckets({
        startDate: "2026-01-02",
        endDate: "2026-01-01",
      }),
  },
])("$contract", ({
  createValidBuckets,
  createBucketsWithInvalidDate,
  createBucketsWithInvalidRange,
}) => {
  it("有効な範囲を受け入れる", () => {
    expect(createValidBuckets).not.toThrow();
  });

  it("無効な日付を拒否する", () => {
    expect(createBucketsWithInvalidDate).toThrow("invalid date");
  });

  it("開始日が終了日より後の範囲を拒否する", () => {
    expect(createBucketsWithInvalidRange).toThrow("invalid range");
  });
});
```

作業ディレクトリには対象ファイルやテスト環境がなく、読み取り専用でもあるため、実ファイルへの反映とテスト実行はできていません。また、`referytale` が要求する対応表と `.agent/CONTINUITY.md` も同じ理由で作成できませんでした。
