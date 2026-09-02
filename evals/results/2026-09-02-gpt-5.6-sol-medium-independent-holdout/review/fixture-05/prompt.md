You are grading six anonymized answers to an independent holdout evaluation. Return only the requested structured result.

# 05: Add NDJSON order export

## Purpose

認可・tenant分離・公開rowの共通経路を維持し、serializer差分だけを追加できるか確認する。

## Input

既存のCSV注文エクスポートにNDJSON形式を追加します。認可、テナント分離、抽出条件、公開可能な項目、件数上限、監査を変えず、形式による差だけを追加する実装案を示してください。handlerから永続化層、serializerまでの流れとテストを具体的にしてください。

現在のhandler:

```ts
export async function exportOrdersCsv(req: Request, session: Session) {
  requirePermission(session, "orders:export");
  const filter = ExportOrderFilterSchema.parse({
    tenantId: session.tenantId,
    status: req.query.status,
    from: req.query.from,
    to: req.query.to,
    limit: Math.min(Number(req.query.limit ?? 10_000), 10_000),
  });

  const rows = streamOrders(filter);
  const publicRows = mapStream(rows, toPublicOrderExportRow);
  audit.record("orders.exported", { tenantId: session.tenantId, format: "csv" });

  return streamCsv(publicRows, {
    headers: ["order_id", "status", "total", "placed_at"],
    contentType: "text/csv; charset=utf-8",
  });
}
```

永続化rowには内部項目も含まれる:

```ts
type OrderRow = {
  tenantId: string;
  orderId: string;
  status: OrderStatus;
  total: string;
  placedAt: string;
  fraudScore: number;
  internalNote: string | null;
};

type PublicOrderExportRow = {
  order_id: string;
  status: OrderStatus;
  total: string;
  placed_at: string;
};
```

新要件:

- query`format=csv|ndjson`で選択し、省略時はCSV。不正値はdataを読まず400。
- NDJSONは1行1 JSON object、UTF-8、末尾newlineあり、`application/x-ndjson; charset=utf-8`。
- 両形式のrow集合、順序、filter、10,000件上限、公開項目は同一。
- 認可とtenant scopeはserializer選択より前に確定し、repository queryは`streamOrders(filter)`だけを使う。
- `fraudScore`と`internalNote`はどちらにも出さない。
- 監査eventは1 requestにつき1件で、実際のformatを記録する。
- CSVの既存出力はbyte-for-byteで変えない。

## Pass conditions

- **S1 Common handler:** format検証後、認可、tenant filter、query、public row変換、上限、auditを両形式で一度だけ通し、NDJSON用handler/query/repositoryを複製しない。
- **S2 Tenant and public fields:** serializerへraw `OrderRow`を渡さず、両形式が同じ`PublicOrderExportRow` streamだけを受け取る構造にする。
- **S3 Format variation:** CSVを変えず、NDJSON framing、UTF-8、末尾newline、content typeを満たす。不正formatはquery前に400。
- **S4 Single types and state:** 既存filter、public row、queryを共用し、形式別DTO、二重取得、二重audit、全件memory化を導入しない。
- **S5 Verification:** 同一row/order、tenant分離、権限拒否、内部項目非出力、上限、不正formatでquery 0、audit 1、CSV byte回帰、NDJSON framingを確認する。

## Critical failure conditions

- NDJSONをtenant条件なしでqueryする、または別repositoryがtenant scopeを再実装する。
- NDJSON serializerへraw `OrderRow`を渡して内部項目が出力され得る。
- 不正formatや権限拒否の後でもdata queryを開始する。

## Scoring

S1〜S5を各0〜2点で採点する。2点は共通data pathと形式固有処理を追跡でき、security、streaming、audit、回帰testまで実装可能、1点は一部不十分、0点は別経路・契約変更・情報露出・tenant欠落・要件未達がある。8〜10点かつ全基準1点以上をPass、6〜7点または0点を含む8点以上をBorderline、5点以下をFailとする。critical failureを優先し、完成実装や理想的class構成は要求しない。


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

