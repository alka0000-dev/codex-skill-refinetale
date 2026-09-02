実装の中心は、`format` をデータ取得前に検証し、既存の共通経路を通した `PublicOrderExportRow` を最後の出力境界でだけCSV/NDJSONへ分岐させることです。永続化層と公開項目変換は変更しません。

## 変更契約

変更する挙動:

- `format=ndjson` を受理する。
- `format` 省略時と `format=csv` は既存CSVを返す。
- 不正な `format` は400となり、`streamOrders`、監査、serializerを呼ばない。
- NDJSONは各 `PublicOrderExportRow` を `JSON.stringify(row) + "\n"` で出力する。
- 監査の `format` に実際の `"csv" | "ndjson"` を記録する。

変更しない挙動:

- `requirePermission(session, "orders:export")`
- `session.tenantId` からのtenant scope確定
- `ExportOrderFilterSchema`
- status、from、to、limitの意味
- 10,000件上限
- `streamOrders(filter)` とその順序
- `toPublicOrderExportRow` による公開項目の限定
- 監査の実行位置と1回だけという性質
- `streamCsv` の実装、引数、headers、content type
- CSVの出力byte列

## 処理の流れ

```text
Request
  ↓
requirePermission
  ↓
session.tenantIdを含むfilterのparse
  ↓
formatのparse（省略時csv）
  │ 不正 → 400。ここまでstreamOrders未実行
  ↓
streamOrders(filter)              ← 永続化層への唯一の経路
  ↓
mapStream(rows, toPublicOrderExportRow)
  │                              ← fraudScore/internalNoteを除去
  ↓
audit.record(..., { format })      ← 1回だけ
  ↓
csv / ndjson serializer            ← ここだけ形式差
```

形式をrepositoryやmapperへ渡さないことが重要です。形式ごとのquery、filter、row型、mapperは作りません。

## handler案

既存の呼び出し元を不要に変更しないため、関数名はひとまず維持できます。

```ts
const ExportOrderFormatSchema = z.enum(["csv", "ndjson"]).default("csv");

type ExportOrderFormat = z.infer<typeof ExportOrderFormatSchema>;

export async function exportOrdersCsv(req: Request, session: Session) {
  requirePermission(session, "orders:export");

  const filter = ExportOrderFilterSchema.parse({
    tenantId: session.tenantId,
    status: req.query.status,
    from: req.query.from,
    to: req.query.to,
    limit: Math.min(Number(req.query.limit ?? 10_000), 10_000),
  });

  // 既存のZodエラー→400変換をそのまま利用する。
  const format: ExportOrderFormat = ExportOrderFormatSchema.parse(
    req.query.format,
  );

  // formatの検証が完了するまで永続化層へ触れない。
  const rows = streamOrders(filter);
  const publicRows = mapStream(rows, toPublicOrderExportRow);

  // 既存CSVと同じ位置で、分岐の外から一度だけ記録する。
  audit.record("orders.exported", {
    tenantId: session.tenantId,
    format,
  });

  if (format === "ndjson") {
    return streamOrderExportNdjson(publicRows);
  }

  // この呼び出しとstreamCsv自体は変更しない。
  return streamCsv(publicRows, {
    headers: ["order_id", "status", "total", "placed_at"],
    contentType: "text/csv; charset=utf-8",
  });
}
```

分岐は、実際に観測可能な差があるserializer呼び出しだけに置きます。

`format` をfilter schemaへ追加するとrepository用filterへ出力形式が混入します。そのため、filterとformatは別々に検証するのが適切です。

## NDJSON serializer案

既存の文字列ストリーム生成機能を使い、全件を配列へ集めない実装にします。

```ts
export function streamOrderExportNdjson(
  rows: AsyncIterable<PublicOrderExportRow>,
) {
  const lines = mapStream(
    rows,
    (row) => `${JSON.stringify(row)}\n`,
  );

  return streamText(lines, {
    contentType: "application/x-ndjson; charset=utf-8",
  });
}
```

`streamText` はプロジェクト既存のUTF-8ストリーミングprimitiveに読み替えます。新しい共通serializer基盤やstrategy registryは不要です。

出力例:

```ndjson
{"order_id":"o-1","status":"paid","total":"1200","placed_at":"2026-09-01T10:00:00Z"}
{"order_id":"o-2","status":"cancelled","total":"800","placed_at":"2026-09-01T11:00:00Z"}
```

各objectの末尾に必ず `\n` が付きます。0件の場合はobject行が存在しないため0 byteです。空行だけを出すと「1行1 JSON object」を破るため、`\n` 単独は出しません。

## 永続化層

変更不要です。

```ts
streamOrders(filter)
```

について、既存queryの以下をそのまま維持します。

- `tenantId` 条件
- status/from/to条件
- 既存のORDER BY
- `limit <= 10_000`
- 0件なら0行
- 1件につき1つの `OrderRow`

