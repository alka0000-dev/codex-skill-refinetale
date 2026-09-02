実装の要点は、公開rowを作るまでの経路を完全に共通化し、最後のserializerだけを分岐させることです。永続化層には変更を加えません。

```text
認可
  → tenantIdを含むfilter確定
  → format検証
  → streamOrders(filter)
  → toPublicOrderExportRow
  → 監査eventを1回記録
  → CSVまたはNDJSON serializer
```

## Handler

既存のCSV呼び出しは、オプションを含めてそのまま残します。これによりCSVのbyte-for-byte互換性を守りやすくなります。

```ts
const ExportOrderFormatSchema = z.enum(["csv", "ndjson"]);

type ExportOrderFormat = z.infer<typeof ExportOrderFormatSchema>;

function parseExportOrderFormat(value: unknown): ExportOrderFormat {
  const result = ExportOrderFormatSchema.safeParse(value ?? "csv");

  if (!result.success) {
    // プロジェクト既存の400エラー型を使用する
    throw new BadRequestError("format must be csv or ndjson");
  }

  return result.data;
}

export async function exportOrdersCsv(req: Request, session: Session) {
  // formatが不正でも、認可を先に評価する。
  requirePermission(session, "orders:export");

  // tenant scopeと抽出条件をserializer選択前に確定する。
  const filter = ExportOrderFilterSchema.parse({
    tenantId: session.tenantId,
    status: req.query.status,
    from: req.query.from,
    to: req.query.to,
    limit: Math.min(Number(req.query.limit ?? 10_000), 10_000),
  });

  // streamOrdersより前なので、不正formatではデータを読まない。
  const format = parseExportOrderFormat(req.query.format);

  // repository呼び出しと公開row変換は両形式で一度だけ行う。
  const rows = streamOrders(filter);
  const publicRows = mapStream(rows, toPublicOrderExportRow);

  // 分岐内で記録すると重複・記録漏れが起きやすいため共通箇所で一度だけ記録する。
  audit.record("orders.exported", {
    tenantId: session.tenantId,
    format,
  });

  if (format === "ndjson") {
    return streamNdjson(publicRows, {
      contentType: "application/x-ndjson; charset=utf-8",
    });
  }

  // この呼び出しは既存コードから変更しない。
  return streamCsv(publicRows, {
    headers: ["order_id", "status", "total", "placed_at"],
    contentType: "text/csv; charset=utf-8",
  });
}
```

関数名 `exportOrdersCsv` は不正確になりますが、既存routeやimportへの影響を避けるなら今回は維持するのが安全です。名前の変更はNDJSON対応とは別差分にします。

## 公開row変換

公開項目の制御はserializerではなく、この変換で一元管理します。

```ts
export function toPublicOrderExportRow(
  row: OrderRow,
): PublicOrderExportRow {
  return {
    order_id: row.orderId,
    status: row.status,
    total: row.total,
    placed_at: row.placedAt,
  };
}
```

`fraudScore` と `internalNote` を「serializer側で除外」する設計にはしません。両serializerが受け取る時点で、すでに公開可能な4項目だけになっていることが重要です。

## 永続化層

新しいrepositoryメソッドやNDJSON専用queryは作りません。

```ts
const rows = streamOrders(filter);
```

この一経路だけを維持するため、次の仕様が形式に依存しません。

- `session.tenantId`によるtenant分離
- status、from、to
- 最大10,000件
- repositoryが保証している並び順
- 同じ行集合

repositoryで選択する内部項目を減らす最適化は、既存CSVにも影響し得るため今回の変更には含めません。

## NDJSON serializer

既存のstreaming応答基盤を使い、1 rowずつUTF-8へ変換します。全件を配列化してはいけません。

```ts
export function streamNdjson(
  rows: AsyncIterable<PublicOrderExportRow>,
  options: {
    contentType: "application/x-ndjson; charset=utf-8";
  },
) {
  const chunks = mapStream(
    rows,
    (row) => `${JSON.stringify(row)}\n`,
  );

  return streamText(chunks, {
    contentType: options.contentType,
    encoding: "utf-8",
  });
}
```

`streamText` はプロジェクト既存のHTTP streaming primitiveに読み替えます。確認すべき契約は以下です。

- chunkを再エンコード・整形しない
- backpressureを維持する
-各objectの直後に`\n`を出す
- `JSON.stringify`失敗時に不完全な別objectを出さない