## Candidate B

実装の中心は「形式をrepositoryへ持ち込まず、公開用rowへ変換した後のserializerだけを切り替える」ことです。

```text
Request
  → 認可
  → format検証
  → tenantIdを含むfilter確定
  → serializer選択
  → streamOrders(filter)
  → toPublicOrderExportRow
  → audit（1回）
  → CSV または NDJSON
```

## handler案

CSV側は既存の`streamCsv`呼び出しをそのまま残します。共通serializerへの無理な統合は、CSVのbyte-for-byte互換性を崩すリスクがあるため避けます。

```ts
import { z } from "zod";

const ExportOrderFormatSchema = z.enum(["csv", "ndjson"]).default("csv");

type ExportOrderFormat = z.infer<typeof ExportOrderFormatSchema>;

export async function exportOrders(req: Request, session: Session) {
  // 不正formatの場合も、repositoryやserializerへ進む前に認可を実施する。
  requirePermission(session, "orders:export");

  // undefinedだけCSVへ既定化する。空文字や配列などは400にする。
  const format = ExportOrderFormatSchema.parse(req.query.format);

  // tenant scopeと既存の抽出条件を、serializer選択より前に確定する。
  const filter = ExportOrderFilterSchema.parse({
    tenantId: session.tenantId,
    status: req.query.status,
    from: req.query.from,
    to: req.query.to,
    limit: Math.min(Number(req.query.limit ?? 10_000), 10_000),
  });

  const serialize = selectOrderExportSerializer(format);

  // repositoryにはformatを渡さない。
  const rows = streamOrders(filter);
  const publicRows = mapStream(rows, toPublicOrderExportRow);

  // 既存と同じタイミングで、1 requestにつき1回だけ記録する。
  audit.record("orders.exported", {
    tenantId: session.tenantId,
    format,
  });

  return serialize(publicRows);
}

function selectOrderExportSerializer(format: ExportOrderFormat) {
  if (format === "ndjson") {
    return streamOrdersNdjson;
  }

  // 既存CSVの設定と実装を変えない。
  return (rows: AsyncIterable<PublicOrderExportRow>) =>
    streamCsv(rows, {
      headers: ["order_id", "status", "total", "placed_at"],
      contentType: "text/csv; charset=utf-8",
    });
}
```

Zodエラーを既存のHTTPエラーミドルウェアが400へ変換している前提です。そうでなければ、`ExportOrderFormatSchema.parse`のエラーだけを既存の400エラー型へ変換します。

重要なのは、`format`の検証を`streamOrders(filter)`より前に行うことです。不正値では`streamOrders`、監査、serializerのいずれも呼ばれません。

## 公開項目への変換

この関数を両形式で共有し、serializerには`OrderRow`を渡さない構造にします。

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

denylist方式で`fraudScore`などを削除するのではなく、許可された4項目を新しいobjectへ明示的にコピーします。これにより、将来`OrderRow`へ内部項目が追加されても自動的には公開されません。

## NDJSON serializer案

```ts
import { Readable } from "node:stream";

export function streamOrdersNdjson(
  rows: AsyncIterable<PublicOrderExportRow>,
) {
  return streamResponse(Readable.from(encodeNdjson(rows)), {
    contentType: "application/x-ndjson; charset=utf-8",
  });
}

async function* encodeNdjson(
  rows: AsyncIterable<PublicOrderExportRow>,
): AsyncGenerator<Buffer> {
  for await (const row of rows) {
    yield Buffer.from(`${JSON.stringify(row)}\n`, "utf8");
  }
}
```

`streamResponse`は、プロジェクトで既に使っているストリーミングHTTPレスポンス生成処理に読み替えます。

この実装では各objectを必ず`\n`付きで出すため、1件以上なら最終行にもnewlineがあります。0件の場合はblank lineを作らず0 byteとするのが自然です。空行はJSON objectではないためです。

## 永続化層

`streamOrders`のシグネチャとqueryには形式を追加しません。

