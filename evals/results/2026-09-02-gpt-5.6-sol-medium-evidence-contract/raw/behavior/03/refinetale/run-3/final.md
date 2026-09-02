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
