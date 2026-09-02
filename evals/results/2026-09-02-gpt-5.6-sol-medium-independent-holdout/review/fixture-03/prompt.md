You are grading six anonymized answers to an independent holdout evaluation. Return only the requested structured result.

# 03: Import a second transaction-file format

## Purpose

安全な共通取り込み経路を維持しながら、ファイル形式固有の変換だけを分離できるか確認する。

## Input

取引ファイル取り込みにVendor Bを追加します。既存のVendor Aの安全性とデータ契約を維持しながら、実装差分を小さくした設計を提案してください。処理順、追加・変更する型や関数、Vendor B固有の変換、失敗時の扱い、テストを具体的に示してください。

現在の取り込み処理:

```ts
export async function importVendorA(input: ImportInput) {
  verifyHmac(input.rawBody, input.signature, input.vendorSecret);
  const bytes = await gunzipWithLimit(input.rawBody, 20 * MB);
  const records = parseDelimited(bytes, { delimiter: ",", header: true });
  const rows = records.map(mapVendorAToCanonical).map((row) => CanonicalRowSchema.parse(row));
  await persistNewTransactions(dedupe(rows, { key: (row) => `${row.vendor}:${row.externalId}` }));
}
```

既存の正規化型:

```ts
const CanonicalRowSchema = z.object({
  vendor: z.enum(["vendor_a"]),
  externalId: z.string().min(1),
  amount: z.string().regex(/^\d+\.\d{2}$/),
  paidAt: z.string().datetime(),
});
```

Vendor Aの列:

```text
id,amount_decimal,paid_at_iso
a-17,12.30,2026-08-20T10:15:00Z
```

Vendor Bの仕様:

- 同じ署名方式、gzip形式、20 MB展開上限を使う。
- 区切りはtabで、列は`transaction_ref`、`total_minor`、`paid_at_ms`。
- `total_minor`は非負の整数文字列で小数部は2桁。例:`1230`は`12.30`。
- `paid_at_ms`はUnix epoch milliseconds。

```text
transaction_ref\ttotal_minor\tpaid_at_ms
b-92\t1230\t1787220900000
```

既存契約:

- HMACは圧縮されたraw bodyに対して、展開やparseより先に検証する。
- 署名不正、展開上限超過、parse/validation errorのfileは1行も保存しない。
- 永続化層は`CanonicalRow`だけを受け取り、Vendor固有DTOを受け取らない。
- 同じ`externalId`でもVendorが異なれば別取引。同じVendor内だけ重複を除く。
- Vendor Aの挙動は変えない。

## Pass conditions

- **S1 Processing path:** 署名検証、上限付き展開、parse、正規化validation、dedupe、永続化を1つの取り込み経路として再利用し、全工程を複製しない。
- **S2 Safety and atomicity:** raw body署名検証を最初に保ち、展開上限と全行validationを保存より前に行い、部分保存しない。
- **S3 Format variation:** tab、header、minor unitsから2桁decimal、epoch millisecondsからISOへの変換を具体化する。
- **S4 Canonical contract:** schemaをVendor Bへ拡張し、永続化は`CanonicalRow`だけを使い、vendorを含むdedupe keyを維持する。
- **S5 Verification:** 正常変換、金額境界、不正整数、日時、列不足、署名不正、展開上限、途中行不正で保存0件、vendor間/内重複、Vendor A回帰を確認する。

## Critical failure conditions

- Vendor Bだけ署名検証または展開上限を迂回する。
- 全行validation前に保存して部分保存し得る。
- Vendor B用の別repositoryまたは永続化DTO経路を追加する。

## Scoring

S1〜S5を各0〜2点で採点する。2点は共通工程と形式差分の境界が実装単位で明確で安全条件とテストが揃う、1点は一部不足、0点は工程複製・契約破壊・変換誤り・安全条件欠落がある。8〜10点かつ全基準1点以上をPass、6〜7点または0点を含む8点以上をBorderline、5点以下をFailとする。critical failureを優先し、抽象化名や完成コードとの一致は要求しない。


## Judge instructions

Score each candidate independently using only its final answer and this fixture.
Do not guess its generation condition. The workspace intentionally contained no source files and
was read-only, so judge the proposed data flow, types, boundaries, failure behavior, and observable
test plan. Do not fail a candidate merely because it could not edit or execute code.

Score S1 through S5 from 0 to 2 exactly as defined by the fixture. `total` must equal their sum.
If any critical failure condition is met, set `critical_failure` to true and `outcome` to
`critical_failure`. Otherwise use: pass = total 8-10 with every S at least 1; borderline = total
6-7, or total 8-10 with any S equal to 0; fail = total 0-5. Evidence must name concrete satisfied
and missing behavior. Do not reward headings, verbosity, or terminology by itself.