```ts
function streamOrders(
  filter: ExportOrderFilter,
): AsyncIterable<OrderRow>;
```

守るべき点は次のとおりです。

- `filter.tenantId`を必須条件としてqueryする
- status、from、toの意味を変えない
- 既存のORDER BYを変えない
- limitは既存どおり最大10,000件
- CSV/NDJSONごとの分岐を置かない
- serializerからrepositoryを直接呼ばない

内部項目を含む`OrderRow`をrepositoryが返すこと自体は変更不要です。公開境界は`toPublicOrderExportRow`に固定します。

## handlerテスト

Jestなら最低限、以下を固定します。

```ts
describe("exportOrders", () => {
  test.each([
    [undefined, "csv"],
    ["csv", "csv"],
    ["ndjson", "ndjson"],
  ])("format=%pで実際の形式を監査する", async (queryFormat, expected) => {
    mockStreamOrders([]);

    await exportOrders(request({ format: queryFormat }), session());

    expect(audit.record).toHaveBeenCalledTimes(1);
    expect(audit.record).toHaveBeenCalledWith("orders.exported", {
      tenantId: "tenant-a",
      format: expected,
    });
  });

  test.each(["json", "", "CSV", ["csv", "ndjson"]])(
    "不正format=%pは永続化層を読まず400",
    async (format) => {
      await expect(
        exportOrders(request({ format }), session()),
      ).rejects.toMatchObject({ status: 400 });

      expect(streamOrders).not.toHaveBeenCalled();
      expect(audit.record).not.toHaveBeenCalled();
      expect(streamCsv).not.toHaveBeenCalled();
      expect(streamOrdersNdjson).not.toHaveBeenCalled();
    },
  );

  test("認可失敗時はformat処理や永続化層へ進まない", async () => {
    mockRequirePermissionDenied();

    await expect(
      exportOrders(request({ format: "ndjson" }), session()),
    ).rejects.toMatchObject({ status: 403 });

    expect(streamOrders).not.toHaveBeenCalled();
    expect(audit.record).not.toHaveBeenCalled();
  });

  test.each(["csv", "ndjson"])(
    "%sでもsessionのtenantIdと同一の抽出条件を使う",
    async (format) => {
      mockStreamOrders([]);

      await exportOrders(
        request({
          format,
          tenantId: "attacker-tenant",
          status: "paid",
          from: "2026-01-01",
          to: "2026-01-31",
          limit: "20000",
        }),
        session({ tenantId: "tenant-a" }),
      );

      expect(streamOrders).toHaveBeenCalledTimes(1);
      expect(streamOrders).toHaveBeenCalledWith({
        tenantId: "tenant-a",
        status: "paid",
        from: "2026-01-01",
        to: "2026-01-31",
        limit: 10_000,
      });
    },
  );
});
```

さらに、呼び出し順序を検査します。

```ts
expect(requirePermission.mock.invocationCallOrder[0])
  .toBeLessThan(streamOrders.mock.invocationCallOrder[0]);

expect(streamOrders.mock.invocationCallOrder[0])
  .toBeLessThan(audit.record.mock.invocationCallOrder[0]);
```

serializer選択自体はmockの呼び出しとして観測しにくいため、設計上「filter確定後に`selectOrderExportSerializer`を呼ぶ」順序をhandler内で固定します。

## serializerテスト

NDJSONは文字列比較とJSONとしての再読込を両方行います。

