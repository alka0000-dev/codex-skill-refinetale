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
