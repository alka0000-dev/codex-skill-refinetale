推奨は、Vendor Aの関数を共通化せずそのまま残し、Vendor B用の入口と変換関数だけを追加する設計です。重複は数行増えますが、Vendor Aの処理順や例外挙動を変えるリスクが最も小さくなります。

## 変更する型

正規化型ではVendorだけを追加します。

```ts
const CanonicalRowSchema = z.object({
  vendor: z.enum(["vendor_a", "vendor_b"]),
  externalId: z.string().min(1),
  amount: z.string().regex(/^\d+\.\d{2}$/),
  paidAt: z.string().datetime(),
});

type CanonicalRow = z.infer<typeof CanonicalRowSchema>;
```

Vendor Bの入力列は、正規化型とは別のDTOとして検証します。

```ts
const MAX_DATE_MS = 8_640_000_000_000_000n;
const MIN_DATE_MS = -MAX_DATE_MS;

const VendorBRecordSchema = z
  .object({
    transaction_ref: z.string().min(1),
    total_minor: z.string().regex(/^\d+$/),
    paid_at_ms: z
      .string()
      .regex(/^-?\d+$/)
      .refine((value) => {
        const milliseconds = BigInt(value);
        return milliseconds >= MIN_DATE_MS && milliseconds <= MAX_DATE_MS;
      }, "paid_at_ms is outside the supported Date range"),
  })
  .strict();

type VendorBRecord = z.infer<typeof VendorBRecordSchema>;
```

`paid_at_ms`について、Vendor Bが非負値だけを保証する仕様なら、正規表現を`/^\d+$/`へ狭めます。提示仕様だけでは1970年以前を明確に禁止していないため、上記は負数もUnix epoch millisecondsとして扱っています。

## Vendor B固有の変換

金額変換には`Number`や浮動小数点を使いません。大きな整数でも丸めを発生させないため、`BigInt`で整数部と小数部を組み立てます。

```ts
function minorUnitsToDecimal(totalMinor: string): string {
  const minor = BigInt(totalMinor);
  const majorPart = minor / 100n;
  const minorPart = (minor % 100n).toString().padStart(2, "0");

  return `${majorPart}.${minorPart}`;
}

function epochMillisecondsToIso(paidAtMs: string): string {
  return new Date(Number(BigInt(paidAtMs))).toISOString();
}

function mapVendorBToCanonical(record: unknown): CanonicalRow {
  const vendorRow = VendorBRecordSchema.parse(record);

  return {
    vendor: "vendor_b",
    externalId: vendorRow.transaction_ref,
    amount: minorUnitsToDecimal(vendorRow.total_minor),
    paidAt: epochMillisecondsToIso(vendorRow.paid_at_ms),
  };
}
```

例の行は次のように変換されます。

```ts
{
  vendor: "vendor_b",
  externalId: "b-92",
  amount: "12.30",
  paidAt: "2026-08-20T10:15:00.000Z",
}
```

## Vendor Bの取り込み処理

```ts
export async function importVendorB(input: ImportInput) {
  // 圧縮されたraw bodyを、展開やparseより先に検証する。
  verifyHmac(input.rawBody, input.signature, input.vendorSecret);

  // Vendor Aと同じ展開後20 MB上限。
  const bytes = await gunzipWithLimit(input.rawBody, 20 * MB);

  const records = parseDelimited(bytes, {
    delimiter: "\t",
    header: true,
  });

  // 全行のVendor DTO検証、変換、CanonicalRow検証を先に完了させる。
  const rows = records
    .map(mapVendorBToCanonical)
    .map((row) => CanonicalRowSchema.parse(row));

  // vendorとexternalIdの組み合わせでのみ重複を除く。
  const uniqueRows = dedupe(rows, {
    key: (row) => `${row.vendor}:${row.externalId}`,
  });

  await persistNewTransactions(uniqueRows);
}
```

重要なのは、`persistNewTransactions`を呼ぶ前に全行の変換と検証を完了させることです。途中で不正な行が見つかっても、それ以前の正常行はまだ保存されていません。

Vendor名をファイル内の値から決めず、呼び出された入口によって固定するため、Vendor Bのファイルが`vendor_a`を名乗る余地もありません。

## 処理順と失敗時の扱い

処理順は次のとおりです。

1. 圧縮された`rawBody`のHMAC検証
2. 20 MBの展開後サイズ制限付きgunzip
3. tab区切り・ヘッダーありでparse
4. 全行のVendor B DTO検証
5. Vendor B固有値を正規化
6. 全行を`CanonicalRowSchema`で再検証
7. `vendor + externalId`で重複排除
8. `CanonicalRow[]`だけを永続化

失敗時は例外をそのまま取り込み失敗として扱い、行単位のスキップや部分成功にはしません。

| 失敗箇所 | 後続処理 | 保存 |
|---|---|---|
| HMAC不正 | gunzipしない | 0件 |
| 展開上限超過・gzip不正 | parseしない | 0件 |
| TSV構文・ヘッダー不正 | 変換しない | 0件 |
| Vendor B列の検証エラー | 永続化しない | 0件 |
| CanonicalRow検証エラー | 永続化しない | 0件 |
| 永続化エラー | 呼び出し元へ失敗を返す | 永続化層の原子性に依存 |

ファイル単位の原子性を永続化エラーにも適用するなら、`persistNewTransactions`自身がDBトランザクション内で全件保存する必要があります。インポーター側で逐次保存や行単位リトライは行いません。

## 必要なテスト

最低限、次を追加します。

- 正常なVendor Bファイルが期待する`CanonicalRow`になる
- `1230 → 12.30`
- `0 → 0.00`
- `1 → 0.01`
- 非常に大きい`total_minor`でも浮動小数点の丸めがない
- `paid_at_ms`がISO 8601文字列になる
- 空の`transaction_ref`、負数・小数・非数値の`total_minor`を拒否する
- Date範囲外または非整数の`paid_at_ms`を拒否する
- comma区切りや欠落列、余分な列を拒否する
- 1行でも不正なら`persistNewTransactions`が一度も呼ばれない
- HMAC不正ならgunzip、parse、永続化が呼ばれない
- 展開上限超過ならparse、永続化が呼ばれない
- 同じVendor B内の同一`transaction_ref`は1件になる
- Vendor AとVendor Bで同じ`externalId`でも別取引になる
- 永続化へVendor B DTOではなく`CanonicalRow`だけが渡る
- 既存Vendor Aテストが無変更で通る

加えて、DBのVendor列に`vendor_a`限定のCHECK制約やenumがある場合は、`vendor_b`追加が必要です。TypeScript側のenumだけでなく、永続化先の制約とVendorによる分岐処理も検索対象にします。

この構成なら既存の`importVendorA`は編集不要で、変更範囲は正規化enum、Vendor BのDTO・変換・入口、必要ならDB制約に限定できます。
