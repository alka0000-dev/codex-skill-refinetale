最小変更として、既存の`requestWithRetry`と`RetryableMethod`は変更せず、429だけを扱う冪等POST専用の入口を`retry.ts`へ追加する案が安全です。これにより、通常のPOSTが汎用再試行APIへ紛れ込むのを避けられます。

## 実装案

### `packages/http/retry.ts`

既存型・関数はそのまま残します。

```ts
type RetryableMethod = "GET" | "PUT" | "DELETE";

export type RetryRequest<T> = {
  method: RetryableMethod;
  retryableStatuses?: readonly number[];
  maxAttempts?: number;
  send: () => Promise<HttpResponse<T>>;
};

export type RetryIdempotentPostOn429Request<TBody, TResponse> = {
  body: TBody;
  idempotencyKey: string;
  send: (
    body: TBody,
    idempotencyKey: string,
  ) => Promise<HttpResponse<TResponse>>;
};

export async function requestWithRetry<T>({
  method,
  retryableStatuses = [429, 503],
  maxAttempts = 3,
  send,
}: RetryRequest<T>): Promise<HttpResponse<T>> {
  return retryLoop({ method, retryableStatuses, maxAttempts, send });
}

export async function requestIdempotentPostOn429<TBody, TResponse>({
  body,
  idempotencyKey,
  send,
}: RetryIdempotentPostOn429Request<TBody, TResponse>): Promise<
  HttpResponse<TResponse>
> {
  if (idempotencyKey.trim() === "") {
    throw new TypeError("idempotencyKey must not be empty");
  }

  return retryLoop({
    method: "POST",
    retryableStatuses: [429],
    maxAttempts: 3,
    send: () => send(body, idempotencyKey),
  });
}
```

`retryLoop`の内部入力型が`RetryableMethod`に限定されている場合だけ、内部型を次のように広げます。公開される`RetryableMethod`は広げません。

```ts
type RetryLoopMethod = RetryableMethod | "POST";
```

通信タイムアウトの判定は、現在の「GET/PUT/DELETEの場合だけ」という条件を維持します。`POST`をタイムアウト再試行対象へ追加してはいけません。

この専用関数では次が固定され、呼び出し側から変更できません。

- 再試行対象: `429`のみ
- 最大試行回数: 合計3回
- メソッド: `POST`
- 各試行へ渡すbodyと冪等性キー: 関数呼び出し時に受け取った同じ値

### `packages/billing/invoice-client.ts`

```ts
import { requestIdempotentPostOn429 } from "../http/retry";

export class InvoiceClient {
  constructor(private readonly http: HttpClient) {}

  createDraft(input: CreateDraftInput, idempotencyKey: string) {
    return requestIdempotentPostOn429({
      body: input,
      idempotencyKey,
      send: (body, key) =>
        this.http.post("/v2/invoices", body, {
          headers: { "Idempotency-Key": key },
        }),
    });
  }
}
```

### `packages/payments/payment-client.ts`

変更しません。

```ts
capture(input: CaptureInput) {
  return this.http.post("/v1/captures", input);
}
```

汎用の`requestWithRetry`は引き続きPOSTを型として受け付けません。また、`HttpClient.post`自体へ再試行を追加しないため、`capture`を含む他のPOSTへ再試行が波及しません。

## 呼び出し関係

```text
InvoiceClient.createDraft
  → requestIdempotentPostOn429
    → retryLoop
      → InvoiceClientから渡されたsend
        → HttpClient.post("/v2/invoices", 同じbody, 同じキー)

PaymentClient.capture
  → HttpClient.post("/v1/captures")
```

既存経路は変わりません。

```text
requestWithRetry（GET/PUT/DELETEのみ）
  → retryLoop
```

## 必要なテスト

### `requestIdempotentPostOn429`

- 1回目が429、2回目が成功なら2回呼ばれる。
- 3回すべて429なら、3回で終了して最後のレスポンスまたはエラーを返す。
- 503、500、502などは1回で終了する。
- 通信タイムアウトは1回で終了する。
- 空文字または空白だけの`idempotencyKey`は、通信前に失敗する。
- 各試行の`send`へ同じbody参照と同じ`idempotencyKey`が渡る。
- 429再試行時も既存の`Retry-After`、指数バックオフ、ログ形式が使われる。

最後の項目は、`retryLoop`の既存テストが十分なら重複させず、「専用関数が`retryLoop`を使用する」ことと429の統合テストで担保できます。

### `InvoiceClient.createDraft`

```ts
expect(http.post).toHaveBeenNthCalledWith(
  1,
  "/v2/invoices",
  input,
  { headers: { "Idempotency-Key": idempotencyKey } },
);

expect(http.post).toHaveBeenNthCalledWith(
  2,
  "/v2/invoices",
  input,
  { headers: { "Idempotency-Key": idempotencyKey } },
);
```

加えて以下を確認します。

- 429の後に成功すると再試行する。
- 503では再試行しない。
- タイムアウトでは再試行しない。
- 3回目の429以降は呼び出さない。

### 回帰テスト

- `PaymentClient.capture`が429、503、タイムアウトになっても`http.post`は1回だけ。
- 既存GET/PUT/DELETEのデフォルト対象が引き続き429と503。
- GET/PUT/DELETEの通信タイムアウト再試行が維持される。
- 既存の最大試行回数、ログ、バックオフ、`Retry-After`のテストが変更なしで通る。

## 仮定

- `maxAttempts: 3`は「初回を含めて合計3試行」を意味するものとします。
- `retryLoop`はHTTP 429をレスポンスとして受け取る設計と仮定しています。`HttpClient`が429を例外として投げる場合は、その例外からstatusを取得する既存経路へ合わせる必要があります。
- 「同じrequest body」は、同じ`input`を各試行へ渡すことを意味すると仮定しています。送信バイト列まで同一である必要があり、`HttpClient`がbodyを変更し得る場合は、事前シリアライズ可能なAPIの有無を追加確認する必要があります。
