You are grading six anonymized answers to an independent holdout evaluation. Return only the requested structured result.

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


## Judge instructions

Score each candidate independently using only its final answer and this fixture.
Do not guess its generation condition. The workspace intentionally contained no source files and
was read-only, so judge the proposed data flow, types, boundaries, failure behavior, and observable
test plan. Do not fail a candidate merely because it could not edit or execute code.

Score S1 through S5 from 0 to 2 exactly as defined by the fixture. `total` must equal their sum.
If any critical failure condition is met, set `critical_failure` to true and `outcome` to
`critical_failure`. Otherwise use: pass = total 8-10 with every S at least 1; borderline = total
6-7, or total 8-10 with any S equal to 0; fail = total 0-5. Evidence must name concrete satisfied
and missing behavior. Do not reward headings, verbosity, or terminology by itself.


## Candidate A

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

## Candidate B

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

## Candidate C

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

## Candidate D

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

## Candidate E

最小変更として、既存の`requestWithRetry`と`RetryableMethod`は変更せず、429だけを扱う冪等POST専用の入口を`retry.ts`へ追加する案が安全です。これにより、通常のPOSTが汎用再試行APIへ紛れ込むのを避けられます。

## 実装案

### `packages/http/retry.ts`

既存型・関数はそのまま残します。

```ts
type RetryableMethod = "GET" | "PUT" | "DELETE";

export type RetryRequest<T> = {
  method: RetryableMethod;
  retryableStatuses?: readonly number[];
  maxAttempts?: number;
  send: () => Promise<HttpResponse<T>>;
};

export type RetryIdempotentPostOn429Request<TBody, TResponse> = {
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
  return retryLoop({ method, retryableStatuses, maxAttempts, send });
}

export async function requestIdempotentPostOn429<TBody, TResponse>({
  body,
  idempotencyKey,
  send,
}: RetryIdempotentPostOn429Request<TBody, TResponse>): Promise<
  HttpResponse<TResponse>
> {
  if (idempotencyKey.trim() === "") {
    throw new TypeError("idempotencyKey must not be empty");
  }

  return retryLoop({
    method: "POST",
    retryableStatuses: [429],
    maxAttempts: 3,
    send: () => send(body, idempotencyKey),
  });
}
```

`retryLoop`の内部入力型が`RetryableMethod`に限定されている場合だけ、内部型を次のように広げます。公開される`RetryableMethod`は広げません。

```ts
type RetryLoopMethod = RetryableMethod | "POST";
```

通信タイムアウトの判定は、現在の「GET/PUT/DELETEの場合だけ」という条件を維持します。`POST`をタイムアウト再試行対象へ追加してはいけません。

この専用関数では次が固定され、呼び出し側から変更できません。

- 再試行対象: `429`のみ
- 最大試行回数: 合計3回
- メソッド: `POST`
- 各試行へ渡すbodyと冪等性キー: 関数呼び出し時に受け取った同じ値

### `packages/billing/invoice-client.ts`

```ts
import { requestIdempotentPostOn429 } from "../http/retry";

export class InvoiceClient {
  constructor(private readonly http: HttpClient) {}

  createDraft(input: CreateDraftInput, idempotencyKey: string) {
    return requestIdempotentPostOn429({
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

### `packages/payments/payment-client.ts`

変更しません。

```ts
capture(input: CaptureInput) {
  return this.http.post("/v1/captures", input);
}
```

汎用の`requestWithRetry`は引き続きPOSTを型として受け付けません。また、`HttpClient.post`自体へ再試行を追加しないため、`capture`を含む他のPOSTへ再試行が波及しません。

## 呼び出し関係

```text
InvoiceClient.createDraft
  → requestIdempotentPostOn429
    → retryLoop
      → InvoiceClientから渡されたsend
        → HttpClient.post("/v2/invoices", 同じbody, 同じキー)

PaymentClient.capture
  → HttpClient.post("/v1/captures")
