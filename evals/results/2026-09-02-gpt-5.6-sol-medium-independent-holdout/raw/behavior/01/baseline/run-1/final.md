推奨案は、`requestWithRetry` に POST を無条件追加せず、「POST・429のみ・最大3試行」を型で明示的に許可し、`createDraft` だけがその経路を使う形です。

### 実装案

`packages/http/retry.ts`

```ts
type RetryableMethod = "GET" | "PUT" | "DELETE";

type RetryRequestBase<T> = {
  send: () => Promise<HttpResponse<T>>;
};

type ExistingRetryRequest<T> = RetryRequestBase<T> & {
  method: RetryableMethod;
  retryableStatuses?: readonly number[];
  maxAttempts?: number;
};

type ExplicitPostRetryRequest<T> = RetryRequestBase<T> & {
  method: "POST";
  retryableStatuses: readonly [429];
  maxAttempts?: 3;
};

export type RetryRequest<T> =
  | ExistingRetryRequest<T>
  | ExplicitPostRetryRequest<T>;

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
    retryTimeouts: method !== "POST",
    send,
  });
}
```

`retryLoop` が現在 `method` だけから通信タイムアウトの再試行可否を判断している場合は、内部の入力型に次を追加します。

```ts
retryTimeouts: boolean;
```

タイムアウト判定だけを以下のようにします。

```ts
if (isCommunicationTimeout(error) && !retryTimeouts) {
  throw error;
}
```

バックオフ、`Retry-After`、ログ、ステータス判定、試行回数の処理には触れません。

`ExplicitPostRetryRequest` によって、POSTでは以下が型として必須になります。

- `retryableStatuses` は `[429]`
- `maxAttempts` は省略または `3`
- 既存のデフォルト `[429, 503]` をPOSTへ誤適用できない

`packages/billing/invoice-client.ts`

```ts
import { requestWithRetry } from "../http/retry";

export class InvoiceClient {
  constructor(private readonly http: HttpClient) {}

  createDraft(input: CreateDraftInput, idempotencyKey: string) {
    if (idempotencyKey.length === 0) {
      throw new TypeError("idempotencyKey must not be empty");
    }

    const requestOptions = {
      headers: { "Idempotency-Key": idempotencyKey },
    } as const;

    return requestWithRetry({
      method: "POST",
      retryableStatuses: [429],
      maxAttempts: 3,
      send: () =>
        this.http.post("/v2/invoices", input, requestOptions),
    });
  }
}
```

`input` と `requestOptions` を一度だけ確定し、全試行の `send` が同じ値を参照します。`maxAttempts: 3` は「初回を含む最大3試行」であり、「3回再試行」ではありません。

`packages/payments/payment-client.ts` は変更しません。

```text
InvoiceClient.createDraft
  → 非空キー検証
  → requestWithRetry（POST / 429 / 最大3試行）
  → retryLoop
  → InvoiceClientが渡したsend
  → HttpClient.post

PaymentClient.capture
  → HttpClient.post（1回だけ）
```

HTTPクライアント全体へPOST再試行を設定しないため、`capture` を含む既存POSTは引き続き再試行されません。

### 必要なテスト

`requestWithRetry` のテスト：

- POSTで `429 → 成功` の場合、2回呼び出す。
- POSTで429が続く場合、合計3回で終了する。
- POSTで503の場合、1回で終了する。
- POSTで500など別の5xxの場合、1回で終了する。
- POSTで通信タイムアウトの場合、1回で終了する。
- GET/PUT/DELETEの既存テストがすべて変更なしで通る。
- POSTの型テストがあるなら、`[429, 503]`、`[503]`、`maxAttempts: 4` がコンパイルエラーになることを確認する。

`InvoiceClient.createDraft` のテスト：

- `429 → 429 → 成功` で `http.post` が3回呼ばれる。
- 全呼び出しのURLが `/v2/invoices` である。
- 全呼び出しで同じ `input` オブジェクトが渡される。
- 全呼び出しで同じ非空の `Idempotency-Key` が渡される。
- 429が3回続いても4回目を呼ばない。
- 503、その他の5xx、通信タイムアウトは各1回で終了する。
- 空文字列のキーでは、通信を始める前に例外になり、`http.post` が呼ばれない。

`PaymentClient.capture` の回帰テスト：

- 429または通信タイムアウトでも `http.post` が1回だけ呼ばれる。

バックオフを伴うテストでは fake timer を使い、実時間を待たせません。既存のバックオフ、`Retry-After`、ログの詳細テストは変更せず、そのまま回帰確認します。

### 仮定

- `retryLoop` に「タイムアウトを再試行するか」を渡せる、または同等の小さな内部変更が可能と仮定しています。
- `HttpClient.post` と呼び出し元は、試行中に `input` や `requestOptions` を変更しないと仮定しています。完全に同一のシリアライズ結果を保証する必要がある場合は、入力型に合わせたスナップショット方法を別途決める必要があります。
- 空白だけのキーは「非空」です。空白も禁止する仕様なら `trim().length === 0` に変更します。
- 既存プロジェクトに入力検証用の例外型がある場合は、`TypeError` ではなくその型を使います。

なお、`referytale` の事前対応表は読み取り専用環境のため保存できず、永続ファイルを作らない形で設計を整理しました。
