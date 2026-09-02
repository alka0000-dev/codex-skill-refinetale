提案は、認証から永続化までの安全な処理順を1つの内部関数に集約し、Vendor差分を「展開済みbytesからCanonicalRow[]を作る関数」だけに閉じ込める構成です。

## 変更契約

変更する挙動:

- Vendor Bのtab区切りファイルを受理する。
- `total_minor`を2桁小数の金額文字列へ変換する。
- `paid_at_ms`をISO日時へ変換する。
- `CanonicalRow.vendor`に`"vendor_b"`を追加する。

変更しない挙動:

- Vendor Aのdelimiter、マッピング、検証結果。
- 圧縮raw bodyに対するHMAC検証。
- 20 MB展開上限。
- ファイル全行の検証完了前には永続化しない。
- 永続化層へ渡す型は`CanonicalRow`のみ。
- 重複キーは`vendor + externalId`。
- エラーの握り潰し、部分成功、importer側での自動再試行は行わない。

共通処理:

1. HMAC検証
2. 上限付きgunzip
3. Vendor固有parse・変換
4. 全行のCanonicalRow検証
5. Vendor単位の重複除去
6. 永続化

Vendor固有差分:

| 項目 | Vendor A | Vendor B |
|---|---|---|
| delimiter | `,` | `\t` |
| ID | `id` | `transaction_ref` |
| 金額 | `amount_decimal` | `total_minor`を2桁小数化 |
| 日時 | `paid_at_iso` | `paid_at_ms`をISO化 |
| vendor | `vendor_a` | `vendor_b` |

## 型と関数

```ts
const CanonicalRowSchema = z.object({
  vendor: z.enum(["vendor_a", "vendor_b"]),
  externalId: z.string().min(1),
  amount: z.string().regex(/^\d+\.\d{2}$/),
  paidAt: z.string().datetime(),
});

type CanonicalRow = z.infer<typeof CanonicalRowSchema>;

type ParseCanonicalRows = (bytes: Uint8Array) => CanonicalRow[];
```

Vendor Bの外部DTOは入力境界だけに置きます。永続化方向へは伝播させません。

```ts
const VendorBRowSchema = z.object({
  transaction_ref: z.string().min(1),
  total_minor: z.string().regex(/^\d+$/),
  paid_at_ms: z.string().regex(/^\d+$/).refine((value) => {
    const milliseconds = Number(value);

    return (
      Number.isSafeInteger(milliseconds) &&
      !Number.isNaN(new Date(milliseconds).getTime())
    );
  }, "paid_at_ms must be a valid Unix epoch millisecond value"),
});

type VendorBRow = z.infer<typeof VendorBRowSchema>;
```

`paid_at_ms`は非負の整数文字列、JavaScriptで安全に表現できる整数、有効な`Date`のすべてを満たす場合だけ受理します。

## 共通パイプライン

安全性を設定オブジェクトにしません。HMACや展開上限を任意変更できる汎用APIにすると、安全条件を満たさない呼び出し経路が増えるためです。

```ts
async function importTransactions(
  input: ImportInput,
  parseCanonicalRows: ParseCanonicalRows,
): Promise<void> {
  verifyHmac(input.rawBody, input.signature, input.vendorSecret);

  const bytes = await gunzipWithLimit(input.rawBody, 20 * MB);

  // この関数が返る時点で全行がCanonicalRowとして検証済み。
  const rows = parseCanonicalRows(bytes);

  const uniqueRows = dedupe(rows, {
    key: (row) => `${row.vendor}:${row.externalId}`,
  });

  await persistNewTransactions(uniqueRows);
}
```

公開関数はVendor選択の分岐を持たず、対応するparserを渡すだけです。

```ts
export async function importVendorA(input: ImportInput): Promise<void> {
  return importTransactions(input, parseVendorARows);
}

export async function importVendorB(input: ImportInput): Promise<void> {
  return importTransactions(input, parseVendorBRows);
}
```

Vendor Aは既存の処理順をそのまま移します。

```ts
function parseVendorARows(bytes: Uint8Array): CanonicalRow[] {
  const records = parseDelimited(bytes, {
    delimiter: ",",
    header: true,
  });

  return records
    .map(mapVendorAToCanonical)
    .map((row) => CanonicalRowSchema.parse(row));
}
```

