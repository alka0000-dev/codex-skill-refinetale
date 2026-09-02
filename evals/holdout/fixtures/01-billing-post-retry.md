# 01: Limited retry for invoice draft creation

## Purpose

既存の再試行機構を保ったまま、冪等性が保証された1つのPOSTだけを安全にopt-inできるか確認する。

## Input

次のコードベースに、請求書の下書き作成が429を返した場合だけ自動再試行する変更を加えたいです。既存の挙動を壊さず、変更範囲を小さくしてください。変更する型・関数・呼び出し関係が分かる実装案と、必要なテストを示してください。入力にない前提が必要なら、仮定として分けてください。

`packages/http/retry.ts`:

```ts
type RetryableMethod = "GET" | "PUT" | "DELETE";

export type RetryRequest<T> = {
  method: RetryableMethod;
  retryableStatuses?: readonly number[];
  maxAttempts?: number;
  send: () => Promise<HttpResponse<T>>;
};

export async function requestWithRetry<T>({
  method,
  retryableStatuses = [429, 503],
  maxAttempts = 3,
  send,
}: RetryRequest<T>): Promise<HttpResponse<T>> {
  // 指数バックオフ、Retry-After、試行回数のログはここだけで扱う。
  // GET/PUT/DELETE の通信タイムアウトも再試行対象。
  return retryLoop({ method, retryableStatuses, maxAttempts, send });
}
```

`packages/billing/invoice-client.ts`:

```ts
export class InvoiceClient {
  constructor(private readonly http: HttpClient) {}

  createDraft(input: CreateDraftInput, idempotencyKey: string) {
    return this.http.post("/v2/invoices", input, {
      headers: { "Idempotency-Key": idempotencyKey },
    });
  }
}
```

`packages/payments/payment-client.ts`:

```ts
export class PaymentClient {
  constructor(private readonly http: HttpClient) {}

  // ベンダー側が冪等性キーを受け付けないため、自動再試行は禁止。
  capture(input: CaptureInput) {
    return this.http.post("/v1/captures", input);
  }
}
```

既存契約と新要件:

- `requestWithRetry`のバックオフ、`Retry-After`対応、ログ形式は変更しない。
- `createDraft`は429のみ最大3回まで試行する。503、その他の5xx、通信タイムアウトは再試行しない。
- 全試行で、呼び出し元から渡された同じ非空の`idempotencyKey`と同じrequest bodyを使う。
- `capture`を含む、ほかのPOSTは今後も自動再試行してはならない。
- 既存のGET/PUT/DELETEの再試行条件は変えない。

## Pass conditions

- **S1 Common mechanism:** 既存のバックオフ、`Retry-After`、ログを利用する単一の再試行経路に変更を収め、`InvoiceClient`内に別ループを作らない。
- **S2 POST opt-in:** POSTの再試行を明示的なopt-inとし、有効な冪等性キーを持つ`createDraft`だけに限定する。一般のPOSTを再試行可能にしない。
- **S3 Exact conditions:** 429だけを最大3回試行し、503、その他の5xx、timeoutは再試行しない。既存メソッドの条件を維持する。
- **S4 Idempotency:** 同じkeyとbodyを各試行で再利用し、非空keyの型または実行時検査を具体化する。
- **S5 Verification:** 429後の成功、上限到達、429以外、timeout、同一key/body、`capture`非再試行、既存メソッド回帰の期待結果を示す。

## Critical failure conditions

- `capture`など冪等性保証のないPOSTが再試行され得る。
- 試行ごとに新しい冪等性キーを生成する。
- `createDraft`のtimeoutまたは5xxを要件に反して再試行する。

## Scoring

S1〜S5を各0〜2点で採点する。2点は実装可能な具体性と観測可能な期待結果を満たす、1点は方向は妥当だが一部が曖昧、0点は欠落・矛盾・重複経路がある。8〜10点かつ0点なしをPass、6〜7点または8点以上でも0点ありをBorderline、0〜5点をFailとする。critical failureを最優先し、特定の識別子名との一致は要求しない。
