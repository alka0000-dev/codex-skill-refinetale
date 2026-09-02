実装方針は、`format` を永続化層へ渡さず、公開用rowへ変換した後のserializerだけを切り替える形です。これにより、認可・tenant scope・filter・上限・row集合・順序・公開項目を共通化できます。

## 処理順序

```text
requirePermission
  → tenantIdをsessionから設定したfilterをparse
  → formatをparse
  → serializerを選択
  → streamOrders(filter)
  → toPublicOrderExportRow
  → audit.record（1回）
  → CSVまたはNDJSONへserialize
```

重要なのは次の3点です。

- `format` の検証完了前に `streamOrders()` を呼ばない。
- `format` をrepositoryへ渡さない。
- CSVとNDJSONの分岐を、公開用rowへ変換した後に限定する。

## handler

```ts
import { z } from "zod";

const ExportOrderFormatSchema = z.enum(["csv", "ndjson"]).default("csv");

type ExportOrderFormat = z.infer<typeof ExportOrderFormatSchema>;

const csvOptions = {
  headers: ["order_id", "status", "total", "placed_at"],
  contentType: "text/csv; charset=utf-8",
} as const;

export async function exportOrders(req: Request, session: Session) {
  requirePermission(session, "orders:export");

  // tenantIdはrequestから受け取らず、必ずsessionから確定する。
  const filter = ExportOrderFilterSchema.parse({
    tenantId: session.tenantId,
    status: req.query.status,
    from: req.query.from,
    to: req.query.to,
    limit: Math.min(Number(req.query.limit ?? 10_000), 10_000),
  });

  // parseに失敗した場合、この後のstreamOrdersには到達しない。
  const format = ExportOrderFormatSchema.parse(req.query.format);

  const rows = streamOrders(filter);
  const publicRows = mapStream(rows, toPublicOrderExportRow);

  audit.record("orders.exported", {
    tenantId: session.tenantId,
    format,
  });

  return serializePublicOrderRows(publicRows, format);
}

function serializePublicOrderRows(
  rows: AsyncIterable<PublicOrderExportRow>,
  format: ExportOrderFormat,
) {
  if (format === "ndjson") {
    return streamOrdersNdjson(rows);
  }

  // 既存呼び出しとoptionsをそのまま残す。
  return streamCsv(rows, csvOptions);
}
```

現在の `ZodError` がHTTP 400へ変換される共通エラーハンドリングを前提としています。共通変換がない場合だけ、既存のfilter validationと同じ方法で400へ変換します。

既存関数名を維持する必要があるなら、`exportOrdersCsv` を `exportOrders` に変更せず、そのまま使っても動作上の問題はありません。ただし、複数形式を返す実態に合わせた名称変更は別コミットに分けるのが安全です。

## 公開用row変換

内部rowをspreadしないことが重要です。

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

以下のような実装は避けます。

```ts
// 内部項目追加時に漏えいするため不可
return {
  ...row,
  order_id: row.orderId,
};
```

`fraudScore` と `internalNote` はserializer側で除外するのではなく、この変換境界以降へ渡さない設計にします。

## NDJSON serializer

serializerの引数を `PublicOrderExportRow` に限定すると、誤って `OrderRow` を直接渡すことも型で防げます。

```ts
const NDJSON_CONTENT_TYPE =
  "application/x-ndjson; charset=utf-8";

export function streamOrdersNdjson(
  rows: AsyncIterable<PublicOrderExportRow>,
): Response {
  const encoder = new TextEncoder();
  const iterator = rows[Symbol.asyncIterator]();

  const body = new ReadableStream<Uint8Array>({
    async pull(controller) {
      try {
        const result = await iterator.next();

        if (result.done) {
          controller.close();
          return;
        }

        controller.enqueue(
          encoder.encode(`${JSON.stringify(result.value)}\n`),
        );
      } catch (error) {
        controller.error(error);
      }
    },

    async cancel(reason) {
      await iterator.return?.(reason);
    },
  });

  return new Response(body, {
    headers: {
      "content-type": NDJSON_CONTENT_TYPE,
    },
  });
}
```

各objectを必ず `JSON.stringify(row) + "\n"` とするため、非空レスポンスには末尾newlineがあります。0件の場合は空bodyです。0件時に `"\n"` を出すと「1行1 JSON object」を破るためです。

## 永続化層

永続化層には変更を加えません。

```ts
const rows: AsyncIterable<OrderRow> = streamOrders(filter);
```

`filter` に含まれるものだけがqueryへ渡ります。

```ts
type ExportOrderFilter = {
  tenantId: string;
  status?: OrderStatus;
  from?: string;
  to?: string;
  limit: number;
};
```

守るべきrepository側の性質は既存どおりです。

- `tenantId` を必須条件としてqueryする。
- status、from、toの条件を既存どおり適用する。
- 既存のORDER BYを変えない。
- `limit <= 10_000` を既存どおり適用する。
- `format` を引数やSQLへ追加しない。
- `OrderRow` に内部項目が含まれること自体は変えない。

