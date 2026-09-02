推奨案は、`requestWithRetry` に POST を無条件追加せず、「POST の場合は再試行ステータスの明示を必須」にする形です。`InvoiceClient.createDraft` だけが `429`・合計3試行を指定し、`capture` は引き続き `http.post` を直接呼びます。

なお、作業ディレクトリに実ファイルがなく読み取り専用だったため、以下は提示コードに基づく実装案です。

## 変更する型

`GET/PUT/DELETE` の既存契約はそのまま残し、POST だけ明示的な指定を要求する discriminated union にします。

```ts
type RetryableMethod = "GET" | "PUT" | "DELETE";

type RetryRequestBase<T> = {
  maxAttempts?: number;
  send: () => Promise<HttpResponse<T>>;
};

type ExistingRetryRequest<T> = RetryRequestBase<T> & {
  method: RetryableMethod;
  retryableStatuses?: readonly number[];
};

type ExplicitPostRetryRequest<T> = RetryRequestBase<T> & {
  method: "POST";

  // POSTではデフォルト値を利用させない。
  retryableStatuses: readonly number[];
};

export type RetryRequest<T> =
  | ExistingRetryRequest<T>
  | ExplicitPostRetryRequest<T>;
```

これにより、既存コードは変更不要です。

```ts
requestWithRetry({
  method: "GET",
  send,
});
```

一方、POST では以下が型エラーになります。

```ts
requestWithRetry({
  method: "POST",
  send,
});
```

POST の再試行条件を明示しない限り利用できないため、既存の `[429, 503]` が誤ってPOSTに適用されません。

## `requestWithRetry`の変更

バックオフ、`Retry-After`、ログ、デフォルト値は変更しません。

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
    send,
  });
}
```

内部の `retryLoop` が `method` を `RetryableMethod` に限定している場合は、受け付ける型だけを次のように広げます。

```ts
type RetryMethod = RetryableMethod | "POST";
```

重要なのは、通信タイムアウトの判定を広げないことです。例えば現在の判定がメソッドの集合に依存しているなら、POST をその集合へ追加しません。

```ts
const retriesCommunicationTimeout =
  method === "GET" || method === "PUT" || method === "DELETE";
```

ステータスによる再試行と通信タイムアウトによる再試行を別々に判定します。これにより、POST は明示されたHTTPステータスだけが対象になります。

## `InvoiceClient.createDraft`の変更

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
      send: () =>
        this.http.post("/v2/invoices", input, {
          headers: {
            "Idempotency-Key": idempotencyKey,
          },
        }),
    });
  }
}
```

`input` と `idempotencyKey` をクロージャで保持するため、すべての試行で同じ body オブジェクトと同じキー値が渡されます。`maxAttempts: 3` は「初回を含めて最大3回」であり、「初回＋3回再試行」ではありません。

## `PaymentClient`は変更しない

```ts
capture(input: CaptureInput) {
  return this.http.post("/v1/captures", input);
}
```

呼び出し関係は次のようになります。

```text
InvoiceClient.createDraft
  → requestWithRetry（POST、429、最大3試行を明示）
    → retryLoop
      → InvoiceClient が渡した send
        → http.post("/v2/invoices", ...)

PaymentClient.capture
  → http.post("/v1/captures", ...)
```

`capture` は `requestWithRetry` を経由しないため、429を含むすべての失敗で自動再試行されません。

## 必要なテスト

### `requestWithRetry`のテスト

既存の再試行テストへ追加します。

- POSTで429を返した後に成功した場合、成功まで再試行する。
- POSTで503を返した場合、`retryableStatuses: [429]` なら1回で終了する。
- POSTで通信タイムアウトが発生した場合、1回で終了する。
- POSTで429が続いた場合、合計3回で終了する。
- GET/PUT/DELETEの429、503、通信タイムアウトに関する既存テストがそのまま通る。
- fake timerを使う場合、既存のバックオフ時間と `Retry-After` のテストを変更せず、終了時に `jest.useRealTimers()` を実行する。

また、型検査によって次を保証します。

```ts
// @ts-expect-error POSTにはretryableStatusesが必須
requestWithRetry({
  method: "POST",
  send,
});
```

### `InvoiceClient.createDraft`のテスト

最低限、次のケースが必要です。

1. 最初から成功する

   - `http.post` は1回。
   - URL、body、`Idempotency-Key` が正しい。

2. 429が2回続いた後に成功する

   - `http.post` は3回。
   - 3回とも同じ `input` オブジェクトを渡す。
   - 3回とも同じ非空の `Idempotency-Key` 値を渡す。
   - 3回目のレスポンスを返す。

3. 429が続く

   - `http.post` は合計3回。
   - 3回目の429を呼び出し元へ返す、または投げる。

4. 503を返す

   - `http.post` は1回だけ。
   - 503をそのまま呼び出し元へ伝える。

5. 429以外の5xxを返す

   - 代表例として500を使用。
   - `http.post` は1回だけ。

6. 通信タイムアウトになる

   - `http.post` は1回だけ。
   - タイムアウトをそのまま呼び出し元へ伝える。

7. 空の冪等性キーを渡す

   - `TypeError`になる。
   - `http.post` は呼ばれない。

### `PaymentClient.capture`の回帰テスト

- `http.post` が429を返しても呼び出しは1回だけ。
- 通信タイムアウトでも呼び出しは1回だけ。
- `requestWithRetry` を経由しないことは実装詳細なので、直接のスパイより `http.post` の呼び出し回数で検証する。

## 仮定

- `HttpClient`／`retryLoop` がHTTPエラーをレスポンスとして返すか例外として投げるかは入力から判断できません。テストのモック方法は既存のエラー表現に合わせる必要があります。
- 「同じrequest body」は、各試行で同じ `input` オブジェクトを `HttpClient` に渡すことを意味すると仮定しています。バイト単位で同一のシリアライズ結果が必要なら、`HttpClient` のシリアライズ時点と入力オブジェクトの変更可能性を追加確認する必要があります。
- 「非空」は `""` を拒否する意味としています。空白だけのキーも拒否するなら `idempotencyKey.trim().length === 0` にします。
- 既存の `retryLoop` がPOSTの通信タイムアウトを暗黙に再試行しないことを、実装確認とテストで保証する必要があります。
