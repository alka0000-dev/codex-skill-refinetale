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
