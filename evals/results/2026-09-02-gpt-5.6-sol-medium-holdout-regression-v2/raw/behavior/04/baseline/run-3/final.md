変更の中心は、`color`の解決だけを共通関数へ切り出し、コマンド固有のdefaultは各コマンドから渡す形です。これなら`deploy`の挙動を維持しつつ、`preview`へ同じ優先順位を適用できます。

## 共有する処理

`OutputOptions`、環境変数の変換、既存の`resolveValue`呼び出しを同じモジュールへ置きます。

```ts
export type OutputOptions = {
  color: boolean;
};

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

入力用のコマンド別型は追加しません。`DeployOutputOptions`や`PreviewOutputOptions`も作らず、両方が同じ`OutputOptions`を使用します。

`parseBoolean(envColor)`は`resolveValue`より先に評価されるため、CLI指定が存在していても`ACME_COLOR`が不正なら従来どおり`ConfigError`になります。これは現在の`deploy`と同じ挙動です。

## CLI引数

既存の`DeployArgs`と`PreviewArgs`に、それぞれ同じプロパティを持たせます。

```ts
type DeployArgs = {
  // 既存項目
  color: boolean | undefined;
};

type PreviewArgs = {
  // 既存項目
  color: boolean | undefined;
};
```

CLIパーサーでは次の値へ正規化します。

| 入力 | `args.color` |
|---|---:|
| `--color` | `true` |
| `--no-color` | `false` |
| どちらも未指定 | `undefined` |

特に`--no-color`を`undefined`へ変換しないことが必要です。`false`は`resolveValue`の最優先値として扱われます。

## コマンドからの値の流れ

```ts
export function deployCommand(args: DeployArgs, ctx: CommandContext) {
  const output = resolveOutputOptions({
    cliColor: args.color,
    envColor: ctx.env.ACME_COLOR,
    fileColor: ctx.config.ui?.color,
    defaultColor: ctx.stdout.isTTY,
  });

  return runDeploy(args, output);
}

export function previewCommand(args: PreviewArgs, ctx: CommandContext) {
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

```text
CLI parser
  --color / --no-color
  ↓ boolean | undefined
args.color
  ┐
ctx.env.ACME_COLOR ─ string | undefined → parseBoolean
  ├→ resolveValue → OutputOptions.color: boolean
ctx.config.ui?.color ─ boolean | undefined
  │
コマンド固有default ┘
```

共有するのは「環境変数をbooleanへ変換し、CLI > 環境変数 > 設定ファイル > defaultで`OutputOptions`を作る部分」までです。`deploy`と`preview`の実行処理やdefault値は共有しません。

## Help

両コマンドに両方のflagを載せます。

```text
--color       Enable colored output
--no-color    Disable colored output
```

加えて、各コマンドのhelpへ優先順位とdefaultを明記します。

```text
Color precedence:
  --color/--no-color > ACME_COLOR > ui.color > command default
```

- `deploy`: `Default: enabled when stdout is a TTY.`
- `preview`: `Default: disabled, including when stdout is a TTY.`

## テストケース

最低限、次を固定します。

### CLIパーサー

- `--color` → `args.color === true`
- `--no-color` → `args.color === false`
- 未指定 → `args.color === undefined`

### 共通の解決処理

| CLI | 環境変数 | ファイル | default | 結果 |
|---:|---:|---:|---:|---:|
| `false` | `"true"` | `true` | `true` | `false` |
| `true` | `"false"` | `false` | `false` | `true` |
| `undefined` | `"false"` | `true` | `true` | `false` |
| `undefined` | `undefined` | `false` | `true` | `false` |
| `undefined` | `undefined` | `undefined` | `true` | `true` |

さらに`envColor: "yes"`などで`ConfigError("invalid boolean: yes")`になることを確認します。CLIが指定されている場合にも不正な環境変数で例外になるテストを残すと、既存`deploy`の評価順序を保護できます。

### コマンド固有default

- `deploy`、全指定なし、`stdout.isTTY === true` → `color === true`
- `deploy`、全指定なし、`stdout.isTTY === false` → `color === false`
- `preview`、全指定なし、`stdout.isTTY === true` → `color === false`
- `preview`、全指定なし、`stdout.isTTY === false` → `color === false`
- `preview --no-color`かつ環境変数・設定ファイルが`true` → `false`
- `deploy`と`preview`の不正な`ACME_COLOR` → どちらも既存の`ConfigError`
- `runDeploy`と`runPreview`へ同じ`OutputOptions`が渡される

なお、作業ディレクトリにはソースファイルがなく読み取り専用だったため、実ファイル名に紐づけた差分確認と、`referytale`が要求する対応表の保存は実施できませんでした。上記は提示されたコードを一次情報とした変更案です。
