実装の中心は、永続化から公開行への変換までを完全に共通化し、最後のserializerだけを分岐させる構造です。CSV側の既存serializer・引数・データ経路には手を入れません。

## 変更契約

変更する挙動：

- `format=ndjson`を受理する。
- `format`省略時と`format=csv`はCSVを返す。
- 不正な`format`は400とし、`streamOrders`を呼ばない。
- NDJSONは公開行1件につきJSON object 1行、UTF-8、各行末に`\n`を付ける。
- 監査イベントの`format`へ実際に選択された`csv`または`ndjson`を記録する。

変更しない挙動：

- `orders:export`認可。
- `session.tenantId`によるtenant scope。
- status、from、to、limitの解釈。
- 10,000件上限。
- repository関数とquery。
- repositoryが決める行集合と順序。
- `toPublicOrderExportRow`が所有する公開項目。
- 監査イベント名と1リクエスト1件という回数。
- CSVのserializer、headers、content type、出力バイト列。

共通処理：

```text
認可
  → tenant付きfilter生成
  → format検証
  → streamOrders(filter)
  → toPublicOrderExportRow
  → 監査
  → serializer選択
```

形式固有の差分は最後の1箇所だけです。

```text
PublicOrderExportRow stream
  ├─ csv    → 既存streamCsv
  └─ ndjson → 新規streamNdjson
```

## Handler案

内部関数名は既存参照への影響を避けるなら`exportOrdersCsv`のままでも動作しますが、複数形式を扱うため`exportOrders`への変更が自然です。HTTP route自体は変えません。

```ts
const ExportOrderFormatSchema = z
  .enum(["csv", "ndjson"])
  .default("csv");

type ExportOrderFormat = z.infer<typeof ExportOrderFormatSchema>;

export async function exportOrders(req: Request, session: Session) {
  requirePermission(session, "orders:export");

  // 既存filterの検証順序とtenant scopeを維持する。
  const filter = ExportOrderFilterSchema.parse({
    tenantId: session.tenantId,
    status: req.query.status,
    from: req.query.from,
    to: req.query.to,
    limit: Math.min(Number(req.query.limit ?? 10_000), 10_000),
  });

  // parse完了前にはrepositoryを呼ばない。
  const format: ExportOrderFormat = ExportOrderFormatSchema.parse(
    req.query.format,
  );

  const rows = streamOrders(filter);
  const publicRows = mapStream(rows, toPublicOrderExportRow);

  // 分岐外に置くことで、成功経路では常に1回だけ記録する。
  // 位置も既存実装と同じくserializer呼び出しより前。
  audit.record("orders.exported", {
    tenantId: session.tenantId,
    format,
  });

  if (format === "ndjson") {
    return streamNdjson(publicRows);
  }

  // 呼び出しとoptionsを一切変えない。
  return streamCsv(publicRows, {
    headers: ["order_id", "status", "total", "placed_at"],
    contentType: "text/csv; charset=utf-8",
  });
}
```

`format`の分岐はここだけです。repository、mapper、監査で形式を再判定しません。

`ExportOrderFormatSchema.parse()`のZodエラーは、既存の入力エラー処理によって400へ変換する前提です。現在そうなっていなければ、形式専用の例外処理ではなく既存のvalidation error middlewareで扱います。

## 永続化層と公開境界

repositoryは変更しません。

```ts
const rows: AsyncIterable<OrderRow> = streamOrders(filter);
```

守るべきquery契約は次のとおりです。

- 入力は既存の`ExportOrderFilter`だけ。
- `tenantId`は常に`session.tenantId`。
- 生成行数は0〜10,000件。
- 0件入力では0件を返す。
- status、from、toの境界条件は既存queryのまま。
- 行順は既存queryのまま。
- NDJSON用queryやformat引数を追加しない。

内部項目の遮断は、既存mapperを唯一の正本にします。

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

serializerへ`OrderRow`を渡さないことが重要です。CSVとNDJSONそれぞれで除外項目を管理すると、公開項目の正本が二重になります。

## NDJSON serializer案

既存のストリーミング基盤を使い、全件配列化しません。以下の`streamText`は、プロジェクトで既に使われているresponse stream helperへ読み替えます。

