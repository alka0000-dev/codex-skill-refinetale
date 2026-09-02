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
