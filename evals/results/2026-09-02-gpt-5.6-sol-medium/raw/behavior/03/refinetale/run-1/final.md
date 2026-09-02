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
