推奨は、署名検証から永続化までの順序だけを共通関数へ抽出し、Vendorごとの差を「展開済みbytesから正規化候補を作る関数」に限定する設計です。Vendor Aのパーサーと変換関数は変更しません。

## 処理順

両Vendorで必ず次の順序に固定します。

1. 圧縮された`rawBody`のHMACを検証
2. 20 MBを上限としてgzipを展開
3. Vendor固有の区切り文字でparse
4. Vendor固有DTOを検証
5. Vendor固有DTOを正規化候補へ変換
6. `CanonicalRowSchema`で全行を検証
7. `${vendor}:${externalId}`でファイル内重複を除去
8. `CanonicalRow[]`だけを永続化

6まで全行をメモリ上で完了してから永続化を呼ぶため、途中の1行が不正でも保存は始まりません。

## 型と関数

```ts
const CanonicalRowSchema = z.object({
  vendor: z.enum(["vendor_a", "vendor_b"]),
  externalId: z.string().min(1),
  amount: z.string().regex(/^\d+\.\d{2}$/),
  paidAt: z.string().datetime(),
});

type CanonicalRow = z.infer<typeof CanonicalRowSchema>;
type CanonicalRowCandidate = z.input<typeof CanonicalRowSchema>;

type DecodeCanonicalCandidates = (
  bytes: Uint8Array,
) => CanonicalRowCandidate[];

async function importSignedGzipTransactions(
  input: ImportInput,
  decodeCandidates: DecodeCanonicalCandidates,
): Promise<void> {
  // rawBodyは圧縮されたまま検証する。この順序を移動しない。
  verifyHmac(input.rawBody, input.signature, input.vendorSecret);

  const bytes = await gunzipWithLimit(input.rawBody, 20 * MB);
  const candidates = decodeCandidates(bytes);

  // 全行の検証が完了するまでpersistを呼ばない。
  const rows = candidates.map((candidate) =>
    CanonicalRowSchema.parse(candidate),
  );

  const uniqueRows = dedupe(rows, {
    key: (row) => `${row.vendor}:${row.externalId}`,
  });

  await persistNewTransactions(uniqueRows);
}
```

Vendor Aは既存のparse条件と変換関数をそのまま委譲します。

```ts
function decodeVendorA(bytes: Uint8Array): CanonicalRowCandidate[] {
  return parseDelimited(bytes, {
    delimiter: ",",
    header: true,
  }).map(mapVendorAToCanonical);
}

export async function importVendorA(input: ImportInput): Promise<void> {
  await importSignedGzipTransactions(input, decodeVendorA);
}
```

Vendor Bの入力型は永続化層から切り離します。

```ts
const VendorBRecordSchema = z.object({
  transaction_ref: z.string().min(1),
  total_minor: z.string().regex(/^\d+$/),
  paid_at_ms: z.string().regex(/^-?\d+$/),
}).strict();

type VendorBRecord = z.infer<typeof VendorBRecordSchema>;
```

`strict()`により、欠落列だけでなく未知の列もエラーにします。列順はヘッダー名で解決し、仕様にない「特定の列順」は要求しません。

## Vendor B固有の変換

金額は`Number`へ変換しません。巨大な整数で丸めが発生しないよう、文字列のまま小数点を挿入します。