CSVとNDJSONでrepositoryを別々に呼び出す実装や、NDJSON専用queryを追加する実装は避けます。

## テスト

### handlerテスト

repositoryとauditを依存単位でmockし、rowはfactoryから作ります。

```ts
describe("exportOrders", () => {
  afterEach(() => {
    jest.resetAllMocks();
  });

  it.each([
    [undefined, "csv"],
    ["csv", "csv"],
    ["ndjson", "ndjson"],
  ] as const)(
    "format=%sでは監査に実際のformat=%sを1回記録する",
    async (requestedFormat, expectedFormat) => {
      streamOrdersMock.mockReturnValue(
        asyncIterable([orderRowFactory.build()]),
      );

      const response = await exportOrders(
        createRequest({
          query: { format: requestedFormat },
        }),
        createSession({ tenantId: "tenant-a" }),
      );

      await consumeResponse(response);

      expect(audit.record).toHaveBeenCalledTimes(1);
      expect(audit.record).toHaveBeenCalledWith(
        "orders.exported",
        {
          tenantId: "tenant-a",
          format: expectedFormat,
        },
      );
    },
  );
});
```

最低限、次を検証します。

1. `format` 省略時

- CSVになる。
- Content-Typeが既存どおり。
- 既存のgolden fixtureとレスポンスbodyをbyte単位で比較する。
- auditのformatが`csv`。

```ts
expect(Buffer.from(await response.arrayBuffer())).toEqual(
  existingCsvFixture,
);
```

文字列snapshotだけでなく`Buffer`比較にすることで、BOM、改行コード、末尾改行、引用符の差も検出できます。

2. `format=ndjson`

- Content-Typeが正確に一致する。
- 1行につき1object。
- 最終objectの後に`\n`がある。
- 入力順序が維持される。
- `fraudScore`と`internalNote`が含まれない。

```ts
expect(response.headers.get("content-type")).toBe(
  "application/x-ndjson; charset=utf-8",
);

expect(await response.text()).toBe(
  [
    '{"order_id":"order-1","status":"paid","total":"1000","placed_at":"2026-09-01T10:00:00Z"}',
    '{"order_id":"order-2","status":"shipped","total":"2000","placed_at":"2026-09-01T11:00:00Z"}',
    "",
  ].join("\n"),
);
```

3. 不正なformat

```ts
it("formatがcsvまたはndjson以外ならdataを読まず400を返す", async () => {
  const response = await callHandler({
    query: { format: "json" },
  });

  expect(response.status).toBe(400);
  expect(streamOrdersMock).not.toHaveBeenCalled();
  expect(audit.record).not.toHaveBeenCalled();
});
```

4. 認可失敗

- 既存の403または例外になる。
- `streamOrders`、serializer、auditのいずれも呼ばれない。

5. tenant分離

requestに別tenantを混ぜても、sessionのtenantだけが渡ることを検証します。

```ts
expect(streamOrdersMock).toHaveBeenCalledWith(
  expect.objectContaining({
    tenantId: "tenant-from-session",
  }),
);
```

6. filterと上限

`csv`と`ndjson`をparameterized testにして、両方で完全に同じfilterが渡ることを検証します。

```ts
it.each(["csv", "ndjson"] as const)(
  "%sでもstatus、期間、10,000件上限を同じfilterでrepositoryへ渡す",
  async (format) => {
    // limit=50000で呼び出す

    expect(streamOrdersMock).toHaveBeenCalledTimes(1);
    expect(streamOrdersMock).toHaveBeenCalledWith({
      tenantId: "tenant-a",
      status: "paid",
      from: "2026-08-01",
      to: "2026-08-31",
      limit: 10_000,
    });
  },
);
```

### mapperテスト

```ts
it("OrderRowから公開可能な4項目だけを生成する", () => {
  const row = orderRowFactory.build({
    fraudScore: 99,
    internalNote: "do not export",
  });

  expect(toPublicOrderExportRow(row)).toStrictEqual({
    order_id: row.orderId,
    status: row.status,
    total: row.total,
    placed_at: row.placedAt,
  });
});
```

### NDJSON serializerテスト

- 1件を正確なUTF-8 bytesへ変換する。
- 複数件の順序を維持する。
- 日本語などの非ASCII文字をUTF-8で出力する。
- 非空入力の末尾が`0x0a`である。
- 0件なら空body。
- upstream iteratorの例外をresponse streamへ伝播する。
- client cancel時にiteratorの`return()`を呼ぶ。

### repositoryテスト

形式別のrepositoryテストは追加しません。形式がrepositoryへ到達しないことが設計上の保証だからです。既存のrepository contract testで次を維持します。

- tenant条件が必須。
- status/from/toが適用される。
- 件数上限が適用される。
- 既存の並び順が安定している。

最後に、CSVのgolden byteテスト、handlerテスト、serializerテスト、型チェック、lintを実行すれば、形式差だけが追加されたことを確認できます。
