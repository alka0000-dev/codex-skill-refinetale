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

実装方針は、`requestWithRetry` にPOSTを無条件で許可せず、「429のみ・総試行回数3回」という組み合わせだけ型で許可し、`createDraft` からその経路を使う形が安全です。`capture` は変更しません。

なお、作業ディレクトリには提示されたコード自体がなく、`.git` 以外は空でした。そのため、以下は提示コードを根拠にした実装案です。また、読み取り専用環境のため `referytale` スキルが要求する対応表ファイルと `.agent/CONTINUITY.md` は作成できませんでした。

## 変更する型

`POST`を単純に`RetryableMethod`へ追加すると、他のPOSTまで既定値の429/503や通信タイムアウトで再試行できてしまう恐れがあります。判別可能なunionで制約します。

```ts
type RetryableMethod = "GET" | "PUT" | "DELETE";

type RetrySend<T> = {
  send: () => Promise<HttpResponse<T>>;
};

type DefaultRetryRequest<T> = RetrySend<T> & {
  method: RetryableMethod;
  retryableStatuses?: readonly number[];
  maxAttempts?: number;
};

type Post429RetryRequest<T> = RetrySend<T> & {
  method: "POST";

  // POSTに許可する設定を型レベルで限定する。
  retryableStatuses: readonly [429];
  maxAttempts: 3;
};

export type RetryRequest<T> =
  | DefaultRetryRequest<T>
  | Post429RetryRequest<T>;
```

これにより、以下は型エラーになります。

```ts
requestWithRetry({
  method: "POST",
  send,
});

requestWithRetry({
  method: "POST",
  retryableStatuses: [503],
  maxAttempts: 3,
  send,
});

requestWithRetry({
  method: "POST",
  retryableStatuses: [429],
  maxAttempts: 4,
  send,
});
```

## `requestWithRetry`の変更

unionを判別して既定値を解決します。`retryLoop`によるバックオフ、`Retry-After`、ログはそのまま使います。

```ts
export async function requestWithRetry<T>(
  request: RetryRequest<T>,
): Promise<HttpResponse<T>> {
  const retryableStatuses =
    request.method === "POST"
      ? request.retryableStatuses
      : request.retryableStatuses ?? [429, 503];

  const maxAttempts =
    request.method === "POST"
      ? request.maxAttempts
      : request.maxAttempts ?? 3;

  return retryLoop({
    method: request.method,
    retryableStatuses,
    maxAttempts,
    send: request.send,
  });
}
```

`retryLoop`側では、通信タイムアウトの判定を必ず次の条件に保ちます。

```ts
const retriesTimeout =
  method === "GET" ||
  method === "PUT" ||
  method === "DELETE";
```

既存実装が「`RetryableMethod`として渡された全メソッドのタイムアウトを再試行する」という判定なら、POST追加に伴い、この明示的な判定へ変更する必要があります。

## `createDraft`の変更

body、キー、リクエストオプションを呼び出しごとに一度だけ確定し、全試行で同じ値をキャプチャします。

```ts
import { requestWithRetry } from "../http/retry";

export class InvoiceClient {
  constructor(private readonly http: HttpClient) {}

  createDraft(input: CreateDraftInput, idempotencyKey: string) {
    const requestOptions = {
      headers: {
        "Idempotency-Key": idempotencyKey,
      },
    };

    return requestWithRetry({
      method: "POST",
      retryableStatuses: [429],
      maxAttempts: 3,
      send: () =>
        this.http.post(
          "/v2/invoices",
          input,
          requestOptions,
        ),
    });
  }
}
```

呼び出し関係は次のようになります。

```text
InvoiceClient.createDraft
  └─ requestWithRetry
       └─ retryLoop
            └─ send
                 └─ HttpClient.post("/v2/invoices", input, requestOptions)

PaymentClient.capture
  └─ HttpClient.post("/v1/captures", input)
```