```ts
function minorUnitsToDecimal(totalMinor: string): string {
  // "0005"も非負の整数文字列として受理し、"0.05"へ正規化する。
  const normalized = totalMinor.replace(/^0+(?=\d)/, "");
  const padded = normalized.padStart(3, "0");

  return `${padded.slice(0, -2)}.${padded.slice(-2)}`;
}

function epochMillisecondsToIso(paidAtMs: string): string {
  const milliseconds = Number(paidAtMs);

  if (!Number.isSafeInteger(milliseconds)) {
    throw new Error("paid_at_ms is outside the safe integer range");
  }

  const date = new Date(milliseconds);

  if (Number.isNaN(date.getTime())) {
    throw new Error("paid_at_ms is outside the supported date range");
  }

  return date.toISOString();
}

function mapVendorBToCanonical(
  record: VendorBRecord,
): CanonicalRowCandidate {
  return {
    vendor: "vendor_b",
    externalId: record.transaction_ref,
    amount: minorUnitsToDecimal(record.total_minor),
    paidAt: epochMillisecondsToIso(record.paid_at_ms),
  };
}

function decodeVendorB(bytes: Uint8Array): CanonicalRowCandidate[] {
  return parseDelimited(bytes, {
    delimiter: "\t",
    header: true,
  }).map((record) =>
    mapVendorBToCanonical(VendorBRecordSchema.parse(record)),
  );
}

export async function importVendorB(input: ImportInput): Promise<void> {
  await importSignedGzipTransactions(input, decodeVendorB);
}
```

提示されたVendor B行は次の正規化結果になります。

```ts
{
  vendor: "vendor_b",
  externalId: "b-92",
  amount: "12.30",
  paidAt: "2026-08-20T10:15:00.000Z",
}
```

## 失敗時の扱い

- 署名不正：展開、parse、永続化を一切呼ばず、そのまま失敗を返す
- gzip破損・20 MB超過：parse、永続化を呼ばない
- TSV構文不正、列不足、未知列：ファイル全体を失敗させる
- `total_minor`が空、負数、小数、非数字：ファイル全体を失敗させる
- `paid_at_ms`が整数でない、正確に扱えない、日付範囲外：ファイル全体を失敗させる
- 正規化後のCanonical検証失敗：ファイル全体を失敗させる
- 永続化失敗：例外を上位へ返す

ログやエラーへ`rawBody`、署名、vendor secretを含めません。行番号とフィールド名は診断情報として付加できます。

なお、「永続化処理自体が途中で失敗した場合も0行に戻す」ことまで要求するなら、`persistNewTransactions`側にDBトランザクションまたは原子的なbulk insertが必要です。提示されたコードだけで保証できるのは、永続化呼び出し前の失敗で0行という点です。

## テスト

最低限、次を追加します。

1. 共通の安全性

   - `verifyHmac`が`gunzipWithLimit`より先に呼ばれる
   - 署名不正時にgunzip、parse、persistが呼ばれない
   - 20 MB超過時にparse、persistが呼ばれない
   - 2行目のvalidation失敗でもpersistが一度も呼ばれない
   - persistへ渡る値がすべて`CanonicalRow`である

2. Vendor B変換

   - `"1230"` → `"12.30"`
   - `"5"` → `"0.05"`
   - `"0"` → `"0.00"`
   - `"0005"` → `"0.05"`
   - `"1787220900000"` → `"2026-08-20T10:15:00.000Z"`
   - tab区切りで読み取れる
   - comma区切りのVendor Bファイルは失敗する

3. Vendor B不正値

   - `total_minor`: `""`、`"-1"`、`"12.3"`、`"abc"`
   - `paid_at_ms`: 小数、非数字、安全整数範囲外、Date範囲外
   - `transaction_ref`の空文字
   - 必須列欠落、余分な列、壊れたTSV
   - 不正行が末尾にある複数行ファイルでも0行保存

4. 重複排除

   - `vendor_b:b-92`同士は1件になる
   - `vendor_a:same-id`と`vendor_b:same-id`は別取引になる
   - 重複排除がCanonical検証後に行われる

5. Vendor A非回帰

   - 既存fixtureの正規化結果が変更されない
   - delimiterが引き続きcomma
   - 署名不正、展開上限、parse/validation失敗時の呼び出し順が従来どおり
   - 既存Vendor Aテストを変更せず通す

実装は「Canonical enumへの1値追加」「共通順序の抽出」「Vendor B DTO・変換・入口の追加」に収まり、Vendor A固有ロジックと永続化インターフェースには変更を入れません。

補足として、設計用の`referytale`スキルは事前対応表の保存を要求しますが、この環境は読み取り専用のため保存工程を実行できませんでした。また、同じ理由で`.agent/CONTINUITY.md`も作成していません。
