`pushToken` を宛先とする最小追加です。将来チャネル向けの抽象化は加えていません。

```ts
async function sendPush(input: NotificationInput) {
  validate(input);
  const body = renderBody(input.template, input.values);
  await pushClient.send({ to: input.pushToken, body });
  await audit.record("push.sent", input.userId);
}
```

`NotificationInput` に未定義なら、`pushToken` も追加してください。作業ディレクトリに実装ファイルがなく読み取り専用だったため、ファイル変更やテスト実行はできませんでした。
