変更案は、`color` の解決処理を1関数へ集約し、各コマンドには実際に異なるdefault値だけを残す形が最小です。

## 変更契約

変更する挙動:

- `preview` が `--color` / `--no-color` を受け付ける。
- `preview` の優先順位を `CLI > ACME_COLOR > ui.color > false` にする。
- 不正な `ACME_COLOR` は `preview` でも `ConfigError` にする。
- 両コマンドのhelpにフラグと優先順位を記載する。

変更しない挙動:

- `deploy` の優先順位は変えない。
- `deploy` のdefaultは引き続き `ctx.stdout.isTTY`。
- `parseBoolean` の受理値と失敗型を変えない。
- `runDeploy`へ渡す `OutputOptions` の形を変えない。
- CLIが指定されていても不正な環境変数を検証する、現在の`deploy`の挙動を維持する。

共通処理:

- CLI値、環境変数、設定ファイル、defaultの解決。
- `ACME_COLOR`のboolean変換。
- `OutputOptions`の生成。

差分処理:

- `deploy`: `defaultColor = ctx.stdout.isTTY`
- `preview`: `defaultColor = false`

## 共通実装

`OutputOptions`と`parseBoolean`が現在置かれている共通モジュールに、次だけを追加します。

```ts
export type OutputOptions = {
  color: boolean;
};

export function parseBoolean(
  value: string | undefined,
): boolean | undefined {
  if (value === undefined) return undefined;
  if (value === "true" || value === "1") return true;
  if (value === "false" || value === "0") return false;
  throw new ConfigError(`invalid boolean: ${value}`);
}

export function resolveOutputOptions(
  cliColor: boolean | undefined,
  ctx: CommandContext,
  defaultColor: boolean,
): OutputOptions {
  // resolveValueを呼ぶ前に評価し、既存どおり不正な環境変数を必ず拒否する。
  const envColor = parseBoolean(ctx.env.ACME_COLOR);

  return {
    color: resolveValue({
      cli: cliColor,
      env: envColor,
      file: ctx.config.ui?.color,
      defaultValue: defaultColor,
    }),
  };
}
```

`parseBoolean`を遅延評価してはいけません。たとえばCLI値があるときに環境変数のparseを省略すると、現在の`deploy`では失敗する不正値が成功するようになり、挙動が変わります。

`OutputResolverOptions`のような追加型や、コマンド別resolver、strategy、コマンド種別の分岐は不要です。

## コマンド側

```ts
export function deployCommand(args: DeployArgs, ctx: CommandContext) {
  const output = resolveOutputOptions(
    args.color,
    ctx,
    ctx.stdout.isTTY,
  );

  return runDeploy(args, output);
}
```

```ts
export function previewCommand(args: PreviewArgs, ctx: CommandContext) {
  const output = resolveOutputOptions(
    args.color,
    ctx,
    false,
  );

  return runPreview(args, output);
}
```

`DeployOutputOptions`や`PreviewOutputOptions`は追加せず、両方とも既存の`OutputOptions`を使います。

値の経路は次の1本です。

```text
--color / --no-color
        ↓
args.color: true | false | undefined
        ↓
resolveOutputOptions
  ├─ ACME_COLOR → parseBoolean → boolean | undefined
  ├─ ui.color                 → boolean | undefined
  └─ command default          → boolean
        ↓
resolveValue<boolean>
        ↓
OutputOptions.color: boolean
        ↓
runDeploy / runPreview
```

`--no-color`は`args.color === false`として渡します。`args.color || undefined`のようなtruthy変換は使用しません。

## CLI定義とhelp

利用中のCLIライブラリのnegatable option機能を使い、2つの独立したbooleanへ分けず、同じ`color`フィールドへ格納します。

期待されるparse結果:

```ts
preview --color     // args.color === true
preview --no-color  // args.color === false
preview             // args.color === undefined
```

両コマンドのhelpには、少なくとも次を記載します。

```text
--color       Enable colored output
--no-color    Disable colored output

Color precedence:
  command-line flag > ACME_COLOR > ui.color > command default
```

加えてdefault差を明記します。

```text
deploy default: stdout is a TTY
preview default: disabled
```

## 最小テストケース

| 契約 | テスト入力 | 期待結果 |
|---|---|---|
| CLI最優先・`false`保持 | `cliColor=false`, env=`true`, file=`true` | `color=false` |
| 環境変数優先 | CLI未指定、env=`false`, file=`true` | `color=false` |
| ファイル優先 | CLI/env未指定、file=`true` | `color=true` |
| deployのdefault維持 | 全入力未指定、`stdout.isTTY=true` | `runDeploy`へ`{ color: true }` |
| deploy非TTY | 全入力未指定、`stdout.isTTY=false` | `runDeploy`へ`{ color: false }` |
| preview固有default | 全入力未指定、`stdout.isTTY=true` | `runPreview`へ`{ color: false }` |
| deployの失敗経路維持 | CLI=`true`, env=`invalid` | `ConfigError("invalid boolean: invalid")`、`runDeploy`未実行 |
| previewの失敗経路 | CLI=`true`, env=`invalid` | 同じ`ConfigError`、`runPreview`未実行 |
| CLI正規化 | `preview --no-color` | `args.color === false` |
| help | `deploy --help`, `preview --help` | 両flag、優先順位、各defaultを表示 |

優先順位の全組み合わせを両コマンドで重複テストする必要はありません。共通resolverで優先順位と`false`を検証し、コマンドテストではそれぞれのdefault、失敗時にrunnerが呼ばれないこと、正しい`OutputOptions`の受け渡しだけを確認します。

作業ツリーには実装ファイルやコミットが存在しなかったため、コード変更・ビルド・テスト実行はしていません。実ファイルが提供された場合は、既存CLIライブラリのoption記法とテスト配置に合わせてこの案を適用する必要があります。
