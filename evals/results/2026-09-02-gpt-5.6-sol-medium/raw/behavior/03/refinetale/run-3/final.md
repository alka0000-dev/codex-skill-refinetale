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