非空出力は必ずnewlineで終わります。0件の場合は、objectに対応しない空行を作らず0 byteとするのがNDJSONとして自然です。この挙動もテストで固定します。

## テスト

### Handlerテスト

依存をmockし、処理順序と呼び出し回数を検証します。

1. `format`省略

   - `streamOrders`が1回呼ばれる
   - filterに`session.tenantId`が入る
   - `streamCsv`が1回呼ばれる
   - `streamNdjson`は呼ばれない
   - 監査eventは1回、`format: "csv"`

2. `format=csv`

   - 省略時と同じfilter、公開row、serializer引数
   - 監査eventは1回、`format: "csv"`

3. `format=ndjson`

   - `streamOrders`は同じfilterで1回
   - `streamNdjson`が公開row streamを受け取る
   - content typeが正確に一致する
   - `streamCsv`は呼ばれない
   - 監査eventは1回、`format: "ndjson"`

4. 不正なformat

```ts
it("returns 400 without reading order data", async () => {
  await expect(
    exportOrdersCsv(request({ format: "json" }), session),
  ).rejects.toMatchObject({ statusCode: 400 });

  expect(streamOrders).not.toHaveBeenCalled();
  expect(streamCsv).not.toHaveBeenCalled();
  expect(streamNdjson).not.toHaveBeenCalled();
  expect(audit.record).not.toHaveBeenCalled();
});
```

5. 認可順序

   - 権限なし＋`format=json`でも認可エラーになる
   - `streamOrders`、serializer、監査は呼ばれない
   - これによりformat検証を認可oracleとして使わせない

6. tenant分離

   - requestにtenant相当の余分なqueryがあっても無視する
   - `streamOrders`へ渡るtenantIdは必ず`session.tenantId`

7. 件数上限

   - `limit=20000`は10,000
   - `limit=100`は100
   - CSVとNDJSONで同じfilterになる

### 公開row変換テスト

```ts
it("maps only public export fields", () => {
  const row: OrderRow = {
    tenantId: "tenant-a",
    orderId: "order-1",
    status: "paid",
    total: "1200",
    placedAt: "2026-09-02T01:02:03Z",
    fraudScore: 98,
    internalNote: "do not export",
  };

  expect(toPublicOrderExportRow(row)).toEqual({
    order_id: "order-1",
    status: "paid",
    total: "1200",
    placed_at: "2026-09-02T01:02:03Z",
  });

  expect(JSON.stringify(toPublicOrderExportRow(row)))
    .not.toContain("fraudScore");
  expect(JSON.stringify(toPublicOrderExportRow(row)))
    .not.toContain("internalNote");
});
```

### NDJSON serializerテスト

期待byte列を直接比較します。

```ts
it("writes one UTF-8 JSON object per line with a trailing newline", async () => {
  const body = await collectBytes(
    streamNdjson(
      asyncRows([
        {
          order_id: "注文-1",
          status: "paid",
          total: "1200",
          placed_at: "2026-09-02T01:02:03Z",
        },
        {
          order_id: "order-2",
          status: "pending",
          total: "500",
          placed_at: "2026-09-02T02:03:04Z",
        },
      ]),
      {
        contentType: "application/x-ndjson; charset=utf-8",
      },
    ),
  );

  expect(body.toString("utf8")).toBe(
    '{"order_id":"注文-1","status":"paid","total":"1200","placed_at":"2026-09-02T01:02:03Z"}\n' +
    '{"order_id":"order-2","status":"pending","total":"500","placed_at":"2026-09-02T02:03:04Z"}\n',
  );
});
```

追加で以下を検証します。

- 0件は0 byte
- 改行、引用符、バックスラッシュを含む値が正しくJSON escapeされる
- 最終行も`\n`で終わる
- `fraudScore`、`internalNote`、`tenantId`が含まれない
- 入力順序と出力行順序が一致する

### CSVの回帰テスト

mockだけではbyte-for-byte互換性を証明できないため、変更前の実装から取得したCSVをgolden fixtureとして固定します。

```ts
expect(await collectBytes(response)).toEqual(
  readFixture("orders-export.csv"),
);
```

同じ固定rowについて、以下を含むfixtureを用意します。

- カンマ
- 二重引用符
- 改行
- 非ASCII文字
- 空文字またはnullable値が許される場合の表現

既存の`streamCsv`、header順、content type、改行コード、quote規則、BOMの有無には手を加えません。これがCSVのbyte-for-byte非変更を担保する中心的なテストになります。