```ts
export function streamNdjson(
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

重要な点は次の3つです。

- `JSON.stringify()`の対象型は`PublicOrderExportRow`だけ。
- 1行ごとに必ず`\n`を加える。
- UTF-8変換、backpressure、stream errorの伝播は既存stream helperに任せる。

例えば2件なら、厳密に次の本文です。

```ndjson
{"order_id":"o-1","status":"paid","total":"1200","placed_at":"2026-09-01T10:00:00Z"}
{"order_id":"o-2","status":"shipped","total":"800","placed_at":"2026-09-01T11:00:00Z"}
```

2行目の後ろにも`\n`があります。

0件時は0 byteとします。改行だけを返すと「1行1 JSON object」に反するためです。「末尾newline」は1件以上存在する出力の最終行にもnewlineがある、という契約として扱います。

## 最小テスト構成

### Mapper単体テスト

公開項目の正本だけを検証します。

```ts
it("内部項目を公開行へ含めない", () => {
  const row: OrderRow = {
    tenantId: "tenant-a",
    orderId: "order-1",
    status: "paid",
    total: "1200",
    placedAt: "2026-09-01T10:00:00Z",
    fraudScore: 98,
    internalNote: "manual review",
  };

  expect(toPublicOrderExportRow(row)).toEqual({
    order_id: "order-1",
    status: "paid",
    total: "1200",
    placed_at: "2026-09-01T10:00:00Z",
  });
});
```

### NDJSON serializer単体テスト

次を厳密なバイト列で検証します。

- content type。
- 1 object 1行。
- 行順。
- 最終newline。
- Unicode、引用符、改行を含む文字列のJSON escaping。
- 0件なら空body。
- iterableの途中失敗がresponse streamへ伝播する。

期待値は文字列を組み立て直すのではなく、固定値にします。

```ts
expect(contentType).toBe(
  "application/x-ndjson; charset=utf-8",
);

expect(bodyBytes).toEqual(
  new TextEncoder().encode(
    '{"order_id":"o-1","status":"paid","total":"1200","placed_at":"2026-09-01T10:00:00Z"}\n' +
    '{"order_id":"o-2","status":"shipped","total":"800","placed_at":"2026-09-01T11:00:00Z"}\n',
  ),
);
```

### Handlerテスト

形式ごとの全組み合わせではなく、handlerが所有する連携契約を検証します。

| 契約 | 入力・条件 | 期待結果 |
|---|---|---|
| CSVデフォルト | `format`なし | 既存CSV fixtureとbodyがbyte-for-byte一致 |
| 明示CSV | `format=csv` | 省略時と同じbody、content type |
| NDJSON選択 | `format=ndjson` | NDJSON serializerのbodyとcontent type |
| 不正形式 | `format=json` | 400、`streamOrders`・serializer・auditは0回 |
| 認可失敗 | 権限なし、各format | 403、filter以降・repository・serializer・auditは0回 |
| tenant分離 | session tenantと異なる注文もfixtureに含める | `streamOrders`へsession tenantのfilterだけを渡す |
| 抽出条件 | status/from/to指定 | 両形式で同一filterをrepositoryへ渡す |
| 件数上限 | `limit=20000` | 両形式でrepository引数のlimitが10,000 |
| 行集合と順序 | 同じrepository rowsを各形式で返す | CSVをparseした配列とNDJSONをparseした配列が同値・同順 |
| 公開項目 | 内部項目入り`OrderRow` | 両形式とも4公開項目のみ |
| 監査 | CSV・NDJSON成功 | 各requestで正確に1回、実際のformatを記録 |
| repository同期失敗 | `streamOrders`がthrow | auditとserializerは0回 |
| stream途中失敗 | iterableが途中でthrow | response消費が失敗し、auditは既存順序どおり1回だけ |
| serializer生成失敗 | serializerがthrow | auditは既存順序どおり1回だけ、重複記録なし |

CSVのbyte互換テストでは、変更前に既存fixtureを確定し、次を丸ごと比較します。

- BOMの有無。
- header名と順序。
- delimiterとquote escaping。
- 改行コード。
- 最終改行。
- content type。
- 本文の全byte。

## 追加しないもの

- `streamOrdersCsv`／`streamOrdersNdjson`のようなrepository分岐。
- formatを含むrepository引数。
- CSV用・NDJSON用の別公開row型。
- serializerごとの公開項目リスト。
- 形式別のfilter作成。
- strategy classやserializer registry。
- NDJSON全件の配列化。
- 将来形式用のenum値やfallback。

これにより、増える実行時状態は検証済みの`format`ひとつ、増える分岐は出力境界のひとつ、増えるデータ経路はNDJSON serializerだけです。CSV経路は既存の呼び出しをそのまま通るため、互換性を最も直接的に保証できます。
