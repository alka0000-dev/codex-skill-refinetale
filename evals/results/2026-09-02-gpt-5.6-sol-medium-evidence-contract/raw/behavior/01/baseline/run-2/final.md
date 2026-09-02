作業ディレクトリが空かつ読み取り専用だったため、実ファイルへの反映とテスト実行はできませんでした。`referytale` の対応表や `.agent/CONTINUITY.md` も作成できない状態です。

適用するリファクタリングは次の形です。外部フィールド名と例外メッセージを維持し、共通処理だけを抽出します。

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

Jestテストには、両方の外部契約に同じ拒否条件を適用できていることを追加します。

```ts
describe.each([
  {
    contract: "ApiRange",
    create: (startDate: string, endDate: string) =>
      createApiBuckets({ from: startDate, to: endDate }),
  },
  {
    contract: "CsvRange",
    create: (startDate: string, endDate: string) =>
      createCsvBuckets({ startDate, endDate }),
  },
])("$contract", ({ create }) => {
  it("開始日が無効な場合は拒否する", () => {
    expect(() => create("not-a-date", "2024-01-02")).toThrow(
      "invalid date",
    );
  });

  it("終了日が無効な場合は拒否する", () => {
    expect(() => create("2024-01-01", "not-a-date")).toThrow(
      "invalid date",
    );
  });

  it("開始日が終了日より後の場合は拒否する", () => {
    expect(() => create("2024-01-02", "2024-01-01")).toThrow(
      "invalid range",
    );
  });

  it("開始日と終了日が同じ場合は受け入れる", () => {
    expect(() => create("2024-01-01", "2024-01-01")).not.toThrow();
  });
});
```

対象ファイルを含む書き込み可能なワークスペースがあれば、実際の既存テスト形式に合わせて反映・lint・型チェック・テスト実行まで可能です。