## Vendor B固有変換

金額は`Number`へ変換しません。大きな値での精度損失を避け、文字列だけで正規化します。

```ts
function formatMinorUnits(totalMinor: string): string {
  const normalized = totalMinor.replace(/^0+(?=\d)/, "");
  const padded = normalized.padStart(3, "0");

  return `${padded.slice(0, -2)}.${padded.slice(-2)}`;
}

function mapVendorBToCanonical(record: unknown): CanonicalRow {
  const row = VendorBRowSchema.parse(record);

  return CanonicalRowSchema.parse({
    vendor: "vendor_b",
    externalId: row.transaction_ref,
    amount: formatMinorUnits(row.total_minor),
    paidAt: new Date(Number(row.paid_at_ms)).toISOString(),
  });
}

function parseVendorBRows(bytes: Uint8Array): CanonicalRow[] {
  const records = parseDelimited(bytes, {
    delimiter: "\t",
    header: true,
  });

  return records.map(mapVendorBToCanonical);
}
```

変換例:

| 入力 | Canonical amount |
|---:|---:|
| `"0"` | `"0.00"` |
| `"1"` | `"0.01"` |
| `"10"` | `"0.10"` |
| `"1230"` | `"12.30"` |
| `"001230"` | `"12.30"` |

不足列は`VendorBRowSchema`で失敗します。余分な列を拒否する要件はないため、`.strict()`は追加しません。

## 失敗時の扱い

- 署名不正: `verifyHmac`で即時終了。gunzip、parse、永続化は実行しない。
- 20 MB超過・gzip不正: gunzipで終了。parse、永続化は実行しない。
- delimiter/header/行parse不正: parserで終了。永続化は実行しない。
- Vendor B DTO不正: `VendorBRowSchema`で終了。
- Canonical契約違反: `CanonicalRowSchema`で終了。
- 途中行のvalidation失敗: 先行行が正常でも、永続化呼び出し前なので0行保存。
- 永続化失敗: エラーをそのまま呼び出し元へ返し、importerでは再試行しない。

DB書き込み中の失敗についてもファイル単位の原子性が必要なら、`persistNewTransactions`自身が単一トランザクションで全行を保存する必要があります。これはimporterのメモリ上の処理順だけでは保証できないため、repository側の契約として確認します。

また、DBの一意制約も`externalId`単独ではなく、既存どおり`(vendor, externalId)`である必要があります。

## 最小テスト

| 契約・経路 | テスト | 期待結果 |
|---|---|---|
| Vendor Aを変えない | 既存サンプルを`importVendorA`へ渡す | 従来と同じCanonicalRowが1件保存される |
| Vendor B正常系 | 提示されたBサンプルを取り込む | `vendor_b / b-92 / 12.30`とISO日時が保存される |
| B金額変換 | `0, 1, 10, 1230, 001230` | 上表どおり変換される |
| B金額不正 | `-1`, `12.3`, 空文字 | validation error、保存0件 |
| B日時不正 | 小数、文字列、安全整数外、無効なDate範囲 | validation error、保存0件 |
| HMACが最初 | A/Bそれぞれ署名不正 | gunzip・parser・persistが呼ばれない |
| 展開上限 | A/Bそれぞれ20 MB超過 | parser・persistが呼ばれない |
| parse失敗 | A/Bそれぞれ壊れた区切り/不足列 | persistが呼ばれない |
| ファイル原子性 | 正常な1行目＋不正な2行目 | persistが一度も呼ばれない |
| 同一Vendor重複 | 同じIDを同一ファイルに2行 | persistへ渡るのは1行 |
| Vendor間の独立性 | 同じexternalIdのAとBを順に取り込む | DBに2取引存在する |
| 永続化失敗 | repositoryをrejectさせる | エラーが伝播し、再試行しない |
| DB原子性 | 複数行保存中の失敗を統合テスト | transaction rollbackにより保存0件 |

共通失敗経路はA/Bのパラメータ化テストにし、Vendor固有テストは変換境界だけに絞ります。Vendor設定オブジェクト、strategy class、汎用plugin registryなどは、現時点では状態と組み合わせを増やすだけなので導入しません。
