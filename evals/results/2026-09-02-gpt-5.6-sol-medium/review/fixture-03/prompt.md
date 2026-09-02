You are grading six anonymized answers to one coding-skill evaluation. Apply the rubric strictly and return only the requested structured result. Do not guess which condition produced an answer.

# 03: Isolate real variation

## Purpose

共通処理を維持しながら、本当に異なる通知チャネル差分だけを隔離できるかを確認する。

## Input

次の通知処理にpush通知を追加してください。email、sms、pushは同じ入力検証、本文生成、監査記録を使います。異なるのは送信clientと宛先フィールドだけです。現在要求されていない将来チャネルの仕組みは追加しないでください。

```ts
async function sendEmail(input: NotificationInput) {
  validate(input);
  const body = renderBody(input.template, input.values);
  await emailClient.send({ to: input.email, body });
  await audit.record("email.sent", input.userId);
}

async function sendSms(input: NotificationInput) {
  validate(input);
  const body = renderBody(input.template, input.values);
  await smsClient.send({ to: input.phoneNumber, body });
  await audit.record("sms.sent", input.userId);
}
```

## Pass conditions

- 入力検証、本文生成、監査記録を共通経路へまとめる。
- 分岐は送信client、宛先フィールド、既存の監査イベント名に必要なチャネル名へ限定する。
- push追加のために、未要求のregistry、feature flag、fallbackを導入しない。
- emailとsmsの外部挙動を維持する。
- 各チャネルの観察可能な送信先と監査記録をテストする。


## Scoring rules

Score each item as `1` (satisfied), `0` (not satisfied), or `-1` (not applicable).

- G1 Contract fidelity: preserves requested external contracts, inputs, outputs, errors, and events.
- G2 Change contract: clearly handles what changes, what must not change, and allowed variation.
- G3 Canonical ownership: keeps one source of truth for the same state or decision.
- G4 Variation isolation: isolates only real differences and does not duplicate common processing.
- G5 No speculative implementation: adds no unrequested future extension, fallback, flag, or abstraction.
- G6 Safety preservation: does not weaken authorization, validation, audit, or failure behavior.
- G7 Verification and stop: identifies necessary verification and stops when no change is needed.

Use only evidence present in the candidate's final answer. Do not reward a promise to finish later.
The workspace intentionally lacked source files and was read-only. Do not fail a candidate merely
for reporting that limitation if it still provides the requested concrete solution and verification
plan. Missing implementation guidance or missing required test coverage can still fail the relevant
criterion. `overall_pass` requires every applicable G score and the fixture-specific conditions to
equal 1. G1 is always critical; G6 is critical when applicable.


## Candidate A

提示コードを次の形に整理するのが最小です。共通処理は1経路に統合し、チャネルごとの差分だけを各関数に残します。

```ts
async function sendNotification(
  input: NotificationInput,
  to: string,
  client: {
    send(message: { to: string; body: string }): Promise<void>;
  },
  auditEvent: "email.sent" | "sms.sent" | "push.sent",
) {
  validate(input);
  const body = renderBody(input.template, input.values);

  await client.send({ to, body });
  await audit.record(auditEvent, input.userId);
}

async function sendEmail(input: NotificationInput) {
  return sendNotification(input, input.email, emailClient, "email.sent");
}

async function sendSms(input: NotificationInput) {
  return sendNotification(input, input.phoneNumber, smsClient, "sms.sent");
}

async function sendPush(input: NotificationInput) {
  return sendNotification(input, input.deviceToken, pushClient, "push.sent");
}
```

`NotificationInput` には、未定義なら次のフィールドを追加します。

```ts
deviceToken: string;
```

これにより、検証・本文生成・送信後の監査記録は一度だけ定義され、push固有の追加は `pushClient`、`deviceToken`、監査イベント値だけです。将来チャネル用のenum、strategy、設定表などは追加していません。

作業領域には実装ファイルやテスト構成がなく、読み取り専用だったため、ファイル適用・ビルド・テスト実行はできませんでした。

## Candidate B

作業ディレクトリが空かつ読み取り専用だったため、実ファイルには適用できませんでした。最小差分は次の形です。push の宛先は `deviceToken` と仮定しています。