NDJSON用query、`streamOrdersNdjson`、format引数、追加SELECTは作りません。内部項目をrepositoryのSELECTから除外する変更も、既存利用箇所への影響が不明なので今回のスコープには含めません。

## 最小テスト構成

### 1. NDJSON serializer単体テスト

serializerが所有する仕様だけを確認します。

```ts
it("writes one UTF-8 JSON object per line with a trailing newline", async () => {
  const response = streamOrderExportNdjson(
    asAsyncIterable([
      {
        order_id: "o-1",
        status: "paid",
        total: "12.30",
        placed_at: "2026-09-01T10:00:00Z",
      },
      {
        order_id: "o-2",
        status: "cancelled",
        total: "0",
        placed_at: "2026-09-01T11:00:00Z",
      },
    ]),
  );

  expect(response.contentType).toBe(
    "application/x-ndjson; charset=utf-8",
  );
  expect(await readUtf8(response)).toBe(
    [
      '{"order_id":"o-1","status":"paid","total":"12.30","placed_at":"2026-09-01T10:00:00Z"}',
      '{"order_id":"o-2","status":"cancelled","total":"0","placed_at":"2026-09-01T11:00:00Z"}',
      "",
    ].join("\n"),
  );
});
```

追加ケース:

- 文字列中の改行、引用符、非ASCII文字が正しいJSON/UTF-8になる。
- 0行入力は0 byte。
- 途中で入力streamが失敗した場合、全件をbufferせずエラーが伝播する。

### 2. CSV互換性テスト

実装前の既存CSV出力をgolden byte列として固定します。

```ts
it.each([
  ["omitted", {}],
  ["explicit csv", { format: "csv" }],
])("keeps the existing CSV bytes: %s", async (_, query) => {
  const response = await exportOrdersCsv(
    request({ query }),
    authorizedSession,
  );

  expect(await readBytes(response)).toEqual(existingCsvGoldenBytes);
});
```

文字列比較ではなく `Buffer` / `Uint8Array` を比較し、次も検出できるようにします。

- BOM
- `LF` / `CRLF`
- header順
- quoting
- charset
- 末尾newline

### 3. handlerの共通経路テスト

CSVとNDJSONを対象にしたtable testを1つ置きます。

```ts
it.each(["csv", "ndjson"] as const)(
  "uses the same scoped repository filter for %s",
  async (format) => {
    await consume(
      await exportOrdersCsv(
        request({
          query: {
            format,
            status: "paid",
            from: "2026-09-01",
            to: "2026-09-02",
            limit: "20000",
          },
        }),
        { ...authorizedSession, tenantId: "tenant-a" },
      ),
    );

    expect(streamOrders).toHaveBeenCalledTimes(1);
    expect(streamOrders).toHaveBeenCalledWith({
      tenantId: "tenant-a",
      status: "paid",
      from: "2026-09-01",
      to: "2026-09-02",
      limit: 10_000,
    });
  },
);
```

### 4. 公開項目と順序の共通性

内部項目を持つ同じrepository row列を両形式で消費します。

期待結果:

- order順が同じ。
- `order_id/status/total/placed_at` の値が同じ。
- `fraudScore` と `internalNote` がどちらにも存在しない。
- `toPublicOrderExportRow` が各rowにつき一度だけ呼ばれる。

CSVは既存parserで読み戻し、NDJSONは行ごとに `JSON.parse` して、同じ `PublicOrderExportRow[]` と比較します。

### 5. 早期終了と副作用

最低限、次を明示的に確認します。

| 条件 | repository | serializer | audit |
|---|---:|---:|---:|
| 権限なし | 0回 | 0回 | 0回 |
| filter不正 | 0回 | 0回 | 0回 |
| format不正 | 0回 | 0回 | 0回 |
| CSV成功 | 1回 | CSV 1回 | `format: "csv"` で1回 |
| NDJSON成功 | 1回 | NDJSON 1回 | `format: "ndjson"` で1回 |

さらに既存監査順序を固定するなら:

- `streamOrders(filter)` が同期的に失敗した場合、監査は0回。
- response bodyの消費中にrepository streamが失敗した場合、監査はすでに1回。
- serializer生成が同期的に失敗した場合も、監査は1回。

これは現在の「`streamOrders` 呼び出し後、serializer呼び出し前に監査する」という位置を維持した結果です。

今回はワークスペースにソースコードやテストがなく、読み取り専用でもあるため、実装・テスト実行・必須の `.agent/CONTINUITY.md` 作成は行えませんでした。したがって上記は具体的な実装案と必要な検証ケースであり、実装完了の報告ではありません。また `referytale` の段階保存も読み取り専用制約で実施できず、ユーザー提示の用語と順序を維持する形で代替しました。
