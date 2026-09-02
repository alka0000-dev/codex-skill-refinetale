実装の中心は、`streamOrders(filter)` と `toPublicOrderExportRow` を共通経路として維持し、その後だけCSV/NDJSONに分岐させることです。これにより、認可・テナント分離・抽出条件・件数上限・公開項目・順序・監査回数を変えずに済みます。

## 処理の流れ

```text
Request
  → 認可
  → tenantIdを含むfilter確定
  → format検証
  → streamOrders(filter)（唯一のrepository query）
  → toPublicOrderExportRow
  → CSV または NDJSON serializer
  → 監査を1件記録
  → Response
```

重要なのは以下の順序です。

1. `requirePermission`
2. `session.tenantId`を入れたfilterの確定
3. `format`の検証
4. `streamOrders(filter)`の呼び出し
5. 公開可能なrowへの変換
6. serializerの選択

不正な`format`の場合は3で400になり、`streamOrders`は呼ばれません。

## handler

既存のCSV serializer呼び出しは一切変えません。CSVのbyte-for-byte互換性を守るため、新しい共通serializerなどには載せ替えない方が安全です。

```ts
import { z } from "zod";

const ExportOrderFormatSchema = z
  .enum(["csv", "ndjson"])
  .default("csv");

type ExportOrderFormat = z.infer<typeof ExportOrderFormatSchema>;

const csvOptions = {
  headers: ["order_id", "status", "total", "placed_at"],
  contentType: "text/csv; charset=utf-8",
} as const;

export async function exportOrders(req: Request, session: Session) {
  requirePermission(session, "orders:export");

  // tenantIdと抽出条件をserializer選択より前に確定する。
  const filter = ExportOrderFilterSchema.parse({
    tenantId: session.tenantId,
    status: req.query.status,
    from: req.query.from,
    to: req.query.to,
    limit: Math.min(Number(req.query.limit ?? 10_000), 10_000),
  });

  // parse失敗時は、この後のrepository呼び出しに到達しない。
  const format: ExportOrderFormat = ExportOrderFormatSchema.parse(
    req.query.format,
  );

  // 両形式が共有する唯一の永続化層呼び出し。
  const rows = streamOrders(filter);

  // 内部項目はserializerへ到達させない。
  const publicRows = mapStream(rows, toPublicOrderExportRow);

  const response =
    format === "csv"
      ? streamCsv(publicRows, csvOptions)
      : streamNdjson(publicRows, {
          contentType: "application/x-ndjson; charset=utf-8",
        });

  audit.record("orders.exported", {
    tenantId: session.tenantId,
    format,
  });

  return response;
}
```

既存ルーティングや外部参照の都合で関数名を維持する必要があれば、`exportOrdersCsv`の名前はそのままでも構いません。ただし、複数形式を扱う実態に合わせて`exportOrders`へ変更する方が明確です。

### formatの400変換

既存のZodエラーハンドリングが`ZodError`を400へ変換している前提です。そうでなければ、既存のrequest validation用エラーへ変換します。

```ts
function parseExportOrderFormat(value: unknown): ExportOrderFormat {
  const result = ExportOrderFormatSchema.safeParse(value);

  if (!result.success) {
    throw new BadRequestError(
      'query "format" must be either "csv" or "ndjson"',
    );
  }

  return result.data;
}
```

その場合、handlerではこの関数をfilter確定後、`streamOrders`より前に呼びます。

## 永続化層

repositoryのシグネチャとqueryは変更しません。

```ts
function streamOrders(
  filter: ExportOrderFilter,
): AsyncIterable<OrderRow>;
```

SQL側でも引き続き、filterの`tenantId`と`limit`をそのまま使用します。

```sql
SELECT
  tenant_id,
  order_id,
  status,
  total,
  placed_at,
  fraud_score,
  internal_note
FROM orders
WHERE tenant_id = :tenantId
  -- 既存のstatus/from/to条件
ORDER BY ...
LIMIT :limit
```

NDJSON用のrepositoryメソッドやqueryを追加しないことが重要です。形式ごとにqueryを分けると、抽出条件や順序が将来ずれる余地ができます。

## 公開rowへの変換

既存関数を両形式で共有します。

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

`fraudScore`と`internalNote`をserializer側で除外する設計にはしません。serializerへ渡す前に`PublicOrderExportRow`へ変換することで、両形式の漏えい防止境界を共通化します。

## NDJSON serializer

既存のstream abstractionに合わせる必要がありますが、Web `ReadableStream`なら次の形にできます。

