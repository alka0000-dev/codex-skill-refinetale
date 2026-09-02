実装の軸は、公開用rowを作るところまでを完全に共通化し、最後のserializerだけを`format`で切り替えることです。

なお、`referytale`の対応表は作業ディレクトリが読み取り専用のため保存できませんでした。以下では、ユーザー提示の既存語だけを中心に設計しています。

## 処理順序

```text
Request
  → 認可
  → format検証
  → session.tenantIdを含むfilter確定
  → streamOrders(filter)
  → toPublicOrderExportRow
  → 監査を1件記録
  → CSVまたはNDJSONへserialize
```

この順序なら、不正な`format`では`streamOrders`へ到達しません。また、serializerを選ぶ時点では、認可とtenant scopeが確定済みです。

## Handler

CSV専用ではなくなるため、handlerを`exportOrders`へ変更する案です。既存のexport名が外部参照されているなら、routeだけ新しいhandlerへ差し替えます。

```ts
import { z } from "zod";

const ExportOrderFormatSchema = z.enum(["csv", "ndjson"]).default("csv");

type ExportOrderFormat = z.infer<typeof ExportOrderFormatSchema>;

export async function exportOrders(req: Request, session: Session) {
  // serializerの選択やrepositoryアクセスより先に認可する。
  requirePermission(session, "orders:export");

  // 不正値はここで400になり、streamOrdersは呼ばれない。
  const format = ExportOrderFormatSchema.parse(req.query.format);

  // tenant scope、抽出条件、上限は形式に依存させない。
  const filter = ExportOrderFilterSchema.parse({
    tenantId: session.tenantId,
    status: req.query.status,
    from: req.query.from,
    to: req.query.to,
    limit: Math.min(Number(req.query.limit ?? 10_000), 10_000),
  });

  // repository queryは既存のものだけを使う。
  const rows = streamOrders(filter);

  // 公開可能な項目への変換も形式間で共通にする。
  const publicRows = mapStream(rows, toPublicOrderExportRow);

  // デフォルト値を解決した実際のformatを1回だけ記録する。
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
  switch (format) {
    case "csv":
      // 既存呼び出しを変更しない。
      return streamCsv(rows, {
        headers: ["order_id", "status", "total", "placed_at"],
        contentType: "text/csv; charset=utf-8",
      });

    case "ndjson":
      return streamNdjson(rows, {
        contentType: "application/x-ndjson; charset=utf-8",
      });
  }
}
```

`format`の検証エラーを既存のZodエラーハンドリングがHTTP 400へ変換する前提です。該当する共通処理がない場合は、handler内でZodエラーを400へ変換します。

## 公開項目の変換

型注釈だけでは内部項目の除外を保証できないため、必ず新しいobjectを明示的に作ります。

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

これにより、`fraudScore`と`internalNote`はCSVにもNDJSONにも渡りません。

## NDJSON serializer

1回の`pull`につき1 rowを`JSON.stringify`し、必ず`\n`を付けます。

```ts
type StreamNdjsonOptions = {
  contentType: "application/x-ndjson; charset=utf-8";
};

export function streamNdjson<T extends object>(
  rows: AsyncIterable<T>,
  options: StreamNdjsonOptions,
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

    async cancel() {
      await iterator.return?.();
    },
  });

  return new Response(body, {
    headers: {
      "Content-Type": options.contentType,
    },
  });
}
```

既存のHTTPレスポンス抽象がある場合は、`Response`生成部分だけそれに合わせます。row単位でencodeするため、全10,000件をメモリへ貯めません。

## 永続化層

新しいrepositoryメソッドやNDJSON専用queryは作りません。

```ts
const rows = streamOrders(filter);
```

両形式が必ず同じ次の条件を共有します。

- `tenantId: session.tenantId`
- `status`
- `from`
- `to`
- 最大10,000件
- `streamOrders`が保証する順序

順序を確実に再現する必要があるなら、それは既存の`streamOrders`内で決定的な`ORDER BY`として保証されているべきです。handlerやserializer側で並べ替えてはいけません。

## テスト

### Handler test

依存をmockし、response bodyを最後まで読み取って検証します。

