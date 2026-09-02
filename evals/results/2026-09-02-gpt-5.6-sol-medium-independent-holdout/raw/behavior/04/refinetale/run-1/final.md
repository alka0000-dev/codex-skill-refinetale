変更案は、`OutputOptions` の生成だけを共通化し、コマンド固有差分を `defaultColor` に限定する形が最小です。`deploy` の既存評価順序—including CLI指定時にも不正な環境変数を検査する挙動—も維持できます。

## 変更契約

変更する挙動:

- `preview` が `--color` / `--no-color` を受け取る。
- `preview` も `CLI > ACME_COLOR > ui.color > default` で解決する。
- `preview` の全未指定時はTTYでも `false`。

変更しない挙動:

- `deploy` の優先順位とデフォルト `ctx.stdout.isTTY`。
- `--no-color` が明示値 `false` としてCLI最優先になること。
- `parseBoolean` が不正値を `ConfigError` にすること。
- `OutputOptions` は `{ color: boolean }` の単一共通型。

共通処理:

- `ACME_COLOR` のパース。
- 4入力の優先順位解決。
- `OutputOptions` の生成。

差分処理:

- `deploy`: `defaultColor = ctx.stdout.isTTY`
- `preview`: `defaultColor = false`

## 共通処理

`OutputOptions` の既存所有モジュールへ、次の関数を置きます。コマンド別の型やstrategyは追加しません。

```ts
export type OutputOptions = {
  color: boolean;
};

export function resolveOutputOptions({
  cliColor,
  ctx,
  defaultColor,
}: {
  cliColor: boolean | undefined;
  ctx: CommandContext;
  defaultColor: boolean;
}): OutputOptions {
  return {
    color: resolveValue({
      cli: cliColor,
      env: parseBoolean(ctx.env.ACME_COLOR),
      file: ctx.config.ui?.color,
      defaultValue: defaultColor,
    }),
  };
}
```

`parseBoolean(ctx.env.ACME_COLOR)` は `resolveValue` の呼び出し前に評価されます。したがって、現在の `deploy` と同様、CLI値が指定されていても環境変数が不正なら `ConfigError` になります。

## コマンド側

```ts
export function deployCommand(args: DeployArgs, ctx: CommandContext) {
  const output = resolveOutputOptions({
    cliColor: args.color,
    ctx,
    defaultColor: ctx.stdout.isTTY,
  });

  return runDeploy(args, output);
}
```

```ts
type PreviewArgs = {
  // 既存プロパティ
  color?: boolean;
};

export function previewCommand(args: PreviewArgs, ctx: CommandContext) {
  const output = resolveOutputOptions({
    cliColor: args.color,
    ctx,
    defaultColor: false,
  });

  return runPreview(args, output);
}
```

値の経路は次の一本だけです。

```text
--color / --no-color ─┐
ACME_COLOR ─parseBoolean─┤
config.ui.color ────────┼─ resolveValue ─ { color: boolean } ─ runDeploy/runPreview
コマンド固有default ───┘
```

CLI登録では次の値を保証します。

- `--color` → `args.color === true`
- `--no-color` → `args.color === false`
- どちらも未指定 → `args.color === undefined`

未指定を `false` に初期化すると環境変数や設定ファイルを常に上書きしてしまうため、CLIパーサー側のデフォルトは必ず `undefined` にします。

## help

既存の `deploy` のflag登録を `preview` にも適用し、両コマンドに以下を記載します。

```text
--color       Enable colored output
--no-color    Disable colored output

Priority: CLI > ACME_COLOR > ui.color > command default.
deploy defaults to stdout TTY detection; preview defaults to no color.
```

CLIライブラリに共通option登録の仕組みが既にある場合だけ登録処理も再利用します。help文言の共有だけを目的とした新しい抽象化は不要です。

## 最小テスト

共通resolverのテーブルテスト:

| CLI | env | file | default | 結果 |
|---:|---:|---:|---:|---:|
| `false` | `"true"` | `true` | `true` | `false` |
| `undefined` | `"false"` | `true` | `true` | `false` |
| `undefined` | `undefined` | `false` | `true` | `false` |
| `undefined` | `undefined` | `undefined` | `true` | `true` |

追加で以下を確認します。

```ts
it("throws ConfigError for an invalid ACME_COLOR", () => {
  expect(() =>
    resolveOutputOptions({
      cliColor: true,
      ctx: contextWithEnv({ ACME_COLOR: "yes" }),
      defaultColor: false,
    }),
  ).toThrow(ConfigError);
});
```

CLI境界:

- `preview --color` → `args.color === true`
- `preview --no-color` → `args.color === false`
- flag未指定 → `args.color === undefined`
- 両コマンドのhelpに両flagと優先順位が含まれる

コマンド連携:

- `deploy`、全設定なし、TTY → `runDeploy(..., { color: true })`
- `preview`、全設定なし、TTY → `runPreview(..., { color: false })`
- `deploy` と `preview` のそれぞれで `ACME_COLOR="invalid"` → `ConfigError`、runnerは呼ばれない

作業ツリーには実装コード・`package.json`・既存テストがなく、かつ読み取り専用だったため、変更およびテスト実行はしていません。実コードが提示された場合は、既存のファイル配置とCLIライブラリに合わせてこの契約を具体的な差分へ落とせます。
