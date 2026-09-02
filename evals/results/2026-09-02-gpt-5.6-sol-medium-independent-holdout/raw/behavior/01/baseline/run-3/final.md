実装方針は、既存のGET/PUT/DELETE用契約を残したまま、明示的なPOST再試行を型で区別し、`createDraft` だけから利用する形が安全です。

## 実装案

### `packages/http/retry.ts`

POSTでは通信タイムアウトを再試行しないことを型と実行時の両方で明示します。

```ts
type RetryableMethod = "GET" | "PUT" | "DELETE";

type ExistingRetryRequest<T> = {
  method: RetryableMethod;
  retryableStatuses?: readonly number[];
  maxAttempts?: number;
  send: () => Promise<HttpResponse<T>>;
};

type StatusOnlyPostRetryRequest<T> = {
  method: "POST";
  retryableStatuses: readonly number[];
  maxAttempts: number;
  retryTimeouts: false;
  send: () => Promise<HttpResponse<T>>;
};

export type RetryRequest<T> =
  | ExistingRetryRequest<T>
  | StatusOnlyPostRetryRequest<T>;

export async function requestWithRetry<T>(
  request: RetryRequest<T>,
): Promise<HttpResponse<T>> {
  const {
    method,
    retryableStatuses = [429, 503],
    maxAttempts = 3,
    send,
  } = request;

  const retryTimeouts =
    method === "POST" ? request.retryTimeouts : true;

  // バックオフ、Retry-After、ログの既存実装は変更しない。
  return retryLoop({
    method,
    retryableStatuses,
    maxAttempts,
    retryTimeouts,
    send,
  });
}
```

`retryLoop` が既にメソッドからタイムアウト再試行可否を判断している場合は、`retryTimeouts` の追加は不要です。その場合は、POSTがタイムアウト分岐へ入らないことだけを確認します。

重要なのは、単純に既存の `RetryableMethod` へ `"POST"` を追加しないことです。POSTでは設定の省略を許さず、ステータスだけを対象にすることを呼び出し側に明示させます。

### `packages/billing/invoice-client.ts`

```ts
import { requestWithRetry } from "../http/retry";

export class InvoiceClient {
  constructor(private readonly http: HttpClient) {}

  createDraft(input: CreateDraftInput, idempotencyKey: string) {
    if (idempotencyKey.length === 0) {
      throw new TypeError("idempotencyKey must not be empty");
    }

    return requestWithRetry({
      method: "POST",
      retryableStatuses: [429],
      maxAttempts: 3,
      retryTimeouts: false,
      send: () =>
        this.http.post("/v2/invoices", input, {
          headers: { "Idempotency-Key": idempotencyKey },
        }),
    });
  }
}
```

`send` のクロージャーが、呼び出し時に受け取った `input` と `idempotencyKey` をそのまま捕捉します。再試行中にbodyやキーを生成し直しません。

### `packages/payments/payment-client.ts`

変更しません。

```ts
capture(input: CaptureInput) {
  return this.http.post("/v1/captures", input);
}
```

## 呼び出し関係

```text
InvoiceClient.createDraft
  └─ requestWithRetry
       └─ retryLoop
            └─ send
                 └─ HttpClient.post("/v2/invoices", ...)

PaymentClient.capture
  └─ HttpClient.post("/v1/captures", ...)
```

`capture` は再試行基盤を経由しないため、429でも1回だけ送信されます。

## 必要なテスト

### `InvoiceClient.createDraft`

最低限、次を確認します。

- 1回目が429、2回目が成功した場合は合計2回送信する。
- 429が続いた場合でも合計3回で終了する。
- 503では1回だけ送信して終了する。
- 500など、その他の5xxでも1回だけ送信する。
- 通信タイムアウトでは1回だけ送信する。
- 全試行のURL、body、`Idempotency-Key` が同じである。
  - bodyは可能なら値の一致だけでなく `toBe(input)` で同一参照も確認する。
- 空文字の `idempotencyKey` は、HTTP送信前に失敗する。
- 初回成功時は従来どおり1回だけ送信し、レスポンスを返す。

429の主要テスト例です。

```ts
it("429の場合だけ同じbodyとidempotency keyで最大3回試行する", async () => {
  const input = createDraftInputFactory();
  const response429 = createHttpResponse({ status: 429 });
  const success = createHttpResponse({ status: 201 });

  http.post
    .mockResolvedValueOnce(response429)
    .mockResolvedValueOnce(response429)
    .mockResolvedValueOnce(success);

  await expect(
    client.createDraft(input, "invoice-key-1"),
  ).resolves.toBe(success);

  expect(http.post).toHaveBeenCalledTimes(3);

  for (const call of http.post.mock.calls) {
    expect(call[0]).toBe("/v2/invoices");
    expect(call[1]).toBe(input);
    expect(call[2]).toEqual({
      headers: { "Idempotency-Key": "invoice-key-1" },
    });
  }
});
```

### `requestWithRetry`

既存テストに以下を追加します。

- POST＋`retryableStatuses: [429]` は429だけ再試行する。
- POST＋`retryTimeouts: false` はタイムアウトを再試行しない。
- GET/PUT/DELETEについて、既定の `[429, 503]`、タイムアウト、最大試行回数が従来どおりである。
- 既存のバックオフ、`Retry-After`、ログ内容のテストが変更なしで通る。

### `PaymentClient.capture`

回帰テストとして、HTTPクライアントが429を返しても `post` が1回しか呼ばれないことを確認します。

## 仮定

- `maxAttempts: 3` は「初回を含む合計3試行」を意味すると仮定しています。
- `HttpClient` または `retryLoop` が、HTTPステータスをレスポンスとして返すのか例外として投げるのかは提示されていません。既存の判定方式に合わせます。
- 「非空」は `""` の禁止と解釈しています。空白だけのキーも禁止するなら、検査を `idempotencyKey.trim().length === 0` にします。
- `HttpClient.post` が渡されたbodyを破壊的に変更しないことを仮定しています。
- 実ファイルが作業ディレクトリになく読み取り専用だったため、これは提示コードに基づく実装案です。`retryLoop` の実際の型とタイムアウト判定を確認後、`retryTimeouts` 追加の要否を確定する必要があります。
