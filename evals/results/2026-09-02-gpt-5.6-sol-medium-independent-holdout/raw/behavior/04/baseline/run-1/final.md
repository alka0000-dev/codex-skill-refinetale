変更案は、色設定の解決だけを共通関数へ切り出し、コマンド固有のデフォルト値は各コマンドに残す形です。これなら `deploy` の現在の挙動を維持できます。

実リポジトリは空だったため、以下のファイル名は配置例です。

### 1. 共通処理

```ts
// output-options.ts
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

export function resolveColor({
  cli,
  env,
  file,
  defaultValue,
}: {
  cli: boolean | undefined;
  env: string | undefined;
  file: boolean | undefined;
  defaultValue: boolean;
}): boolean {
  return resolveValue({
    cli,
    // resolveValueより先に評価されるため、CLI指定時でも不正値は
    // 従来のdeployと同じくConfigErrorになる。
    env: parseBoolean(env),
    file,
    defaultValue,
  });
}
```

`resolveColor` が共有するのは以下だけです。

- `ACME_COLOR` のパース
- `CLI > env > file > default` の解決

`stdout.isTTY` か `false` かという判断は共有せず、各コマンドが渡します。

### 2. CLI引数

両コマンドの `args.color` を同じ形にします。

```ts
type ColorArgs = {
  color: boolean | undefined;
};

type DeployArgs = ExistingDeployArgs & ColorArgs;
type PreviewArgs = ExistingPreviewArgs & ColorArgs;
```

CLIパーサーは、両フラグを同じプロパティへ割り当てます。

```text
未指定       → args.color === undefined
--color      → args.color === true
--no-color   → args.color === false
```

重要なのは、`--no-color` を `undefined` に変換したり、truthy判定で落としたりしないことです。

### 3. `deploy`

```ts
export function deployCommand(
  args: DeployArgs,
  ctx: CommandContext,
) {
  const output: OutputOptions = {
    color: resolveColor({
      cli: args.color,
      env: ctx.env.ACME_COLOR,
      file: ctx.config.ui?.color,
      defaultValue: ctx.stdout.isTTY,
    }),
  };

  return runDeploy(args, output);
}
```

デフォルトは従来どおり `ctx.stdout.isTTY` です。

### 4. `preview`

```ts
export function previewCommand(
  args: PreviewArgs,
  ctx: CommandContext,
) {
  const output: OutputOptions = {
    color: resolveColor({
      cli: args.color,
      env: ctx.env.ACME_COLOR,
      file: ctx.config.ui?.color,
      defaultValue: false,
    }),
  };

  return runPreview(args, output);
}
```

`preview` はTTYでも、全設定が未指定なら必ず `false` になります。`PreviewOutputOptions` のような別型は追加しません。

### 値の流れ

| 入力元 | 入力型 | 変換 | 解決時の型 |
|---|---|---|---|
| `--color` / `--no-color` | CLIパーサー入力 | `args.color` | `boolean \| undefined` |
| `ACME_COLOR` | `string \| undefined` | `parseBoolean` | `boolean \| undefined` |
| `ui.color` | 設定ファイル | 変換なし | `boolean \| undefined` |
| コマンド既定値 | コマンド内 | 変換なし | `boolean` |
| `resolveValue` の結果 | 上記4値 | 優先順位を適用 | `boolean` |
| 実行関数への引数 | 解決結果 | `{ color }` | `OutputOptions` |

### テストケース

共通処理のテーブルテストとして、最低限以下を置きます。

| CLI | env | file | default | 結果 |
|---:|---:|---:|---:|---:|
| `false` | `"true"` | `true` | `true` | `false` |
| `true` | `"false"` | `false` | `false` | `true` |
| `undefined` | `"false"` | `true` | `true` | `false` |
| `undefined` | `"1"` | `false` | `false` | `true` |
| `undefined` | `undefined` | `false` | `true` | `false` |
| `undefined` | `undefined` | `undefined` | `true` | `true` |
| `undefined` | `undefined` | `undefined` | `false` | `false` |

加えて次を確認します。

- `--no-color` が `args.color === false` になる。
- CLI未指定が `undefined` になる。
- `deploy` は全設定未指定かつTTYなら `color: true`。
- `preview` は全設定未指定かつTTYでも `color: false`。
- 両コマンドで `ACME_COLOR=invalid` が既存の `ConfigError` になる。
- `deploy` の既存挙動を厳密に維持するなら、CLI指定があっても不正な `ACME_COLOR` は `ConfigError` になる。
- `runDeploy` と `runPreview` が同じ `OutputOptions` を受け取る。

### help

両コマンドで、例えば次の記載に統一します。

```text
--color       Enable colored output
--no-color    Disable colored output

Color setting priority:
CLI flags > ACME_COLOR > ui.color > command default
```

`preview` には「command default is disabled」、`deploy` には「command default follows stdout TTY」を補足すると、優先順位を重複実装せず差異だけを明示できます。
