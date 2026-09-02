提案は、認証・展開・正規化・保存の共通部分だけを抽出し、Vendor固有部分を「解析」と「CanonicalRowへの変換」に限定する形です。Vendor Aのコードパスは処理順も関数呼び出しも維持します。

## 処理順

両Vendorで次の順序を固定します。

1. 圧縮済みの`rawBody`に対してHMACを検証
2. 20 MB上限付きでgzipを展開
3. Vendor固有の区切り文字・ヘッダーで解析
4. Vendor固有DTOを検証
5. Vendor固有DTOをCanonical形式へ変換
6. `CanonicalRowSchema`で全行を検証
7. `vendor + externalId`でファイル内重複を除外
8. 全行の処理が成功した場合だけ、一度だけ永続化

重要なのは、7まで完了する前に`persistNewTransactions`を呼ばないことです。

## 型の変更

既存の正規化型にはVendor Bだけを追加します。

```ts
export const CanonicalRowSchema = z.object({
  vendor: z.enum(["vendor_a", "vendor_b"]),
  externalId: z.string().min(1),
  amount: z.string().regex(/^\d+\.\d{2}$/),
  paidAt: z.string().datetime(),
});

export type CanonicalRow = z.infer<typeof CanonicalRowSchema>;
```

Vendor Bの入力行は永続化層から見えない、取り込みモジュール内の型にします。

```ts
const VendorBSourceRowSchema = z
  .object({
    transaction_ref: z.string().min(1),
    total_minor: z.string().regex(/^\d+$/),
    paid_at_ms: z.string().regex(/^-?\d+$/),
  })
  .strict();

type VendorBSourceRow = z.infer<typeof VendorBSourceRowSchema>;
```

`total_minor`は仕様どおり非負、`paid_at_ms`は仕様に非負制約が書かれていないため、1970年以前も表現できる整数として扱います。もしVendor Bが非負のみと保証しているなら、後者も`/^\d+$/`に狭められます。

## 共通部分の抽出

抽出するのは安全性に関わる固定順序だけです。

```ts
type ParseAndMapRows = (bytes: Uint8Array) => unknown[];

async function importVerifiedGzipTransactions(
  input: ImportInput,
  parseAndMapRows: ParseAndMapRows,
): Promise<void> {
  verifyHmac(input.rawBody, input.signature, input.vendorSecret);

  const bytes = await gunzipWithLimit(input.rawBody, 20 * MB);

  const rows = parseAndMapRows(bytes).map((row) =>
    CanonicalRowSchema.parse(row),
  );

  const uniqueRows = dedupe(rows, {
    key: (row) => `${row.vendor}:${row.externalId}`,
  });

  await persistNewTransactions(uniqueRows);
}
```

この関数はVendor DTOを受け取らず、永続化にも渡しません。コールバックから返された値を必ず`CanonicalRowSchema`で検証してから保存します。

Vendor Aは既存処理をそのまま移します。

```ts
export async function importVendorA(input: ImportInput): Promise<void> {
  return importVerifiedGzipTransactions(input, (bytes) => {
    const records = parseDelimited(bytes, {
      delimiter: ",",
      header: true,
    });

    return records.map(mapVendorAToCanonical);
  });
}
```

抽出による回帰リスクを避けるなら、最初にVendor Aの現状を固定するcharacterization testを追加し、その後でこの抽出を行います。

## Vendor B固有の解析と変換

ヘッダーは完全一致を検証します。

```ts
const VENDOR_B_HEADERS = [
  "transaction_ref",
  "total_minor",
  "paid_at_ms",
] as const;

function parseVendorBRows(bytes: Uint8Array): unknown[] {
  const { headers, records } = parseDelimitedWithHeaders(bytes, {
    delimiter: "\t",
    header: true,
  });

  assertExactHeaders(headers, VENDOR_B_HEADERS);

  return records.map(mapVendorBToCanonical);
}
```

既存の`parseDelimited`がヘッダーを返せるなら、それを利用します。返せない場合のみ、Vendor B用に`parseDelimitedWithHeaders`または`parseVendorBRows`を追加します。既存のVendor A呼び出しは変更しません。

ヘッダー検証を行単位のZod検証だけに任せると、誤ったヘッダーしかない空ファイルを検出できないため、ヘッダー自体を明示的に検証する必要があります。

