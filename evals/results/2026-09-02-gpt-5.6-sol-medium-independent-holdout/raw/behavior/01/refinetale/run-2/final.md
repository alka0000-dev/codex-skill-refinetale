実装方針は、既存の `requestWithRetry` と `retryLoop` を再利用し、POST の許可条件を型で狭く表現する案が最小です。`HttpClient.post` 自体には再試行を追加しません。

## 変更契約

変更する挙動:

- `InvoiceClient.createDraft` のみ、429を受けた場合に合計最大3回まで試行する。
- 空文字の `idempotencyKey` は通信前に拒否する。
- 再試行でも同じ `input` と `idempotencyKey` を使う。

変更しない挙動:

- `requestWithRetry` のバックオフ、`Retry-After`、ログ、最終レスポンス／例外の返し方。
- GET/PUT/DELETEの既存のステータス・通信タイムアウト再試行。
- `capture` を含む他のPOST。引き続き `HttpClient.post` を直接1回だけ呼ぶ。
- `createDraft` の503、その他の5xx、通信タイムアウトは1回で終了する。

共通処理:

- 試行回数、待機、レスポンス判定は引き続き `requestWithRetry` → `retryLoop` が所有する。

差分処理:

- POSTは明示的に `[429]` を指定した呼び出しだけ受け付ける。
- 通信タイムアウトを再試行可能と判断するメソッド集合にはPOSTを加えない。

## 型と関数の変更案

`packages/http/retry.ts` では、単純に `RetryableMethod` へ `"POST"` を追加するより、POSTの条件を判別共用体で制限します。

```ts
type RetryableMethod = "GET" | "PUT" | "DELETE";

type RetryRequestBase<T> = {
  maxAttempts?: number;
  send: () => Promise<HttpResponse<T>>;
};

export type RetryRequest<T> =
  | (RetryRequestBase<T> & {
      method: RetryableMethod;
      retryableStatuses?: readonly number[];
    })
  | (RetryRequestBase<T> & {
      method: "POST";
      retryableStatuses: readonly [429];
    });

export async function requestWithRetry<T>({
  method,
  retryableStatuses = [429, 503],
  maxAttempts = 3,
  send,
}: RetryRequest<T>): Promise<HttpResponse<T>> {
  return retryLoop({ method, retryableStatuses, maxAttempts, send });
}
```

これにより、以下は型エラーになります。

```ts
requestWithRetry({
  method: "POST",
  retryableStatuses: [429, 503],
  send,
});
```

`retryLoop` の入力型には `"POST"` を追加する必要があります。ただし、通信タイムアウトの判定で使っている既存の `"GET" | "PUT" | "DELETE"` の集合は変更しません。

```text
ステータス判定:
  retryableStatuses に含まれる場合のみ再試行

通信タイムアウト判定:
  method が GET / PUT / DELETE の場合のみ再試行
```

タイムアウト可否を表す新しいboolean設定は追加しません。`method` から導出でき、状態の重複になるためです。

## `createDraft` の変更案

```ts
import { requestWithRetry } from "../http/retry";

export class InvoiceClient {
  constructor(private readonly http: HttpClient) {}

  createDraft(input: CreateDraftInput, idempotencyKey: string) {
    if (!idempotencyKey) {
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

`input` と `idempotencyKey` は再生成・変更せず、クロージャが同じ値を全試行で参照します。既定値が将来変わっても請求書の契約が変化しないよう、`maxAttempts: 3` は明示します。

`PaymentClient.capture` は変更しません。

## 呼び出し関係

```text
InvoiceClient.createDraft
  → requestWithRetry
    → retryLoop
      → send
        → HttpClient.post("/v2/invoices", same input, same key)

PaymentClient.capture
  → HttpClient.post("/v1/captures")
```

`HttpClient.post` や共通HTTPクライアントに自動再試行を追加しないことが、他のPOSTとの安全境界です。

## 必要なテスト

`packages/billing/invoice-client.test.ts`:

1. `429 → 成功`
   - `post` が2回呼ばれる。
   - 両方で同じURL、同じbody参照、同じ非空の冪等性キーを使う。

2. `429 → 429 → 429 → 成功予定`
   - `post` は3回まで。
   - 4回目は呼ばれない。
   - 結果は既存 `retryLoop` の試行枯渇時契約どおり。

3. `503` と代表的なその他5xx（例: `500`）
   - table-driven testで、それぞれ1回しか呼ばれない。

4. 通信タイムアウト
   - 同じタイムアウト例外が返る。
   - `post` は1回だけ。

5. 空の `idempotencyKey`
   - 通信前に失敗する。
   - `post` は呼ばれない。

`packages/http/retry.test.ts`:

- POSTに `[429]` を指定すると429のみ再試行できる。
- POSTの通信タイムアウトは再試行しない。
- 既存のGET/PUT/DELETEについて、429、503、通信タイムアウトの既存テストを実行する。存在しなければ3メソッドをtable-driven testにして追加する。

`packages/payments/payment-client.test.ts`:

- `capture` が429を受けても `post` は1回だけ。
- `requestWithRetry` を経由しないことではなく、観測可能な「送信が1回」という契約を検証する。

## 仮定

- `maxAttempts` は再試行回数ではなく、初回を含む総試行回数です。
- `retryLoop` はHTTPステータスと通信タイムアウトを区別できます。
- 「非空」は `""` の禁止を意味し、空白だけの文字列の扱いは変更しません。
- 空キーの例外型・メッセージは、実際のコードベースに既存の入力検証規約があればそれに合わせます。
- `HttpClient.post` は渡されたbodyを破壊的に変更しません。

作業ディレクトリには提示コードやテストが存在せず、読み取り専用だったため、実装・テスト実行・`.agent/CONTINUITY.md` 作成は未実施です。実リポジトリでは上記テストの成功を完了条件とします。また ReferyTale は対応表の保存が必須ですが、読み取り専用のため適用を中断し、新しい抽象名を増やさず既存名だけで案を構成しました。