```ts
describe("streamOrdersNdjson", () => {
  test("1行1object、UTF-8、末尾newlineで出力する", async () => {
    const rows = asAsyncIterable([
      {
        order_id: "注文-1",
        status: "paid",
        total: "1200",
        placed_at: "2026-01-02T03:04:05Z",
      },
      {
        order_id: "order-2\nescaped",
        status: "cancelled",
        total: "0",
        placed_at: "2026-01-03T04:05:06Z",
      },
    ]);

    const response = streamOrdersNdjson(rows);
    const body = await readUtf8(response);

    expect(response.contentType).toBe(
      "application/x-ndjson; charset=utf-8",
    );
    expect(body).toBe(
      '{"order_id":"注文-1","status":"paid","total":"1200","placed_at":"2026-01-02T03:04:05Z"}\n' +
      '{"order_id":"order-2\\nescaped","status":"cancelled","total":"0","placed_at":"2026-01-03T04:05:06Z"}\n',
    );

    expect(body.endsWith("\n")).toBe(true);
    expect(body.trimEnd().split("\n").map(JSON.parse)).toEqual([
      {
        order_id: "注文-1",
        status: "paid",
        total: "1200",
        placed_at: "2026-01-02T03:04:05Z",
      },
      {
        order_id: "order-2\nescaped",
        status: "cancelled",
        total: "0",
        placed_at: "2026-01-03T04:05:06Z",
      },
    ]);
  });

  test("内部項目を出力しない", async () => {
    const row: OrderRow = {
      tenantId: "tenant-a",
      orderId: "order-1",
      status: "paid",
      total: "1200",
      placedAt: "2026-01-02T03:04:05Z",
      fraudScore: 99,
      internalNote: "never export",
    };

    const body = await exportBody("ndjson", [row]);

    expect(body).not.toContain("tenantId");
    expect(body).not.toContain("fraudScore");
    expect(body).not.toContain("internalNote");
    expect(body).not.toContain("never export");
  });
});
```

## CSV回帰テスト

既存の代表データをfixture化し、変更前に生成したbyte列と比較します。文字列ではなく`Buffer`で比較するのが重要です。

```ts
test.each([undefined, "csv"])(
  "既存CSVとbyte-for-byteで一致する",
  async (format) => {
    const response = await exportOrders(
      request({ format }),
      session(),
    );

    const actual = await readBuffer(response);

    expect(response.contentType).toBe("text/csv; charset=utf-8");
    expect(actual.equals(existingCsvGoldenBuffer)).toBe(true);
  },
);
```

fixtureには少なくとも以下を含めます。

- header
- UTF-8文字
- comma、double quote、改行を含む値
- null相当の既存表現
- 複数rowによる順序
- CSV既存の改行コード
- 空データ

最後にrepository統合テストで、複数tenantの注文を同時に用意し、`tenant-a`のfilterでは`tenant-a`だけが既存順序かつ最大10,000件で返ることを検証します。同じrepository結果をCSVとNDJSONへ流し、復元した公開row配列が完全一致することまで確認すれば、形式以外の差が入っていないことを担保できます。

## Candidate C

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

## Candidate D

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

## Candidate E

変更点は「入力形式の検証」と「公開rowの最終serialize」だけに限定します。永続化経路や公開項目変換は分岐させません。

## 変更契約

変更する挙動:

- `format=ndjson`を受理する。
- 省略時はCSV。
- その他の値は400で終了し、`streamOrders`を呼ばない。
- NDJSONは各公開rowを`JSON.stringify(row) + "\n"`で出力する。
- 監査の`format`に、検証済みの実形式を記録する。

変更しない挙動:

- `orders:export`認可
- `session.tenantId`によるtenant scope
- status/from/to/limitの検証・抽出条件
- 10,000件上限
- repositoryとその並び順
- `toPublicOrderExportRow`
- CSV serializerへの引数と出力bytes
- 監査の発火位置・回数
- ストリーミング処理

## データフロー

```text
Request
  │
  ├─ requirePermission
  ├─ formatを検証・正規化
  ├─ session.tenantIdを含むfilterを確定
  │
  └─ streamOrders(filter)              ← 唯一のrepository経路
        │ OrderRow
        ▼
     toPublicOrderExportRow            ← 内部項目を落とす唯一の境界
        │ PublicOrderExportRow
        ├─ audit.record（1回）
        ▼
     formatに応じたserializer          ← 唯一の形式分岐
        ├─ CSV: 既存streamCsv
        └─ NDJSON: JSON object + "\n"
```

`OrderRow`をserializerへ直接渡さないことが重要です。特にNDJSONはオブジェクトの全enumerable propertyを出力するため、`PublicOrderExportRow`への変換前に分岐すると内部項目が漏れる危険があります。