```ts
describe("exportOrders", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("format省略時は既存CSVをbyte-for-byteで返す", async () => {
    streamOrdersMock.mockReturnValue(
      asyncRows([
        orderRow({
          orderId: "ord_1",
          status: "paid",
          total: "1200",
          placedAt: "2026-09-01T10:00:00Z",
          fraudScore: 98,
          internalNote: "never expose",
        }),
      ]),
    );

    const response = await exportOrders(
      request({ query: {} }),
      session({ tenantId: "tenant-a" }),
    );

    expect(response.headers.get("content-type"))
      .toBe("text/csv; charset=utf-8");

    expect(await response.text()).toBe(
      [
        "order_id,status,total,placed_at",
        "ord_1,paid,1200,2026-09-01T10:00:00Z",
        "",
      ].join("\r\n"), // 実際には既存CSVのgolden bytesを使用する
    );

    expect(audit.record).toHaveBeenCalledTimes(1);
    expect(audit.record).toHaveBeenCalledWith("orders.exported", {
      tenantId: "tenant-a",
      format: "csv",
    });
  });

  it("NDJSONをUTF-8、1 row 1 object、末尾newlineで返す", async () => {
    streamOrdersMock.mockReturnValue(
      asyncRows([
        orderRow({
          orderId: "ord_1",
          status: "paid",
          total: "1200",
          placedAt: "2026-09-01T10:00:00Z",
          fraudScore: 98,
          internalNote: "never expose",
        }),
        orderRow({
          orderId: "ord_2",
          status: "cancelled",
          total: "500",
          placedAt: "2026-09-01T11:00:00Z",
        }),
      ]),
    );

    const response = await exportOrders(
      request({ query: { format: "ndjson" } }),
      session({ tenantId: "tenant-a" }),
    );

    expect(response.headers.get("content-type")).toBe(
      "application/x-ndjson; charset=utf-8",
    );

    expect(await response.text()).toBe(
      [
        '{"order_id":"ord_1","status":"paid","total":"1200","placed_at":"2026-09-01T10:00:00Z"}',
        '{"order_id":"ord_2","status":"cancelled","total":"500","placed_at":"2026-09-01T11:00:00Z"}',
        "",
      ].join("\n"),
    );

    expect(audit.record).toHaveBeenCalledTimes(1);
    expect(audit.record).toHaveBeenCalledWith("orders.exported", {
      tenantId: "tenant-a",
      format: "ndjson",
    });
  });

  it("不正なformatは400になり、dataを読まない", async () => {
    const response = await invokeHttpHandler(
      request({ query: { format: "xml" } }),
      session({ tenantId: "tenant-a" }),
    );

    expect(response.status).toBe(400);
    expect(streamOrdersMock).not.toHaveBeenCalled();
    expect(audit.record).not.toHaveBeenCalled();
  });

  it("認可失敗時はrepository、serializer、監査へ進まない", async () => {
    requirePermissionMock.mockImplementation(() => {
      throw new ForbiddenError();
    });

    await expect(
      exportOrders(
        request({ query: { format: "ndjson" } }),
        session({ tenantId: "tenant-a" }),
      ),
    ).rejects.toThrow(ForbiddenError);

    expect(streamOrdersMock).not.toHaveBeenCalled();
    expect(audit.record).not.toHaveBeenCalled();
  });

  it.each(["csv", "ndjson"] as const)(
    "%sでも同じtenant scope、filter、上限を使う",
    async (format) => {
      streamOrdersMock.mockReturnValue(asyncRows([]));

      const response = await exportOrders(
        request({
          query: {
            format,
            status: "paid",
            from: "2026-08-01",
            to: "2026-08-31",
            limit: "50000",
          },
        }),
        session({ tenantId: "tenant-a" }),
      );

      await response.text();

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
});
```

### 形式間の同一性テスト

CSVとNDJSONをそれぞれparseし、同じ公開row列になることを比較します。

```ts
it("CSVとNDJSONは同じ公開rowを同じ順序で返す", async () => {
  const sourceRows = [
    orderRow({ orderId: "ord_2", fraudScore: 99, internalNote: "secret" }),
    orderRow({ orderId: "ord_1", fraudScore: 10, internalNote: null }),
  ];

  const csvResponse = await runExport("csv", sourceRows);
  const ndjsonResponse = await runExport("ndjson", sourceRows);

  const csvRows = parseCsv(await csvResponse.text());
  const ndjsonRows = (await ndjsonResponse.text())
    .trimEnd()
    .split("\n")
    .map((line) => JSON.parse(line));

  expect(ndjsonRows).toEqual(csvRows);
  expect(ndjsonRows.map((row) => row.order_id)).toEqual([
    "ord_2",
    "ord_1",
  ]);

  for (const row of ndjsonRows) {
    expect(Object.keys(row)).toEqual([
      "order_id",
      "status",
      "total",
      "placed_at",
    ]);
    expect(row).not.toHaveProperty("fraudScore");
    expect(row).not.toHaveProperty("internalNote");
  }
});
```

CSVのbyte-for-byte保証には、新たに組み立てた期待文字列よりも、変更前handlerの実出力を保存したgolden fixtureを使うのが安全です。CSV serializer自体とその引数を変更しないことに加え、代表値、カンマ・引用符、改行を含む値、空集合、日本語をfixtureへ含めて回帰検証します。
