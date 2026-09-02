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

作業ディレクトリに実装ファイルがなく読み取り専用だったため、変更は適用できませんでした。提示コードへの最小実装案は次のとおりです。push宛先は `input.pushToken` と仮定しています。

```ts
type NotificationClient = {
  send(message: { to: string; body: string }): Promise<void>;
};

async function sendNotification(
  input: NotificationInput,
  client: NotificationClient,
  to: string,
  auditEvent: string,
) {
  validate(input);
  const body = renderBody(input.template, input.values);
  await client.send({ to, body });
  await audit.record(auditEvent, input.userId);
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

共通の正本は `sendNotification` の検証・本文生成・送信・監査という一経路です。差分はclient、宛先、既存契約上チャネル別となる監査イベントだけです。将来チャネル用のenum、strategy、registryなどは追加していません。

必要な最小検証は以下です。

- email、sms、pushごとに正しいclient・宛先・監査イベントが使われる。
- 全チャネルで同じ `validate` と `renderBody` の結果が送信される。
- 検証失敗時は本文生成・送信・監査を実行しない。
- 本文生成失敗時は送信・監査を実行しない。
- 送信失敗時は監査を実行しない。
- 送信成功後にだけ監査を実行する。

実ファイル、テスト環境、`NotificationInput` の定義がないため、ビルド・リント・テストおよび `.agent/CONTINUITY.md` の作成は未実施です。

## Candidate B

共通部分だけを関数化し、3チャネル以外の仕組みは追加しません。push の宛先は `input.pushToken` と仮定しています。

```ts
type NotificationEvent = "email.sent" | "sms.sent" | "push.sent";

type SendNotification = (message: {
  to: string;
  body: string;
}) => Promise<void>;

async function sendNotification(
  input: NotificationInput,
  to: string,
  send: SendNotification,
  event: NotificationEvent,
) {
  validate(input);
  const body = renderBody(input.template, input.values);

  await send({ to, body });
  await audit.record(event, input.userId);
}

async function sendEmail(input: NotificationInput) {
  await sendNotification(
    input,
    input.email,
    (message) => emailClient.send(message),
    "email.sent",
  );
}

async function sendSms(input: NotificationInput) {
  await sendNotification(
    input,
    input.phoneNumber,
    (message) => smsClient.send(message),
    "sms.sent",
  );
}

async function sendPush(input: NotificationInput) {
  await sendNotification(
    input,
    input.pushToken,
    (message) => pushClient.send(message),
    "push.sent",
  );
}
```

`NotificationInput` に未定義なら `pushToken` を追加してください。作業ディレクトリが空かつ読み取り専用だったため、実ファイルへの反映とテスト実行はできませんでした。

## Candidate C

共通処理を1本にまとめ、3チャネルの差分を送信client・宛先・監査イベントだけに限定する実装です。pushの宛先フィールドは `input.pushToken` と仮定しています。

```ts
type NotificationClient = {
  send(message: { to: string; body: string }): Promise<void>;
};

type NotificationSentEvent =
  | "email.sent"
  | "sms.sent"
  | "push.sent";

async function sendNotification(
  input: NotificationInput,
  client: NotificationClient,
  to: string,
  sentEvent: NotificationSentEvent,
) {
  validate(input);
  const body = renderBody(input.template, input.values);

  await client.send({ to, body });
  await audit.record(sentEvent, input.userId);
}

async function sendEmail(input: NotificationInput) {
  await sendNotification(
    input,
    emailClient,
    input.email,
    "email.sent",
  );
}

async function sendSms(input: NotificationInput) {
  await sendNotification(
    input,
    smsClient,
    input.phoneNumber,
    "sms.sent",
  );
}

