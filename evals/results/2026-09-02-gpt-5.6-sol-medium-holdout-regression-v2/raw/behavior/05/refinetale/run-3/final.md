結論として、分岐は出力境界の1か所だけに置きます。`streamOrders(filter)` と `toPublicOrderExportRow` は完全に共通化し、永続化層には形式を伝えません。

処理順序は次のとおりです。

```text
認可
→ session.tenantIdを含むfilter確定
→ format検証
→ streamOrders(filter)
→ PublicOrderExportRowへ変換
→ 監査を1回記録
→ CSVまたはNDJSONへserialize
```

## 変更契約

変更する挙動:

- `format=ndjson` を受理する。
- `format` 省略時はCSV。
- 不正な `format` は400で終了し、repositoryを呼ばない。
- NDJSONは各公開行をJSON objectとしてUTF-8で出力し、各行を `\n` で終える。
- 監査の `format` に実際の形式を記録する。

変更しない挙動:

- `orders:export` の認可。
- `session.tenantId` によるtenant scope。
- status/from/to/limitの検証。
- 10,000件上限。
- `streamOrders(filter)` のquery、件数、順序。
- `toPublicOrderExportRow` が所有する公開項目。
- CSVのheader、escaping、改行、BOMなどを含む全byte列。
- 監査をserializer生成前に記録する現在のタイミング。

## Handler

handler名は責務に合わせて `exportOrders` に変更し、route側の参照も同じ変更で更新します。互換aliasは、外部公開された関数である根拠がない限り追加しません。

```ts
import { z } from "zod";

const ExportOrderFormatSchema = z
  .enum(["csv", "ndjson"])
  .default("csv");

type ExportOrderFormat = z.infer<typeof ExportOrderFormatSchema>;

export async function exportOrders(req: Request, session: Session) {
  requirePermission(session, "orders:export");

  // 既存コードを変更しない。tenant scopeと上限の正本はここ。
  const filter = ExportOrderFilterSchema.parse({
    tenantId: session.tenantId,
    status: req.query.status,
    from: req.query.from,
    to: req.query.to,
    limit: Math.min(Number(req.query.limit ?? 10_000), 10_000),
  });

  // undefinedだけがcsvになる。未知値や配列は拒否する。
  const format = ExportOrderFormatSchema.parse(req.query.format);

  // format検証後に初めてrepositoryへ到達する。
  const rows = streamOrders(filter);
  const publicRows = mapStream(rows, toPublicOrderExportRow);

  // 既存と同じ位置・回数。stream完了監査への意味変更は行わない。
  audit.record("orders.exported", {
    tenantId: session.tenantId,
    format,
  });

  // 実際に出力が異なる唯一の分岐。
  switch (format) {
    case "csv":
      // byte-for-byte互換のため、既存呼び出しをそのまま残す。
      return streamCsv(publicRows, {
        headers: ["order_id", "status", "total", "placed_at"],
        contentType: "text/csv; charset=utf-8",
      });

    case "ndjson":
      return streamPublicOrderExportNdjson(publicRows);
  }
}
```

重要なのは、`format` の検証より先に認可とtenant入りfilterを確定し、`streamOrders` より前にformatを検証する順序です。したがって、認可されていないリクエストはformatに関係なく拒否され、不正formatはデータを読みません。

## 永続化層と公開行変換

永続化層は変更しません。

```ts
streamOrders(filter)
  // AsyncIterable<OrderRow>
```

次のような形式別repositoryは追加しません。

```ts
// 追加しない
streamOrdersCsv(filter);
streamOrdersNdjson(filter);
streamOrders(filter, { format });
```

公開境界も既存の1か所を使います。

```ts
function toPublicOrderExportRow(
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

`fraudScore` と `internalNote` はこの変換より後へ到達しないため、どちらのserializerでも出力できません。

## NDJSON serializer

汎用の `streamNdjson<T>()` にすると、誤って `OrderRow` を直接渡せる公開経路が増えます。入力型を `PublicOrderExportRow` に限定します。

```ts
const NDJSON_CONTENT_TYPE =
  "application/x-ndjson; charset=utf-8";

async function* encodePublicOrderExportNdjson(
  rows: AsyncIterable<PublicOrderExportRow>,
): AsyncGenerator<Uint8Array> {
  const encoder = new TextEncoder();

  for await (const row of rows) {
    yield encoder.encode(`${JSON.stringify(row)}\n`);
  }
}

