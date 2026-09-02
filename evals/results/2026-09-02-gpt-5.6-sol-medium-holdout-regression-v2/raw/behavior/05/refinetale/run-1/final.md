実装の核は、`format` を入力境界で検証し、形式分岐を serializer 境界の1か所だけに置くことです。repository までのデータ経路はCSVとNDJSONで完全に共通化します。

今回は提示されたコード以外のプロジェクトファイルが作業領域になく、読み取り専用だったため、実装・テスト実行・`.agent/CONTINUITY.md` 作成は行っていません。以下は具体的な実装案です。

## 変更契約

変更する挙動:

- `format=csv|ndjson` を受理する。
- 省略時は `csv`。
- `ndjson` は公開rowを1行1 JSON objectとしてUTF-8出力し、各rowを `\n` で終える。
- Content-Typeは `application/x-ndjson; charset=utf-8`。
- 監査イベントの `format` に実際に選択された値を記録する。

変更しない挙動:

- `orders:export` 認可。
- `session.tenantId` によるtenant scope。
- status/from/to/limitの抽出条件。
- 10,000件上限。
- `streamOrders(filter)` という唯一のrepository経路。
- rowの集合と順序。
- `toPublicOrderExportRow` による公開項目制限。
- CSVのContent-Type、header、escaping、改行を含む全バイト。
- 監査タイミングと、成功したhandler呼び出し当たり1イベント。

共通処理:

```text
認可
  → format検証
  → tenantを含むfilter生成
  → streamOrders(filter)
  → toPublicOrderExportRow
  → 監査（1回）
  → serializer
```

形式差は最後のserializerだけです。

## Handler

関数名は実態に合わせて `exportOrders` に変更します。既存名が外部契約なら、実在する呼び出し元だけを同時に更新します。根拠なく互換aliasは残しません。

```ts
import { z } from "zod";

const ExportOrderFormatSchema = z.enum(["csv", "ndjson"]);
type ExportOrderFormat = z.infer<typeof ExportOrderFormatSchema>;

export async function exportOrders(req: Request, session: Session) {
  requirePermission(session, "orders:export");

  // 検証であり、まだserializerは選択しない。
  const format = ExportOrderFormatSchema.parse(req.query.format ?? "csv");

  // tenant scopeと既存の抽出条件を、この時点で確定する。
  const filter = ExportOrderFilterSchema.parse({
    tenantId: session.tenantId,
    status: req.query.status,
    from: req.query.from,
    to: req.query.to,
    limit: Math.min(Number(req.query.limit ?? 10_000), 10_000),
  });

  // formatはrepositoryへ渡さない。
  const rows = streamOrders(filter);
  const publicRows = mapStream(rows, toPublicOrderExportRow);

  // 既存と同じく、streamの消費完了ではなくexport開始時に1回記録する。
  audit.record("orders.exported", {
    tenantId: session.tenantId,
    format,
  });

  return streamOrderExport(format, publicRows);
}
```

重要な順序は次のとおりです。

- 認可失敗なら、format検証もrepository呼び出しも監査も行わない。
- format不正なら、filter生成より後ろ、特に `streamOrders` へ到達しない。
- serializer選択は、認可とtenant付きfilterの確定後。
- `format` を `ExportOrderFilter` に追加しない。永続化層に表示形式を伝播させない。

Zodエラーを400へ変換する既存のHTTPエラーハンドリングがある前提です。存在しない場合は、このhandlerだけで例外変換せず、既存の入力検証境界へ追加します。

## Serializer

形式の分岐はここだけに置きます。

```ts
type PublicOrderRows =
  AsyncIterable<PublicOrderExportRow>;

type OrderExportSerializer = (
  rows: PublicOrderRows,
) => Response;

const orderExportSerializers = {
  csv: (rows) =>
    streamCsv(rows, {
      headers: ["order_id", "status", "total", "placed_at"],
      contentType: "text/csv; charset=utf-8",
    }),

  ndjson: (rows) =>
    streamNdjson(rows, {
      contentType: "application/x-ndjson; charset=utf-8",
    }),
} satisfies Record<ExportOrderFormat, OrderExportSerializer>;

export function streamOrderExport(
  format: ExportOrderFormat,
  rows: PublicOrderRows,
): Response {
  return orderExportSerializers[format](rows);
}
```

