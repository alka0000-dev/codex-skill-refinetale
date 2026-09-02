変更案は、色設定の「環境変数の変換＋優先順位解決＋`OutputOptions`生成」だけを共通関数へ抽出する形です。`deploy` と `preview` はデフォルト値だけをそれぞれ渡します。

なお、作業ディレクトリにはコミットや実装ファイルが存在しなかったため、以下のファイル名とCLI定義部分は配置例です。提示されたコードを一次情報として設計しています。

### 共通処理

`OutputOptions` と `parseBoolean` が置かれている共通モジュールへ追加します。

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

export function resolveOutputOptions({
  cliColor,
  envColor,
  fileColor,
  defaultColor,
}: {
  cliColor: boolean | undefined;
  envColor: string | undefined;
  fileColor: boolean | undefined;
  defaultColor: boolean;
}): OutputOptions {
  return {
    color: resolveValue({
      cli: cliColor,
      env: parseBoolean(envColor),
      file: fileColor,
      defaultValue: defaultColor,
    }),
  };
}
```

共通化するのは色設定の解決だけです。コマンド実行やTTYデフォルトの決定は共有しません。

`parseBoolean(envColor)` は `resolveValue` の呼び出し前に評価されるため、現在の `deploy` と同様、不正な `ACME_COLOR` はCLI指定の有無にかかわらず `ConfigError` になります。

### コマンド側

既存の `DeployArgs` と `PreviewArgs` に同じフィールドを追加します。コマンド別の `OutputOptions` は作りません。

```ts
type DeployArgs = {
  // 既存フィールド
  color: boolean | undefined;
};

type PreviewArgs = {
  // 既存フィールド
  color: boolean | undefined;
};
```

`deploy` は共通関数への置換だけで、デフォルトを変えません。

```ts
export function deployCommand(
  args: DeployArgs,
  ctx: CommandContext,
) {
  const output = resolveOutputOptions({
    cliColor: args.color,
    envColor: ctx.env.ACME_COLOR,
    fileColor: ctx.config.ui?.color,
    defaultColor: ctx.stdout.isTTY,
  });

  return runDeploy(args, output);
}
```

`preview` はTTY状態を参照せず、常に `false` をデフォルトとして渡します。

```ts
export function previewCommand(
  args: PreviewArgs,
  ctx: CommandContext,
) {
  const output = resolveOutputOptions({
    cliColor: args.color,
    envColor: ctx.env.ACME_COLOR,
    fileColor: ctx.config.ui?.color,
    defaultColor: false,
  });

  return runPreview(args, output);
}
```

値の流れは次のとおりです。

| 入力元 | 入力型 | 渡し先 | 解決時の型 |
|---|---:|---|---:|
| `args.color` | `boolean \| undefined` | `cliColor` | `boolean \| undefined` |
| `ctx.env.ACME_COLOR` | `string \| undefined` | `parseBoolean` → `env` | `boolean \| undefined` |
| `ctx.config.ui?.color` | `boolean \| undefined` | `fileColor` | `boolean \| undefined` |
| コマンド既定値 | `boolean` | `defaultColor` | `boolean` |
| `resolveValue`の結果 | — | `OutputOptions.color` | `boolean` |

### CLI定義

CLIライブラリの具体的なAPIは現物に合わせますが、パーサーが保証すべき値は以下です。

```text
--color      → args.color === true
--no-color   → args.color === false
指定なし     → args.color === undefined
```

特に、未指定時にCLIライブラリのデフォルトとして `true` や `false` を入れないことが重要です。デフォルトを入れると環境変数と設定ファイルが参照されなくなります。

help文面例は両コマンドで共通です。

```text
--color       Enable colored output
--no-color    Disable colored output

Color setting precedence:
  CLI flags > ACME_COLOR > ui.color > command default
```

補足として、コマンドデフォルトはhelpに明記すると差が伝わります。

```text
deploy default: stdout.isTTY
preview default: false
```

### テストケース

共通関数の単体テストで優先順位を固定します。

```ts
describe("resolveOutputOptions", () => {
  it.each([
    {
      name: "CLI true wins",
      input: {
        cliColor: true,
        envColor: "false",
        fileColor: false,
        defaultColor: false,
      },
      expected: true,
    },
    {
      name: "CLI false is not treated as unspecified",
      input: {
        cliColor: false,
        envColor: "true",
        fileColor: true,
        defaultColor: true,
      },
      expected: false,
    },
    {
      name: "environment variable wins over file",
      input: {
        cliColor: undefined,
        envColor: "false",
        fileColor: true,
        defaultColor: true,
      },
      expected: false,
    },
    {
      name: "file wins over default",
      input: {
        cliColor: undefined,
        envColor: undefined,
        fileColor: false,
        defaultColor: true,
      },
      expected: false,
    },
    {
      name: "default is used when every optional source is absent",
      input: {
        cliColor: undefined,
        envColor: undefined,
        fileColor: undefined,
        defaultColor: true,
      },
      expected: true,
    },
  ])("$name", ({ input, expected }) => {
    expect(resolveOutputOptions(input)).toEqual({
      color: expected,
    });
  });

  it("rejects an invalid environment variable", () => {
    expect(() =>
      resolveOutputOptions({
        cliColor: undefined,
        envColor: "yes",
        fileColor: undefined,
        defaultColor: false,
      }),
    ).toThrow(ConfigError);
  });

  it("preserves deploy behavior by validating env even when CLI is set", () => {
    expect(() =>
      resolveOutputOptions({
        cliColor: true,
        envColor: "yes",
        fileColor: undefined,
        defaultColor: false,
      }),
    ).toThrow(ConfigError);
  });
});
```

コマンド結合テストでは次を確認します。

- `deploy`、全設定未指定、`stdout.isTTY === true` → `color: true`
- `deploy`、全設定未指定、`stdout.isTTY === false` → `color: false`
- `preview`、全設定未指定、`stdout.isTTY === true` → `color: false`
- `preview --color` → `color: true`
- `preview --no-color`、環境変数と設定ファイルが `true` → `color: false`
- `preview`、`ACME_COLOR=1` → `color: true`
- `preview`、`ACME_COLOR=invalid` → `ConfigError`
- 両コマンドのhelpに `--color`、`--no-color`、優先順位が表示される
- CLIパーサー単体で、未指定が `undefined`、`--no-color` が `false`

これにより、共有範囲は `resolveOutputOptions`、`OutputOptions`、`parseBoolean` に限定され、コマンド固有のデフォルト差は呼び出し側に明示的に残ります。