## 実装案

### 1. formatの入力境界

```ts
import { z } from "zod";

export const ExportOrderFormatSchema = z
  .enum(["csv", "ndjson"])
  .default("csv");

export type ExportOrderFormat = z.infer<
  typeof ExportOrderFormatSchema
>;
```

`parse(req.query.format)`にすることで、次のようになります。

- `undefined` → `"csv"`
- `"csv"` → `"csv"`
- `"ndjson"` → `"ndjson"`
- 空文字、配列、その他の値 → validation error

既存のZodエラーが400へ変換される前提です。そうでなければ、その既存HTTPエラー変換層で400に対応させます。

### 2. handler

```ts
export async function exportOrders(req: Request, session: Session) {
  requirePermission(session, "orders:export");

  const format = ExportOrderFormatSchema.parse(req.query.format);

  const filter = ExportOrderFilterSchema.parse({
    tenantId: session.tenantId,
    status: req.query.status,
    from: req.query.from,
    to: req.query.to,
    limit: Math.min(Number(req.query.limit ?? 10_000), 10_000),
  });

  const rows = streamOrders(filter);
  const publicRows = mapStream(rows, toPublicOrderExportRow);

  audit.record("orders.exported", {
    tenantId: session.tenantId,
    format,
  });

  return streamOrderExport(publicRows, format);
}
```

既存のexport関数名が外部から参照されているなら、今回の要件だけを理由に互換aliasは追加せず、名前は`exportOrdersCsv`のままでも構いません。ルート内だけの名前なら`exportOrders`へ更新します。

処理順には以下の意味があります。

1. 認可失敗時はformat検証もrepositoryアクセスも行わない。
2. format不正時はfilter生成・repositoryアクセス・監査を行わない。
3. tenant scopeを含むfilter確定後にのみrepositoryを呼ぶ。
4. 監査は既存どおり、ストリームを返す直前に1回だけ記録する。

### 3. serializerの形式分岐

```ts
export function streamOrderExport(
  rows: AsyncIterable<PublicOrderExportRow>,
  format: ExportOrderFormat,
) {
  switch (format) {
    case "csv":
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

CSVケースの`streamCsv`呼び出しは、既存コードからそのまま移動します。headers、順序、content type、serializer自体を変更しません。

汎用ストリームprimitiveが既にある場合、NDJSONは次の最小実装で十分です。

```ts
export function streamNdjson<T extends object>(
  rows: AsyncIterable<T>,
  options: { contentType: string },
) {
  const chunks = mapStream(
    rows,
    (row) => `${JSON.stringify(row)}\n`,
  );

  return streamText(chunks, options);
}
```

実際の`streamText`やstream型はプロジェクト既存のprimitiveに合わせます。Bufferへの全件蓄積はせず、1 rowずつserializeします。

0件の場合は空bodyです。1件以上なら、すべてのJSON objectと最終行がnewlineで終わります。0件時に単独のnewlineを出すと「1行1 JSON object」に反するため出しません。

### 4. 公開項目の正本

既存変換を両形式で共有します。

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

NDJSON専用row型やNDJSON専用mapperは作りません。これにより以下が両形式で同一になります。

- row集合
- row順序
- 値の内部表現
- 公開フィールド
- `fraudScore`と`internalNote`の除外

## 永続化層

repositoryは変更しません。

```ts
streamOrders(filter)
```

だけを呼び、`format`をrepositoryへ渡しません。SQL、SELECT項目、ORDER BY、tenant predicate、期間境界、limitの責務も既存repositoryに残します。

repositoryの生成行数は次の既存契約を維持します。

```text
0 <= rows <= min(抽出条件に一致した件数, filter.limit)
filter.limit <= 10_000
```

`internalNote`のnullは`OrderRow`内だけで発生し、公開rowへ到達しません。

## 最小テスト構成

### mapper単体テスト

内部項目を含む`OrderRow`を変換し、完全一致で検証します。

```ts
expect(toPublicOrderExportRow(orderRow)).toEqual({
  order_id: "order-1",
  status: "paid",
  total: "1200",
  placed_at: "2026-09-01T00:00:00Z",
});