```ts
async function sendNotification(
  input: NotificationInput,
  send: (body: string) => Promise<void>,
  auditEvent: "email.sent" | "sms.sent" | "push.sent",
) {
  validate(input);
  const body = renderBody(input.template, input.values);
  await send(body);
  await audit.record(auditEvent, input.userId);
}

async function sendEmail(input: NotificationInput) {
  await sendNotification(
    input,
    (body) => emailClient.send({ to: input.email, body }),
    "email.sent",
  );
}

async function sendSms(input: NotificationInput) {
  await sendNotification(
    input,
    (body) => smsClient.send({ to: input.phoneNumber, body }),
    "sms.sent",
  );
}

async function sendPush(input: NotificationInput) {
  await sendNotification(
    input,
    (body) => pushClient.send({ to: input.deviceToken, body }),
    "push.sent",
  );
}
```

共通化は現在の3チャネルで重複する処理だけに限定し、チャネル登録機構や将来向け設定は追加していません。実ファイルと書き込み可能な環境があれば、型定義・テストも含めて適用できます。

なお `referytale` が要求する事前対応表も、読み取り専用のため保存できませんでした。

## Candidate C

`pushToken` を push の宛先フィールドと仮定した最小構成です。既存APIを保ち、共通処理は1本に集約します。

```ts
type NotificationClient = {
  send(message: { to: string; body: string }): Promise<void>;
};

async function sendNotification(
  input: NotificationInput,
  to: string,
  client: NotificationClient,
  auditEvent: "email.sent" | "sms.sent" | "push.sent",
) {
  validate(input);
  const body = renderBody(input.template, input.values);

  await client.send({ to, body });
  await audit.record(auditEvent, input.userId);
}

async function sendEmail(input: NotificationInput) {
  await sendNotification(input, input.email, emailClient, "email.sent");
}

async function sendSms(input: NotificationInput) {
  await sendNotification(input, input.phoneNumber, smsClient, "sms.sent");
}

async function sendPush(input: NotificationInput) {
  await sendNotification(input, input.pushToken, pushClient, "push.sent");
}
```

将来チャネル向けの enum、registry、strategy は追加していません。なお、ワークスペースには実装ファイルやテスト設定が存在せず、読み取り専用だったため、ファイル変更とテスト実行はできませんでした。

## Candidate D

`pushToken` を宛先とする最小追加です。将来チャネル向けの抽象化は加えていません。

```ts
async function sendPush(input: NotificationInput) {
  validate(input);
  const body = renderBody(input.template, input.values);
  await pushClient.send({ to: input.pushToken, body });
  await audit.record("push.sent", input.userId);
}
```

`NotificationInput` に未定義なら、`pushToken` も追加してください。作業ディレクトリに実装ファイルがなく読み取り専用だったため、ファイル変更やテスト実行はできませんでした。

## Candidate E

実装できませんでした。現在のワークスペースは読み取り専用で、Git リポジトリ内にソースコード・テスト・`package.json` がありません。

また、`referytale` が要求する事前の対応表も保存できないため、コード生成へ進めません。対象プロジェクトを編集可能な状態で配置してください。少なくとも次が必要です。

- 提示コードを含む TypeScript ファイル
- `NotificationInput` と各 client の定義
- 関連テストまたはテスト設定

配置後、email / sms / push で検証・本文生成・監査記録のみを共有し、送信 client と宛先だけをチャネルごとに分ける最小差分で実装します。

## Candidate F

作業ツリーにソースファイルが存在せず読み取り専用のため、変更は適用できませんでした。提示コードには、次の最小構成が適します（`pushToken` は仮定した宛先フィールドです）。

```ts
type NotificationClient = {
  send(message: { to: string; body: string }): Promise<void>;
};

async function sendNotification(
  input: NotificationInput,
  client: NotificationClient,
  to: string,
  sentEvent: "email.sent" | "sms.sent" | "push.sent",
) {
  validate(input);
  const body = renderBody(input.template, input.values);
  await client.send({ to, body });
  await audit.record(sentEvent, input.userId);
}

async function sendEmail(input: NotificationInput) {
  await sendNotification(input, emailClient, input.email, "email.sent");
}

async function sendSms(input: NotificationInput) {
  await sendNotification(input, smsClient, input.phoneNumber, "sms.sent");
}

async function sendPush(input: NotificationInput) {
  await sendNotification(input, pushClient, input.pushToken, "push.sent");
}
```

`NotificationInput` には `pushToken: string` を追加します。共通処理の正本は `sendNotification` の一か所にし、分岐・チャネル登録機構・将来用設定は追加していません。実ファイルがないため、ビルド・リント・テストは未実施です。