`capture`は`requestWithRetry`を経由しないため、変更不要です。

## 必要なテスト

### `requestWithRetry`

- POSTが429を返した後に成功した場合、成功するまで再試行する。
- POSTが429を返し続けた場合、総試行回数が3回で終了する。
- POSTの503、その他の5xxでは1回しか送信しない。
- POSTの通信タイムアウトでは1回しか送信しない。
- GET/PUT/DELETEの既存既定値が429、503のままである。
- GET/PUT/DELETEの通信タイムアウトが引き続き再試行される。
- 既存のバックオフ、`Retry-After`、試行ログのテストが変更なしで通る。
- `@ts-expect-error`による型テストで、POSTの503、既定値省略、4回試行を拒否する。

### `InvoiceClient.createDraft`

- `429 → 成功`で`http.post`が2回呼ばれる。
- `429 → 429 → 成功`で3回呼ばれる。
- 429が継続しても3回を超えない。
- 503、500、通信タイムアウトでは1回だけ呼ばれる。
- 全試行で次が同一である。

```ts
expect(http.post.mock.calls[0][1]).toBe(input);
expect(http.post.mock.calls[1][1]).toBe(input);

expect(http.post.mock.calls[0][2]).toBe(
  http.post.mock.calls[1][2],
);

expect(http.post.mock.calls[0][2].headers["Idempotency-Key"])
  .toBe(idempotencyKey);
```

### `PaymentClient.capture`

429を返すモックを使用し、`http.post`が1回だけ呼ばれることを回帰テストにします。

## 仮定

- `maxAttempts: 3`は「初回を含む総試行回数3回」を意味します。
- `retryLoop`はステータスコードと通信タイムアウトを区別できます。
- 呼び出し元が非空の`idempotencyKey`を保証します。既存挙動を壊さないため、この変更では空文字の新しい実行時検証を追加しません。
- `HttpClient.post`は渡されたbodyやoptionsを破壊的に変更しません。変更する可能性がある場合は、HTTPクライアント側の契約確認が必要です。

## Candidate B

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

## Candidate C

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

## Candidate D

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

## Candidate E

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

## Candidate F

実装方針は、既存のGET/PUT/DELETE用契約を残したまま、明示的なPOST再試行を型で区別し、`createDraft` だけから利用する形が安全です。

## 実装案

### `packages/http/retry.ts`

POSTでは通信タイムアウトを再試行しないことを型と実行時の両方で明示します。

```ts
type RetryableMethod = "GET" | "PUT" | "DELETE";

type ExistingRetryRequest<T> = {
  method: RetryableMethod;
  retryableStatuses?: readonly number[];
  maxAttempts?: number;
  send: () => Promise<HttpResponse<T>>;
};

type StatusOnlyPostRetryRequest<T> = {
  method: "POST";
  retryableStatuses: readonly number[];
  maxAttempts: number;
  retryTimeouts: false;
  send: () => Promise<HttpResponse<T>>;
};

export type RetryRequest<T> =
  | ExistingRetryRequest<T>
  | StatusOnlyPostRetryRequest<T>;

export async function requestWithRetry<T>(
  request: RetryRequest<T>,
): Promise<HttpResponse<T>> {
  const {
    method,
    retryableStatuses = [429, 503],
    maxAttempts = 3,
    send,
  } = request;

  const retryTimeouts =
    method === "POST" ? request.retryTimeouts : true;

  // バックオフ、Retry-After、ログの既存実装は変更しない。
  return retryLoop({
    method,
    retryableStatuses,
    maxAttempts,
    retryTimeouts,
    send,
  });
}
```

`retryLoop` が既にメソッドからタイムアウト再試行可否を判断している場合は、`retryTimeouts` の追加は不要です。その場合は、POSTがタイムアウト分岐へ入らないことだけを確認します。

