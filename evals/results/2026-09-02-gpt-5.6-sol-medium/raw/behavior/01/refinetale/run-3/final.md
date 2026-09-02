作業ディレクトリにソース／テストがなく、さらに読み取り専用だったため、実ファイルへの反映とテスト実行はできませんでした。適用すべき最小リファクタリングは以下です。

```ts
type ApiRange = { from: string; to: string };
type CsvRange = { startDate: string; endDate: string };

function createBucketsFromDateStrings(startDate: string, endDate: string) {
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

テストは両方の外部契約を同じ仕様テーブルで検証できます。

```ts
const bucketCreators = [
  [
    "API",
    (start: string, end: string) =>
      createApiBuckets({ from: start, to: end }),
  ],
  [
    "CSV",
    (start: string, end: string) =>
      createCsvBuckets({ startDate: start, endDate: end }),
  ],
] as const;

describe.each(bucketCreators)("%s range", (_, create) => {
  it("有効な範囲を受け付ける", () => {
    expect(() => create("2026-01-01", "2026-01-02")).not.toThrow();
  });

  it("無効な日付を拒否する", () => {
    expect(() => create("invalid", "2026-01-02")).toThrow("invalid date");
  });

  it("開始日が終了日より後の範囲を拒否する", () => {
    expect(() => create("2026-01-02", "2026-01-01")).toThrow("invalid range");
  });
});
```

入力フィールド名とエラー契約は維持され、重複していた日付変換・検証・生成経路だけが単一の正本へ統合されます。
