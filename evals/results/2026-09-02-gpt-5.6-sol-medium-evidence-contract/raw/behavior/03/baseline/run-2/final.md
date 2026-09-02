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
