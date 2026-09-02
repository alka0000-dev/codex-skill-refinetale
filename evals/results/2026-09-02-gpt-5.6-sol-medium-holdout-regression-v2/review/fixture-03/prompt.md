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

## Candidate B

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

## Candidate C

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

## Candidate D

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

## Candidate E

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

## Candidate F

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