async function sendPush(input: NotificationInput) {
  await sendNotification(
    input,
    pushClient,
    input.pushToken,
    "push.sent",
  );
}
```

変更契約は次のとおりです。

- 変更する挙動: push通知を `pushClient`、`pushToken`、`push.sent` で送信・記録する。
- 変更しない挙動: emailとsmsの宛先、client、監査イベント、副作用順序を維持する。
- 共通処理: `validate → renderBody → client.send → audit.record`。
- 差分処理: client、宛先、監査イベントのみ。
- 将来チャネル用のregistry、strategy、fallback、設定値は追加しない。

作業ディレクトリは空の未コミットGitリポジトリで、かつ読み取り専用だったため、ファイル変更やテスト実行はできませんでした。適用時に必要な最小検証は以下です。

- email／sms／pushが、それぞれ正しいclient・宛先・監査イベントを使用する。
- 検証失敗時は本文生成、送信、監査を実行しない。
- 本文生成失敗時は送信、監査を実行しない。
- 送信失敗時は監査を実行しない。
- 監査失敗時はエラーを伝播する（送信は既に完了済み）。
- 成功時の順序が検証、本文生成、送信、監査になる。

## Candidate D

作業ディレクトリが空かつ読み取り専用のため、実装は適用できませんでした。`push` の宛先フィールドを `pushToken` と仮定した最小変更は次のとおりです。

```ts
async function sendPush(input: NotificationInput) {
  validate(input);
  const body = renderBody(input.template, input.values);
  await pushClient.send({ to: input.pushToken, body });
  await audit.record("push.sent", input.userId);
}
```

あわせて型へ宛先を追加します。

```ts
type NotificationInput = {
  // 既存フィールド
  pushToken: string;
};
```

既存の `validate`、`renderBody`、`audit.record` をそのまま再利用し、要求されていないチャネル抽象化は追加していません。

検証状況:

- リポジトリにソースコードやテストは存在せず、実行不可
- 読み取り専用のため `.agent/CONTINUITY.md` と `referytale` の対応表も作成不可
- 実際の宛先名が `deviceToken` などの場合は、`pushToken` を既存仕様に合わせる必要があります

## Candidate E

`pushToken` をPush通知の宛先フィールドと仮定した実装例です。共通処理は1か所にまとめ、対象チャネルは現在必要な3種類に限定します。

```ts
type NotificationChannel = "email" | "sms" | "push";

async function sendNotification(
  input: NotificationInput,
  channel: NotificationChannel,
) {
  validate(input);
  const body = renderBody(input.template, input.values);

  switch (channel) {
    case "email":
      await emailClient.send({ to: input.email, body });
      break;
    case "sms":
      await smsClient.send({ to: input.phoneNumber, body });
      break;
    case "push":
      await pushClient.send({ to: input.pushToken, body });
      break;
  }

  await audit.record(`${channel}.sent`, input.userId);
}

async function sendEmail(input: NotificationInput) {
  await sendNotification(input, "email");
}

async function sendSms(input: NotificationInput) {
  await sendNotification(input, "sms");
}

async function sendPush(input: NotificationInput) {
  await sendNotification(input, "push");
}
```

`NotificationInput` に未定義なら `pushToken` を追加してください。作業ディレクトリには実装ファイルがなく読み取り専用だったため、コードへの適用やテスト実行はしていません。また同じ理由で、`referytale` が要求する対応表と `.agent/CONTINUITY.md` も作成できませんでした。

## Candidate F

作業ツリーに実装ファイルがなく、かつ読み取り専用のため変更は適用できませんでした。提示コードに対する最小実装は次の形です。push の宛先は `input.pushToken` と仮定しています。

```ts
type NotificationClient = {
  send(message: { to: string; body: string }): Promise<void>;
};

type NotificationSentEvent =
  | "email.sent"
  | "sms.sent"
  | "push.sent";

async function sendNotification(
  input: NotificationInput,
  client: NotificationClient,
  to: string,
  sentEvent: NotificationSentEvent,
) {
  validate(input);
  const body = renderBody(input.template, input.values);

  await client.send({ to, body });
  await audit.record(sentEvent, input.userId);
}

async function sendEmail(input: NotificationInput) {
  await sendNotification(
    input,
    emailClient,
    input.email,
    "email.sent",
  );
}

async function sendSms(input: NotificationInput) {
  await sendNotification(
    input,
    smsClient,
    input.phoneNumber,
    "sms.sent",
  );
}

async function sendPush(input: NotificationInput) {
  await sendNotification(
    input,
    pushClient,
    input.pushToken,
    "push.sent",
  );
}
```

変更契約：

- push は `pushClient` と `input.pushToken` を使用し、成功後に `push.sent` を記録する。
- email/sms の宛先、client、監査イベント、処理順序は維持する。
- 検証、本文生成、送信、監査記録は単一経路に統合する。
- 将来チャネル向けのenum、registry、strategy、fallbackは追加しない。

なお、提示コードでは監査イベント名もチャネルごとに異なるため、既存契約を維持して引数にしています。検証すべき最小ケースは各チャネルの正しい宛先・イベント、検証失敗時の送信抑止、送信失敗時の監査抑止、成功時の「送信→監査」の順序です。実ファイルとテスト環境がないため、ビルド・lint・テストは未実施です。
