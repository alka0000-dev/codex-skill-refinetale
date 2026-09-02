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
