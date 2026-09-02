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

## Candidate B

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

## Candidate C

実装の要点は、公開rowを作るまでの経路を完全に共通化し、最後のserializerだけを分岐させることです。永続化層には変更を加えません。

```text
認可
  → tenantIdを含むfilter確定
  → format検証
  → streamOrders(filter)
  → toPublicOrderExportRow
  → 監査eventを1回記録
  → CSVまたはNDJSON serializer
```

## Handler

既存のCSV呼び出しは、オプションを含めてそのまま残します。これによりCSVのbyte-for-byte互換性を守りやすくなります。

```ts
const ExportOrderFormatSchema = z.enum(["csv", "ndjson"]);

type ExportOrderFormat = z.infer<typeof ExportOrderFormatSchema>;

function parseExportOrderFormat(value: unknown): ExportOrderFormat {
  const result = ExportOrderFormatSchema.safeParse(value ?? "csv");

  if (!result.success) {
    // プロジェクト既存の400エラー型を使用する
    throw new BadRequestError("format must be csv or ndjson");
  }

  return result.data;
}

export async function exportOrdersCsv(req: Request, session: Session) {
  // formatが不正でも、認可を先に評価する。
  requirePermission(session, "orders:export");

  // tenant scopeと抽出条件をserializer選択前に確定する。
  const filter = ExportOrderFilterSchema.parse({
    tenantId: session.tenantId,
    status: req.query.status,
    from: req.query.from,
    to: req.query.to,
    limit: Math.min(Number(req.query.limit ?? 10_000), 10_000),
  });

  // streamOrdersより前なので、不正formatではデータを読まない。
  const format = parseExportOrderFormat(req.query.format);

  // repository呼び出しと公開row変換は両形式で一度だけ行う。
  const rows = streamOrders(filter);
  const publicRows = mapStream(rows, toPublicOrderExportRow);

  // 分岐内で記録すると重複・記録漏れが起きやすいため共通箇所で一度だけ記録する。
  audit.record("orders.exported", {
    tenantId: session.tenantId,
    format,
  });

  if (format === "ndjson") {
    return streamNdjson(publicRows, {
      contentType: "application/x-ndjson; charset=utf-8",
    });
  }

  // この呼び出しは既存コードから変更しない。
  return streamCsv(publicRows, {
    headers: ["order_id", "status", "total", "placed_at"],
    contentType: "text/csv; charset=utf-8",
  });
}
```

関数名 `exportOrdersCsv` は不正確になりますが、既存routeやimportへの影響を避けるなら今回は維持するのが安全です。名前の変更はNDJSON対応とは別差分にします。

## 公開row変換

公開項目の制御はserializerではなく、この変換で一元管理します。

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

`fraudScore` と `internalNote` を「serializer側で除外」する設計にはしません。両serializerが受け取る時点で、すでに公開可能な4項目だけになっていることが重要です。

## 永続化層

新しいrepositoryメソッドやNDJSON専用queryは作りません。

```ts
const rows = streamOrders(filter);
```

この一経路だけを維持するため、次の仕様が形式に依存しません。

- `session.tenantId`によるtenant分離
- status、from、to
- 最大10,000件
- repositoryが保証している並び順
- 同じ行集合

repositoryで選択する内部項目を減らす最適化は、既存CSVにも影響し得るため今回の変更には含めません。

## NDJSON serializer

既存のstreaming応答基盤を使い、1 rowずつUTF-8へ変換します。全件を配列化してはいけません。

```ts
export function streamNdjson(
  rows: AsyncIterable<PublicOrderExportRow>,
  options: {
    contentType: "application/x-ndjson; charset=utf-8";
  },
) {
  const chunks = mapStream(
    rows,
    (row) => `${JSON.stringify(row)}\n`,
  );

  return streamText(chunks, {
    contentType: options.contentType,
    encoding: "utf-8",
  });
}
```

`streamText` はプロジェクト既存のHTTP streaming primitiveに読み替えます。確認すべき契約は以下です。

- chunkを再エンコード・整形しない
- backpressureを維持する
-各objectの直後に`\n`を出す
- `JSON.stringify`失敗時に不完全な別objectを出さない

非空出力は必ずnewlineで終わります。0件の場合は、objectに対応しない空行を作らず0 byteとするのがNDJSONとして自然です。この挙動もテストで固定します。

## テスト

### Handlerテスト

