重複する日付変換・検証だけを内部関数へ集約します。外部契約のフィールド名と例外メッセージは変わりません。

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

Jestでは両方の外部契約に同じ振る舞いを要求します。

```ts
describe.each([
  [
    "ApiRange",
    (startDate: string, endDate: string) =>
      createApiBuckets({ from: startDate, to: endDate }),
  ],
  [
    "CsvRange",
    (startDate: string, endDate: string) =>
      createCsvBuckets({ startDate, endDate }),
  ],
])("%s", (_contractName, createBucketsForRange) => {
  it("有効な期間を受け入れる", () => {
    expect(() =>
      createBucketsForRange("2026-01-01", "2026-01-31"),
    ).not.toThrow();
  });

  it("開始日が無効な場合は拒否する", () => {
    expect(() =>
      createBucketsForRange("not-a-date", "2026-01-31"),
    ).toThrow("invalid date");
  });

  it("終了日が無効な場合は拒否する", () => {
    expect(() =>
      createBucketsForRange("2026-01-01", "not-a-date"),
    ).toThrow("invalid date");
  });

  it("開始日が終了日より後の場合は拒否する", () => {
    expect(() =>
      createBucketsForRange("2026-02-01", "2026-01-31"),
    ).toThrow("invalid range");
  });

  it("開始日と終了日が同じ場合は受け入れる", () => {
    expect(() =>
      createBucketsForRange("2026-01-01", "2026-01-01"),
    ).not.toThrow();
  });
});
```

ワークスペースには対象ファイルや有効な `HEAD` がなく、かつ読み取り専用だったため、実ファイルの変更・テスト実行・`referytale` の対応表および `.agent/CONTINUITY.md` の作成はできませんでした。上記はそのまま適用できる変更案です。
