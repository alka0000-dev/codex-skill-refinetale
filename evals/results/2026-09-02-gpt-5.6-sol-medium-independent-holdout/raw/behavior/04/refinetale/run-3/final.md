## 変更契約

変更する挙動:

- `preview`が`--color`と`--no-color`を受け付ける。
- `preview`も `CLI > ACME_COLOR > ui.color > default` で色設定を解決する。
- `preview`のdefaultは常に`false`。

変更しない挙動:

- `deploy`の優先順位を維持する。
- `deploy`のdefaultは引き続き`ctx.stdout.isTTY`。
- `ACME_COLOR`の不正値は、CLI指定の有無にかかわらず`ConfigError`になる。
- `false`は有効な指定値であり、後続の値へfallbackしない。

## 実装案

共通の出力設定モジュールへ`OutputOptions`と新しいresolverを置きます。`resolveValue`と既存の`parseBoolean`はそのまま再利用します。

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

`envColor`を先に評価するのが重要です。これにより、`cliColor`が指定されていても不正な`ACME_COLOR`を従来どおり`ConfigError`にします。

`deploy`はdefaultだけを渡します。

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

`preview`も同じ経路へ入り、実際に異なるdefaultだけを`false`にします。

```ts
export function previewCommand(args: PreviewArgs, ctx: CommandContext) {
  const output = resolveOutputOptions({
    cliColor: args.color,
    ctx,
    defaultColor: false,
  });

  return runPreview(args, output);
}
```

値の流れは次の1経路です。

```text
--color / --no-color
        │
        ▼
args.color: boolean | undefined ───────┐
                                       │
ACME_COLOR: string | undefined         │
        │                              │
        ▼                              ▼
parseBoolean() ───────────────► resolveOutputOptions()
                                       ▲
ui.color: boolean | undefined ─────────┤
                                       │
deploy: stdout.isTTY                    │
preview: false ─────────────────────────┘
                                       │
                                       ▼
                         OutputOptions { color: boolean }
                                       │
                           ┌───────────┴───────────┐
                           ▼                       ▼
                     runDeploy()              runPreview()
```

新しいコマンド別出力型やstrategy、コマンド名による分岐は追加しません。差異は呼び出し側の`defaultColor`だけです。

## CLI定義

`PreviewArgs`の`color`は、`DeployArgs`と同じ表現にします。

```ts
type PreviewArgs = {
  // 既存フィールド
  color: boolean | undefined;
};
```

CLI parserでは以下を保証します。

```text
未指定      -> undefined
--color     -> true
--no-color  -> false
```

未指定時にparser側で`false`をdefault設定してはいけません。それをすると環境変数と設定ファイルへfallbackできなくなります。両flagが同時指定された場合の扱いは、新しい規則を作らず既存の`deploy`と同じparser設定を再利用します。

両コマンドのhelpには、少なくとも次を記載します。

```text
--color       Enable colored output
--no-color    Disable colored output

Priority: --color/--no-color > ACME_COLOR > ui.color > default.
Default: deploy uses stdout TTY; preview disables color.
```

## 最小テストケース

共通resolverのテスト:

| CLI | 環境変数 | file | default | 結果 |
|---:|---:|---:|---:|---:|
| `false` | `"true"` | `true` | `true` | `false` |
| `undefined` | `"false"` | `true` | `true` | `false` |
| `undefined` | `undefined` | `false` | `true` | `false` |
| `undefined` | `undefined` | `undefined` | `true` | `true` |

最初のケースが、`--no-color`を未指定扱いしないことを直接保証します。

さらに、resolverへ次を追加します。

```ts
expect(() =>
  resolveOutputOptions({
    cliColor: true,
    ctx: contextWithEnv({ ACME_COLOR: "invalid" }),
    defaultColor: false,
  }),
).toThrow(ConfigError);
```

CLI・コマンド結合テスト:

- `preview --color` → `args.color === true`
- `preview --no-color` → `args.color === false`
- flag未指定 → `args.color === undefined`
- TTY上で全入力未指定の`preview` → `runPreview(..., { color: false })`
- `ACME_COLOR=true`の`preview` → `{ color: true }`
- 不正な`ACME_COLOR`の`preview` → `ConfigError`
- TTY上で全入力未指定の`deploy` → 従来どおり`{ color: true }`
- 不正な`ACME_COLOR`の`deploy` → 従来どおり`ConfigError`
- 両コマンドのhelp → 両flagと優先順位を含む

実際のソースとテストは作業ディレクトリに存在しなかったため、実行検証はできませんでした。上記が実装時に必要な最小検証です。`refinetale`の観点では、新規要素を共通の`resolveOutputOptions`一つに限定し、コマンド間の差異をdefault値だけに閉じ込めています。なお、`referytale`指定の一時対応表は読み取り専用環境のため作成できず、追加の抽象語・型は導入しない形で代替しました。