変換では金額に`Number`や浮動小数点演算を使いません。

```ts
function mapVendorBToCanonical(record: unknown): CanonicalRow {
  const source = VendorBSourceRowSchema.parse(record);

  const minor = BigInt(source.total_minor);
  const whole = minor / 100n;
  const fraction = (minor % 100n).toString().padStart(2, "0");

  const milliseconds = BigInt(source.paid_at_ms);

  // JavaScript Dateの有効範囲。
  if (
    milliseconds < -8_640_000_000_000_000n ||
    milliseconds > 8_640_000_000_000_000n
  ) {
    throw new RangeError("paid_at_ms is outside the supported Date range");
  }

  const paidAt = new Date(Number(milliseconds)).toISOString();

  return CanonicalRowSchema.parse({
    vendor: "vendor_b",
    externalId: source.transaction_ref,
    amount: `${whole}.${fraction}`,
    paidAt,
  });
}
```

変換例は次のとおりです。

| Vendor B入力 | Canonical値 |
|---|---|
| `transaction_ref = "b-92"` | `externalId = "b-92"` |
| `total_minor = "1230"` | `amount = "12.30"` |
| `total_minor = "0"` | `amount = "0.00"` |
| `paid_at_ms = "1787220900000"` | `paidAt = "2026-08-20T10:15:00.000Z"` |
| 固定値 | `vendor = "vendor_b"` |

エントリーポイントは次の形です。

```ts
export async function importVendorB(input: ImportInput): Promise<void> {
  return importVerifiedGzipTransactions(input, parseVendorBRows);
}
```

## 失敗時の扱い

例外を握りつぶさず、取り込み全体を失敗させます。

- 署名不正：展開・解析・保存を実行しない
- 20 MB超過：解析・保存を実行しない
- gzip不正：解析・保存を実行しない
- 区切り形式またはヘッダー不正：保存しない
- いずれか1行のDTO検証・変換・Canonical検証失敗：全行保存しない
- 重複：エラーではなく、同一Vendor内でのみ除外
- 永続化失敗：呼び出し元へ例外を返す

全行をメモリ上で検証してから永続化を一度だけ呼ぶため、たとえば100行目が不正でも1〜99行目は保存されません。

また、別ファイルや同時実行間の重複はメモリ上の`dedupe`だけでは防げません。永続化層には既存どおり、`(vendor, externalId)`相当の複合一意制約を置くべきです。バッチ保存自体もDBトランザクション内で行います。

## テスト

最低限、次を追加します。

### Vendor A回帰テスト

- 正常ファイルから従来と同じ`CanonicalRow`が保存される
- HMACが展開より先に呼ばれる
- 不正署名では展開・解析・保存が呼ばれない
- 20 MB超過では解析・保存が呼ばれない
- 途中行の検証失敗で保存が一度も呼ばれない
- ファイル内重複の既存挙動が変わらない

### Vendor B正常系

- tab区切りと所定のヘッダーを解析できる
- `1230`が`12.30`になる
- `0`が`0.00`になる
- 大きな`total_minor`でも浮動小数点誤差が生じない
- `1787220900000`が正しいISO日時になる
- 保存される値にVendor Bの列名が残らない

### Vendor B異常系

- 不正署名では展開前に失敗する
- gzip不正、20 MB超過で保存されない
- comma区切り、欠落ヘッダー、余分なヘッダーで失敗する
- ヘッダーだけのファイルでもヘッダー不正を検出する
- 空、負数、小数、指数表記の`total_minor`を拒否する
- 空または整数でない`paid_at_ms`を拒否する
- `Date`の範囲外の`paid_at_ms`を拒否する
- 2行目以降が不正でも正常行を含めて一切保存しない

### 重複契約

- 同一Vendor B・同一`externalId`は1件になる
- Vendor AとVendor Bで同じ`externalId`を保存できる
- 永続化層の一意性が`externalId`単独ではなく、`vendor + externalId`である

この設計の実質的な変更点は、Canonicalのenum拡張、固定順序を守る小さな共通関数、Vendor Bの入力検証・変換・エントリーポイントだけです。Vendor A固有の解析と変換には手を加えません。
