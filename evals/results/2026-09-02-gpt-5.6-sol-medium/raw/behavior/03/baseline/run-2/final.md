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
