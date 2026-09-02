推奨は、署名検証から永続化までの順序だけを小さな共通関数へ抽出し、Vendor差分を設定と変換関数に閉じ込める設計です。継承・クラス・動的なVendorレジストリは不要です。

## 処理順

両Vendorで次の順序を固定します。

1. 圧縮された`rawBody`のHMACを検証
2. 20 MB上限付きでgzip展開
3. Vendorごとの区切り文字で全行をparse
4. Vendor固有DTOを検証・正規化
5. 全行を`CanonicalRowSchema`で検証
6. `${vendor}:${externalId}`でファイル内重複を除去
7. `CanonicalRow[]`を一度だけ永続化

4〜6がすべて成功するまで永続化を呼ばないため、途中行だけ保存されることはありません。

## 型と関数

変更する正規化型は`vendor_b`の追加だけです。

```ts
const CanonicalRowSchema = z.object({
  vendor: z.enum(["vendor_a", "vendor_b"]),
  externalId: z.string().min(1),
  amount: z.string().regex(/^\d+\.\d{2}$/),
  paidAt: z.string().datetime(),
});

type CanonicalRow = z.infer<typeof CanonicalRowSchema>;
```

Vendor Bの入力DTOは永続化層から隔離します。

```ts
const MAX_DATE_MS = 8_640_000_000_000_000n;

const VendorBRowSchema = z.object({
  transaction_ref: z.string().min(1),
  total_minor: z.string().regex(/^\d+$/),
  paid_at_ms: z
    .string()
    .regex(/^-?\d+$/)
    .refine((value) => {
      const milliseconds = BigInt(value);

      return (
        milliseconds >= -MAX_DATE_MS &&
        milliseconds <= MAX_DATE_MS
      );
    }, "paid_at_ms is outside the supported Date range"),
}).strict();

type VendorBRow = z.infer<typeof VendorBRowSchema>;
```

`paid_at_ms`はUnix epoch millisecondsなので、1970年以前を表現できる負数も許容しています。業務契約として1970年以降に限定するなら、正規表現を`/^\d+$/`に変更します。

共通化する範囲は、既存の処理順を表す部分だけです。

```ts
type ParsedRecord = Record<string, string>;

type VendorImportDefinition = Readonly<{
  delimiter: "," | "\t";
  mapToCanonical: (record: ParsedRecord) => unknown;
}>;

async function importDelimitedTransactions(
  input: ImportInput,
  definition: VendorImportDefinition,
): Promise<void> {
  verifyHmac(input.rawBody, input.signature, input.vendorSecret);

  const bytes = await gunzipWithLimit(input.rawBody, 20 * MB);

  const records = parseDelimited(bytes, {
    delimiter: definition.delimiter,
    header: true,
  });

  const rows = records
    .map((record) => definition.mapToCanonical(record))
    .map((row) => CanonicalRowSchema.parse(row));

  const uniqueRows = dedupe(rows, {
    key: (row) => `${row.vendor}:${row.externalId}`,
  });

  await persistNewTransactions(uniqueRows);
}
```

公開関数はVendorを固定し、入力ファイル自身にVendorを選ばせません。

```ts
const vendorADefinition = {
  delimiter: ",",
  mapToCanonical: mapVendorAToCanonical,
} satisfies VendorImportDefinition;

const vendorBDefinition = {
  delimiter: "\t",
  mapToCanonical: mapVendorBToCanonical,
} satisfies VendorImportDefinition;

export function importVendorA(input: ImportInput): Promise<void> {
  return importDelimitedTransactions(input, vendorADefinition);
}

export function importVendorB(input: ImportInput): Promise<void> {
  return importDelimitedTransactions(input, vendorBDefinition);
}
```

Vendor Aは既存の`mapVendorAToCanonical`をそのまま使用します。共通関数抽出前に既存挙動の回帰テストを追加し、抽出前後で永続化される値と失敗条件が一致することを確認します。

## Vendor B固有の変換

金額は`Number`や浮動小数点へ変換しません。桁数の大きい値でも精度を失わない文字列操作にします。

