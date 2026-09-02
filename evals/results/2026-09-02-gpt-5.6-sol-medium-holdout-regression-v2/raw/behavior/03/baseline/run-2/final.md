最小差分かつVendor Aへの回帰リスクが低いのは、既存の `importVendorA` を変更せず、同じ処理順の `importVendorB` を追加する設計です。共通パイプラインへのリファクタリングは、Vendorがさらに増えた段階で行うのが安全です。

## 変更範囲

既存の正規化契約は、`vendor_b` を許可する点だけ拡張します。その他のフィールド仕様は変えません。

```ts
export const CanonicalRowSchema = z.object({
  vendor: z.enum(["vendor_a", "vendor_b"]),
  externalId: z.string().min(1),
  amount: z.string().regex(/^\d+\.\d{2}$/),
  paidAt: z.string().datetime(),
});

export type CanonicalRow = z.infer<typeof CanonicalRowSchema>;
```

Vendor Bの入力行は、永続化層へ漏らさない内部DTOとして定義します。

```ts
const VendorBRowSchema = z.object({
  transaction_ref: z.string().min(1),
  total_minor: z.string().regex(/^\d+$/),
  paid_at_ms: z.string().regex(/^\d+$/),
}).strict();

type VendorBRow = z.infer<typeof VendorBRowSchema>;
```

`.strict()` により、列不足だけでなく想定外の列もVendor Bのファイル契約違反として拒否します。余分な列を許容すべき既存仕様があるなら外してください。

## Vendor B固有の変換

金額は浮動小数点を使わず、`BigInt` で変換します。これにより丸め誤差や大きな整数の精度落ちを避けられます。

```ts
function minorUnitsToDecimal(totalMinor: string): string {
  const minor = BigInt(totalMinor);
  const majorPart = minor / 100n;
  const minorPart = (minor % 100n).toString().padStart(2, "0");

  return `${majorPart}.${minorPart}`;
}

function epochMillisecondsToIso(paidAtMs: string): string {
  const milliseconds = Number(paidAtMs);

  if (!Number.isSafeInteger(milliseconds)) {
    throw new RangeError("paid_at_ms must be a safe integer");
  }

  const date = new Date(milliseconds);

  if (Number.isNaN(date.getTime())) {
    throw new RangeError("paid_at_ms is outside the supported date range");
  }

  return date.toISOString();
}

function mapVendorBToCanonical(row: VendorBRow): CanonicalRow {
  return {
    vendor: "vendor_b",
    externalId: row.transaction_ref,
    amount: minorUnitsToDecimal(row.total_minor),
    paidAt: epochMillisecondsToIso(row.paid_at_ms),
  };
}
```

変換例は次のとおりです。

| Vendor B入力 | CanonicalRow |
|---|---|
| `transaction_ref = "b-92"` | `externalId = "b-92"` |
| `total_minor = "1230"` | `amount = "12.30"` |
| `total_minor = "0"` | `amount = "0.00"` |
| `paid_at_ms = "1787220900000"` | `paidAt = "2026-08-20T10:15:00.000Z"` |

先頭ゼロを禁止する仕様はないため、`"001230"` も `"12.30"` として扱います。

## 取り込み処理

```ts
export async function importVendorB(input: ImportInput) {
  // 必ず圧縮されたraw bodyを検証する。
  verifyHmac(input.rawBody, input.signature, input.vendorSecret);

  // HMAC検証成功後にのみ展開する。
  const bytes = await gunzipWithLimit(input.rawBody, 20 * MB);

  // Vendor Bはtab区切り。
  const records = parseDelimited(bytes, {
    delimiter: "\t",
    header: true,
  });

  // 全行の入力契約とCanonical契約を確認してから永続化する。
  const rows = records
    .map((record) => VendorBRowSchema.parse(record))
    .map(mapVendorBToCanonical)
    .map((row) => CanonicalRowSchema.parse(row));

  await persistNewTransactions(
    dedupe(rows, {
      key: (row) => `${row.vendor}:${row.externalId}`,
    }),
  );
}
```

処理順は固定します。

1. 圧縮された `rawBody` のHMAC検証
2. 20 MB上限付きgzip展開
3. tab区切りとしてファイル全体をparse
4. 全行を `VendorBRowSchema` で検証
5. Vendor B固有形式からCanonical形式へ変換
6. 全行を `CanonicalRowSchema` で再検証
7. `vendor + externalId` で重複排除
8. CanonicalRowだけを一括永続化

Vendor判定のためにファイルを先に展開したり、区切り文字を自動判定したりしないことが重要です。呼び出し元のエンドポイントや設定で `importVendorA` / `importVendorB` を選択してください。

## 失敗時の扱い

HMAC不正、展開上限超過、TSV parse失敗、DTO検証失敗、変換失敗、Canonical検証失敗では、`persistNewTransactions` を呼びません。途中まで正常な行があっても保存件数は0件です。

特別なcatchや行単位のスキップは追加せず、既存と同様に例外を呼び出し元へ伝播させます。

永続化については、次の契約を維持します。

- ファイル単位で1回だけ一括呼び出しする
- Vendor固有DTOを渡さない
- importer側で分割保存や自動リトライをしない
- DB障害時にも部分保存を禁止する必要があるなら、`persistNewTransactions` 自体をトランザクション境界とする

## テスト

最低限、次を追加します。

1. 正常系

- tab区切りをparseできる
- `1230` が `12.30` になる
- epoch millisecondsがISO日時になる
- 永続化へ渡る全要素が `CanonicalRow` である

2. 処理順と安全性

- HMAC不正時は展開、parse、永続化が呼ばれない
- HMACが圧縮済みbytesに対して呼ばれる
- 展開上限超過時はparse、永続化が呼ばれない
- HMAC検証が展開より先に呼ばれる

3. ファイル単位の原子性

- 2行目だけが不正でも保存件数は0件
- header不足、余分な列、不正なtab形式で保存件数は0件
- 正常行を先に変換済みでも、後続行が失敗したら永続化されない

4. Vendor Bの入力境界

- `total_minor`: `"0"`、`"1"`、`"1230"`、大きな整数
- 拒否: `"-1"`、`"12.30"`、`"1e3"`、空文字
- `paid_at_ms`: 正常な整数文字列
- 拒否: 負数、小数、非数値、安全な整数範囲外、JavaScriptの日時範囲外
- 空の `transaction_ref` を拒否

5. 重複排除

- Vendor B内の同じ `transaction_ref` は1件になる
- `vendor_a:a-17` と `vendor_b:a-17` は別取引として残る
- 重複排除後も永続化は1回だけ呼ばれる

6. Vendor Aの回帰

- 既存のVendor Aテストを無変更で通す
- Vendor Aのdelimiter、変換結果、HMAC対象、20 MB上限、重複キーが変わっていないことを確認する

今回は読み取り専用環境のため実装ファイルは変更していません。また、`referytale` の対応表は所定の作業ルートへ保存できなかったため、提示された仕様とコードを直接照合して設計しています。
