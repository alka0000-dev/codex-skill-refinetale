You are grading six anonymized answers to one coding-skill evaluation. Apply the rubric strictly and return only the requested structured result. Do not guess which condition produced an answer.

# 01: Normalize at the boundary

## Purpose

外部形式を維持したまま境界で正規化し、内部の検証と処理を1本化できるかを確認する。

## Input

次のTypeScriptコードをリファクタリングしてください。`ApiRange` と `CsvRange` は外部契約なので、フィールド名を変更してはいけません。無効な日付と開始日が終了日より後の範囲は、これまでどおり拒否してください。必要なテストも更新してください。

```ts
type ApiRange = { from: string; to: string };
type CsvRange = { startDate: string; endDate: string };

export function createApiBuckets(input: ApiRange) {
  const start = new Date(input.from);
  const end = new Date(input.to);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    throw new Error("invalid date");
  }
  if (start > end) throw new Error("invalid range");
  return createBuckets(start, end);
}

export function createCsvBuckets(input: CsvRange) {
  const start = new Date(input.startDate);
  const end = new Date(input.endDate);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    throw new Error("invalid date");
  }
  if (start > end) throw new Error("invalid range");
  return createBuckets(start, end);
}
```

## Pass conditions

- `ApiRange` と `CsvRange` の外部フィールド名を維持する。
- 境界で共通の内部表現へ正規化する。
- 日付変換、検証、bucket生成の共通経路を1つにする。
- `invalid date` と `invalid range` の契約を維持する。
- 公開経路の振る舞いを確認するテストを残し、内部helperごとの重複テストを増やさない。


## Scoring rules

Score each item as `1` (satisfied), `0` (not satisfied), or `-1` (not applicable).

- G1 Contract fidelity: preserves requested external contracts, inputs, outputs, errors, and events.
- G2 Change contract: clearly handles what changes, what must not change, and allowed variation.
- G3 Canonical ownership: keeps one source of truth for the same state or decision.
- G4 Variation isolation: isolates only real differences and does not duplicate common processing.
- G5 No speculative implementation: adds no unrequested future extension, fallback, flag, or abstraction.
- G6 Safety preservation: does not weaken authorization, validation, audit, or failure behavior.
- G7 Verification and stop: identifies necessary verification and stops when no change is needed.

Use only evidence present in the candidate's final answer. Do not reward a promise to finish later.
The workspace intentionally lacked source files and was read-only. Do not fail a candidate merely
for reporting that limitation if it still provides the requested concrete solution and verification
plan. Missing implementation guidance or missing required test coverage can still fail the relevant
criterion. `overall_pass` requires every applicable G score and the fixture-specific conditions to
equal 1. G1 is always critical; G6 is critical when applicable.


## Candidate A

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

## Candidate B

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

## Candidate C

作業ディレクトリには実装・テスト・`package.json` がなく、さらに読み取り専用のため、ファイルへの適用とテスト実行はできませんでした。適用すべき最小リファクタリングは次です。

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

テストは既存の正常系を残し、検証契約が両方の入口で維持されることを確認します。Jestなら次のように重複を抑えられます。

```ts
const bucketCreators: Array<
  [string, (start: string, end: string) => unknown]
> = [
  [
    "API range",
    (start, end) => createApiBuckets({ from: start, to: end }),
  ],
  [
    "CSV range",
    (start, end) =>
      createCsvBuckets({ startDate: start, endDate: end }),
  ],
];

describe.each(bucketCreators)("%s", (_, createBucketsForRange) => {
  it("rejects an invalid date", () => {
    expect(() =>
      createBucketsForRange("invalid", "2026-09-02"),
    ).toThrow("invalid date");
  });

  it("rejects a range whose start is after its end", () => {
    expect(() =>
      createBucketsForRange("2026-09-03", "2026-09-02"),
    ).toThrow("invalid range");
  });
});
```

外部フィールド名は維持し、新しい内部Range型も増やさず、異なる入力名だけを境界で位置引数へ変換しています。`.agent/CONTINUITY.md` も読み取り専用のため作成できませんでした。

## Candidate D

作業を開始しましたが、ワークスペースには `.git` しかなく、TypeScriptファイル・テスト・`package.json` がありません。また、現在の環境は読み取り専用です。

そのため、以下を実行できませんでした。

- 対象コードの特定・編集
- テストフレームワークの確認とテスト更新
- ビルド、リント、型チェック、テスト
- `.agent/CONTINUITY.md` と `referytale` の指示対象表の作成

対象プロジェクトまたは実装・テストファイルをワークスペースへ配置し、書き込み可能な状態で再実行してください。ファイル名が分かる場合は、そのパスも指定してください。

## Candidate E

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

## Candidate F

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
