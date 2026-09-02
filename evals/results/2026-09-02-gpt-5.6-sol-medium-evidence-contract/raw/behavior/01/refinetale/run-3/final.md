ワークスペースが読み取り専用かつ実装・テストファイルが存在しないため、実ファイルへの適用はできませんでした。以下がそのまま置き換えられる最小実装です。

```ts
type ApiRange = { from: string; to: string };
type CsvRange = { startDate: string; endDate: string };

function createBucketsFromDateStrings(startValue: string, endValue: string) {
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
  return createBucketsFromDateStrings(input.from, input.to);
}

export function createCsvBuckets(input: CsvRange) {
  return createBucketsFromDateStrings(input.startDate, input.endDate);
}
```

Jestテストの更新例です（import先は実際のファイル名に合わせてください）。

```ts
import { createApiBuckets, createCsvBuckets } from "./ranges";

type CreateBuckets = (start: string, end: string) => unknown;

const adapters: ReadonlyArray<readonly [string, CreateBuckets]> = [
  [
    "API",
    (start, end) => createApiBuckets({ from: start, to: end }),
  ],
  [
    "CSV",
    (start, end) =>
      createCsvBuckets({ startDate: start, endDate: end }),
  ],
];

it("APIとCSVのフィールドを同じ日付範囲へ変換する", () => {
  expect(
    createApiBuckets({ from: "2026-01-01", to: "2026-01-02" }),
  ).toEqual(
    createCsvBuckets({
      startDate: "2026-01-01",
      endDate: "2026-01-02",
    }),
  );
});

describe.each(adapters)("%s", (_name, createBuckets) => {
  it.each([
    ["invalid", "2026-01-02"],
    ["2026-01-01", "invalid"],
  ])("無効な日付 %s〜%s を拒否する", (start, end) => {
    expect(() => createBuckets(start, end)).toThrow("invalid date");
  });

  it("開始日が終了日より後の範囲を拒否する", () => {
    expect(() =>
      createBuckets("2026-01-02", "2026-01-01"),
    ).toThrow("invalid range");
  });

  it("開始日と終了日が同じ範囲を受理する", () => {
    expect(() =>
      createBuckets("2026-01-01", "2026-01-01"),
    ).not.toThrow();
  });
});
```

検証用のインライン実行では、API/CSVの正常系、両境界の無効日付4件、逆転範囲2件の計8件が成功しました。外部フィールド名とエラー文言は変更せず、重複していた解析・検証経路だけを共通化しています。実プロジェクトのビルド・lint・テスト実行には、実装ファイルと書き込み可能なワークスペースが必要です。