## Candidate A

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

## Candidate B

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

## Candidate C

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

## Candidate D

## 推奨設計

Vendor固有差分を入口の「delimiter」と「CanonicalRowへの変換」に限定し、署名検証以降のパイプラインを1本にします。Vendorによる`switch`は不要です。

### 変更契約

変更する挙動:

- Vendor Bの署名付きgzip TSVを受理する。
- Vendor BをCanonicalRowへ変換して保存する。
- `CanonicalRow.vendor`に`vendor_b`を追加する。

変更しない挙動:

- Vendor Aの入力形式、変換結果、エラー、重複判定。
- HMAC検証対象は圧縮済みraw body。
- HMAC → 展開 → parse → 全行validation → dedupe → 永続化の順序。
- validation完了前には1行も保存しない。
- 永続化層へ渡す型はCanonicalRowのみ。
- 重複キーは`vendor + externalId`。

## 型と関数

```ts
const CanonicalRowSchema = z.object({
  vendor: z.enum(["vendor_a", "vendor_b"]),
  externalId: z.string().min(1),
  amount: z.string().regex(/^\d+\.\d{2}$/),
  paidAt: z.string().datetime(),
});

type CanonicalRow = z.infer<typeof CanonicalRowSchema>;
type CanonicalRowInput = z.input<typeof CanonicalRowSchema>;
type RowMapper = (record: unknown) => CanonicalRowInput;
```

共通パイプラインは引数を増やしすぎず、実際に異なる2点だけを受け取ります。

```ts
async function importDelimitedTransactions(
  input: ImportInput,
  delimiter: "," | "\t",
  mapToCanonical: RowMapper,
): Promise<void> {
  verifyHmac(input.rawBody, input.signature, input.vendorSecret);

  const bytes = await gunzipWithLimit(input.rawBody, 20 * MB);
  const records = parseDelimited(bytes, { delimiter, header: true });

  // 全行の変換・検証が完了するまで副作用を起こさない。
  const rows = records.map((record) =>
    CanonicalRowSchema.parse(mapToCanonical(record)),
  );

  const uniqueRows = dedupe(rows, {
    key: (row) => `${row.vendor}:${row.externalId}`,
  });

  await persistNewTransactions(uniqueRows);
}

export function importVendorA(input: ImportInput): Promise<void> {
  return importDelimitedTransactions(input, ",", mapVendorAToCanonical);
}

export function importVendorB(input: ImportInput): Promise<void> {
  return importDelimitedTransactions(input, "\t", mapVendorBToCanonical);
}
```

Vendor Aのmapperには手を加えません。既存処理を薄いwrapperにするだけなので、観測可能な処理順と結果は維持されます。

## Vendor B固有変換

Vendor Bの外部DTOはアダプター内だけに閉じ込めます。

```ts
const EpochMillisecondsSchema = z
  .string()
  .regex(/^-?\d+$/)
  .transform(Number)
  .refine(Number.isSafeInteger, "paid_at_ms must be a safe integer")
  .refine(
    (value) => !Number.isNaN(new Date(value).getTime()),
    "paid_at_ms is outside the supported date range",
  );

const VendorBRecordSchema = z.object({
  transaction_ref: z.string().min(1),
  total_minor: z.string().regex(/^\d+$/),
  paid_at_ms: EpochMillisecondsSchema,
});

function minorUnitsToDecimal(value: string): string {
  // Numberへ変換せず、桁落ちや指数表記を避ける。
  const digits = value.padStart(3, "0");
  const major = digits.slice(0, -2).replace(/^0+(?=\d)/, "");

  return `${major}.${digits.slice(-2)}`;
}

function mapVendorBToCanonical(record: unknown): CanonicalRowInput {
  const row = VendorBRecordSchema.parse(record);

  return {
    vendor: "vendor_b",
    externalId: row.transaction_ref,
    amount: minorUnitsToDecimal(row.total_minor),
    paidAt: new Date(row.paid_at_ms).toISOString(),
  };
}
```

変換例:

| Vendor B | Canonical |
|---|---|
| `transaction_ref: "b-92"` | `externalId: "b-92"` |
| `total_minor: "1230"` | `amount: "12.30"` |
| `total_minor: "1"` | `amount: "0.01"` |
| `total_minor: "0"` | `amount: "0.00"` |
| `paid_at_ms: "1787220900000"` | `paidAt: "2026-08-20T10:15:00.000Z"` |

`paid_at_ms`には、仕様にない「非負」の制約を追加しません。負のepoch値を拒否する必要があるなら、Vendor Bの契約として明示された時点で追加します。

## 失敗時の扱い

例外を握りつぶしたり、不正行だけをskipしたりしません。

