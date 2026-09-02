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