CSV側は既存の `streamCsv` 呼び出しをそのまま移動します。共通serializerへ一般化したり、CSVの既存設定を組み直したりしないことがbyte-for-byte互換性の要点です。

NDJSON serializerは、公開rowだけを受け取ります。

```ts
export function streamNdjson<T>(
  rows: AsyncIterable<T>,
  options: { contentType: string },
): Response {
  return streamText(
    mapStream(rows, (row) => `${JSON.stringify(row)}\n`),
    options,
  );
}
```

`streamText` はプロジェクト既存のUTF-8ストリーム応答生成機構に読み替えます。新しいbuffer全件保持はせず、backpressureとストリームエラー伝播を維持します。

`toPublicOrderExportRow` は両形式で共有します。

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

これにより `fraudScore` と `internalNote` はserializerへ到達しません。serializer内で除外する設計にはしません。

なお、0件の場合は空bodyとします。「末尾newline」は各object行を `\n` で終える意味です。0件時に `\n` だけ出すと、JSON objectではない空行が生じるためです。

## 永続化層

変更しません。

```ts
const rows = streamOrders(filter);
```

次のような追加は禁止します。

```ts
// 不採用
streamOrdersCsv(filter);
streamOrdersNdjson(filter);
streamOrders({ ...filter, format });
```

repositoryは既存と同じ件数・順序・境界条件を持つ `OrderRow` ストリームを1本だけ返します。内部項目が含まれる点も変えず、公開境界は引き続き `toPublicOrderExportRow` が所有します。

## 最小テスト構成

### 1. Handler連携テスト

`streamOrders`、`audit.record`、`streamOrderExport` をmockします。

| 契約 | 入力・操作 | 期待結果 |
|---|---|---|
| 認可が最初 | 権限なし、`format=invalid` | 403。`streamOrders`、serializer、auditは0回 |
| 不正formatの早期終了 | 権限あり、`format=xml` | 400。`streamOrders`、serializer、auditは0回 |
| CSVデフォルト | format省略 | serializerに `"csv"`。監査は `{tenantId, format:"csv"}` で1回 |
| CSV明示 | `format=csv` | デフォルトと同じfilter、serializerは `"csv"` |
| NDJSON | `format=ndjson` | CSVと同じfilter、serializerは `"ndjson"`、監査は1回 |
| tenant分離 | session tenantが `tenant-a`、queryに別tenant相当値 | `streamOrders` のfilterは必ず `tenantId:"tenant-a"` |
| 件数上限 | `limit=10001`、両format | 両方とも `streamOrders({…, limit:10000})` |
| 抽出条件不変 | 同じstatus/from/toを両formatに渡す | `streamOrders` の引数が完全一致 |
| repository失敗 | `streamOrders` が同期的にthrow | serializerとauditは0回、エラー伝播 |
| audit失敗 | `audit.record` がthrow | serializerは0回、エラー伝播 |

代表例:

```ts
it.each([
  [undefined, "csv"],
  ["csv", "csv"],
  ["ndjson", "ndjson"],
] as const)(
  "同一filterを使い、選択されたformatを監査する",
  async (queryFormat, expectedFormat) => {
    const req = request({
      format: queryFormat,
      status: "paid",
      from: "2026-08-01",
      to: "2026-08-31",
      limit: "20000",
    });
    const session = sessionWith({
      tenantId: "tenant-a",
      permissions: ["orders:export"],
    });

    await exportOrders(req, session);

    expect(streamOrders).toHaveBeenCalledTimes(1);
    expect(streamOrders).toHaveBeenCalledWith({
      tenantId: "tenant-a",
      status: "paid",
      from: "2026-08-01",
      to: "2026-08-31",
      limit: 10_000,
    });
    expect(streamOrderExport).toHaveBeenCalledWith(
      expectedFormat,
      expect.anything(),
    );
    expect(audit.record).toHaveBeenCalledTimes(1);
    expect(audit.record).toHaveBeenCalledWith("orders.exported", {
      tenantId: "tenant-a",
      format: expectedFormat,
    });
  },
);
```