依存をmockし、処理順序と呼び出し回数を検証します。

1. `format`省略

   - `streamOrders`が1回呼ばれる
   - filterに`session.tenantId`が入る
   - `streamCsv`が1回呼ばれる
   - `streamNdjson`は呼ばれない
   - 監査eventは1回、`format: "csv"`

2. `format=csv`

   - 省略時と同じfilter、公開row、serializer引数
   - 監査eventは1回、`format: "csv"`

3. `format=ndjson`

   - `streamOrders`は同じfilterで1回
   - `streamNdjson`が公開row streamを受け取る
   - content typeが正確に一致する
   - `streamCsv`は呼ばれない
   - 監査eventは1回、`format: "ndjson"`

4. 不正なformat

```ts
it("returns 400 without reading order data", async () => {
  await expect(
    exportOrdersCsv(request({ format: "json" }), session),
  ).rejects.toMatchObject({ statusCode: 400 });

  expect(streamOrders).not.toHaveBeenCalled();
  expect(streamCsv).not.toHaveBeenCalled();
  expect(streamNdjson).not.toHaveBeenCalled();
  expect(audit.record).not.toHaveBeenCalled();
});
```

5. 認可順序

   - 権限なし＋`format=json`でも認可エラーになる
   - `streamOrders`、serializer、監査は呼ばれない
   - これによりformat検証を認可oracleとして使わせない

6. tenant分離

   - requestにtenant相当の余分なqueryがあっても無視する
   - `streamOrders`へ渡るtenantIdは必ず`session.tenantId`

7. 件数上限

   - `limit=20000`は10,000
   - `limit=100`は100
   - CSVとNDJSONで同じfilterになる

### 公開row変換テスト

```ts
it("maps only public export fields", () => {
  const row: OrderRow = {
    tenantId: "tenant-a",
    orderId: "order-1",
    status: "paid",
    total: "1200",
    placedAt: "2026-09-02T01:02:03Z",
    fraudScore: 98,
    internalNote: "do not export",
  };

  expect(toPublicOrderExportRow(row)).toEqual({
    order_id: "order-1",
    status: "paid",
    total: "1200",
    placed_at: "2026-09-02T01:02:03Z",
  });

  expect(JSON.stringify(toPublicOrderExportRow(row)))
    .not.toContain("fraudScore");
  expect(JSON.stringify(toPublicOrderExportRow(row)))
    .not.toContain("internalNote");
});
```

### NDJSON serializerテスト

期待byte列を直接比較します。

```ts
it("writes one UTF-8 JSON object per line with a trailing newline", async () => {
  const body = await collectBytes(
    streamNdjson(
      asyncRows([
        {
          order_id: "注文-1",
          status: "paid",
          total: "1200",
          placed_at: "2026-09-02T01:02:03Z",
        },
        {
          order_id: "order-2",
          status: "pending",
          total: "500",
          placed_at: "2026-09-02T02:03:04Z",
        },
      ]),
      {
        contentType: "application/x-ndjson; charset=utf-8",
      },
    ),
  );

  expect(body.toString("utf8")).toBe(
    '{"order_id":"注文-1","status":"paid","total":"1200","placed_at":"2026-09-02T01:02:03Z"}\n' +
    '{"order_id":"order-2","status":"pending","total":"500","placed_at":"2026-09-02T02:03:04Z"}\n',
  );
});
```

追加で以下を検証します。

- 0件は0 byte
- 改行、引用符、バックスラッシュを含む値が正しくJSON escapeされる
- 最終行も`\n`で終わる
- `fraudScore`、`internalNote`、`tenantId`が含まれない
- 入力順序と出力行順序が一致する

### CSVの回帰テスト

mockだけではbyte-for-byte互換性を証明できないため、変更前の実装から取得したCSVをgolden fixtureとして固定します。

```ts
expect(await collectBytes(response)).toEqual(
  readFixture("orders-export.csv"),
);
```

同じ固定rowについて、以下を含むfixtureを用意します。

- カンマ
- 二重引用符
- 改行
- 非ASCII文字
- 空文字またはnullable値が許される場合の表現

既存の`streamCsv`、header順、content type、改行コード、quote規則、BOMの有無には手を加えません。これがCSVのbyte-for-byte非変更を担保する中心的なテストになります。

## Candidate D

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

## Candidate E

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

## Candidate F

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
