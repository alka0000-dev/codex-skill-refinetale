最小変更なら、`RetryableMethod` に単純に `"POST"` を追加せず、請求書下書き専用の分岐だけを `requestWithRetry` に追加するのが安全です。これにより、既存のGET/PUT/DELETEと `capture` には影響しません。

## 実装案

### 1. `packages/http/retry.ts`

既存のリクエスト型を、従来のメソッドと請求書下書きPOSTの判別可能なunionにします。

```ts
type RetryableMethod = "GET" | "PUT" | "DELETE";

type StandardRetryRequest<T> = {
  method: RetryableMethod;
  retryableStatuses?: readonly number[];
  maxAttempts?: number;
  send: () => Promise<HttpResponse<T>>;
};

type InvoiceDraftRetryRequest<T> = {
  method: "POST";
  retryPolicy: "invoice-draft-429-only";
  retryableStatuses?: never;
  maxAttempts?: never;
  send: () => Promise<HttpResponse<T>>;
};

export type RetryRequest<T> =
  | StandardRetryRequest<T>
  | InvoiceDraftRetryRequest<T>;
```

POST側では再試行条件を呼び出し元から変更できないようにします。

```ts
export async function requestWithRetry<T>(
  request: RetryRequest<T>,
): Promise<HttpResponse<T>> {
  if (request.method === "POST") {
    return retryLoop({
      method: request.method,
      retryableStatuses: [429],
      maxAttempts: 3,
      retryTimeouts: false,
      send: request.send,
    });
  }

  const {
    method,
    retryableStatuses = [429, 503],
    maxAttempts = 3,
    send,
  } = request;

  return retryLoop({
    method,
    retryableStatuses,
    maxAttempts,
    retryTimeouts: true,
    send,
  });
}
```

`retryLoop` の内部引数に、通信タイムアウトを再試行対象とするかを明示するフラグを追加します。

```ts
type RetryLoopRequest<T> = {
  method: RetryableMethod | "POST";
  retryableStatuses: readonly number[];
  maxAttempts: number;
  retryTimeouts: boolean;
  send: () => Promise<HttpResponse<T>>;
};
```

タイムアウトを判定している既存箇所だけを、次の条件に変更します。

```ts
if (isTimeout(error) && !retryTimeouts) {
  throw error;
}
```

バックオフ計算、`Retry-After`、ログ出力、試行回数の扱いには手を加えません。

重要なのは、`RetryableMethod` 自体に `"POST"` を追加しないことです。追加すると、POSTが既存のデフォルト値 `[429, 503]` やタイムアウト再試行へ誤って入る余地ができます。

### 2. `packages/billing/invoice-client.ts`

同じbodyと同じヘッダー値をクロージャーで全試行に渡します。

```ts
import { requestWithRetry } from "../http/retry";

export class InvoiceClient {
  constructor(private readonly http: HttpClient) {}

  async createDraft(input: CreateDraftInput, idempotencyKey: string) {
    if (idempotencyKey.length === 0) {
      throw new TypeError("idempotencyKey must not be empty");
    }

    const requestBody = input;
    const requestOptions = {
      headers: { "Idempotency-Key": idempotencyKey },
    };

    return requestWithRetry({
      method: "POST",
      retryPolicy: "invoice-draft-429-only",
      send: () =>
        this.http.post("/v2/invoices", requestBody, requestOptions),
    });
  }
}
```

`async` にすることで、空文字の場合も同期例外ではなくPromiseのrejectとして扱えます。

### 3. `packages/payments/payment-client.ts`

変更しません。

```ts
capture(input: CaptureInput) {
  return this.http.post("/v1/captures", input);
}
```

呼び出し関係は次のとおりです。

```text
InvoiceClient.createDraft
  → requestWithRetry（invoice-draft-429-only）
    → retryLoop（429、最大3試行、タイムアウト対象外）
      → HttpClient.post

PaymentClient.capture
  → HttpClient.post（再試行なし）
```

## 必要なテスト

### `packages/http/retry.test.ts`

新しいPOST分岐：

- 1回目が429、2回目が成功なら2回呼ばれる。
- 3回とも429なら、合計3回で終了する。
- 503は1回で終了し、再試行しない。
- 500などほかの5xxも再試行しない。
- 通信タイムアウトは再試行せず、1回目のエラーを返す。
- 429の再試行時も、既存のバックオフと`Retry-After`処理を通る。
- `requestWithRetry({ method: "POST", ... })` は、専用の `retryPolicy` がなければ型エラーになる。
- POSTでは `retryableStatuses` や `maxAttempts` を指定できないことを型テストで確認する。

既存契約の回帰テスト：

- GET/PUT/DELETEではデフォルトの429、503が引き続き再試行される。
- GET/PUT/DELETEでは通信タイムアウトが引き続き再試行される。
-既存の最大試行回数、ログ、`Retry-After`のテストがそのまま通る。

### `packages/billing/invoice-client.test.ts`

- 429、429、成功の場合、`http.post` が合計3回呼ばれる。
- 全呼び出しのURLが `/v2/invoices`。
- 各試行のbodyが同じオブジェクトであることを `toBe(input)` で確認する。
- 各試行の `Idempotency-Key` が呼び出し元の値と同じ。
- 503、500、タイムアウトでは `http.post` が1回だけ呼ばれる。
- 空の `idempotencyKey` はHTTP通信前にrejectされる。
- 1回目で成功した場合は1回だけ呼ばれる。

### `packages/payments/payment-client.test.ts`

- 429が返っても `http.post` は1回だけ。
- タイムアウトでも `http.post` は1回だけ。
- 元のレスポンスまたはエラーがそのまま呼び出し元へ返る。

## 仮定

- 「最大3回」は、初回を含む合計3試行を意味します。
- `HttpClient.post` の429が `HttpResponse` として解決されるか、既存の `retryLoop` が認識できるHTTPエラーとしてrejectされるものとします。後者の場合は、既存のステータス抽出方法をそのまま使います。
- 「非空」は `idempotencyKey.length > 0` を意味します。空白だけの文字列も禁止するなら、判定を `idempotencyKey.trim().length === 0` に変更します。
- `HttpClient` が送信時にrequest bodyを破壊的に変更しないことを前提とします。
- `referytale` の手順に沿って対象と呼び出し順を先に整理しましたが、必須の対応表ファイルは読み取り専用環境のため作成できませんでした。
