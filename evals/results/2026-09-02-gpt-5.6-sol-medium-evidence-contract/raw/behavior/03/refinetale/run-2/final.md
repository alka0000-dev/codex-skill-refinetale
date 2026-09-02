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
