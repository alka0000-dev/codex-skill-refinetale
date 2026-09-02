作業ディレクトリに実装・テストファイルがなく、読み取り専用だったため、実ファイルへの適用はできませんでした。適用すべき最小リファクタリングは次のとおりです。

```ts
type ApiRange = { from: string; to: string };
type CsvRange = { startDate: string; endDate: string };

function createBucketsForRange(startValue: string, endValue: string) {
  const start = new Date(startValue);
  const end = new Date(endValue);

  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    throw new Error("invalid date");
  }
  if (start > end) throw new Error("invalid range");

  return createBuckets(start, end);
}

export function createApiBuckets(input: ApiRange) {
  return createBucketsForRange(input.from, input.to);
}

export function createCsvBuckets(input: CsvRange) {
  return createBucketsForRange(input.startDate, input.endDate);
}
```

API/CSV 固有の処理は外部フィールドから値を取り出す箇所だけです。日付変換、検証、バケット生成は一つの経路へ集約しています。

必要な契約テスト例です。

```ts
describe.each([
  {
    name: "API",
    valid: () =>
      createApiBuckets({ from: "2026-01-01", to: "2026-01-02" }),
    invalidStart: () =>
      createApiBuckets({ from: "invalid", to: "2026-01-02" }),
    invalidEnd: () =>
      createApiBuckets({ from: "2026-01-01", to: "invalid" }),
    reversed: () =>
      createApiBuckets({ from: "2026-01-02", to: "2026-01-01" }),
  },
  {
    name: "CSV",
    valid: () =>
      createCsvBuckets({
        startDate: "2026-01-01",
        endDate: "2026-01-02",
      }),
    invalidStart: () =>
      createCsvBuckets({
        startDate: "invalid",
        endDate: "2026-01-02",
      }),
    invalidEnd: () =>
      createCsvBuckets({
        startDate: "2026-01-01",
        endDate: "invalid",
      }),
    reversed: () =>
      createCsvBuckets({
        startDate: "2026-01-02",
        endDate: "2026-01-01",
      }),
  },
])("$name range", ({ valid, invalidStart, invalidEnd, reversed }) => {
  test("有効な範囲を受理する", () => {
    expect(valid).not.toThrow();
  });

  test.each([invalidStart, invalidEnd])("無効な日付を拒否する", (run) => {
    expect(run).toThrow("invalid date");
  });

  test("開始日が終了日より後の範囲を拒否する", () => {
    expect(reversed).toThrow("invalid range");
  });
});
```

同等の JavaScript 実装で8件の契約チェックを実行し、すべて成功しました。拒否された入力では `createBuckets` が呼ばれないことも確認済みです。実プロジェクトのビルド・リント・テストは対象ファイルと設定が存在しないため未実施です。
