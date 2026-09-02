提案は、Vendor Aの関数を共通化せずそのまま残し、Vendor B専用の取り込み関数と変換関数だけを追加する構成です。共通パイプラインへの抽象化は差分が広がり、Vendor Aの挙動を変えるリスクがあるため、今回は行いません。

## 処理順

Vendor Bも次の順序を固定します。

1. 圧縮済みの`rawBody`に対してHMACを検証
2. 20 MB上限付きでgzipを展開
3. tab区切り・ヘッダーありとしてparse
4. 全行をVendor Bの列型で検証
5. Vendor Bの値を正規化形式へ変換
6. 全行を`CanonicalRowSchema`で検証
7. `vendor + externalId`でファイル内重複を除去
8. 全工程が成功した場合だけ、正規化済み行を一括永続化

配列全体の検証が終わるまで`persistNewTransactions`を呼ばないため、途中の行が不正でも1行も保存されません。

## 型の変更・追加

既存スキーマは、Vendor Bを正規化後に受け入れられるよう判別値だけを追加します。

```ts
const CanonicalRowSchema = z.object({
  vendor: z.enum(["vendor_a", "vendor_b"]),
  externalId: z.string().min(1),
  amount: z.string().regex(/^\d+\.\d{2}$/),
  paidAt: z.string().datetime(),
});

type CanonicalRow = z.infer<typeof CanonicalRowSchema>;
```

Vendor Bのparse直後の行には、専用スキーマを追加します。

```ts
const VendorBRowSchema = z
  .object({
    transaction_ref: z.string().min(1),
    total_minor: z.string().regex(/^\d+$/),
    paid_at_ms: z.string().regex(/^-?\d+$/),
  })
  .strict();

type VendorBRow = z.infer<typeof VendorBRowSchema>;
```

`.strict()`により、列名の誤りや余分な列もvalidation errorにします。利用中のCSVパーサーがヘッダーだけのファイルを行として返さない場合は、ヘッダーが次の3列と完全一致することもparseラッパーで検証します。

```ts
[
  "transaction_ref",
  "total_minor",
  "paid_at_ms",
]
```

列順を契約に含めないなら集合一致、仕様どおりの順序まで要求するなら配列一致にします。

## Vendor B固有の変換

`total_minor`は`Number`へ変換しません。金額が大きい場合の精度落ちや指数表記を避けるため、文字列のまま小数点を挿入します。

```ts
function minorUnitsToDecimal(value: string): string {
  const normalized = value.replace(/^0+(?=\d)/, "");
  const padded = normalized.padStart(3, "0");

  return `${padded.slice(0, -2)}.${padded.slice(-2)}`;
}

function epochMillisecondsToIso(value: string): string {
  const milliseconds = Number(value);

  if (!Number.isSafeInteger(milliseconds)) {
    throw new Error("paid_at_ms is outside the supported integer range");
  }

  const date = new Date(milliseconds);

  if (Number.isNaN(date.getTime())) {
    throw new Error("paid_at_ms is outside the supported date range");
  }

  return date.toISOString();
}

function mapVendorBToCanonical(
  row: VendorBRow,
): z.input<typeof CanonicalRowSchema> {
  return {
    vendor: "vendor_b",
    externalId: row.transaction_ref,
    amount: minorUnitsToDecimal(row.total_minor),
    paidAt: epochMillisecondsToIso(row.paid_at_ms),
  };
}
```

変換例は以下です。

| Vendor B入力 | 正規化後 |
|---|---|
| `total_minor: "1230"` | `amount: "12.30"` |
| `total_minor: "0"` | `amount: "0.00"` |
| `total_minor: "1"` | `amount: "0.01"` |
| `paid_at_ms: "1787220900000"` | `paidAt: "2026-08-20T10:15:00.000Z"` |

## 取り込み関数

```ts
export async function importVendorB(input: ImportInput) {
  verifyHmac(input.rawBody, input.signature, input.vendorSecret);

  const bytes = await gunzipWithLimit(input.rawBody, 20 * MB);

  const records = parseDelimited(bytes, {
    delimiter: "\t",
    header: true,
  });

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

Vendor Aの既存関数には触れません。将来Vendor Cなどが増え、同一処理の重複が実害になった段階でのみ共通化を検討します。

永続化層にDBの一意制約がある場合は、`externalId`単独ではなく`(vendor, externalId)`の複合一意制約になっていることを確認します。DBのvendor列がenumなら`vendor_b`の追加も必要です。

## 失敗時の扱い

- 署名不正：展開、parse、永続化を一切行わない
- gzip破損・20 MB超過：parse、永続化を行わない
- ヘッダー・列・数値形式の不正：変換または永続化を行わない
- 変換不能な日時：永続化を行わない
- 途中の行だけ不正：有効な先行行も含めて保存しない
- 永続化エラー：`persistNewTransactions`内のトランザクションをロールバックする

ログやエラー応答に署名値、secret、raw bodyを含めないことも既存方針を維持します。

## テスト

最低限、以下を追加します。

1. 正常系

   - tab区切りを読み取れる
   - `1230`が`12.30`になる
   - epoch millisecondsがISO日時になる
   - 永続化層には`CanonicalRow`だけが渡る

2. 処理順と安全性

   - HMAC不正時に`gunzipWithLimit`が呼ばれない
   - HMACが展開後bytesではなく圧縮済み`rawBody`を受け取る
   - 20 MB超過時にparseと永続化が呼ばれない
   - parse error時に永続化が呼ばれない
   - 1行目が正常、2行目が不正でも永続化が一度も呼ばれない

3. Vendor Bの列検証

   - `transaction_ref`が空なら失敗
   - `total_minor`が負数、小数、空文字、指数表記なら失敗
   - 列不足、未知の列、誤った区切り文字なら失敗
   - `paid_at_ms`が整数でない、またはDate範囲外なら失敗

4. 金額の境界値

   - `"0"` → `"0.00"`
   - `"1"` → `"0.01"`
   - `"10"` → `"0.10"`
   - `"100"` → `"1.00"`
   - JavaScriptの安全整数範囲を超える大きな金額も精度を失わない

5. 重複

   - Vendor B内で同じ`transaction_ref`が複数あれば1件
   - Vendor Aの`externalId: "same"`とVendor Bの`externalId: "same"`は別取引
   - 永続化層の褁合一意制約も同じ結果になる

6. Vendor Aの回帰

   - 既存Vendor Aテストを無変更で通す
   - delimiter、変換結果、HMAC検証順、20 MB上限が従来どおり
   - `vendor_a`の正規化結果に差分がない

この構成なら、既存コードの実質的な変更は`CanonicalRowSchema`への`vendor_b`追加だけで、残りはVendor B専用コードとして閉じ込められます。
