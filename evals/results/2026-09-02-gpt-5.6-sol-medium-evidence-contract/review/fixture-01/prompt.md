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

## Candidate B

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

## Candidate C

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

## Candidate D

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

## Candidate E

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

## Candidate F

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