不正format:

```ts
it("不正formatはデータを読まず400にする", async () => {
  await expect(
    invokeExport({ format: "xml" }, authorizedSession),
  ).rejects.toMatchObject({ status: 400 });

  expect(streamOrders).not.toHaveBeenCalled();
  expect(streamOrderExport).not.toHaveBeenCalled();
  expect(audit.record).not.toHaveBeenCalled();
});
```

### 2. 公開row変換テスト

この責務の所有者で、内部項目除外を一度だけ保証します。

```ts
it("公開可能な4項目だけへ変換する", () => {
  const row: OrderRow = {
    tenantId: "tenant-a",
    orderId: "order-1",
    status: "paid",
    total: "1200",
    placedAt: "2026-08-10T12:00:00Z",
    fraudScore: 98,
    internalNote: "do not export",
  };

  expect(toPublicOrderExportRow(row)).toEqual({
    order_id: "order-1",
    status: "paid",
    total: "1200",
    placed_at: "2026-08-10T12:00:00Z",
  });
});
```

このテストにより、両serializerで同じ除外テストを重複させる必要はありません。

### 3. CSV回帰テスト

変更前に既存serializerの出力をfixtureとして固定し、変更後も同一bytesであることを確認します。文字列の意味比較ではなく `Buffer.equals` を使います。

```ts
it("既存CSV出力をbyte-for-byteで維持する", async () => {
  const response = streamOrderExport(
    "csv",
    rowsFrom(publicRowsFixture),
  );

  const actual = Buffer.from(await response.arrayBuffer());
  const expected = await readFixture("orders-export.csv");

  expect(actual.equals(expected)).toBe(true);
  expect(response.headers.get("content-type"))
    .toBe("text/csv; charset=utf-8");
});
```

fixtureには最低限、次を含めます。

- 複数rowによる順序確認。
- comma、quote、改行、非ASCII文字を含む値。
- 既存CSVのheaderと改行コード。

### 4. NDJSON serializerテスト

```ts
it("1行1objectをUTF-8で出力し、最終行もnewlineで終える", async () => {
  const response = streamOrderExport(
    "ndjson",
    rowsFrom([
      {
        order_id: "注文-1",
        status: "paid",
        total: "1200",
        placed_at: "2026-08-10T12:00:00Z",
      },
      {
        order_id: "order-2",
        status: "shipped",
        total: "3400",
        placed_at: "2026-08-11T12:00:00Z",
      },
    ]),
  );

  expect(response.headers.get("content-type")).toBe(
    "application/x-ndjson; charset=utf-8",
  );
  expect(await response.text()).toBe(
    '{"order_id":"注文-1","status":"paid","total":"1200","placed_at":"2026-08-10T12:00:00Z"}\n' +
    '{"order_id":"order-2","status":"shipped","total":"3400","placed_at":"2026-08-11T12:00:00Z"}\n',
  );
});
```

追加で0件は空body、途中でrow streamが失敗した場合はエラーが呼び出し元へ伝播することを確認します。

### 5. 両形式の不変条件テスト

内部項目を持つ同じrepository fixtureをhandlerから最後まで流し、次を確認します。

- CSVをparseしたrow配列と、NDJSONを各行 `JSON.parse` した配列が同一。
- 入力順序が維持される。
- ちょうど10,000件で10,000件出力される。
- 10,001要求でもrepository filterが10,000で、出力も最大10,000件。
- 全rowのkeyが `order_id/status/total/placed_at` のみ。

全status・全期間の直積テストは不要です。filterの正本は既存schema/repositoryであり、この変更で追加される契約は「formatによってfilterが変わらないこと」だからです。

この構成なら、新しい状態は検証済みの `format` 1つ、形式分岐はserializer table 1か所、データ経路と公開境界は従来どおり1本に保てます。