```ts
type StreamNdjsonOptions = {
  contentType: "application/x-ndjson; charset=utf-8";
};

export function streamNdjson<T>(
  rows: AsyncIterable<T>,
  options: StreamNdjsonOptions,
): Response {
  const encoder = new TextEncoder();

  const body = new ReadableStream<Uint8Array>({
    async start(controller) {
      try {
        for await (const row of rows) {
          controller.enqueue(
            encoder.encode(`${JSON.stringify(row)}\n`),
          );
        }

        controller.close();
      } catch (error) {
        controller.error(error);
      }
    },
  });

  return new Response(body, {
    headers: {
      "Content-Type": options.contentType,
    },
  });
}
```

各rowについて必ず`JSON.stringify(row) + "\n"`を出すため、

- 1行1 JSON object
- UTF-8
- 最終rowにもnewline
- 0件なら空body

となります。

## テスト構成

最低限、次の3層に分けると仕様の所在が明確です。

### 1. handlerテスト

repository、serializer、auditを依存単位でmockします。

```ts
describe("exportOrders", () => {
  afterEach(() => {
    jest.resetAllMocks();
  });

  it("format省略時は既存CSV serializerへ公開rowを渡す", async () => {
    const order = createOrderRowFactory().build({
      tenantId: "tenant-a",
      fraudScore: 91,
      internalNote: "do not export",
    });

    mockedStreamOrders.mockReturnValue(asAsyncIterable([order]));
    mockedStreamCsv.mockReturnValue(csvResponse);

    const response = await exportOrders(
      createRequest({ query: {} }),
      createSession({
        tenantId: "tenant-a",
        permissions: ["orders:export"],
      }),
    );

    expect(response).toBe(csvResponse);
    expect(mockedStreamOrders).toHaveBeenCalledTimes(1);
    expect(mockedStreamOrders).toHaveBeenCalledWith(
      expect.objectContaining({
        tenantId: "tenant-a",
        limit: 10_000,
      }),
    );

    const publicRows = mockedStreamCsv.mock.calls[0][0];

    await expect(collect(publicRows)).resolves.toEqual([
      {
        order_id: order.orderId,
        status: order.status,
        total: order.total,
        placed_at: order.placedAt,
      },
    ]);

    expect(mockedStreamCsv).toHaveBeenCalledWith(
      expect.anything(),
      {
        headers: ["order_id", "status", "total", "placed_at"],
        contentType: "text/csv; charset=utf-8",
      },
    );

    expect(mockedStreamNdjson).not.toHaveBeenCalled();
    expect(mockedAuditRecord).toHaveBeenCalledTimes(1);
    expect(mockedAuditRecord).toHaveBeenCalledWith(
      "orders.exported",
      {
        tenantId: "tenant-a",
        format: "csv",
      },
    );
  });

  it("format=ndjsonは同じrepository結果を公開rowへ変換してNDJSON serializerへ渡す", async () => {
    const orders = createOrderRowFactory().buildList(2, {
      tenantId: "tenant-a",
    });

    mockedStreamOrders.mockReturnValue(asAsyncIterable(orders));
    mockedStreamNdjson.mockReturnValue(ndjsonResponse);

    const response = await exportOrders(
      createRequest({
        query: {
          format: "ndjson",
          status: "paid",
          limit: "50000",
        },
      }),
      createSession({
        tenantId: "tenant-a",
        permissions: ["orders:export"],
      }),
    );

    expect(response).toBe(ndjsonResponse);
    expect(mockedStreamOrders).toHaveBeenCalledTimes(1);
    expect(mockedStreamOrders).toHaveBeenCalledWith(
      expect.objectContaining({
        tenantId: "tenant-a",
        status: "paid",
        limit: 10_000,
      }),
    );

    expect(mockedStreamCsv).not.toHaveBeenCalled();
    expect(mockedStreamNdjson).toHaveBeenCalledTimes(1);
    expect(mockedAuditRecord).toHaveBeenCalledTimes(1);
    expect(mockedAuditRecord).toHaveBeenCalledWith(
      "orders.exported",
      {
        tenantId: "tenant-a",
        format: "ndjson",
      },
    );
  });

  it("不正なformatは400を返しrepository、serializer、監査を呼ばない", async () => {
    const response = await invokeHandler(
      createRequest({ query: { format: "xml" } }),
      createSession({
        tenantId: "tenant-a",
        permissions: ["orders:export"],
      }),
    );

    expect(response.status).toBe(400);
    expect(mockedStreamOrders).not.toHaveBeenCalled();
    expect(mockedStreamCsv).not.toHaveBeenCalled();
    expect(mockedStreamNdjson).not.toHaveBeenCalled();
    expect(mockedAuditRecord).not.toHaveBeenCalled();
  });

  it("権限がなければformat検証とrepositoryアクセスより前に拒否する", async () => {
    const response = await invokeHandler(
      createRequest({ query: { format: "ndjson" } }),
      createSession({
        tenantId: "tenant-a",
        permissions: [],
      }),
    );

    expect(response.status).toBe(403);
    expect(mockedStreamOrders).not.toHaveBeenCalled();
    expect(mockedStreamCsv).not.toHaveBeenCalled();
    expect(mockedStreamNdjson).not.toHaveBeenCalled();
    expect(mockedAuditRecord).not.toHaveBeenCalled();
  });
});
```

