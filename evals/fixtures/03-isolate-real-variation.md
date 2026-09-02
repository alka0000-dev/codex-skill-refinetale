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