- 署名不正: 展開・parse・永続化を実行しない。
- 展開上限超過: parse・永続化を実行しない。
- TSV parse失敗: 変換・永続化を実行しない。
- B DTO不正: Canonical変換を中止し、永続化しない。
- Canonical validation失敗: 永続化しない。
- 1行でも不正: `records.map(...)`が完了しないため、正常行も含めて0行保存。
- 永続化失敗: エラーを呼び出し元へ返す。DB障害までfile単位の原子性が必要なら、`persistNewTransactions`自身が単一トランザクションを所有する必要があります。

DB側にvendor列のenum/check制約がある場合は`vendor_b`を追加します。重複制約は引き続き`UNIQUE (vendor, external_id)`であり、`external_id`単独には変更しません。

## 最小テスト

| 対象 | ケース | 期待結果 |
|---|---|---|
| Vendor A回帰 | 既存CSVを取り込む | 従来と同じCanonicalRowを1回保存 |
| Vendor B成功 | 提示されたTSV | `vendor_b / b-92 / 12.30 / ISO日時`を保存 |
| B金額変換 | `0`, `1`, `1230`, `0001` | `0.00`, `0.01`, `12.30`, `0.01` |
| B金額不正 | `-1`, `1.2`, 空文字 | file全体をreject、保存0回 |
| B日時不正 | 小数、非数値、安全整数外、Date範囲外 | file全体をreject、保存0回 |
| B混在file | 正常行＋不正行 | 正常行も保存されず、保存0回 |
| A/B署名不正 | gzipでないraw body＋不正署名 | HMACエラー。gunzip・parse・保存0回 |
| A/B上限超過 | 正しい署名の展開超過gzip | parse・保存0回 |
| 同Vendor重複 | Bで同じrefを2行 | CanonicalRowは1行だけ保存 |
| Vendor間同一ID | AとBで同じexternalIdを順次取り込み | DBには2取引 |
| DB重複契約 | 同じvendor/externalIdを再取り込み | 既存の`persistNewTransactions`契約どおり新規作成なし |

今回はコードベースが提示されておらず設計提案のみのため、テストは未実行です。実装時は特に「不正署名の入力を非gzipにする」テストで、HMAC検証が展開より確実に先であることを直接証明できます。

## Candidate E

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

## Candidate F

## 提案

Vendor A/B の入口関数は分けたまま、署名検証以降の安全な処理順を1つの共通関数へ集約します。Vendor差分は `delimiter` と `mapToCanonical` だけです。Vendor判定用の `switch` や共通DTOは追加しません。

### 変更契約

変更する挙動:

- `importVendorB` でtab区切りのVendor Bファイルを受理する。
- `total_minor` を2桁小数文字列へ変換する。
- `paid_at_ms` をISO日時へ変換する。
- 正規化後の `vendor` は `"vendor_b"` になる。

変更しない挙動:

- Vendor Aの列、変換結果、処理順。
- HMACは圧縮された `rawBody` に対して最初に検証する。
- 展開上限は20 MB。
- 1行でもparse/validationに失敗すれば永続化を呼ばない。
- 永続化層へ渡すのは `CanonicalRow` だけ。
- 重複キーは `vendor + externalId`。
- 永続化エラーは握りつぶさず呼び出し元へ返す。

## 型と関数

### 1. 正規化型へVendor Bを追加

```ts
export const CanonicalRowSchema = z.object({
  vendor: z.enum(["vendor_a", "vendor_b"]),
  externalId: z.string().min(1),
  amount: z.string().regex(/^\d+\.\d{2}$/),
  paidAt: z.string().datetime(),
});

export type CanonicalRow = z.infer<typeof CanonicalRowSchema>;
```

変更はenum値の追加だけです。Vendor固有DTOを永続化層や後続処理へ公開しません。

### 2. Vendor B境界の検証と変換

```ts
const MinorUnitsSchema = z
  .string()
  .regex(/^\d+$/)
  .transform((value) => {
    const normalized = value.replace(/^0+(?=\d)/, "");
    const padded = normalized.padStart(3, "0");

    return `${padded.slice(0, -2)}.${padded.slice(-2)}`;
  });

const EpochMillisecondsSchema = z
  .string()
  .regex(/^\d+$/)
  .transform((value, context) => {
    const milliseconds = Number(value);
    const date = new Date(milliseconds);

    if (
      !Number.isSafeInteger(milliseconds) ||
      Number.isNaN(date.getTime())
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "paid_at_ms must be valid Unix epoch milliseconds",
      });
      return z.NEVER;
    }

    return date.toISOString();
  });

const VendorBRowSchema = z.object({
  transaction_ref: z.string().min(1),
  total_minor: MinorUnitsSchema,
  paid_at_ms: EpochMillisecondsSchema,
});

function mapVendorBToCanonical(record: unknown) {
  const row = VendorBRowSchema.parse(record);

  return {
    vendor: "vendor_b" as const,
    externalId: row.transaction_ref,
    amount: row.total_minor,
    paidAt: row.paid_at_ms,
  };
}
```