expect(toPublicOrderExportRow(orderRow)).not.toHaveProperty("fraudScore");
expect(toPublicOrderExportRow(orderRow)).not.toHaveProperty("internalNote");
```

### serializer単体テスト

NDJSONについて以下を確認します。

- content typeが`application/x-ndjson; charset=utf-8`
- 1 rowが1 JSON object
- 入力順序が維持される
- 最終objectの後ろにnewlineがある
- UnicodeがUTF-8として復元できる
- 0件は空body
- 内部項目が存在しない

期待body例:

```text
{"order_id":"order-2","status":"paid","total":"1200","placed_at":"2026-09-01T00:00:00Z"}
{"order_id":"order-1","status":"cancelled","total":"500","placed_at":"2026-08-31T00:00:00Z"}
```

テスト上の文字列表現は、末尾を含めて次のようにします。

```ts
expect(body).toBe(
  '{"order_id":"order-2","status":"paid","total":"1200","placed_at":"2026-09-01T00:00:00Z"}\n' +
  '{"order_id":"order-1","status":"cancelled","total":"500","placed_at":"2026-08-31T00:00:00Z"}\n',
);
```

CSVは変更前の実出力をfixtureとして保存し、`Buffer.equals`またはbyte列の完全一致で検証します。改行コード、引用符、BOMの有無をテスト側で作り直さず、変更前に取得したgolden bytesを正本にします。

### handlerテスト

必要なケースは次のとおりです。

| ケース | HTTP/形式 | repository | 監査 |
|---|---|---:|---|
| format省略 | CSV、既存bytesと一致 | 1回 | 1回、`csv` |
| `format=csv` | CSV、既存bytesと一致 | 1回 | 1回、`csv` |
| `format=ndjson` | NDJSON、指定content type | 1回 | 1回、`ndjson` |
| 不正format | 400 | 0回 | 0回 |
| 認可失敗＋不正format | 既存の403 | 0回 | 0回 |
| limitが10,001以上 | filter.limitが10,000 | 1回 | 1回 |
| filter不正 | 400 | 0回 | 0回 |
| `streamOrders`呼び出し時に失敗 | 既存エラー | 1回 | 0回 |

CSVとNDJSONへ同じ順序のrepository fixtureを別リクエストで返し、CSVをdecodeしたrow列とNDJSONをdecodeしたrow列を完全一致させます。これが「同じrow集合・順序・公開項目」の直接的な証拠になります。

ストリームのiteration中に失敗するケースでは、現在の監査位置を維持するため監査はすでに1回記録されています。転送完了後だけ監査する仕様へ変えるには、ストリーミング完了との連携や切断時の扱いが必要になるため、今回には含めません。

## 検証状況

今回は作業領域に実装ファイル、テスト、package設定が存在しないため、コード変更・ビルド・lint・テスト実行はできていません。実装時の完了条件は以下です。

- 変更前後のCSV golden bytesが完全一致
- NDJSONのbody・末尾newline・content typeが一致
- 両形式をdecodeしたrow列が完全一致
- 無効format、認可失敗、filter不正でrepositoryが0回
- 各成功リクエストで監査が正確に1回
- repository呼び出しが両形式とも`streamOrders(filter)`の1経路だけ

この構成なら、形式差はserializer境界の1か所だけに残り、安全境界とデータ経路は増えません。

## Candidate F

実装方針は、`OrderRow → PublicOrderExportRow` までを完全に共通化し、最後の serializer だけを `csv | ndjson` で切り替える形です。repository に形式を渡さず、CSV経路も既存の `streamCsv` 呼び出しをそのまま維持します。

## 変更契約

変更する挙動:

- `format=ndjson` を受理する。
- 省略時と `format=csv` はCSVを返す。
- 不正な `format` は400となり、repositoryを呼ばない。
- 監査イベントの `format` に実際の形式を記録する。

変更しない挙動:

- 認可、テナント境界、抽出条件、並び順、10,000件上限。
- `streamOrders(filter)` というrepository経路。
- `toPublicOrderExportRow` による公開項目境界。
- CSVのheader、content type、エスケープ、改行を含む全byte列。
- 監査イベント名と1リクエスト1件という回数。

共通処理と差分は次の位置に限定します。

```text
Request
  ↓
