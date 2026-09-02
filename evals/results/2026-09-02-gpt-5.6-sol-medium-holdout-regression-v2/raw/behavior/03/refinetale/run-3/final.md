提案は、署名検証から永続化までの安全な処理順を1本の非公開関数に集約し、Vendor差分を「delimiter」と「CanonicalRowへの変換」だけに限定する設計です。

## 変更契約

変更する挙動:

- Vendor B のtab区切りgzipファイルを受理する。
- `total_minor`を精度損失なく小数2桁へ変換する。
- `paid_at_ms`をISO 8601へ変換する。
- `CanonicalRow.vendor`に`vendor_b`を追加する。

変更しない挙動:

- Vendor Aの入力形式、変換結果、エラー、副作用順序。
- HMAC検証対象は圧縮済み`rawBody`。
- 展開上限は20 MB。
- 全行のparse・変換・validation完了前には永続化しない。
- 永続化層へ渡す型は`CanonicalRow`のみ。
- 重複キーは`vendor + externalId`。

## 処理順

両Vendorで次の1経路を使います。

```text
圧縮rawBodyのHMAC検証
  → 20 MB上限付きgunzip
  → Vendor固有delimiterでparse
  → Vendor固有DTO検証・変換
  → CanonicalRowSchemaで全行検証
  → vendor + externalIdでdedupe
  → persistNewTransactions
```

重要なのは、永続化を最後まで遅延させることです。2行目以降で失敗しても、`persistNewTransactions`には到達しません。

## 型と関数

```ts
const CanonicalRowSchema = z.object({
  vendor: z.enum(["vendor_a", "vendor_b"]),
  externalId: z.string().min(1),
  amount: z.string().regex(/^\d+\.\d{2}$/),
  paidAt: z.string().datetime(),
});

type CanonicalRow = z.infer<typeof CanonicalRowSchema>;
type DelimitedRecord = Readonly<Record<string, string>>;
type MapToCanonical = (record: DelimitedRecord) => unknown;
type Delimiter = "," | "\t";
```

共通関数は非公開にします。汎用strategyや公開設定APIまでは不要です。

```ts
async function importDelimitedTransactions(
  input: ImportInput,
  delimiter: Delimiter,
  mapToCanonical: MapToCanonical,
): Promise<void> {
  verifyHmac(input.rawBody, input.signature, input.vendorSecret);

  const bytes = await gunzipWithLimit(input.rawBody, 20 * MB);
  const records = parseDelimited(bytes, { delimiter, header: true });

  // 全行が完成するまで副作用を開始しない。
  const rows = records
    .map(mapToCanonical)
    .map((row) => CanonicalRowSchema.parse(row));

  await persistNewTransactions(
    dedupe(rows, {
      key: (row) => `${row.vendor}:${row.externalId}`,
    }),
  );
}
```

公開関数はVendor差分だけを指定します。

```ts
export async function importVendorA(input: ImportInput): Promise<void> {
  await importDelimitedTransactions(input, ",", mapVendorAToCanonical);
}

export async function importVendorB(input: ImportInput): Promise<void> {
  await importDelimitedTransactions(input, "\t", mapVendorBToCanonical);
}
```

`vendor`を共通関数の別引数にしないのがポイントです。Vendor識別子の正本は各mapperに一つだけ置き、mapperの出力と別引数が食い違う状態を作りません。

## Vendor B固有変換

```ts
const VendorBRowSchema = z.object({
  transaction_ref: z.string().min(1),
  total_minor: z.string().regex(/^\d+$/),
  paid_at_ms: z
    .string()
    .regex(/^-?\d+$/)
    .refine((value) => {
      const milliseconds = Number(value);
      return (
        Number.isSafeInteger(milliseconds) &&
        !Number.isNaN(new Date(milliseconds).getTime())
      );
    }, "paid_at_ms must be a valid Unix epoch millisecond value"),
});

function minorUnitsToDecimal(minorUnits: string): string {
  const digits = minorUnits.replace(/^0+(?=\d)/, "");
  const padded = digits.padStart(3, "0");

  return `${padded.slice(0, -2)}.${padded.slice(-2)}`;
}

function mapVendorBToCanonical(record: DelimitedRecord): unknown {
  const row = VendorBRowSchema.parse(record);

  return {
    vendor: "vendor_b",
    externalId: row.transaction_ref,
    amount: minorUnitsToDecimal(row.total_minor),
    paidAt: new Date(Number(row.paid_at_ms)).toISOString(),
  };
}
```

