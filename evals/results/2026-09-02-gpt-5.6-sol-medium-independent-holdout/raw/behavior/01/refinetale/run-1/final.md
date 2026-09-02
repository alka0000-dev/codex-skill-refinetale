提示コードを前提にすると、`requestWithRetry` を再利用しつつ、POST は明示設定された場合だけ通す設計が最小かつ安全です。`capture` などを一律リトライ対象にする変更は不要です。

## 変更契約

変更する挙動:

- `InvoiceClient.createDraft` は429だけを最大3回まで試行する。
- 全試行で同じ `input` と同じ `idempotencyKey` を使用する。
- 空の `idempotencyKey` は通信前に拒否する。

変更しない挙動:

- 503、その他の5xx、通信タイムアウトでは `createDraft` を再試行しない。
- `capture` を含むほかのPOSTは `requestWithRetry` を経由しない。
- GET/PUT/DELETEの既定ステータス、タイムアウト再試行、バックオフ、`Retry-After`、ログ形式は変更しない。

共通処理:

- 試行回数、待機、レスポンス判定、ログは引き続き `requestWithRetry` / `retryLoop` が所有する。

差分処理:

- 請求書クライアントだけが `POST + [429] + 3回` を指定する。
- 通信タイムアウトの再試行可否だけは、HTTP層がメソッドから判断する。

## 実装案

### `packages/http/retry.ts`

既存の自動再試行可能メソッドと、明示的に許可するPOSTを型で分離します。POSTでは `retryableStatuses` を必須にし、既定値 `[429, 503]` が暗黙適用されないようにします。

```ts
type RetryableMethod = "GET" | "PUT" | "DELETE";
type RetryMethod = RetryableMethod | "POST";

type RetryRequestBase<T> = {
  maxAttempts?: number;
  send: () => Promise<HttpResponse<T>>;
};

export type RetryRequest<T> = RetryRequestBase<T> &
  (
    | {
        method: RetryableMethod;
        retryableStatuses?: readonly number[];
      }
    | {
        method: "POST";
        retryableStatuses: readonly number[];
      }
  );

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

`retryLoop` の入力型には、内部専用のフラグを1つ追加します。

```ts
type RetryLoopRequest<T> = {
  method: RetryMethod;
  retryableStatuses: readonly number[];
  maxAttempts: number;
  retryTimeouts: boolean;
  send: () => Promise<HttpResponse<T>>;
};
```

通信例外を判定する既存箇所だけで `retryTimeouts` を使用します。

```ts
if (!retryTimeouts || !isCommunicationTimeout(error)) {
  throw error;
}
```

ステータス判定、指数バックオフ、`Retry-After`、ログ処理には手を入れません。

もし実際の `retryLoop` がすでにメソッドごとにタイムアウト可否を判定しているなら、`retryTimeouts` の追加は不要です。その場合は既存判定においてPOSTが対象外であることをテストで確認します。

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
      send: () =>
        this.http.post("/v2/invoices", input, {
          headers: { "Idempotency-Key": idempotencyKey },
        }),
    });
  }
}
```

`input` と `idempotencyKey` はコピーや更新をせず、同じクロージャから参照します。これにより全試行の本文とキーの正本はそれぞれ1つです。

### `packages/payments/payment-client.ts`

変更しません。

呼び出し関係は次のとおりです。

```text
InvoiceClient.createDraft
  └─ requestWithRetry
       └─ retryLoop
            └─ send
                 └─ HttpClient.post("/v2/invoices", 同じinput, 同じkey)

PaymentClient.capture
  └─ HttpClient.post("/v1/captures")  // retry経路に入らない
```

## 必要なテスト

`invoice-client` のテスト:

1. 429の後に成功する

   - POSTが2回呼ばれる。
   - 両試行のURL、本文、`Idempotency-Key` が同じ。
   - 可能なら本文は `toBe(input)` で同一参照も確認する。

2. 429が続く

   - 429を3回返す。
   - 合計3回で停止する。
   - 最後の429が既存契約どおり返却または送出される。
   - 3回すべてで同じ本文とキーを使う。

3. 非429レスポンス

   - 503、代表的なその他5xx（例: 500）をテーブルテストにする。
   - それぞれPOSTが1回だけ呼ばれる。

4. 通信タイムアウト

   - `HttpClient.post` が既存のタイムアウト例外を送出する。
   - POSTは1回だけで、同じ例外が呼び出し元へ送出される。

5. 空の冪等性キー

   - `createDraft(input, "")` が通信前に失敗する。
   - `HttpClient.post` は呼ばれない。

`payment-client` の回帰テスト:

6. `capture` が429を受けてもPOSTは1回だけ

   - `requestWithRetry` を経由させていないことを観測可能な振る舞いで固定する。

HTTP再試行層の回帰確認:

- 既存のGET/PUT/DELETEについて、429、503、通信タイムアウトの既存テストをそのまま実行する。
- バックオフ時間、`Retry-After`、試行ログの既存テスト結果が変わらないことを確認する。
- POSTで `retryableStatuses` を省略できないことは型チェックで確認する。

## 仮定・未確認事項

- 「非空」は長さ0の文字列だけを指すと仮定しています。空白だけの文字列も拒否するなら、`trim()` を使う仕様判断が必要です。
- `retryLoop` の実装が提示されていないため、タイムアウト判定箇所と最終429の返却・送出形式は未確認です。
- 実際の作業ツリーには提示ファイルやテスト設定が存在せず、読み取り専用でもあるため、実装・型チェック・テスト実行はできていません。上記6ケースと既存HTTP再試行テストの成功が完了条件です。
