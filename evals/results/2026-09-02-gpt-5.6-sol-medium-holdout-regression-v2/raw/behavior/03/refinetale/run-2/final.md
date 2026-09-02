提案は、署名検証から永続化までを非公開の共通関数へ移し、Vendor固有差分を「区切り文字」と「行変換関数」だけに限定する構成です。Vendor別の処理全体を複製せず、安全性を担う順序を1か所に保ちます。

## 変更契約

変更する挙動:

- Vendor Bのgzipファイルをtab区切りで取り込める。
- Vendor Bの金額と日時を`CanonicalRow`へ変換できる。
- `CanonicalRow.vendor`が`vendor_b`を受理する。

変更しない挙動:

- Vendor Aの入力形式、変換結果、エラー、永続化順序。
- 圧縮された`rawBody`に対するHMAC検証。
- 20 MBの展開上限。
- 全行のparse・validation完了前には保存しない。
- 同一Vendor内では重複排除し、Vendor間では同じ`externalId`を別取引として扱う。
- 永続化層が受け取る型は`CanonicalRow`だけ。

## 処理順

両Vendorで次の順序を固定します。

1. 圧縮された`input.rawBody`のHMACを検証する。
2. 成功した場合だけ、20 MB上限付きでgzipを展開する。
3. Vendor固有の区切り文字で全行をparseする。
4. Vendor固有の行変換を行う。
5. 全行を`CanonicalRowSchema.parse`で検証する。
6. `${vendor}:${externalId}`で同一ファイル内を重複排除する。
7. `CanonicalRow[]`だけを永続化する。

1〜5のどこかで失敗した場合、6〜7へ進まないため保存件数は0です。

## 型と関数

```ts
const CanonicalRowSchema = z.object({
  vendor: z.enum(["vendor_a", "vendor_b"]),
  externalId: z.string().min(1),
  amount: z.string().regex(/^\d+\.\d{2}$/),
  paidAt: z.string().datetime(),
});

type CanonicalRow = z.infer<typeof CanonicalRowSchema>;

type RowMapper = (record: unknown) => unknown;

async function importTransactions(
  input: ImportInput,
  delimiter: "," | "\t",
  mapToCanonical: RowMapper,
) {
  verifyHmac(input.rawBody, input.signature, input.vendorSecret);

  const bytes = await gunzipWithLimit(input.rawBody, 20 * MB);
  const records = parseDelimited(bytes, { delimiter, header: true });

  // 既存Vendor Aと同じく、変換後に全行をCanonicalRowとして検証する。
  const rows = records
    .map(mapToCanonical)
    .map((row) => CanonicalRowSchema.parse(row));

  const uniqueRows = dedupe(rows, {
    key: (row) => `${row.vendor}:${row.externalId}`,
  });

  await persistNewTransactions(uniqueRows);
}

export function importVendorA(input: ImportInput) {
  return importTransactions(input, ",", mapVendorAToCanonical);
}

export function importVendorB(input: ImportInput) {
  return importTransactions(input, "\t", mapVendorBToCanonical);
}
```

`importTransactions`はモジュール非公開にします。展開上限、HMAC検証、header設定、重複キー、永続化を引数化しないことで、安全条件を呼び出し側が変更できないようにします。

Vendor選択用の`switch`やstrategy registryは不要です。公開入口を`importVendorA`と`importVendorB`に分ければ、Vendorの判定を複数層へ伝播させずに済みます。

## Vendor B固有の変換

Vendor Bの入力行は永続化層へ渡さず、変換関数の内部だけで扱います。

```ts
const VendorBRowSchema = z.object({
  transaction_ref: z.string().min(1),
  total_minor: z.string().regex(/^\d+$/),
  paid_at_ms: z
    .string()
    .regex(/^-?\d+$/)
    .refine(isValidEpochMilliseconds, {
      message: "Invalid Unix epoch milliseconds",
    }),
}).strict();

function isValidEpochMilliseconds(value: string): boolean {
  const milliseconds = Number(value);

  return (
    Number.isSafeInteger(milliseconds) &&
    Number.isFinite(new Date(milliseconds).getTime())
  );
}

function mapVendorBToCanonical(record: unknown): unknown {
  const row = VendorBRowSchema.parse(record);

  // Numberへ変換しないため、大きなminor値でも精度を失わない。
  const minorDigits = row.total_minor
    .replace(/^0+(?=\d)/, "")
    .padStart(3, "0");

  return {
    vendor: "vendor_b",
    externalId: row.transaction_ref,
    amount: `${minorDigits.slice(0, -2)}.${minorDigits.slice(-2)}`,
    paidAt: new Date(Number(row.paid_at_ms)).toISOString(),
  };
}
```