重要なのは、単純に既存の `RetryableMethod` へ `"POST"` を追加しないことです。POSTでは設定の省略を許さず、ステータスだけを対象にすることを呼び出し側に明示させます。

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
      retryTimeouts: false,
      send: () =>
        this.http.post("/v2/invoices", input, {
          headers: { "Idempotency-Key": idempotencyKey },
        }),
    });
  }
}
```

`send` のクロージャーが、呼び出し時に受け取った `input` と `idempotencyKey` をそのまま捕捉します。再試行中にbodyやキーを生成し直しません。

### `packages/payments/payment-client.ts`

変更しません。

```ts
capture(input: CaptureInput) {
  return this.http.post("/v1/captures", input);
}
```

## 呼び出し関係

```text
InvoiceClient.createDraft
  └─ requestWithRetry
       └─ retryLoop
            └─ send
                 └─ HttpClient.post("/v2/invoices", ...)

PaymentClient.capture
  └─ HttpClient.post("/v1/captures", ...)
```

`capture` は再試行基盤を経由しないため、429でも1回だけ送信されます。

## 必要なテスト

### `InvoiceClient.createDraft`

最低限、次を確認します。

- 1回目が429、2回目が成功した場合は合計2回送信する。
- 429が続いた場合でも合計3回で終了する。
- 503では1回だけ送信して終了する。
- 500など、その他の5xxでも1回だけ送信する。
- 通信タイムアウトでは1回だけ送信する。
- 全試行のURL、body、`Idempotency-Key` が同じである。
  - bodyは可能なら値の一致だけでなく `toBe(input)` で同一参照も確認する。
- 空文字の `idempotencyKey` は、HTTP送信前に失敗する。
- 初回成功時は従来どおり1回だけ送信し、レスポンスを返す。

429の主要テスト例です。

```ts
it("429の場合だけ同じbodyとidempotency keyで最大3回試行する", async () => {
  const input = createDraftInputFactory();
  const response429 = createHttpResponse({ status: 429 });
  const success = createHttpResponse({ status: 201 });

  http.post
    .mockResolvedValueOnce(response429)
    .mockResolvedValueOnce(response429)
    .mockResolvedValueOnce(success);

  await expect(
    client.createDraft(input, "invoice-key-1"),
  ).resolves.toBe(success);

  expect(http.post).toHaveBeenCalledTimes(3);

  for (const call of http.post.mock.calls) {
    expect(call[0]).toBe("/v2/invoices");
    expect(call[1]).toBe(input);
    expect(call[2]).toEqual({
      headers: { "Idempotency-Key": "invoice-key-1" },
    });
  }
});
```

### `requestWithRetry`

既存テストに以下を追加します。

- POST＋`retryableStatuses: [429]` は429だけ再試行する。
- POST＋`retryTimeouts: false` はタイムアウトを再試行しない。
- GET/PUT/DELETEについて、既定の `[429, 503]`、タイムアウト、最大試行回数が従来どおりである。
- 既存のバックオフ、`Retry-After`、ログ内容のテストが変更なしで通る。

### `PaymentClient.capture`

回帰テストとして、HTTPクライアントが429を返しても `post` が1回しか呼ばれないことを確認します。

## 仮定

- `maxAttempts: 3` は「初回を含む合計3試行」を意味すると仮定しています。
- `HttpClient` または `retryLoop` が、HTTPステータスをレスポンスとして返すのか例外として投げるのかは提示されていません。既存の判定方式に合わせます。
- 「非空」は `""` の禁止と解釈しています。空白だけのキーも禁止するなら、検査を `idempotencyKey.trim().length === 0` にします。
- `HttpClient.post` が渡されたbodyを破壊的に変更しないことを仮定しています。
- 実ファイルが作業ディレクトリになく読み取り専用だったため、これは提示コードに基づく実装案です。`retryLoop` の実際の型とタイムアウト判定を確認後、`retryTimeouts` 追加の要否を確定する必要があります。
