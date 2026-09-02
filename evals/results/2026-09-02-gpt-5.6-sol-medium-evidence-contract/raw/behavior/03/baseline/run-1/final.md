作業ディレクトリが空かつ読み取り専用のため、実装は適用できませんでした。`push` の宛先フィールドを `pushToken` と仮定した最小変更は次のとおりです。

```ts
async function sendPush(input: NotificationInput) {
  validate(input);
  const body = renderBody(input.template, input.values);
  await pushClient.send({ to: input.pushToken, body });
  await audit.record("push.sent", input.userId);
}
```

あわせて型へ宛先を追加します。

```ts
type NotificationInput = {
  // 既存フィールド
  pushToken: string;
};
```

既存の `validate`、`renderBody`、`audit.record` をそのまま再利用し、要求されていないチャネル抽象化は追加していません。

検証状況:

- リポジトリにソースコードやテストは存在せず、実行不可
- 読み取り専用のため `.agent/CONTINUITY.md` と `referytale` の対応表も作成不可
- 実際の宛先名が `deviceToken` などの場合は、`pushToken` を既存仕様に合わせる必要があります