```ts
function minorUnitsToDecimal(totalMinor: string): string {
  const normalized = totalMinor.replace(/^0+(?=\d)/, "");
  const padded = normalized.padStart(3, "0");

  return `${padded.slice(0, -2)}.${padded.slice(-2)}`;
}

function epochMillisecondsToIso(paidAtMs: string): string {
  return new Date(Number(BigInt(paidAtMs))).toISOString();
}

function mapVendorBToCanonical(
  record: ParsedRecord,
): z.input<typeof CanonicalRowSchema> {
  const row: VendorBRow = VendorBRowSchema.parse(record);

  return {
    vendor: "vendor_b",
    externalId: row.transaction_ref,
    amount: minorUnitsToDecimal(row.total_minor),
    paidAt: epochMillisecondsToIso(row.paid_at_ms),
  };
}
```

変換例は次のとおりです。

| Vendor B値 | Canonical値 |
|---|---|
| `transaction_ref: "b-92"` | `externalId: "b-92"` |
| `total_minor: "1230"` | `amount: "12.30"` |
| `total_minor: "1"` | `amount: "0.01"` |
| `total_minor: "0"` | `amount: "0.00"` |
| `paid_at_ms: "1787220900000"` | ISO 8601 UTC文字列 |
| 任意の入力行 | `vendor: "vendor_b"` |

## 失敗時の扱い

| 失敗箇所 | 挙動 |
|---|---|
| HMAC不正 | 即時失敗。展開・parse・永続化を呼ばない |
| 展開後20 MB超過、gzip不正 | 即時失敗。parse・永続化を呼ばない |
| 区切り形式やヘッダー不正 | ファイル全体を失敗させ、永続化を呼ばない |
| `total_minor`が負数・小数・空文字 | Vendor B入力検証エラー。永続化を呼ばない |
| `paid_at_ms`が整数でない、Date範囲外 | Vendor B入力検証エラー。永続化を呼ばない |
| Canonical変換結果が不正 | Canonical validation error。永続化を呼ばない |
| 永続化失敗 | エラーをそのまま上位へ返す。既存の永続化契約を変更しない |

行単位の`try/catch`や不正行のスキップは入れません。また、エラーメッセージへ署名、secret、raw bodyを含めません。

永続化処理自身の途中失敗までファイル単位で原子的にしたい場合は、`persistNewTransactions`内部のトランザクションが必要です。ただし、これは提示された既存契約より広い変更なので、今回のVendor B追加とは分離するのが安全です。

## テスト

最低限、次を追加します。

- Vendor A回帰

  - 正常ファイルで従来と同じ`CanonicalRow[]`が一度だけ保存される
  - 不正署名、展開上限、parse/validation errorの既存挙動が変わらない

- セキュリティと処理順

  - 展開後本文に対する正しい署名でも、圧縮`rawBody`に対して不正なら拒否する
  - HMAC不正時は`gunzipWithLimit`、`parseDelimited`、永続化が未呼び出し
  - 展開上限超過時はparse、永続化が未呼び出し
  - 前半行が正常で後半行が不正でも保存件数が0

- Vendor B正常系

  - tab区切りを読み込む
  - `1230 → 12.30`
  - epoch millisecondsをISO 8601 UTCへ変換する
  - 永続化引数に`transaction_ref`などVendor B固有列が残らない

- 金額境界値

  - `0 → 0.00`
  - `1 → 0.01`
  - `99 → 0.99`
  - `100 → 1.00`
  - `001230 → 12.30`
  - `-1`、`1.2`、空文字を拒否
  - `Number.MAX_SAFE_INTEGER`を超える桁数でも文字列として正確に変換

- 日時異常系

  - 小数、非数値、Date範囲外を拒否
  - 有効な負のepochを許容するか、業務判断に応じて拒否する

- 重複

  - Vendor B内で同一`externalId`を1件にする
  - `vendor_a/a-1`と`vendor_b/a-1`を別取引として扱う
  - DBの一意制約も`(vendor, externalId)`であることを確認する

この構成なら、Vendor A固有変換と永続化契約を維持しつつ、新規差分はCanonical enum、Vendor B DTO、2個の変換関数、Vendor定義、公開関数、テストに限定できます。

なお、今回は読み取り専用環境での設計提案のため、`.agent/CONTINUITY.md`や設計用対応表を含むファイル変更は行っていません。
