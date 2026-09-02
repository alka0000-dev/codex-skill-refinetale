変更案は、色設定の解決だけを共有関数へ抽出し、コマンドごとの差はデフォルト値として渡す形です。これなら`deploy`の評価順序・例外・デフォルトを維持できます。

なお、作業ディレクトリにはコードが存在しなかったため、以下のファイル名は配置例です。

### 1. 共通の出力設定解決

```ts
// output-options.ts

export type OutputOptions = {
  color: boolean;
};

export function resolveOutputOptions(
  cliColor: boolean | undefined,
  ctx: CommandContext,
  defaultColor: boolean,
): OutputOptions {
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

共有範囲は次の3点だけです。

- `ACME_COLOR`を`parseBoolean`で検証・変換する
- `CLI > ACME_COLOR > ui.color > default`の順に解決する
- 結果を既存の`OutputOptions`へ格納する

`OutputOptions`、`parseBoolean`、`resolveValue`は共通のままです。`DeployOutputOptions`や`PreviewOutputOptions`のようなコマンド別型は追加しません。

重要なのは、`parseBoolean(ctx.env.ACME_COLOR)`を`resolveValue`の引数評価時に実行している点です。現在の`deploy`と同じく、CLI値が指定されていても環境変数が不正なら`ConfigError`になります。

### 2. コマンドからデフォルト値を渡す

```ts
// deploy.ts

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
// preview.ts

export function previewCommand(args: PreviewArgs, ctx: CommandContext) {
  const output = resolveOutputOptions(
    args.color,
    ctx,
    false,
  );

  return runPreview(args, output);
}
```

引数型には同じプロパティを追加します。

```ts
type DeployArgs = {
  // 既存プロパティ
  color?: boolean;
};

type PreviewArgs = {
  // 既存プロパティ
  color?: boolean;
};
```

コマンド別の引数型自体は既存ですが、`color`の表現は両方とも`boolean | undefined`です。

### 3. CLIパーサー

CLIライブラリ固有の記法は既存実装へ合わせますが、パース結果は必ず次の形にします。

| 入力 | `args.color` |
|---|---:|
| 指定なし | `undefined` |
| `--color` | `true` |
| `--no-color` | `false` |

Commander系なら、たとえば以下のようなnegatable optionにできます。

```ts
.option("--color", "Enable color output")
.option("--no-color", "Disable color output")
```

パーサー設定によって未指定時に`true`や`false`が自動設定されないことを確認します。未指定は必ず`undefined`でなければ、環境変数や設定ファイルへフォールバックできません。

### 4. 値の流れ

```text
--color / --no-color
  ↓ boolean | undefined
args.color
  ┐
ACME_COLOR: string | undefined
  ↓ parseBoolean()
  ↓ boolean | undefined、またはConfigError
ctx.env
  ├→ resolveValue<boolean>()
ctx.config.ui?.color
  ↓ boolean | undefined
default
  ┘
  ↓ boolean
OutputOptions.color
  ↓
runDeploy / runPreview
```

デフォルトだけがコマンドごとに異なります。

- `deploy`: `ctx.stdout.isTTY`
- `preview`: 常に`false`

### 5. help

両コマンドに以下を表示します。

```text
--color       Enable color output
--no-color    Disable color output

Color precedence:
  CLI (--color/--no-color) > ACME_COLOR > ui.color > default
```

加えてデフォルトの違いを明記します。

```text
deploy default: stdout.isTTY
preview default: false
```

### 6. テストケース

共通resolverのテーブルテスト:

| CLI | env | file | default | 結果 |
|---:|---:|---:|---:|---:|
| `true` | `false` | `false` | `false` | `true` |
| `false` | `true` | `true` | `true` | `false` |
| `undefined` | `true` | `false` | `false` | `true` |
| `undefined` | `false` | `true` | `true` | `false` |
| `undefined` | `undefined` | `true` | `false` | `true` |
| `undefined` | `undefined` | `undefined` | `true` | `true` |
| `undefined` | `undefined` | `undefined` | `false` | `false` |

CLIパーサー:

```ts
expect(parsePreviewArgs([]).color).toBeUndefined();
expect(parsePreviewArgs(["--color"]).color).toBe(true);
expect(parsePreviewArgs(["--no-color"]).color).toBe(false);
```

コマンド統合テスト:

```ts
it("previewはTTYでもデフォルトでcolor=false", () => {
  const ctx = createContext({ isTTY: true });

  previewCommand(createPreviewArgs(), ctx);

  expect(runPreview).toHaveBeenCalledWith(
    expect.anything(),
    { color: false },
  );
});

it("deployは従来どおりTTYをデフォルトにする", () => {
  const ctx = createContext({ isTTY: true });

  deployCommand(createDeployArgs(), ctx);

  expect(runDeploy).toHaveBeenCalledWith(
    expect.anything(),
    { color: true },
  );
});

it("--no-colorは未指定ではなくfalseとして最優先される", () => {
  const ctx = createContext({
    env: { ACME_COLOR: "true" },
    config: { ui: { color: true } },
  });

  previewCommand(createPreviewArgs({ color: false }), ctx);

  expect(runPreview).toHaveBeenCalledWith(
    expect.anything(),
    { color: false },
  );
});
```

不正な環境変数は両コマンドで確認します。

```ts
it.each([
  ["deploy", deployCommand, createDeployArgs],
  ["preview", previewCommand, createPreviewArgs],
])("%sは不正なACME_COLORをConfigErrorにする", (_, command, createArgs) => {
  const ctx = createContext({
    env: { ACME_COLOR: "yes" },
  });

  expect(() => command(createArgs(), ctx))
    .toThrow(new ConfigError("invalid boolean: yes"));
});
```

さらに`deploy`の既存挙動を厳密に固定するなら、CLI指定があっても不正な環境変数を検証するケースを残します。

```ts
expect(() =>
  deployCommand(
    createDeployArgs({ color: true }),
    createContext({ env: { ACME_COLOR: "yes" } }),
  ),
).toThrow(ConfigError);
```

この構成では、共通化によって隠れるのは「色設定の取得と優先順位」だけで、各コマンド固有のデフォルトと実行処理は各コマンド内に残ります。