```

既存経路は変わりません。

```text
requestWithRetry（GET/PUT/DELETEのみ）
  → retryLoop
```

## 必要なテスト

### `requestIdempotentPostOn429`

- 1回目が429、2回目が成功なら2回呼ばれる。
- 3回すべて429なら、3回で終了して最後のレスポンスまたはエラーを返す。
- 503、500、502などは1回で終了する。
- 通信タイムアウトは1回で終了する。
- 空文字または空白だけの`idempotencyKey`は、通信前に失敗する。
- 各試行の`send`へ同じbody参照と同じ`idempotencyKey`が渡る。
- 429再試行時も既存の`Retry-After`、指数バックオフ、ログ形式が使われる。

最後の項目は、`retryLoop`の既存テストが十分なら重複させず、「専用関数が`retryLoop`を使用する」ことと429の統合テストで担保できます。

### `InvoiceClient.createDraft`

```ts
expect(http.post).toHaveBeenNthCalledWith(
  1,
  "/v2/invoices",
  input,
  { headers: { "Idempotency-Key": idempotencyKey } },
);

expect(http.post).toHaveBeenNthCalledWith(
  2,
  "/v2/invoices",
  input,
  { headers: { "Idempotency-Key": idempotencyKey } },
);
```

加えて以下を確認します。

- 429の後に成功すると再試行する。
- 503では再試行しない。
- タイムアウトでは再試行しない。
- 3回目の429以降は呼び出さない。

### 回帰テスト

- `PaymentClient.capture`が429、503、タイムアウトになっても`http.post`は1回だけ。
- 既存GET/PUT/DELETEのデフォルト対象が引き続き429と503。
- GET/PUT/DELETEの通信タイムアウト再試行が維持される。
- 既存の最大試行回数、ログ、バックオフ、`Retry-After`のテストが変更なしで通る。

## 仮定

- `maxAttempts: 3`は「初回を含めて合計3試行」を意味するものとします。
- `retryLoop`はHTTP 429をレスポンスとして受け取る設計と仮定しています。`HttpClient`が429を例外として投げる場合は、その例外からstatusを取得する既存経路へ合わせる必要があります。
- 「同じrequest body」は、同じ`input`を各試行へ渡すことを意味すると仮定しています。送信バイト列まで同一である必要があり、`HttpClient`がbodyを変更し得る場合は、事前シリアライズ可能なAPIの有無を追加確認する必要があります。

## Candidate F

調査した作業ディレクトリには実装ファイルやテストがなく、提示されたコード断片だけを根拠にした実装案です。実装・テスト実行はできませんでした。

## 変更契約

変更する挙動：

- `InvoiceClient.createDraft`だけが429を再試行する。
- 初回を含め最大3試行。
- 全試行で同じ `input` と `idempotencyKey` を渡す。
- 空の `idempotencyKey` は送信前に拒否する。

変更しない挙動：

- 503、その他の5xx、通信タイムアウトは `createDraft` では再試行しない。
- `capture`を含む他のPOSTは、従来どおり `HttpClient.post` を直接1回だけ呼ぶ。
- GET/PUT/DELETEのステータス、タイムアウト、既定値は不変。
- バックオフ、`Retry-After`、試行ログは既存の `requestWithRetry` / `retryLoop` が引き続き所有する。

## 最小実装案

`RetryableMethod`に無条件でPOSTを追加するだけでは、既存のタイムアウト判定次第でPOSTも再試行される危険があります。POSTを許可すると同時に、タイムアウト再試行を既存3メソッドへ明示的に限定します。

```ts
// packages/http/retry.ts

type RetryableMethod = "GET" | "PUT" | "DELETE" | "POST";

const retriesTransportTimeout = (
  method: RetryableMethod,
): method is Exclude<RetryableMethod, "POST"> =>
  method === "GET" || method === "PUT" || method === "DELETE";
