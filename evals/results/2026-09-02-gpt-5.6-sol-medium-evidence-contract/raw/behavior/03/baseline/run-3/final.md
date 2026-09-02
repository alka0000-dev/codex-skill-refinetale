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
