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