変換例:

| Vendor B入力 | Canonical値 |
|---|---|
| `total_minor: "0"` | `amount: "0.00"` |
| `total_minor: "5"` | `amount: "0.05"` |
| `total_minor: "1230"` | `amount: "12.30"` |
| `paid_at_ms: "1787220900000"` | `paidAt: "2026-08-20T10:15:00.000Z"` |

金額は `Number` に変換しません。これにより、大きな整数文字列でも浮動小数点の丸めを持ち込みません。

### 3. 安全境界を共通処理にする

```ts
type Delimiter = "," | "\t";

type MapToCanonical = (
  record: unknown,
) => z.input<typeof CanonicalRowSchema>;

async function importTransactions(
  input: ImportInput,
  delimiter: Delimiter,
  mapToCanonical: MapToCanonical,
) {
  verifyHmac(input.rawBody, input.signature, input.vendorSecret);

  const bytes = await gunzipWithLimit(input.rawBody, 20 * MB);

  const records = parseDelimited(bytes, {
    delimiter,
    header: true,
  });

  const rows = records
    .map(mapToCanonical)
    .map((row) => CanonicalRowSchema.parse(row));

  const uniqueRows = dedupe(rows, {
    key: (row) => `${row.vendor}:${row.externalId}`,
  });

  await persistNewTransactions(uniqueRows);
}
```

入口関数は薄いラッパーにします。

```ts
export function importVendorA(input: ImportInput) {
  return importTransactions(input, ",", mapVendorAToCanonical);
}

export function importVendorB(input: ImportInput) {
  return importTransactions(input, "\t", mapVendorBToCanonical);
}
```

Vendor Aのmapperは変更しません。Vendor判定の分岐もありません。入口で選ばれたmapperは正規化後すぐ共通の `CanonicalRow[]` へ合流します。

## 処理順と失敗時の扱い

```text
compressed rawBody
  → HMAC検証
  → 20 MB制限付きgunzip
  → vendor固有delimiterでparse
  → vendor固有の入力検証・変換
  → CanonicalRowSchemaで共通検証
  → vendor + externalIdで重複排除
  → 1回だけ永続化
```

各失敗の結果:

- 署名不正: gunzip、parse、永続化を実行しない。
- 展開上限超過: parse、永続化を実行しない。
- TSV/CSV parse失敗: mapper、永続化を実行しない。
- 必須列欠落・不正金額・不正日時: `records.map(...)` が完了しないため永続化を実行しない。
- Canonical検証失敗: 永続化を実行しない。
- 永続化失敗: エラーをそのまま伝播し、独自retryや部分fallbackは追加しない。

すべての行を配列へ正規化・検証した後に初めて `persistNewTransactions` を呼ぶため、「2行目が不正でも1行目を保存しない」が維持されます。

なお、永続化処理そのものの途中失敗に対するDB原子性は、既存repositoryのトランザクション契約に属します。今回の入力形式追加では変更しません。

## 最小テスト

実装ファイルが提示されておらず、作業ディレクトリも空だったためテストは未実施です。実装時には次を最低限追加します。

1. Vendor A回帰

- 既存CSVから従来と同じCanonicalRowが保存される。
- `vendor: "vendor_a"`、`amount: "12.30"`、元の日時表現が有効であることを確認。

2. Vendor B成功

- 提示されたTSVから次が1回保存される。

```ts
{
  vendor: "vendor_b",
  externalId: "b-92",
  amount: "12.30",
  paidAt: "2026-08-20T10:15:00.000Z",
}
```

3. Vendor B固有の境界値

- `"0"` → `"0.00"`
- `"5"` → `"0.05"`
- `"1230"` → `"12.30"`
- `"-1"`、`"1.2"`、空文字はvalidation error。
- 小数でない、範囲外の `paid_at_ms` はvalidation error。

4. 全件原子性

- 2行のVendor Bファイルで2行目を不正にし、`persistNewTransactions` が0回であることを確認。

5. 安全境界をVendor A/Bで共通確認

`it.each` で両入口に対して確認します。

- 署名不正なら `gunzipWithLimit` と永続化が0回。
- 20 MB超過ならparseと永続化が0回。
- parse/validation失敗なら永続化が0回。
- 成功時のみ永続化が1回。

6. 重複契約

- 同一Vendor・同一`externalId`は1件。
- `"vendor_a:x"` と `"vendor_b:x"` は2件として残る。

この設計では、追加される正本はVendor Bの入力スキーマとmapperだけです。安全な処理順、Canonical検証、重複排除、永続化経路は単一のまま維持されます。