さらにhandler層で次をテストします。

- `format=csv`と省略時が同じCSV serializer/optionsを使う
- `limit=10001`、極端に大きい値でもrepositoryへ`10_000`を渡す
- `status/from/to`がCSVとNDJSONで同じfilterになる
- `session.tenantId`以外のtenant IDをqueryから指定できない
- 両形式とも監査がちょうど1件
- serializerへ渡るrowに`fraudScore`と`internalNote`が存在しない
- repositoryが返した順序のままserializerへ渡る

### 2. NDJSON serializerテスト

```ts
describe("streamNdjson", () => {
  it("各公開rowをUTF-8のJSON object 1行として出力し末尾にnewlineを付ける", async () => {
    const response = streamNdjson(
      asAsyncIterable([
        {
          order_id: "order-1",
          status: "paid",
          total: "1200",
          placed_at: "2026-09-01T10:00:00Z",
        },
        {
          order_id: "注文-2",
          status: "shipped",
          total: "3400",
          placed_at: "2026-09-01T11:00:00Z",
        },
      ]),
      {
        contentType: "application/x-ndjson; charset=utf-8",
      },
    );

    expect(response.headers.get("Content-Type")).toBe(
      "application/x-ndjson; charset=utf-8",
    );

    await expect(response.text()).resolves.toBe(
      [
        '{"order_id":"order-1","status":"paid","total":"1200","placed_at":"2026-09-01T10:00:00Z"}',
        '{"order_id":"注文-2","status":"shipped","total":"3400","placed_at":"2026-09-01T11:00:00Z"}',
        "",
      ].join("\n"),
    );
  });

  it("0件の場合は空bodyを返す", async () => {
    const response = streamNdjson(
      asAsyncIterable([]),
      {
        contentType: "application/x-ndjson; charset=utf-8",
      },
    );

    await expect(response.text()).resolves.toBe("");
  });

  it("入力rowの順序を維持する", async () => {
    const response = streamNdjson(
      asAsyncIterable([
        createPublicOrderExportRow({ order_id: "order-2" }),
        createPublicOrderExportRow({ order_id: "order-1" }),
      ]),
      {
        contentType: "application/x-ndjson; charset=utf-8",
      },
    );

    const lines = (await response.text()).trimEnd().split("\n");
    expect(lines.map((line) => JSON.parse(line).order_id)).toEqual([
      "order-2",
      "order-1",
    ]);
  });
});
```

### 3. CSV互換性と形式間の同一性テスト

CSVは「意味が同じ」ではなく、既存の期待バイト列との完全一致を検証します。

```ts
it("format省略時のCSVは変更前の出力とbyte-for-byteで一致する", async () => {
  const response = await invokeExport({
    query: {},
    rows: csvRegressionRows,
  });

  const actual = Buffer.from(await response.arrayBuffer());

  expect(actual.equals(existingCsvGoldenBytes)).toBe(true);
});
```

CSVとNDJSONのrow集合・順序・公開項目の同一性も比較します。

```ts
it("CSVとNDJSONは同じ公開rowを同じ順序で出力する", async () => {
  const rows = createOrderRowFactory().buildList(3, {
    tenantId: "tenant-a",
  });

  const csvResponse = await invokeExport({
    query: { format: "csv" },
    rows,
  });

  const ndjsonResponse = await invokeExport({
    query: { format: "ndjson" },
    rows,
  });

  const csvRows = parseCsv(await csvResponse.text());
  const ndjsonRows = (await ndjsonResponse.text())
    .trimEnd()
    .split("\n")
    .map((line) => JSON.parse(line));

  expect(ndjsonRows).toEqual(csvRows);

  for (const row of [...csvRows, ...ndjsonRows]) {
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

この構成なら変更点は、format検証、NDJSON serializer、handler末尾の形式分岐だけです。特にCSV経路の`streamCsv(publicRows, options)`を既存のまま残すことと、形式間同一性テストに加えてCSVのバイト列回帰テストを置くことが、互換性維持の要になります。
