## 提案

Vendor A/B の差分を delimiter と mapper だけに限定し、署名検証から永続化までを1本の共通パイプラインにします。

```text
compressed raw body
  → HMAC検証
  → 20 MB制限付きgunzip
  → Vendor別delimiterでparse
  → Vendor別mapper
  → CanonicalRowSchemaで全行検証
  → vendor + externalIdで重複排除
  → CanonicalRow[]を一度だけ永続化
```

### 変更契約

変更する挙動:

- Vendor B のtab区切りgzipファイルを受理する。
- `total_minor`を正確な小数文字列へ変換する。
- `paid_at_ms`をISO 8601へ変換する。
- CanonicalRowの`vendor`に`vendor_b`を追加する。

変更しない挙動:

- HMACは圧縮状態の`rawBody`に対して最初に検証する。
- 展開上限は20 MB。
- 署名、展開、parse、行変換、Canonical validationのどこかが失敗したら永続化しない。
- Vendor Aのdelimiter、mapper、検証結果を変えない。
- 永続化層には`CanonicalRow[]`だけを渡す。
- 重複判定は同じVendor内に限定する。

## 型と関数

Canonical schemaはVendor Bを追加するだけです。

```ts
const CanonicalRowSchema = z.object({
  vendor: z.enum(["vendor_a", "vendor_b"]),
  externalId: z.string().min(1),
  amount: z.string().regex(/^\d+\.\d{2}$/),
  paidAt: z.string().datetime(),
});

type CanonicalRow = z.infer<typeof CanonicalRowSchema>;
type CanonicalRowInput = z.input<typeof CanonicalRowSchema>;
type VendorRowMapper = (record: unknown) => CanonicalRowInput;
```

Vendor Bの入力DTOは取り込み境界だけに置き、永続化層へ伝播させません。

```ts
const VendorBRowSchema = z.object({
  transaction_ref: z.string().min(1),

  // Numberへ変換すると大きな値で精度を失うため、文字列のまま扱う。
  total_minor: z.string().regex(/^\d+$/),

  paid_at_ms: z.string()
    .regex(/^-?\d+$/)
    .transform(Number)
    .refine((value) => Number.isSafeInteger(value), {
      message: "paid_at_ms must be a safe integer",
    })
    .refine((value) => !Number.isNaN(new Date(value).getTime()), {
      message: "paid_at_ms is outside the supported date range",
    }),
});
```

追加する関数は共通パイプライン、Vendor B mapper、minor-unit変換の3つで十分です。

```ts
function minorUnitsToDecimal(minorUnits: string): string {
  const normalized = minorUnits.replace(/^0+(?=\d)/, "");
  const padded = normalized.padStart(3, "0");

  return `${padded.slice(0, -2)}.${padded.slice(-2)}`;
}

function mapVendorBToCanonical(record: unknown): CanonicalRowInput {
  const row = VendorBRowSchema.parse(record);

  return {
    vendor: "vendor_b",
    externalId: row.transaction_ref,
    amount: minorUnitsToDecimal(row.total_minor),
    paidAt: new Date(row.paid_at_ms).toISOString(),
  };
}

async function importDelimitedTransactions(
  input: ImportInput,
  delimiter: "," | "\t",
  mapRow: VendorRowMapper,
): Promise<void> {
  verifyHmac(input.rawBody, input.signature, input.vendorSecret);

  const bytes = await gunzipWithLimit(input.rawBody, 20 * MB);
  const records = parseDelimited(bytes, { delimiter, header: true });

  // 全行の変換・検証が完了するまで永続化を呼ばない。
  const rows = records.map((record) =>
    CanonicalRowSchema.parse(mapRow(record)),
  );

  const uniqueRows = dedupe(rows, {
    key: (row) => `${row.vendor}:${row.externalId}`,
  });

  await persistNewTransactions(uniqueRows);
}
```

公開関数は薄い入口にします。

```ts
export function importVendorA(input: ImportInput): Promise<void> {
  return importDelimitedTransactions(input, ",", mapVendorAToCanonical);
}

export function importVendorB(input: ImportInput): Promise<void> {
  return importDelimitedTransactions(input, "\t", mapVendorBToCanonical);
}
```

Vendorによる`switch`やstrategy registryは不要です。実際に異なるdelimiterとmapperを入口で渡し、その後は直ちに共通経路へ合流させます。

なお、Vendor Bの余分な列を拒否するかどうかはVendor Aの既存方針に合わせます。明示契約がないため、Bだけ`.strict()`にして新しい拒否条件を追加しません。

## Vendor B固有の変換

| 入力 | Canonical値 |
|---|---|
| `transaction_ref: "b-92"` | `externalId: "b-92"` |
| `total_minor: "1230"` | `amount: "12.30"` |
| `total_minor: "5"` | `amount: "0.05"` |
| `total_minor: "0"` | `amount: "0.00"` |
| `paid_at_ms: "1787220900000"` | `paidAt: "2026-08-20T10:15:00.000Z"` |
| 固定値 | `vendor: "vendor_b"` |

金額変換で`Number(total_minor) / 100`や`toFixed(2)`は使いません。大きな整数での丸めと指数表記を避けるためです。

## 失敗時の扱い

- 署名不正:
  `verifyHmac`で終了。展開、parse、永続化は呼ばない。
- gzip不正・20 MB超過:
  展開で終了。parse、永続化は呼ばない。
- delimiter/header/構文エラー:
  parseで終了。永続化は呼ばない。
- Vendor B DTOエラー:
  空の参照、負数・小数・非数字の`total_minor`、不正な`paid_at_ms`を拒否する。
- Canonical validationエラー:
  1行でも不正なら`rows`の構築が完了せず、永続化は呼ばれない。
- 永続化エラー:
  エラーをそのまま呼び出し元へ返す。catchして成功扱いや行単位リトライにしない。

DBエラー時にもファイル単位の部分保存を禁止する必要があるなら、`persistNewTransactions`自身が単一トランザクションであることを確認します。これはmapper側で保証できる性質ではありません。

## 最小テスト

1. Vendor B mapperの単体テスト

- サンプル行が`vendor_b / b-92 / 12.30 / 2026-08-20T10:15:00.000Z`になる。
- `0 → 0.00`、`5 → 0.05`、`1230 → 12.30`。
- 負数、小数、空文字、非数字の`total_minor`を拒否する。
- 非整数、安全整数範囲外、Date範囲外の`paid_at_ms`を拒否する。
- 必須列の欠落を拒否する。

2. Vendor A回帰テスト

- 既存サンプルが従来と同じCanonicalRowになる。
- delimiterが`,`のままである。
- 既存のエラー型や余分な列の扱いを変えない。

3. 共通安全境界テスト

Vendor A/B双方について、または共通パイプラインの既存テストで次を保証します。

| ケース | 期待結果 |
|---|---|
| 署名不正 | gunzip・parse・persistが0回 |
| 20 MB超過 | parse・persistが0回 |
| parse失敗 | persistが0回 |
| 最後の行でvalidation失敗 | persistが0回 |
| 全行正常 | persistが1回 |
| persist失敗 | エラーが伝播する |

4. 重複契約テスト

- `vendor_a:a-17`が2行なら1行だけ保存。
- `vendor_b:b-92`が2行なら1行だけ保存。
- `vendor_a:same-id`と`vendor_b:same-id`は両方保存。

今回は設計提案のみのため、コード・テストの実行や`.agent/CONTINUITY.md`の作成は行っていません。提示されたepoch値のISO変換結果のみローカルで確認済みです。
