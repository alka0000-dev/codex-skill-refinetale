実装案は、`requestWithRetry` に「明示的に制限された POST」を追加し、`InvoiceClient.createDraft` だけをその経路へ接続する形です。`capture` や既存の GET/PUT/DELETE の経路は変更しません。

なお、作業ディレクトリには提示されたコードやテストが存在しなかったため、以下は提示内容に基づく具体案です。テスト実行はしていません。

## 変更契約

変更する挙動:

- `createDraft` が429を受けた場合だけ、合計最大3回試行する。
- 再試行でも同じ `input` と `idempotencyKey` を使用する。

変更しない挙動:

- `createDraft` の503、その他の5xx、通信タイムアウトは1回で終了する。
- `capture` を含む他のPOSTは再試行しない。
- GET/PUT/DELETEのステータス・タイムアウト再試行条件は維持する。
- バックオフ、`Retry-After`、ログ、試行回数管理は引き続き `retryLoop` が所有する。

## 型と関数の変更

POSTに既存の省略時設定 `[429, 503]` を適用できてしまわないよう、`RetryRequest` を判別可能なunionにします。

```ts
type TimeoutRetryableMethod = "GET" | "PUT" | "DELETE";

type RetryPolicy =
  | {
      method: TimeoutRetryableMethod;
      retryableStatuses?: readonly number[];
      maxAttempts?: number;
    }
  | {
      method: "POST";
      retryableStatuses: readonly [429];
      maxAttempts: 3;
    };

export type RetryRequest<T> = RetryPolicy & {
  send: () => Promise<HttpResponse<T>>;
};

export async function requestWithRetry<T>({
  method,
  retryableStatuses = [429, 503],
  maxAttempts = 3,
  send,
}: RetryRequest<T>): Promise<HttpResponse<T>> {
  return retryLoop({ method, retryableStatuses, maxAttempts, send });
}
```

これによりPOSTでは、呼び出し側が次を明示しない限り型チェックを通りません。

```ts
{
  method: "POST",
  retryableStatuses: [429],
  maxAttempts: 3,
}
```

単純に既存の `RetryableMethod` へ `"POST"` を足すだけの案は避けます。その場合、POSTが省略時設定によって503も再試行でき、さらに `retryLoop` の実装次第ではタイムアウトまで再試行対象になるためです。

`retryLoop` のメソッド型もPOSTを受け取れるようにする必要があります。ただし、タイムアウト判定は明示的に次の3種類だけに保ちます。

```ts
type RetryMethod = TimeoutRetryableMethod | "POST";
```

```ts
function isTimeoutRetryableMethod(
  method: RetryMethod,
): method is TimeoutRetryableMethod {
  return method === "GET" || method === "PUT" || method === "DELETE";
}
```

既存の `retryLoop` が「受理した全メソッドのタイムアウトを再試行する」実装なら、その判定箇所だけを上記へ置き換えます。バックオフ、レスポンスステータス判定、`Retry-After`、ログには触れません。

## `createDraft` の変更

```ts
import { requestWithRetry } from "../http/retry";

export class InvoiceClient {
  constructor(private readonly http: HttpClient) {}

  createDraft(input: CreateDraftInput, idempotencyKey: string) {
    return requestWithRetry({
      method: "POST",
      retryableStatuses: [429],
      maxAttempts: 3,
      send: () =>
        this.http.post("/v2/invoices", input, {
          headers: { "Idempotency-Key": idempotencyKey },
        }),
    });
  }
}
```

`input` と `idempotencyKey` を試行ごとに生成・変更せず、同じクロージャから参照します。

呼び出し関係は次のようになります。

```text
InvoiceClient.createDraft
  → requestWithRetry（POST・429・最大3回）
    → retryLoop
      → send
        → http.post（同じbody、同じIdempotency-Key）

PaymentClient.capture
  → http.post（従来どおり直接呼び出し）
```

## 必要なテスト

### `requestWithRetry` のテスト

1. POSTが `429 → 429 → 成功` の場合

   - `send` が3回呼ばれる。
   - 3回目のレスポンスを返す。

2. POSTが429を返し続ける場合

   - `send` は3回で止まる。
   - 3回目の429を既存契約どおり返す、または例外として伝播する。

3. POSTが503または代表的な他の5xxを返す場合

   - 各ケースとも `send` は1回だけ。
   - 結果をそのまま伝播する。

4. POSTが通信タイムアウトになる場合

   - `send` は1回だけ。
   - タイムアウトをそのまま伝播する。

5. GET/PUT/DELETEの既存回帰テスト

   - 各メソッドについて、既存の再試行対象ステータスが従来の回数だけ試行される。
   - 各メソッドについて、通信タイムアウトが従来どおり再試行される。
   - 既存のバックオフ、`Retry-After`、ログのテストを変更せず通す。

### `InvoiceClient` のテスト

`429 → 429 → 成功` を返す `HttpClient` mockを使い、3回すべてについて以下を確認します。

```ts
expect(http.post).toHaveBeenNthCalledWith(
  1,
  "/v2/invoices",
  input,
  { headers: { "Idempotency-Key": idempotencyKey } },
);
```

同じ確認を第2・第3呼び出しにも行います。可能なら値の一致だけでなく、bodyが同じ参照であることも確認します。

加えて、503とタイムアウトでは `http.post` が1回だけであることを確認します。

### `PaymentClient` の回帰テスト

429を返す `HttpClient` mockに対して:

- `capture` がエラーまたはレスポンスをそのまま伝播する。
- `http.post` が1回しか呼ばれない。

これは「他のPOSTは再試行しない」という安全境界を直接保証します。

## 仮定

- `retryLoop` はHTTPステータスと通信タイムアウトを区別できる既存実装になっている。
- `HttpClient.post` は試行のたびに渡されたbodyを書き換えない。
- 非空の `idempotencyKey` は呼び出し元ですでに保証されている。

最後の仮定が成立しない場合は、`createDraft` の冒頭で空文字列を通信前に拒否し、「空キーでは `http.post` が0回」というテストを追加する必要があります。ブランド型などの新しい型階層は、この要件だけのためには追加しません。
