変更案は、4つの値から `OutputOptions` を組み立てる部分だけを共通化します。CLIの解析、コマンド固有のデフォルト値、実行処理は各コマンドに残します。

リポジトリには実装ファイルが存在しなかったため、以下のパス名は構成例です。また、読み取り専用環境のため変更は加えていません。

### 値の流れ

| 入力元 | 入力型 | 変換 | 共通処理へ渡す型 |
|---|---:|---|---:|
| `--color` | CLI flag | `args.color = true` | `boolean \| undefined` |
| `--no-color` | CLI flag | `args.color = false` | `boolean \| undefined` |
| CLI未指定 | CLI parser | `args.color = undefined` | `boolean \| undefined` |
| `ACME_COLOR` | `string \| undefined` | `parseBoolean` | `boolean \| undefined` |
| `ui.color` | config | 変換なし | `boolean \| undefined` |
| command default | command | `deploy`: `stdout.isTTY`、`preview`: `false` | `boolean` |
| 解決結果 | `resolveValue` | CLI → env → file → default | `OutputOptions` |

`false` は `undefined` と区別されるため、既存の `resolveValue` のままで `--no-color` が正しく最優先になります。

### 共通処理

```ts
export type OutputOptions = {
  color: boolean;
};

export function resolveOutputOptions({
  cli,
  env,
  file,
  defaultValue,
}: {
  cli: boolean | undefined;
  env: string | undefined;
  file: boolean | undefined;
  defaultValue: boolean;
}): OutputOptions {
  const parsedEnv = parseBoolean(env);

  return {
    color: resolveValue({
      cli,
      env: parsedEnv,
      file,
      defaultValue,
    }),
  };
}
```

ここで共通化するのは次の2点だけです。

- `ACME_COLOR` を既存の `parseBoolean` で変換する
- 4つの値を既存の `resolveValue` に同じ順序で渡し、`OutputOptions` を作る

`parsedEnv` を先に評価するため、不正な `ACME_COLOR` はCLI値の有無にかかわらず従来どおり `ConfigError` になります。これは現在の `deploy` の評価動作を維持します。

### コマンド側

`DeployArgs` は変更不要です。`PreviewArgs` に同じプロパティだけを追加し、コマンド別の出力型は作りません。

```ts
type PreviewArgs = {
  // 既存のプロパティ
  color?: boolean;
};
```

`deploy` は既存のデフォルトをそのまま渡します。

```ts
export function deployCommand(args: DeployArgs, ctx: CommandContext) {
  const output = resolveOutputOptions({
    cli: args.color,
    env: ctx.env.ACME_COLOR,
    file: ctx.config.ui?.color,
    defaultValue: ctx.stdout.isTTY,
  });

  return runDeploy(args, output);
}
```

`preview` はTTYに関係なく `false` を渡します。

```ts
export function previewCommand(args: PreviewArgs, ctx: CommandContext) {
  const output = resolveOutputOptions({
    cli: args.color,
    env: ctx.env.ACME_COLOR,
    file: ctx.config.ui?.color,
    defaultValue: false,
  });

  return runPreview(args, output);
}
```

必要なら `runPreview` のシグネチャを次のように変更します。

```ts
function runPreview(
  args: PreviewArgs,
  output: OutputOptions,
): ReturnTypeOfPreview {
  // ...
}
```

`PreviewOutputOptions` のような別型は追加しません。

### CLI parser

利用しているCLIライブラリに合わせて、次の対応を保証します。

```ts
--color     => args.color === true
--no-color  => args.color === false
未指定      => args.color === undefined
```

特に「未指定時に暗黙で `true` または `false` を入れる」設定は避けます。CLIライブラリによっては否定形オプション単独の登録でデフォルトが変わるため、parser単体テストで上記3状態を固定します。

両方を同時指定した場合の扱いは、`deploy` が現在採用している既存のparser規則をそのまま使い、新しい競合規則は導入しません。

### help

両コマンドに以下を掲載します。

```text
--color       Enable colored output
--no-color    Disable colored output

Priority: --color/--no-color > ACME_COLOR > ui.color > command default
```

さらにデフォルトだけコマンド別にします。

```text
deploy default: enabled when stdout is a TTY
preview default: disabled, including when stdout is a TTY
```

### テストケース

共通処理の表形式テスト:

| CLI | env | file | default | 期待値 |
|---:|---:|---:|---:|---:|
| `true` | `"false"` | `false` | `false` | `true` |
| `false` | `"true"` | `true` | `true` | `false` |
| `undefined` | `"false"` | `true` | `true` | `false` |
| `undefined` | `"1"` | `false` | `false` | `true` |
| `undefined` | `undefined` | `false` | `true` | `false` |
| `undefined` | `undefined` | `undefined` | `true` | `true` |
| `undefined` | `undefined` | `undefined` | `false` | `false` |

追加の境界テスト:

- `parseBoolean("yes")` は既存の `ConfigError`
- `deploy` は不正な環境変数値で `ConfigError`
- `preview` も同じ不正値で `ConfigError`
- CLI値が指定されていても、不正な環境変数値は従来どおり `ConfigError`
- `deploy` は全設定未指定かつTTYなら `color: true`
- `deploy` は全設定未指定かつ非TTYなら `color: false`
- `preview` は全設定未指定ならTTYでも `color: false`
- `preview --color` はTTY状態にかかわらず `true`
- `preview --no-color` はenv・fileが `true` でも `false`
- parser単体で、未指定／`--color`／`--no-color` がそれぞれ `undefined`／`true`／`false`
- 両コマンドのhelpに両flag、優先順位、コマンド固有defaultが含まれる

この分け方なら、`deploy` の既存動作を固定したまま、両コマンドで共有するのは環境変数の変換と優先順位の適用だけです。