export function streamPublicOrderExportNdjson(
  rows: AsyncIterable<PublicOrderExportRow>,
) {
  return streamBytes(
    encodePublicOrderExportNdjson(rows),
    {
      contentType: NDJSON_CONTENT_TYPE,
    },
  );
}
```

`streamBytes` はプロジェクト既存の、`AsyncIterable<Uint8Array>` をresponse bodyへ流すadapterを想定しています。全件を配列化したり文字列結合したりしません。

非空の場合は最後のobjectも必ず `\n` で終わります。0件の場合は、レコードが存在しないため空bodyです。

## 最小テスト構成

### Serializer単体テスト

NDJSON固有の仕様は最も低い責務で検証します。

```ts
describe("streamPublicOrderExportNdjson", () => {
  it("各公開行をUTF-8のJSON objectとして入力順に出力し最終行もnewlineで終える", async () => {
    const rows = asyncRows([
      {
        order_id: "order-1",
        status: "paid",
        total: "1200",
        placed_at: "2026-09-01T01:00:00Z",
      },
      {
        order_id: "order-2",
        status: "cancelled",
        total: "800",
        placed_at: "2026-09-01T02:00:00Z",
      },
    ]);

    const response = streamPublicOrderExportNdjson(rows);

    expect(response.headers.get("content-type")).toBe(
      "application/x-ndjson; charset=utf-8",
    );
    await expect(readResponseBytes(response)).resolves.toEqual(
      Buffer.from(
        [
          '{"order_id":"order-1","status":"paid","total":"1200","placed_at":"2026-09-01T01:00:00Z"}',
          '{"order_id":"order-2","status":"cancelled","total":"800","placed_at":"2026-09-01T02:00:00Z"}',
          "",
        ].join("\n"),
        "utf8",
      ),
    );
  });

  it("0件では空bodyを返す", async () => {
    const response = streamPublicOrderExportNdjson(asyncRows([]));

    await expect(readResponseBytes(response)).resolves.toEqual(
      Buffer.alloc(0),
    );
  });
});
```

### Handler/HTTP境界テスト

既存factoryがあれば、内部項目を含む `OrderRow` はfactoryから生成します。

最低限、次を検証します。

1. `format` 省略:

   - 既存CSV golden bytesと完全一致
   - content typeが従来どおり
   - auditは1回、`format: "csv"`

2. `format=csv`:

   - 同じCSV golden bytesと完全一致
   - 省略時と明示時で差がない

3. `format=ndjson`:

   - repositoryが返した順序と同じ
   - exact NDJSON bytes
   - 最終newlineあり
   - `fraudScore`、`internalNote` の値がbodyに存在しない
   - auditは1回、`format: "ndjson"`

4. `format=xml`:

   - HTTP 400
   - `streamOrders` は未呼び出し
   - auditは未呼び出し

5. 認可エラーかつ `format=xml`:

   - 400ではなく既存の認可エラー
   - `streamOrders`、auditとも未呼び出し
   - 認可がformat検証より先であることを保証

6. tenant scopeと上限を両形式で検証:

```ts
it.each(["csv", "ndjson"] as const)(
  "%sでもsessionのtenantと10,000件上限だけをrepositoryへ渡す",
  async (format) => {
    await requestExport({
      session: tenantSession("tenant-a"),
      query: {
        format,
        tenantId: "tenant-b",
        limit: "10001",
        status: "paid",
      },
    });

    expect(streamOrders).toHaveBeenCalledTimes(1);
    expect(streamOrders).toHaveBeenCalledWith({
      tenantId: "tenant-a",
      status: "paid",
      from: undefined,
      to: undefined,
      limit: 10_000,
    });
  },
);
```

7. stream途中でrepositoryが失敗:

   - responseの読み取りが失敗する
   - auditは現在の契約どおり既に1回だけ記録済み
   - 2件目の監査は発生しない

## 要件と検証の対応

| 契約 | 直接の証拠 |
|---|---|
| 省略時CSV | 省略時のCSV golden-byteテスト |
| 明示的CSVの互換性 | `format=csv` の同一golden-byteテスト |
| NDJSON、UTF-8、最終newline | serializerのexact-byteテスト |
| 不正formatは400、data未読 | HTTP 400＋`streamOrders`未呼び出し |
| 認可が先 | 認可エラー＋不正formatで認可エラーを確認 |
| tenant分離 | repository引数が必ず`session.tenantId` |
| filterと10,000件上限が同一 | `it.each(["csv", "ndjson"])` の引数検証 |
| row集合と順序が同一 | 同じrepository rowsに対する両形式のexact body |
| 内部項目を除外 | 秘密値を持つ`OrderRow`から生成したbodyに値・keyがない |
| repository queryが1経路 | `streamOrders`が1回だけ呼ばれる |
| 監査が1回、実formatを記録 | default CSV、明示CSV、NDJSONそれぞれのaudit検証 |
| 後続stream失敗時も監査を増やさない | body読み取り失敗後もauditが1回 |

作業領域には実装コードやテスト実行環境がなく、読み取り専用だったため、コード変更・テスト実行・`.agent/CONTINUITY.md` 作成は行っていません。また、指定skillの対応表をファイル保存できない制約があったため、変更契約を回答内で明示する形に留めています。
