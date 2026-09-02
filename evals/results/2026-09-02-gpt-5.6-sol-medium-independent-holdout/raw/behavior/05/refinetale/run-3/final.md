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