requirePermission
  ↓
format検証 + session由来tenantIdを含むfilter確定
  ↓
streamOrders(filter)              ← repositoryは変更なし
  ↓
toPublicOrderExportRow            ← 公開項目の唯一の境界
  ↓
audit.record（1回）
  ↓
csv / ndjson serializer           ← ここだけ形式差
```

## Handler

handler名は実態に合わせて `exportOrders` に変更します。ルーティング側の参照変更が不要なら既存名を残しても実行時挙動は同じですが、互換aliasを追加して二重管理にはしません。

```ts
import { z } from "zod";

const ExportOrderFormatSchema = z
  .enum(["csv", "ndjson"])
  .default("csv");

type ExportOrderFormat = z.infer<typeof ExportOrderFormatSchema>;

type OrderExportSerializer = (
  rows: AsyncIterable<PublicOrderExportRow>,
) => Response;

const orderExportSerializers = {
  csv: (rows) =>
    streamCsv(rows, {
      // 既存値を一字も変更しない
      headers: ["order_id", "status", "total", "placed_at"],
      contentType: "text/csv; charset=utf-8",
    }),

  ndjson: (rows) =>
    streamOrderExportNdjson(rows, {
      contentType: "application/x-ndjson; charset=utf-8",
    }),
} satisfies Record<ExportOrderFormat, OrderExportSerializer>;

export async function exportOrders(req: Request, session: Session) {
  // 不正なformatよりも認可を先に評価し、権限境界を維持する。
  requirePermission(session, "orders:export");

  const format = ExportOrderFormatSchema.parse(req.query.format);

  const filter = ExportOrderFilterSchema.parse({
    // queryからtenantIdを受け取らない。
    tenantId: session.tenantId,
    status: req.query.status,
    from: req.query.from,
    to: req.query.to,
    limit: Math.min(Number(req.query.limit ?? 10_000), 10_000),
  });

  // format検証とtenant scope確定後にだけrepositoryへ到達する。
  const rows = streamOrders(filter);
  const publicRows = mapStream(rows, toPublicOrderExportRow);

  audit.record("orders.exported", {
    tenantId: session.tenantId,
    format,
  });

  // 形式分岐は出力境界の一箇所だけ。
  return orderExportSerializers[format](publicRows);
}
```

`zod` の検証エラーを400へ変換する既存HTTPエラーハンドリングをそのまま利用します。直接handlerをテストする場合はZodエラー、HTTPレベルでは400を確認します。

## 公開項目境界

ここは両形式で共有し、serializerに `OrderRow` を渡さないことが重要です。オブジェクトspreadは使いません。

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

これにより `fraudScore` と `internalNote` は、CSV/NDJSONの分岐へ到達する前に消えます。

## NDJSON serializer

既存のストリーミング応答生成ヘルパーを使い、全件bufferしません。以下の `streamUtf8` は、プロジェクトで `streamCsv` が利用している低レベルのresponse helperに読み替えます。

```ts
type StreamNdjsonOptions = {
  contentType: "application/x-ndjson; charset=utf-8";
};

async function* encodeOrderExportNdjson(
  rows: AsyncIterable<PublicOrderExportRow>,
): AsyncIterable<string> {
  for await (const row of rows) {
    yield `${JSON.stringify(row)}\n`;
  }
}

