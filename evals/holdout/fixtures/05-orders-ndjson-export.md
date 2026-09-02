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
