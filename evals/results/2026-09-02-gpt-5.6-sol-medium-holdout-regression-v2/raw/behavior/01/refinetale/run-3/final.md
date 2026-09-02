提示された断片を正本にすると、`POST` を汎用の `RetryableMethod` に追加せず、請求書下書き専用の狭い入口から既存の `retryLoop` を使う案が最も安全です。

実リポジトリには対象コードやテストが存在しなかったため、以下は具体的な実装案と必要テストです。実行検証はしていません。

## 変更契約

変更する挙動:

- `InvoiceClient.createDraft` は429だけを再試行する。
- `maxAttempts = 3` は初回を含む最大3回。
- 空の `idempotencyKey` は送信前に拒否する。

変更しない挙動:

- GET/PUT/DELETEの再試行条件。
- `requestWithRetry` のデフォルト値。
- バックオフ、`Retry-After`、ログ形式。
- `capture` を含む他のPOST。429でも1回だけ送信する。
- 503、他の5xx、タイムアウト時の `createDraft` は再試行しない。

共通処理:

- 試行回数管理、待機、`Retry-After` 解釈、ログは引き続き `retryLoop` が所有する。

差分処理:

- 請求書下書きだけが、固定ポリシー「POST・429・最大3回・タイムアウト対象外」でループへ入る。

## 実装案

### `packages/http/retry.ts`

既存の公開型は変更しません。

```ts
type RetryableMethod = "GET" | "PUT" | "DELETE";

export type RetryRequest<T> = {
  method: RetryableMethod;
  retryableStatuses?: readonly number[];
  maxAttempts?: number;
  send: () => Promise<HttpResponse<T>>;
};
```

請求書下書き専用の狭い関数を追加します。可能ならHTTPパッケージの公開barrelからはexportせず、billingからの内部importだけにします。

```ts
export function requestInvoiceDraftWithRetry<T>(
  send: () => Promise<HttpResponse<T>>,
): Promise<HttpResponse<T>> {
  return retryLoop({
    method: "POST",
    retryableStatuses: [429],
    maxAttempts: 3,
    retryTimeouts: false,
    send,
  });
}
```

既存経路は明示的にタイムアウト再試行を維持します。

```ts
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
    retryTimeouts: true,
    send,
  });
}
```

`retryLoop` の内部入力型だけを次のように広げます。

```ts
type RetryLoopRequest<T> = {
  method: RetryableMethod | "POST";
  retryableStatuses: readonly number[];
  maxAttempts: number;
  retryTimeouts: boolean;
  send: () => Promise<HttpResponse<T>>;
};
```

タイムアウト処理では `retryTimeouts` が偽なら直ちに同じエラーを返します。ステータス応答に対するバックオフやログ処理は触りません。

なお、現在の `retryLoop` がすでに「POSTのタイムアウトを再試行しない」と保証できる構造なら、`retryTimeouts` の追加は不要です。その場合は内部のmethod型を広げるだけに留めます。

### `packages/billing/invoice-client.ts`

```ts
import { requestInvoiceDraftWithRetry } from "../http/retry";

export class InvoiceClient {
  constructor(private readonly http: HttpClient) {}

  createDraft(input: CreateDraftInput, idempotencyKey: string) {
    if (idempotencyKey.length === 0) {
      throw new TypeError("idempotencyKey must not be empty");
    }

    return requestInvoiceDraftWithRetry(() =>
      this.http.post("/v2/invoices", input, {
        headers: { "Idempotency-Key": idempotencyKey },
      }),
    );
  }
}
```

`input` と `idempotencyKey` は1つのクロージャが捕捉するため、各試行で別の値を生成しません。`NonEmptyString` のような新型は追加せず、既存呼び出し元への型変更の伝播を避けます。

### `packages/payments/payment-client.ts`

変更しません。

### 呼び出し関係

```text
InvoiceClient.createDraft
  ├─ 非空キーを検証
  └─ requestInvoiceDraftWithRetry
       └─ retryLoop
            └─ HttpClient.post（最大3回、429のみ）

PaymentClient.capture
  └─ HttpClient.post（常に1回）

requestWithRetry
  └─ retryLoop（既存GET/PUT/DELETE契約）
```

`RetryableMethod` に単純に `"POST"` を追加する案は採用しません。それを行うと、`capture` を含む任意のPOSTが汎用APIから再試行可能になり、安全境界が型として失われるためです。

## 必要なテスト

| 契約 | テスト | 期待結果 |
|---|---|---|
| `createDraft` は429を再試行 | 429、429、成功を返す | POSTが3回、最終成功を返す |
| 最大3回 | 429を連続して返す | POSTは3回だけ。3回目の応答を返す |
| 同じbodyとキー | 上記3回のPOST引数を記録 | 全回で同じ `input`、同じURL、同じヘッダー値 |
| 空キー禁止 | `idempotencyKey = ""` | 同期的に例外。POSTは0回 |
| 503対象外 | 最初に503 | POSTは1回、待機なし |
| その他5xx対象外 | 最初に500 | POSTは1回、待機なし |
| タイムアウト対象外 | POSTがtimeoutをreject | POSTは1回、同じエラーでreject、待機なし |
| `Retry-After`維持 | 429に`Retry-After`を付け、その後成功 | 既存ループと同じ待機時間・ログ形式 |
| 通常成功 | 最初に成功 | POSTは1回 |
| `capture`は対象外 | captureのPOSTが429を返す | POSTは1回だけ |
| GET/PUT/DELETE維持 | 既存retryテストをそのまま実行 | 429/503およびtimeoutの既存結果が不変 |

GET/PUT/DELETEについて既存テストが不足している場合だけ、3メソッドをパラメータ化した回帰テストを追加します。請求書テスト側でバックオフアルゴリズム全体を再テストする必要はなく、429が既存ループへ接続されていることを `Retry-After` の1ケースで確認すれば十分です。

## 仮定

- `HttpClient.post` と呼び出し元は、再試行中に `input` オブジェクトを変更しない。
- `HttpClient` は同じ入力から同じrequest bodyを生成する。
- 「非空」は長さが0でないことを意味し、空白だけのキーを拒否する要件ではない。
- 429などのHTTPステータスは `HttpResponse` として返り、通信タイムアウトだけがrejectされる。
- `retryLoop` にタイムアウト再試行を制御できる最小変更を加えられる。

呼び出し中の入力変更まで防ぐ必要がある場合は、`HttpClient` のシリアライズ境界でbodyを一度だけ固定する設計が必要です。`structuredClone` の追加は入力型の互換性を壊し得るため、現時点では含めません。
