実装の要点は、`format`を永続化条件に含めず、公開用rowを作った後だけserializerを分岐させることです。CSV側は既存の`streamCsv`呼び出しをそのまま残します。

### 処理の流れ

```text
Request
  → 権限確認
  → session.tenantIdを含むfilter確定
  → format検証
  → streamOrders(filter)を1回だけ呼ぶ
  → toPublicOrderExportRowで公開項目へ変換
  → 監査を1回記録
  → CSVまたはNDJSONへ直列化
```

`format`が不正なら、`streamOrders`を呼ぶ前に400になります。

### handler案

```ts
import { z } from "zod";

const ExportOrderFormatSchema = z
  .enum(["csv", "ndjson"])
  .default("csv");

type ExportOrderFormat = z.infer<typeof ExportOrderFormatSchema>;

export async function exportOrders(req: Request, session: Session) {
  // serializerやrepositoryへ到達する前に認可を確定する。
  requirePermission(session, "orders:export");

  // tenantIdはリクエストから受け取らず、必ずsessionから設定する。
  const filter = ExportOrderFilterSchema.parse({
    tenantId: session.tenantId,
    status: req.query.status,
    from: req.query.from,
    to: req.query.to,
    limit: Math.min(Number(req.query.limit ?? 10_000), 10_000),
  });

  // defaultはundefinedのときだけ適用される。不正値をCSVへフォールバックさせない。
  const format = ExportOrderFormatSchema.parse(req.query.format);

  // format検証より後なので、不正formatでは呼ばれない。
  // format自体はrepositoryへ渡さない。
  const rows = streamOrders(filter);
  const publicRows = mapStream(rows, toPublicOrderExportRow);

  // 分岐の外で一度だけ記録する。
  audit.record("orders.exported", {
    tenantId: session.tenantId,
    format,
  });

  if (format === "ndjson") {
    return streamNdjson(publicRows, {
      contentType: "application/x-ndjson; charset=utf-8",
    });
  }

  // 既存のCSV呼び出しは変更しない。
  return streamCsv(publicRows, {
    headers: ["order_id", "status", "total", "placed_at"],
    contentType: "text/csv; charset=utf-8",
  });
}
```

Zodエラーを既存のエラーハンドラが400へ変換する前提です。そうでなければ、`ZodError`を400へ変換する既存の共通処理へ接続します。

既存関数名を維持する必要があるなら、`exportOrdersCsv`の名前を変えずに上記内容へ置き換えても出力には影響しません。ただし、ルートが複数形式を扱うことを表す`exportOrders`のほうが責務は明確です。

### 公開項目への変換

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

次のような実装は禁止します。

```ts
// fraudScoreやinternalNoteが混入し得る。
return {
  ...row,
  order_id: row.orderId,
};
```

両serializerには`PublicOrderExportRow`のstreamだけを渡します。これにより、公開項目を決める場所は形式によらず一か所です。

### NDJSON serializer案

serializerは各rowを個別に`JSON.stringify`し、必ず各objectの直後へ`\n`を付加します。最後のrowにもnewlineが付くため、末尾newline要件を満たします。

```ts
type StreamNdjsonOptions = {
  contentType: "application/x-ndjson; charset=utf-8";
};

export function streamNdjson(
  rows: AsyncIterable<PublicOrderExportRow>,
  options: StreamNdjsonOptions,
) {
  return streamText(serializeNdjson(rows), {
    contentType: options.contentType,
    encoding: "utf-8",
  });
}

async function* serializeNdjson(
  rows: AsyncIterable<PublicOrderExportRow>,
): AsyncGenerator<string> {
  for await (const row of rows) {
    // 公開row以外のプロパティを出力しないよう明示的に組み立てる。
    const object = {
      order_id: row.order_id,
      status: row.status,
      total: row.total,
      placed_at: row.placed_at,
    };

    yield `${JSON.stringify(object)}\n`;
  }
}
```

`streamText`が存在しない場合は、同じ責務のHTTP stream adapterを追加します。UTF-8への変換には`TextEncoder`を使用し、row全件を配列へ蓄積しないようにします。

### 永続化層

永続化層は変更しません。

```ts
function streamOrders(
  filter: ExportOrderFilter,
): AsyncIterable<OrderRow>;
```

守るべき点は以下です。

- `format`を`ExportOrderFilter`へ追加しない
- CSV用・NDJSON用のrepositoryメソッドを作らない
- handlerからのrepository呼び出しは`streamOrders(filter)`の1回だけ
- tenant条件、抽出条件、limit、既存の並び順を変えない
- NDJSON用に全件取得や再ソートを行わない

同じstreamを同じ公開row変換へ通すため、形式間のrow集合と順序は自然に一致します。

## テスト方針

### 1. handlerテスト

最低限、次をJestで固定します。

