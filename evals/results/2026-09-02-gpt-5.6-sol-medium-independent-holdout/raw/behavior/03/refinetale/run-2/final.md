## 提案

Vendor A/B の入口関数は分けたまま、署名検証以降の安全な処理順を1つの共通関数へ集約します。Vendor差分は `delimiter` と `mapToCanonical` だけです。Vendor判定用の `switch` や共通DTOは追加しません。

### 変更契約

変更する挙動:

- `importVendorB` でtab区切りのVendor Bファイルを受理する。
- `total_minor` を2桁小数文字列へ変換する。
- `paid_at_ms` をISO日時へ変換する。
- 正規化後の `vendor` は `"vendor_b"` になる。

変更しない挙動:

- Vendor Aの列、変換結果、処理順。
- HMACは圧縮された `rawBody` に対して最初に検証する。
- 展開上限は20 MB。
- 1行でもparse/validationに失敗すれば永続化を呼ばない。
- 永続化層へ渡すのは `CanonicalRow` だけ。
- 重複キーは `vendor + externalId`。
- 永続化エラーは握りつぶさず呼び出し元へ返す。

## 型と関数

### 1. 正規化型へVendor Bを追加

```ts
export const CanonicalRowSchema = z.object({
  vendor: z.enum(["vendor_a", "vendor_b"]),
  externalId: z.string().min(1),
  amount: z.string().regex(/^\d+\.\d{2}$/),
  paidAt: z.string().datetime(),
});

export type CanonicalRow = z.infer<typeof CanonicalRowSchema>;
```

変更はenum値の追加だけです。Vendor固有DTOを永続化層や後続処理へ公開しません。

### 2. Vendor B境界の検証と変換

```ts
const MinorUnitsSchema = z
  .string()
  .regex(/^\d+$/)
  .transform((value) => {
    const normalized = value.replace(/^0+(?=\d)/, "");
    const padded = normalized.padStart(3, "0");

    return `${padded.slice(0, -2)}.${padded.slice(-2)}`;
  });

const EpochMillisecondsSchema = z
  .string()
  .regex(/^\d+$/)
  .transform((value, context) => {
    const milliseconds = Number(value);
    const date = new Date(milliseconds);

    if (
      !Number.isSafeInteger(milliseconds) ||
      Number.isNaN(date.getTime())
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "paid_at_ms must be valid Unix epoch milliseconds",
      });
      return z.NEVER;
    }

    return date.toISOString();
  });

const VendorBRowSchema = z.object({
  transaction_ref: z.string().min(1),
  total_minor: MinorUnitsSchema,
  paid_at_ms: EpochMillisecondsSchema,
});

function mapVendorBToCanonical(record: unknown) {
  const row = VendorBRowSchema.parse(record);

  return {
    vendor: "vendor_b" as const,
    externalId: row.transaction_ref,
    amount: row.total_minor,
    paidAt: row.paid_at_ms,
  };
}
```

変換例:

| Vendor B入力 | Canonical値 |
|---|---|
| `total_minor: "0"` | `amount: "0.00"` |
| `total_minor: "5"` | `amount: "0.05"` |
| `total_minor: "1230"` | `amount: "12.30"` |
| `paid_at_ms: "1787220900000"` | `paidAt: "2026-08-20T10:15:00.000Z"` |

金額は `Number` に変換しません。これにより、大きな整数文字列でも浮動小数点の丸めを持ち込みません。

### 3. 安全境界を共通処理にする

```ts
type Delimiter = "," | "\t";

type MapToCanonical = (
  record: unknown,
) => z.input<typeof CanonicalRowSchema>;

async function importTransactions(
  input: ImportInput,
  delimiter: Delimiter,
  mapToCanonical: MapToCanonical,
) {
  verifyHmac(input.rawBody, input.signature, input.vendorSecret);

  const bytes = await gunzipWithLimit(input.rawBody, 20 * MB);

  const records = parseDelimited(bytes, {
    delimiter,
    header: true,
  });

  const rows = records
    .map(mapToCanonical)
    .map((row) => CanonicalRowSchema.parse(row));

  const uniqueRows = dedupe(rows, {
    key: (row) => `${row.vendor}:${row.externalId}`,
  });

  await persistNewTransactions(uniqueRows);
}
```

入口関数は薄いラッパーにします。

```ts
export function importVendorA(input: ImportInput) {
  return importTransactions(input, ",", mapVendorAToCanonical);
}

export function importVendorB(input: ImportInput) {
  return importTransactions(input, "\t", mapVendorBToCanonical);
}
```

Vendor Aのmapperは変更しません。Vendor判定の分岐もありません。入口で選ばれたmapperは正規化後すぐ共通の `CanonicalRow[]` へ合流します。

## 処理順と失敗時の扱い

```text
compressed rawBody
  → HMAC検証
  → 20 MB制限付きgunzip
  → vendor固有delimiterでparse
  → vendor固有の入力検証・変換
  → CanonicalRowSchemaで共通検証
  → vendor + externalIdで重複排除
  → 1回だけ永続化
```

各失敗の結果:

- 署名不正: gunzip、parse、永続化を実行しない。
- 展開上限超過: parse、永続化を実行しない。
- TSV/CSV parse失敗: mapper、永続化を実行しない。
- 必須列欠落・不正金額・不正日時: `records.map(...)` が完了しないため永続化を実行しない。
- Canonical検証失敗: 永続化を実行しない。
- 永続化失敗: エラーをそのまま伝播し、独自retryや部分fallbackは追加しない。

すべての行を配列へ正規化・検証した後に初めて `persistNewTransactions` を呼ぶため、「2行目が不正でも1行目を保存しない」が維持されます。

なお、永続化処理そのものの途中失敗に対するDB原子性は、既存repositoryのトランザクション契約に属します。今回の入力形式追加では変更しません。

## 最小テスト

実装ファイルが提示されておらず、作業ディレクトリも空だったためテストは未実施です。実装時には次を最低限追加します。

1. Vendor A回帰

- 既存CSVから従来と同じCanonicalRowが保存される。
- `vendor: "vendor_a"`、`amount: "12.30"`、元の日時表現が有効であることを確認。

2. Vendor B成功

- 提示されたTSVから次が1回保存される。

```ts
{
  vendor: "vendor_b",
  externalId: "b-92",
  amount: "12.30",
  paidAt: "2026-08-20T10:15:00.000Z",
}
```

3. Vendor B固有の境界値

- `"0"` → `"0.00"`
- `"5"` → `"0.05"`
- `"1230"` → `"12.30"`
- `"-1"`、`"1.2"`、空文字はvalidation error。
- 小数でない、範囲外の `paid_at_ms` はvalidation error。

4. 全件原子性

- 2行のVendor Bファイルで2行目を不正にし、`persistNewTransactions` が0回であることを確認。

5. 安全境界をVendor A/Bで共通確認

`it.each` で両入口に対して確認します。

- 署名不正なら `gunzipWithLimit` と永続化が0回。
- 20 MB超過ならparseと永続化が0回。
- parse/validation失敗なら永続化が0回。
- 成功時のみ永続化が1回。

6. 重複契約

- 同一Vendor・同一`externalId`は1件。
- `"vendor_a:x"` と `"vendor_b:x"` は2件として残る。

この設計では、追加される正本はVendor Bの入力スキーマとmapperだけです。安全な処理順、Canonical検証、重複排除、永続化経路は単一のまま維持されます。
