結論として、共通化するのは「4つの入力から`OutputOptions.color`を解決する処理」だけにします。コマンド差分は`defaultColor`のみです。`deploy` / `preview`を判定する分岐やコマンド別の出力型は不要です。

## 変更契約

変更する挙動:

- `preview`が`--color` / `--no-color`を受け取る。
- `preview`もCLI > `ACME_COLOR` > `ui.color` > defaultで解決する。
- `preview`のdefaultはTTYに関係なく`false`。

変更しない挙動:

- `deploy`の優先順位。
- `deploy`のdefaultである`stdout.isTTY`。
- `--no-color`を明示値`false`として扱うこと。
- `parseBoolean`の受理値と`ConfigError`。
- 不正な`ACME_COLOR`は、CLI値が指定されていてもエラーになる既存の評価順序。

## 共通処理

`OutputOptions`をdeploy固有の場所から共通の出力設定モジュールへ移し、次の関数を追加します。ファイル名は既存構成に合わせますが、例として`output-options.ts`とします。

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

`parseBoolean(envColor)`は`resolveValue`を呼ぶ前に評価されます。このため、`cliColor`が指定済みでも不正な環境変数が`ConfigError`になる現在の`deploy`の挙動を維持できます。遅延評価や「CLIがあれば環境変数をparseしない」という分岐は追加しません。

既存の`resolveValue`と`parseBoolean`自体は変更不要です。

## コマンド側

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
```

```ts
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

型は以下の関係にします。

```ts
type PreviewArgs = {
  // 既存フィールド
  color: boolean | undefined;
};
```

`DeployArgs.color`も同じ`boolean | undefined`を維持します。コマンド別の`PreviewOutputOptions`などは作りません。

値の経路は一本です。

```text
CLI parser
  --color    → args.color = true
  --no-color → args.color = false
  未指定     → args.color = undefined
                         │
ACME_COLOR: string | undefined
ui.color: boolean | undefined
command default: boolean
                         │
             resolveOutputOptions
                         │
              OutputOptions.color
                         │
             runDeploy / runPreview
```

CLIライブラリのnegatable option機能を使い、両flagを同じ`args.color`へ格納します。`noColor`のような別フィールドを作って後から合成すると、同じ概念の状態と分岐が増えるため避けます。

## help

両コマンドのhelpに、少なくとも次を記載します。

```text
--color       Enable colored output
--no-color    Disable colored output

Priority: CLI flag > ACME_COLOR > ui.color > command default.
deploy defaults to TTY detection; preview defaults to no color.
```

共通help断片が既にあるなら共有します。ただし、この2行だけのために新しいhelp生成抽象化を追加する必要はありません。

## 最小テストケース

共有resolverの単体テスト:

| 入力 | 期待値 |
|---|---:|
| CLI=`false`, env=`"true"`, file=`true`, default=`true` | `false` |
| CLI=`undefined`, env=`"false"`, file=`true`, default=`true` | `false` |
| CLI/env=`undefined`, file=`false`, default=`true` | `false` |
| 全入力未指定、default=`true` | `true` |
| 全入力未指定、default=`false` | `false` |
| env=`"invalid"` | `ConfigError` |
| CLI=`true`, env=`"invalid"` | `ConfigError` |

コマンド結合テスト:

- `deploy`: 全設定未指定かつTTYなら`runDeploy`へ `{ color: true }`。既存挙動の回帰確認。
- `preview`: 全設定未指定かつTTYでも`runPreview`へ `{ color: false }`。
- `preview --no-color`: env/fileが`true`でも`runPreview`へ `{ color: false }`。
- `preview --color`: env/fileが`false`でも`runPreview`へ `{ color: true }`。
- `deploy`と`preview`: `ACME_COLOR`が不正なら、それぞれ`ConfigError`となり実行関数は呼ばれない。
- CLI parser: `--color`→`true`、`--no-color`→`false`、未指定→`undefined`。
- help: 両flag、優先順位、コマンドごとのdefaultを含む。

作業ツリーには対象実装やテストが存在せず、Gitにもコミットがないため、実テストは未実施です。実装ファイルが提供された場合は、上記ケースを既存テストの最も低い責務へ配置して検証できます。なお、`referytale`が要求する対応表の保存も読み取り専用環境のため実施できませんでした。