```

`retryLoop`内の既存の通信タイムアウト判定を、次の条件に限定します。

```ts
if (isCommunicationTimeout(error) && retriesTransportTimeout(method)) {
  // 既存の再試行経路
}
```

ステータス再試行、バックオフ、`Retry-After`、ログの処理は変更しません。既存コードがすでにメソッド別のタイムアウト判定を持つ場合、新しい関数は不要で、その条件にPOSTが含まれないことだけ確認します。

`createDraft`を既存の再試行経路へ載せます。

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

`input`と`idempotencyKey`は関数内で複製・更新せず、同じクロージャーから毎回参照します。`PaymentClient.capture`は変更しません。

呼び出し関係は次のとおりです。

```text
InvoiceClient.createDraft
  └─ requestWithRetry（POST、429、最大3試行）
       └─ retryLoop
            └─ 同一クロージャー
                 └─ HttpClient.post（同一input・同一idempotencyKey）

PaymentClient.capture
  └─ HttpClient.post（従来どおり1回）
```

## 変更する型・関数

| 対象 | 変更 |
|---|---|
| `RetryableMethod` | `"POST"`を追加 |
| `requestWithRetry` | シグネチャや既定値は変更しない |
| `retryLoop`のタイムアウト判定 | GET/PUT/DELETEだけを対象に限定 |
| `InvoiceClient.createDraft` | 非空検証と固定された再試行設定を追加 |
| `PaymentClient.capture` | 変更なし |

任意の `retryTimeouts` フラグやPOST専用strategyは追加しません。新しい設定状態を増やさず、実際に異なる「POSTはタイムアウト再試行不可」という条件を、タイムアウト判定の正本だけで表します。

## 必要なテスト

| 契約・失敗経路 | テスト | 期待結果 |
|---|---|---|
| 429のみ再試行 | 429の後に成功 | `send`が2回呼ばれ、成功結果を返す |
| 最大3試行 | 429を3回返す | 呼び出しは3回で停止し、既存契約どおり最終結果を返す／投げる |
| 503除外 | POSTが503を返す | 1回だけ呼ばれる |
| その他5xx除外 | POSTが500を返す | 1回だけ呼ばれる |
| タイムアウト除外 | POSTが通信タイムアウトを投げる | 1回だけ呼ばれ、同じエラーを送出 |
| 同一body・同一キー | `createDraft`で429、429、成功 | 3回すべて同じ `input` オブジェクトと同じヘッダー値 |
| 非空キー | `createDraft(input, "")` | `HttpClient.post`を呼ばず同期的に例外 |
| 他のPOSTを除外 | `capture`のPOSTが429を返す | `HttpClient.post`は1回だけ |
| 既存メソッド不変 | GET/PUT/DELETEの既存ステータス再試行テスト | 従来どおり成功 |
| 既存タイムアウト不変 | GET/PUT/DELETEでタイムアウト後に成功 | 従来の最大回数とバックオフで再試行 |
| 共通処理不変 | 429応答に`Retry-After`を設定 | 既存の待機処理とログ形式が使われる |

責務の重複を避けるため、429・503・500・タイムアウト・最大回数は `retry.ts` のテストで保証し、`invoice-client` のテストでは設定の配線と同一引数だけを確認します。`payment-client`には「429でも1回」の回帰テストを1件置けば十分です。

## 仮定

- 「最大3回」は、再試行3回ではなく、既存の `maxAttempts` の意味どおり初回を含む合計3試行と仮定しています。
- 「非空」は `idempotencyKey.length > 0` と仮定しています。空白だけの文字列も拒否するなら、API契約として明示したうえで `trim().length === 0` にします。
- `HttpClient.post`は渡されたbodyを破壊的に変更しないと仮定しています。変更する可能性がある場合、単純な同一参照では同一bodyを保証できないため、HTTP境界側の契約確認が必要です。
- `retryLoop`が最終応答または例外をどう返すかは既存契約を維持します。提示コードからは具体的な終了形式を確定できません。
