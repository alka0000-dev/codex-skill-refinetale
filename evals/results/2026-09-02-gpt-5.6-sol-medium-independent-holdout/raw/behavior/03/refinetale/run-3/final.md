## 推奨設計

Vendor固有差分を入口の「delimiter」と「CanonicalRowへの変換」に限定し、署名検証以降のパイプラインを1本にします。Vendorによる`switch`は不要です。

### 変更契約

変更する挙動:

- Vendor Bの署名付きgzip TSVを受理する。
- Vendor BをCanonicalRowへ変換して保存する。
- `CanonicalRow.vendor`に`vendor_b`を追加する。

変更しない挙動:

- Vendor Aの入力形式、変換結果、エラー、重複判定。
- HMAC検証対象は圧縮済みraw body。
- HMAC → 展開 → parse → 全行validation → dedupe → 永続化の順序。
- validation完了前には1行も保存しない。
- 永続化層へ渡す型はCanonicalRowのみ。
- 重複キーは`vendor + externalId`。

## 型と関数

```ts
const CanonicalRowSchema = z.object({
  vendor: z.enum(["vendor_a", "vendor_b"]),
  externalId: z.string().min(1),
  amount: z.string().regex(/^\d+\.\d{2}$/),
  paidAt: z.string().datetime(),
});

type CanonicalRow = z.infer<typeof CanonicalRowSchema>;
type CanonicalRowInput = z.input<typeof CanonicalRowSchema>;
type RowMapper = (record: unknown) => CanonicalRowInput;
```

共通パイプラインは引数を増やしすぎず、実際に異なる2点だけを受け取ります。

```ts
async function importDelimitedTransactions(
  input: ImportInput,
  delimiter: "," | "\t",
  mapToCanonical: RowMapper,
): Promise<void> {
  verifyHmac(input.rawBody, input.signature, input.vendorSecret);

  const bytes = await gunzipWithLimit(input.rawBody, 20 * MB);
  const records = parseDelimited(bytes, { delimiter, header: true });

  // 全行の変換・検証が完了するまで副作用を起こさない。
  const rows = records.map((record) =>
    CanonicalRowSchema.parse(mapToCanonical(record)),
  );

  const uniqueRows = dedupe(rows, {
    key: (row) => `${row.vendor}:${row.externalId}`,
  });

  await persistNewTransactions(uniqueRows);
}

export function importVendorA(input: ImportInput): Promise<void> {
  return importDelimitedTransactions(input, ",", mapVendorAToCanonical);
}

export function importVendorB(input: ImportInput): Promise<void> {
  return importDelimitedTransactions(input, "\t", mapVendorBToCanonical);
}
```

Vendor Aのmapperには手を加えません。既存処理を薄いwrapperにするだけなので、観測可能な処理順と結果は維持されます。

## Vendor B固有変換

Vendor Bの外部DTOはアダプター内だけに閉じ込めます。

```ts
const EpochMillisecondsSchema = z
  .string()
  .regex(/^-?\d+$/)
  .transform(Number)
  .refine(Number.isSafeInteger, "paid_at_ms must be a safe integer")
  .refine(
    (value) => !Number.isNaN(new Date(value).getTime()),
    "paid_at_ms is outside the supported date range",
  );

const VendorBRecordSchema = z.object({
  transaction_ref: z.string().min(1),
  total_minor: z.string().regex(/^\d+$/),
  paid_at_ms: EpochMillisecondsSchema,
});

function minorUnitsToDecimal(value: string): string {
  // Numberへ変換せず、桁落ちや指数表記を避ける。
  const digits = value.padStart(3, "0");
  const major = digits.slice(0, -2).replace(/^0+(?=\d)/, "");

  return `${major}.${digits.slice(-2)}`;
}

function mapVendorBToCanonical(record: unknown): CanonicalRowInput {
  const row = VendorBRecordSchema.parse(record);

  return {
    vendor: "vendor_b",
    externalId: row.transaction_ref,
    amount: minorUnitsToDecimal(row.total_minor),
    paidAt: new Date(row.paid_at_ms).toISOString(),
  };
}
```

変換例:

| Vendor B | Canonical |
|---|---|
| `transaction_ref: "b-92"` | `externalId: "b-92"` |
| `total_minor: "1230"` | `amount: "12.30"` |
| `total_minor: "1"` | `amount: "0.01"` |
| `total_minor: "0"` | `amount: "0.00"` |
| `paid_at_ms: "1787220900000"` | `paidAt: "2026-08-20T10:15:00.000Z"` |

`paid_at_ms`には、仕様にない「非負」の制約を追加しません。負のepoch値を拒否する必要があるなら、Vendor Bの契約として明示された時点で追加します。

## 失敗時の扱い

例外を握りつぶしたり、不正行だけをskipしたりしません。

- 署名不正: 展開・parse・永続化を実行しない。
- 展開上限超過: parse・永続化を実行しない。
- TSV parse失敗: 変換・永続化を実行しない。
- B DTO不正: Canonical変換を中止し、永続化しない。
- Canonical validation失敗: 永続化しない。
- 1行でも不正: `records.map(...)`が完了しないため、正常行も含めて0行保存。
- 永続化失敗: エラーを呼び出し元へ返す。DB障害までfile単位の原子性が必要なら、`persistNewTransactions`自身が単一トランザクションを所有する必要があります。

DB側にvendor列のenum/check制約がある場合は`vendor_b`を追加します。重複制約は引き続き`UNIQUE (vendor, external_id)`であり、`external_id`単独には変更しません。

## 最小テスト

| 対象 | ケース | 期待結果 |
|---|---|---|
| Vendor A回帰 | 既存CSVを取り込む | 従来と同じCanonicalRowを1回保存 |
| Vendor B成功 | 提示されたTSV | `vendor_b / b-92 / 12.30 / ISO日時`を保存 |
| B金額変換 | `0`, `1`, `1230`, `0001` | `0.00`, `0.01`, `12.30`, `0.01` |
| B金額不正 | `-1`, `1.2`, 空文字 | file全体をreject、保存0回 |
| B日時不正 | 小数、非数値、安全整数外、Date範囲外 | file全体をreject、保存0回 |
| B混在file | 正常行＋不正行 | 正常行も保存されず、保存0回 |
| A/B署名不正 | gzipでないraw body＋不正署名 | HMACエラー。gunzip・parse・保存0回 |
| A/B上限超過 | 正しい署名の展開超過gzip | parse・保存0回 |
| 同Vendor重複 | Bで同じrefを2行 | CanonicalRowは1行だけ保存 |
| Vendor間同一ID | AとBで同じexternalIdを順次取り込み | DBには2取引 |
| DB重複契約 | 同じvendor/externalIdを再取り込み | 既存の`persistNewTransactions`契約どおり新規作成なし |

今回はコードベースが提示されておらず設計提案のみのため、テストは未実行です。実装時は特に「不正署名の入力を非gzipにする」テストで、HMAC検証が展開より確実に先であることを直接証明できます。
