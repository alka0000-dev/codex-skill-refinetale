実装方針は、`requestWithRetry` にPOSTを無条件で許可せず、「429のみ・総試行回数3回」という組み合わせだけ型で許可し、`createDraft` からその経路を使う形が安全です。`capture` は変更しません。

なお、作業ディレクトリには提示されたコード自体がなく、`.git` 以外は空でした。そのため、以下は提示コードを根拠にした実装案です。また、読み取り専用環境のため `referytale` スキルが要求する対応表ファイルと `.agent/CONTINUITY.md` は作成できませんでした。

## 変更する型

`POST`を単純に`RetryableMethod`へ追加すると、他のPOSTまで既定値の429/503や通信タイムアウトで再試行できてしまう恐れがあります。判別可能なunionで制約します。

```ts
type RetryableMethod = "GET" | "PUT" | "DELETE";

type RetrySend<T> = {
  send: () => Promise<HttpResponse<T>>;
};

type DefaultRetryRequest<T> = RetrySend<T> & {
  method: RetryableMethod;
  retryableStatuses?: readonly number[];
  maxAttempts?: number;
};

type Post429RetryRequest<T> = RetrySend<T> & {
  method: "POST";

  // POSTに許可する設定を型レベルで限定する。
  retryableStatuses: readonly [429];
  maxAttempts: 3;
};

export type RetryRequest<T> =
  | DefaultRetryRequest<T>
  | Post429RetryRequest<T>;
```

これにより、以下は型エラーになります。

```ts
requestWithRetry({
  method: "POST",
  send,
});

requestWithRetry({
  method: "POST",
  retryableStatuses: [503],
  maxAttempts: 3,
  send,
});

requestWithRetry({
  method: "POST",
  retryableStatuses: [429],
  maxAttempts: 4,
  send,
});
```

## `requestWithRetry`の変更

unionを判別して既定値を解決します。`retryLoop`によるバックオフ、`Retry-After`、ログはそのまま使います。

```ts
export async function requestWithRetry<T>(
  request: RetryRequest<T>,
): Promise<HttpResponse<T>> {
  const retryableStatuses =
    request.method === "POST"
      ? request.retryableStatuses
      : request.retryableStatuses ?? [429, 503];

  const maxAttempts =
    request.method === "POST"
      ? request.maxAttempts
      : request.maxAttempts ?? 3;

  return retryLoop({
    method: request.method,
    retryableStatuses,
    maxAttempts,
    send: request.send,
  });
}
```

`retryLoop`側では、通信タイムアウトの判定を必ず次の条件に保ちます。

```ts
const retriesTimeout =
  method === "GET" ||
  method === "PUT" ||
  method === "DELETE";
```

既存実装が「`RetryableMethod`として渡された全メソッドのタイムアウトを再試行する」という判定なら、POST追加に伴い、この明示的な判定へ変更する必要があります。

## `createDraft`の変更

body、キー、リクエストオプションを呼び出しごとに一度だけ確定し、全試行で同じ値をキャプチャします。

```ts
import { requestWithRetry } from "../http/retry";

export class InvoiceClient {
  constructor(private readonly http: HttpClient) {}

  createDraft(input: CreateDraftInput, idempotencyKey: string) {
    const requestOptions = {
      headers: {
        "Idempotency-Key": idempotencyKey,
      },
    };

    return requestWithRetry({
      method: "POST",
      retryableStatuses: [429],
      maxAttempts: 3,
      send: () =>
        this.http.post(
          "/v2/invoices",
          input,
          requestOptions,
        ),
    });
  }
}
```

呼び出し関係は次のようになります。

```text
InvoiceClient.createDraft
  └─ requestWithRetry
       └─ retryLoop
            └─ send
                 └─ HttpClient.post("/v2/invoices", input, requestOptions)

PaymentClient.capture
  └─ HttpClient.post("/v1/captures", input)
```

`capture`は`requestWithRetry`を経由しないため、変更不要です。

## 必要なテスト

### `requestWithRetry`

- POSTが429を返した後に成功した場合、成功するまで再試行する。
- POSTが429を返し続けた場合、総試行回数が3回で終了する。
- POSTの503、その他の5xxでは1回しか送信しない。
- POSTの通信タイムアウトでは1回しか送信しない。
- GET/PUT/DELETEの既存既定値が429、503のままである。
- GET/PUT/DELETEの通信タイムアウトが引き続き再試行される。
- 既存のバックオフ、`Retry-After`、試行ログのテストが変更なしで通る。
- `@ts-expect-error`による型テストで、POSTの503、既定値省略、4回試行を拒否する。

### `InvoiceClient.createDraft`

- `429 → 成功`で`http.post`が2回呼ばれる。
- `429 → 429 → 成功`で3回呼ばれる。
- 429が継続しても3回を超えない。
- 503、500、通信タイムアウトでは1回だけ呼ばれる。
- 全試行で次が同一である。

```ts
expect(http.post.mock.calls[0][1]).toBe(input);
expect(http.post.mock.calls[1][1]).toBe(input);

expect(http.post.mock.calls[0][2]).toBe(
  http.post.mock.calls[1][2],
);

expect(http.post.mock.calls[0][2].headers["Idempotency-Key"])
  .toBe(idempotencyKey);
```

### `PaymentClient.capture`

429を返すモックを使用し、`http.post`が1回だけ呼ばれることを回帰テストにします。

## 仮定

- `maxAttempts: 3`は「初回を含む総試行回数3回」を意味します。
- `retryLoop`はステータスコードと通信タイムアウトを区別できます。
- 呼び出し元が非空の`idempotencyKey`を保証します。既存挙動を壊さないため、この変更では空文字の新しい実行時検証を追加しません。
- `HttpClient.post`は渡されたbodyやoptionsを破壊的に変更しません。変更する可能性がある場合は、HTTPクライアント側の契約確認が必要です。
