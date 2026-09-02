提示された範囲では、`RetryableMethod` に `"POST"` を追加せず、冪等性キー付きPOST専用の狭い入口を `retry.ts` に追加する案が最小かつ安全です。

## 変更契約

変更する挙動:

- `InvoiceClient.createDraft` は429だけ再試行する。
- 初回を含め最大3試行とする。
- 全試行で同じ `input` と非空の `idempotencyKey` を使う。

変更しない挙動:

- 503、その他の5xx、通信タイムアウトでは再試行しない。
- `capture` を含む通常のPOSTは直接 `HttpClient.post` を呼ぶ。
- `RetryableMethod`、`RetryRequest`、`requestWithRetry` の公開契約は変えない。
- GET/PUT/DELETEの対象ステータス、タイムアウト再試行、待機、`Retry-After`、ログ形式は変えない。

## 実装案

`packages/http/retry.ts` に、通常の再試行APIとは分離した入口を追加します。

```ts
type RetryableMethod = "GET" | "PUT" | "DELETE";
type RetryLoopMethod = RetryableMethod | "POST";

export type RetryRequest<T> = {
  method: RetryableMethod;
  retryableStatuses?: readonly number[];
  maxAttempts?: number;
  send: () => Promise<HttpResponse<T>>;
};

type IdempotentPostRetryRequest<TBody, TResponse> = {
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
  return retryLoop({
    method,
    retryableStatuses,
    maxAttempts,
    retryTransportErrors: true,
    send,
  });
}

export async function requestIdempotentPostWithRetry<TBody, TResponse>({
  body,
  idempotencyKey,
  send,
}: IdempotentPostRetryRequest<TBody, TResponse>): Promise<HttpResponse<TResponse>> {
  if (idempotencyKey.length === 0) {
    throw new TypeError("idempotencyKey must not be empty");
  }

  return retryLoop({
    method: "POST",
    retryableStatuses: [429],
    maxAttempts: 3,
    retryTransportErrors: false,
    send: () => send(body, idempotencyKey),
  });
}
```

`retryLoop` の内部入力型だけ、次のように拡張します。

```ts
type RetryLoopRequest<T> = {
  method: RetryLoopMethod;
  retryableStatuses: readonly number[];
  maxAttempts: number;
  retryTransportErrors: boolean;
  send: () => Promise<HttpResponse<T>>;
};
```

`retryTransportErrors` は公開設定にしません。

- `requestWithRetry` は常に `true`
- 冪等性キー付きPOST専用入口は常に `false`

通信エラーを捕捉する既存箇所だけでこの値を判定し、レスポンスステータスの判定、バックオフ、`Retry-After`、ログ処理には手を入れません。

`InvoiceClient` は次のように変更します。

```ts
export class InvoiceClient {
  constructor(private readonly http: HttpClient) {}

  createDraft(input: CreateDraftInput, idempotencyKey: string) {
    return requestIdempotentPostWithRetry({
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

呼び出し関係は以下になります。

```text
InvoiceClient.createDraft
  → requestIdempotentPostWithRetry
    → retryLoop
      → HttpClient.post

requestWithRetry（GET/PUT/DELETE）
  → retryLoop

PaymentClient.capture
  → HttpClient.post
```

`PaymentClient.capture` は変更しません。`HttpClient.post` 自体にも再試行設定を追加しません。

## 必要なテスト

| 契約 | 入力・経路 | 期待結果 |
|---|---|---|
| 429を再試行 | 429 → 成功 | POSTが2回、2回目の結果を返す |
| 最大3試行 | 429 → 429 → 429 | POSTは3回だけ、最後の429を既存形式で返す／送出する |
| 同じbodyとキー | 429 → 429 → 成功 | 全3回で同一の`input`参照、同一キー、同一路径 |
| 503を除外 | 503 | POSTは1回 |
| その他5xxを除外 | 500 | POSTは1回 |
| タイムアウトを除外 | `http.post`がreject | POSTは1回、同じエラーを送出 |
| 通常成功 | 初回成功 | POSTは1回 |
| 空キーを除外 | `idempotencyKey === ""` | HTTP通信なし、Promiseがreject |
| 他のPOSTを維持 | `capture`が429 | `capture`のPOSTは1回 |
| GET/PUT/DELETEを維持 | 既存の429、503、タイムアウトテスト | 従来と同じ回数・結果 |
| 待機等を維持 | 既存のバックオフ、`Retry-After`、ログテスト | 既存期待値がすべて成功 |

429のテストでbody・キー・試行上限をまとめて確認できます。503、500、タイムアウトは失敗経路が異なるため個別テストが必要です。

## 仮定

- 「最大3回」は、再試行3回ではなく初回を含む合計3試行です。
- 「同じrequest body」は、各試行で同じ `input` オブジェクトを `HttpClient.post` に渡すことを意味します。送信後に呼び出し元やHTTP実装がオブジェクトを変更しない前提です。
- 「非空」は `idempotencyKey.length > 0` を意味し、空白だけの文字列を拒否する要件ではありません。
- `retryLoop` が現在どのように通信エラーを分類しているかは未提示です。既にメソッド別判定がある場合、`retryTransportErrors` の追加は不要で、その既存判定でPOSTを除外します。

作業ツリーには実コードやテストが存在しなかったため、変更およびテスト実行は行っていません。