変換例:

```ts
{
  transaction_ref: "b-92",
  total_minor: "1230",
  paid_at_ms: "1787220900000",
}
```

から:

```ts
{
  vendor: "vendor_b",
  externalId: "b-92",
  amount: "12.30",
  paidAt: "2026-08-20T10:15:00.000Z",
}
```

金額変換に`Number(total_minor) / 100`を使わないため、大きな整数でも浮動小数点の丸めや指数表記が発生しません。

`paid_at_ms`については「非負」という指定がないため、Dateで表現可能な負のepochも受理しています。非負限定が別契約として確定した場合だけ、正規表現を`/^\d+$/`へ変更します。

## 失敗時の扱い

`catch`やfallback、部分スキップは追加せず、既存のエラーをそのまま呼び出し元へ返します。

| 失敗箇所 | 後続処理 | 保存 |
|---|---|---|
| HMAC不正 | gunzipもparseもしない | 0行 |
| 展開上限超過・gzip不正 | parseしない | 0行 |
| delimiter/CSV・TSV parse失敗 | mappingしない | 0行 |
| Vendor DTO不正 | Canonical検証完了前に終了 | 0行 |
| CanonicalRow不正 | dedupe・永続化しない | 0行 |
| 永続化失敗 | エラーを返し、暗黙の再試行をしない | 永続化層のトランザクション契約に従う |

最後の永続化失敗について、現在示された契約だけではロールバックまで保証できません。保存開始後もファイル単位の原子性が必要なら、`persistNewTransactions`自身が単一トランザクションを所有すべきです。Importer側で補償削除を追加するのは避けます。

## 必要なテストと期待結果

| 契約 | テスト | 期待結果 |
|---|---|---|
| Vendor Aを変更しない | 既存A fixtureを取り込む回帰テスト | commaでparseされ、従来と同じCanonicalRowを1回保存 |
| Vendor Bを追加 | 提示されたB fixtureを取り込む | tabでparseされ、上記CanonicalRowを保存 |
| 圧縮bodyを先に認証 | A/BそれぞれでHMACを失敗させる | `verifyHmac`だけが呼ばれ、gunzip・parse・persistは0回 |
| 20 MB上限 | A/B共通契約テストでgunzip引数を確認し、超過を発生させる | 上限が`20 * MB`、parse・persistは0回 |
| parse失敗で全件破棄 | malformed A/Bファイル | persistは0回 |
| validation失敗で全件破棄 | 1行目正常、2行目不正のA/Bファイル | persistは0回 |
| Bの金額契約 | `0`, `1`, `12`, `1230`, `001230` | `0.00`, `0.01`, `0.12`, `12.30`, `12.30` |
| Bの不正金額 | `-1`, `12.3`, 空文字 | validation error、persistは0回 |
| Bの時刻変換 | `1787220900000` | `2026-08-20T10:15:00.000Z` |
| Bの不正時刻 | 小数、非数値、Date範囲外 | validation error、persistは0回 |
| 同一Vendor内の重複 | 同じB `transaction_ref`を2行 | 1行だけ保存 |
| Vendor間のID独立性 | `vendor_a/x`と`vendor_b/x`をdedupeへ渡す | 2行とも残る |
| 永続化成功 | 全検証済みファイル | persistを1回だけ呼ぶ |
| 永続化失敗 | persistをrejectさせる | 同じエラーを返し、再試行しない |

安全境界のテストはA/Bを`describe.each`で共有できますが、形式差分の期待値はA用・B用fixtureで明示します。内部関数の引数構造やmapperが呼ばれた回数だけを固定するテストは不要です。

今回は作業ディレクトリに実装・テストファイルが存在しないため、コード変更やテスト実行は行っていません。実装時の正本は、既存のCanonical schema、Importer、Vendor mapper、永続化層の各所有箇所に置くのが最小です。