| ケース | 主な検証 |
|---|---|
| `format`省略 | CSVの既存バイト列、CSV Content-Type |
| `format=csv` | 省略時と同じバイト列 |
| `format=ndjson` | NDJSON Content-Type、1行1object、末尾newline |
| 不正format | 400、repository未呼び出し、監査未記録 |
| 権限なし | repository未呼び出し、serializer未呼び出し |
| tenant分離 | `session.tenantId`がfilterへ設定される |
| limit超過 | repositoryへ渡るlimitが10,000 |
| 両形式 | repositoryへ渡るfilterが完全一致 |
| 両形式 | row集合と順序が一致 |
| 内部項目 | どちらにも出力されない |
| 監査 | 成功requestごとに1回、選択されたformatを記録 |

例：

```ts
describe.each([
  [undefined, "csv"],
  ["csv", "csv"],
  ["ndjson", "ndjson"],
] as const)("format=%s", (queryFormat, expectedFormat) => {
  it("同じfilterでstreamOrdersを一度だけ呼ぶ", async () => {
    streamOrdersMock.mockReturnValue(streamOf(orderRow1, orderRow2));

    await exportOrders(
      request({
        format: queryFormat,
        status: "paid",
        limit: "20000",
      }),
      session({
        tenantId: "tenant-a",
        permissions: ["orders:export"],
      }),
    );

    expect(streamOrdersMock).toHaveBeenCalledTimes(1);
    expect(streamOrdersMock).toHaveBeenCalledWith({
      tenantId: "tenant-a",
      status: "paid",
      from: undefined,
      to: undefined,
      limit: 10_000,
    });

    expect(auditRecordMock).toHaveBeenCalledTimes(1);
    expect(auditRecordMock).toHaveBeenCalledWith("orders.exported", {
      tenantId: "tenant-a",
      format: expectedFormat,
    });
  });
});
```

不正値のテスト：

```ts
it("不正formatはdataを読まず400にする", async () => {
  const response = await invokeRoute({
    query: { format: "json" },
    session: authorizedSession,
  });

  expect(response.status).toBe(400);
  expect(streamOrdersMock).not.toHaveBeenCalled();
  expect(auditRecordMock).not.toHaveBeenCalled();
  expect(streamCsvMock).not.toHaveBeenCalled();
  expect(streamNdjsonMock).not.toHaveBeenCalled();
});
```

### 2. NDJSON serializerテスト

完全一致で検証します。

```ts
it("1行1object、UTF-8、末尾newlineで出力する", async () => {
  const response = streamNdjson(
    streamOf(
      {
        order_id: "ord-1",
        status: "paid",
        total: "1200",
        placed_at: "2026-09-01T10:00:00Z",
      },
      {
        order_id: "注文-2",
        status: "shipped",
        total: "500",
        placed_at: "2026-09-01T11:00:00Z",
      },
    ),
    {
      contentType: "application/x-ndjson; charset=utf-8",
    },
  );

  expect(response.headers.get("content-type")).toBe(
    "application/x-ndjson; charset=utf-8",
  );

  expect(await readUtf8Body(response)).toBe(
    '{"order_id":"ord-1","status":"paid","total":"1200","placed_at":"2026-09-01T10:00:00Z"}\n' +
      '{"order_id":"注文-2","status":"shipped","total":"500","placed_at":"2026-09-01T11:00:00Z"}\n',
  );
});
```

空streamなら本文は空文字です。「末尾newlineあり」は出力される各JSON objectの末尾にnewlineがある、という扱いにします。

### 3. 非公開項目の回帰テスト

内部値には検出しやすい文字列を設定します。

```ts
const persistenceRow: OrderRow = {
  tenantId: "tenant-secret",
  orderId: "ord-1",
  status: "paid",
  total: "1200",
  placedAt: "2026-09-01T10:00:00Z",
  fraudScore: 987654,
  internalNote: "DO_NOT_EXPORT_INTERNAL_NOTE",
};

expect(csvBody).not.toContain("987654");
expect(csvBody).not.toContain("DO_NOT_EXPORT_INTERNAL_NOTE");
expect(csvBody).not.toContain("tenant-secret");

expect(ndjsonBody).not.toContain("fraudScore");
expect(ndjsonBody).not.toContain("internalNote");
expect(ndjsonBody).not.toContain("tenantId");
expect(ndjsonBody).not.toContain("987654");
expect(ndjsonBody).not.toContain("DO_NOT_EXPORT_INTERNAL_NOTE");
```

### 4. 形式間の同一性テスト

CSVとNDJSONをそれぞれ解析し、同じ公開row配列として比較します。

```ts
expect(parseCsv(csvBody)).toEqual(parseNdjson(ndjsonBody));
```

ここでは配列として比較するため、集合だけでなく順序も検証できます。

### 5. CSVのbyte-for-byte回帰

既存のCSVテストfixtureを変更せず、`format`省略時と`format=csv`の両方を同じ期待バイト列へ照合します。

```ts
expect(await readBodyBytes(defaultResponse)).toEqual(existingCsvFixture);
expect(await readBodyBytes(explicitCsvResponse)).toEqual(existingCsvFixture);
```

文字列比較ではなくbyte列で比較し、BOM、改行コード、quote、header順、Content-Typeを含む既存挙動を固定します。CSV側のserializerやheader定義を共通化のためにリファクタリングしないことが、最も安全です。