export function streamOrderExportNdjson(
  rows: AsyncIterable<PublicOrderExportRow>,
  options: StreamNdjsonOptions,
): Response {
  return streamUtf8(encodeOrderExportNdjson(rows), {
    contentType: options.contentType,
  });
}
```

各objectを必ず `\n` 付きで出すため、1件以上なら末尾newlineが保証されます。0件時は空byte列とします。空データに単独の改行を出すと「1行1 JSON object」に反するためです。

repository側には変更を入れません。

```ts
streamOrders(filter);
```

`format` 引数、形式別query、形式別DTOは追加しません。既存SQLのtenant条件、status/date条件、ORDER BY、LIMITがそのまま正本です。

## 最小テスト構成

### Handler/APIテスト

1. CSV互換性

```ts
it.each([
  ["省略", undefined],
  ["明示", "csv"],
])("%s時に既存CSVとbyte-for-byteで一致する", async (_, format) => {
  // 変更前に固定したgolden bytesと完全一致
  expect(await response.bytes()).toEqual(existingCsvGoldenBytes);
  expect(response.headers.get("content-type"))
    .toBe("text/csv; charset=utf-8");
});
```

省略時と明示CSVのbodyも相互に完全一致させます。

2. NDJSON固有差分

```ts
expect(await response.text()).toBe(
  '{"order_id":"o-2","status":"paid","total":"200","placed_at":"2026-09-02T02:00:00Z"}\n' +
  '{"order_id":"o-1","status":"pending","total":"100","placed_at":"2026-09-02T01:00:00Z"}\n'
);

expect(response.headers.get("content-type"))
  .toBe("application/x-ndjson; charset=utf-8");
```

このfixtureの永続化rowには `fraudScore` と `internalNote` も持たせ、bodyに含まれないことを確認します。

3. 共通filterと上限

両形式を機械的に全組み合わせテストせず、共通経路で一度確認します。

```ts
expect(streamOrders).toHaveBeenCalledTimes(1);
expect(streamOrders).toHaveBeenCalledWith({
  tenantId: session.tenantId,
  status: "paid",
  from: "...",
  to: "...",
  limit: 10_000,
});
```

queryに別tenant IDを混ぜても `session.tenantId` だけが渡ることを確認します。

4. 不正形式の早期終了

```ts
expect(response.status).toBe(400);
expect(streamOrders).not.toHaveBeenCalled();
expect(audit.record).not.toHaveBeenCalled();
```

`format=json`、配列値などを代表ケースとして確認します。

5. 認可順序

不正formatかつ権限なしのリクエストで認可エラーになることを確認します。

```ts
expect(requirePermission).toHaveBeenCalledBefore(/* format parse相当 */);
expect(streamOrders).not.toHaveBeenCalled();
expect(audit.record).not.toHaveBeenCalled();
```

内部呼び出し順をmockで固定するより、HTTP結果が403でrepository未呼び出しであることを主に検証します。

6. 監査

- CSV成功: `{ tenantId, format: "csv" }` が1回。
- NDJSON成功: `{ tenantId, format: "ndjson" }` が1回。
- 認可失敗・入力不正: 0回。
- ストリームを最後まで消費しても追加記録されない。
- ストリーム途中でrepositoryが失敗しても、既存と同じく開始時に記録済みの1回だけ。

### Serializerテスト

- 2行が入力順のまま出る。
- 各行が単独で `JSON.parse` できる。
- 最終行が `\n` で終わる。
- Unicode値をUTF-8で往復できる。
- 0件は空byte列。
- upstreamのエラーを握りつぶさない。

### 公開mapperテスト

内部項目を持つ `OrderRow` を渡し、結果のkeyを完全一致で検証します。

```ts
expect(toPublicOrderExportRow(orderRow)).toEqual({
  order_id: orderRow.orderId,
  status: orderRow.status,
  total: orderRow.total,
  placed_at: orderRow.placedAt,
});
```

repositoryテストは既存のtenant条件・抽出条件・ORDER BY・LIMITテストをそのまま実行し、形式別テストは追加しません。

今回は作業ディレクトリに実装ファイルがなく、読み取り専用でもあるため、コード変更・テスト実行・`.agent/CONTINUITY.md` 作成は未実施です。実リポジトリでは上記テストに加え、既存のbuild・lint・型チェックを通すことで完了判定できます。