変換例:

| Vendor B入力 | Canonical値 |
|---|---|
| `transaction_ref = "b-92"` | `externalId = "b-92"` |
| `total_minor = "1230"` | `amount = "12.30"` |
| `total_minor = "1"` | `amount = "0.01"` |
| `total_minor = "0"` | `amount = "0.00"` |
| `paid_at_ms = "1787220900000"` | `paidAt = "2026-08-20T10:15:00.000Z"` |

`total_minor`は`Number`へ変換しません。これにより、JavaScriptの安全整数上限を超える値でも十進文字列として正確に変換できます。

`paid_at_ms`については仕様上「非負」とされていないため、整数形式としては負値も許可しています。ただし、安全整数かつJavaScriptの`Date`で表現可能な範囲に限定します。負値を拒否する契約が別途ある場合だけ、正規表現を`/^\d+$/`へ変更します。

## 失敗時の扱い

- 署名不正: 即時reject。展開、parse、変換、保存は呼ばない。
- gzip不正・20 MB超過: reject。parse、変換、保存は呼ばない。
- TSV/CSV parse失敗: reject。保存は呼ばない。
- Vendor固有行のvalidation失敗: reject。ほかの行が正常でも保存は呼ばない。
- Canonical validation失敗: reject。保存は呼ばない。
- 永続化失敗: エラーをそのまま呼び出し元へ返し、fallbackや自動再試行は追加しない。

永続化途中の障害でもファイル全体を0件に戻す必要があるなら、`persistNewTransactions`が単一トランザクションを所有する必要があります。現状その保証が不明なため、今回の取り込み関数だけで「永続化中の失敗も必ず0件」とは約束できません。

DBの一意制約も既存契約どおり、`externalId`単独ではなく`(vendor, externalId)`である必要があります。

## 必要なテストと期待結果

| 変更契約・失敗経路 | テスト | 期待結果 |
|---|---|---|
| Vendor Aを変更しない | 既存CSVを`importVendorA`へ渡す | 従来と同じ`CanonicalRow`が1件保存される |
| Vendor B成功 | 提示されたTSVをgzip化し正しい署名で渡す | `vendor_b / b-92 / 12.30 / 2026-08-20T10:15:00.000Z`が保存される |
| 圧縮bodyのHMACを先に検証 | 両Vendorについて不正署名を渡し、各依存をspyする | `verifyHmac`のみ呼ばれ、`gunzipWithLimit`以下は0回 |
| 展開上限 | 両Vendorについて展開後20 MB超のgzipを渡す | rejectし、parse・保存は0回 |
| parse error | 不正なCSVとTSVをそれぞれ渡す | rejectし、保存は0回 |
| ファイル単位のvalidation | 正常行の後に不正行を置いたファイルを両Vendorで渡す | rejectし、正常行を含め保存は0回 |
| Bの非負整数契約 | `-1`、`1.2`、空文字を`total_minor`へ設定 | Vendor B validation error、保存は0回 |
| Bの金額変換 | `0`、`1`、`12`、`1230`、安全整数を超える長い数字を試す | `0.00`、`0.01`、`0.12`、`12.30`、精度損失のない文字列になる |
| Bのepoch変換 | 提示値、非整数、表現範囲外を試す | 提示値はISO日時になり、不正値では保存0件 |
| CanonicalRowだけを保存 | `persistNewTransactions`の引数を検査 | Vendor固有列がなく、全要素が`CanonicalRowSchema`を通過済み |
| 同一Vendor内の重複 | 同じB行を2回含める | 保存されるB取引は1件 |
| Vendor間の同一ID | AとBで同じ`externalId`を順に取り込む | `(vendor_a, id)`と`(vendor_b, id)`の2件が存在する |
| 永続化成功 | repositoryを成功させる | importが正常終了する |
| 永続化失敗 | repositoryをrejectさせる | importもrejectする。transactional repositoryなら書き込みはrollbackされる |

共通の安全性テストは`describe.each(["vendor_a", "vendor_b"])`で同じ期待結果を適用し、Vendor固有テストは区切り文字・列検証・値変換だけに絞るのが適切です。

今回は設計提案のみで、作業領域に実装ファイルがなく読み取り専用だったため、コード変更・テスト実行・`.agent/CONTINUITY.md`およびReferyTaleの対応表作成は未実施です。
