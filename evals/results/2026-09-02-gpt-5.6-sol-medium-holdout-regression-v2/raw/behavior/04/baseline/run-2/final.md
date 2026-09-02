提案は、色設定の解決だけを共通関数へ切り出し、コマンド固有のdefaultは呼び出し側に残す形です。これなら`deploy`の挙動を維持しつつ、`preview`だけ常にdefaultを`false`にできます。

※作業ディレクトリに実装ファイルがなかったため、提示コードを前提にした変更案です。

### 共通処理

```ts
export type OutputOptions = {
  color: boolean;
};

export function resolveOutputOptions(
  args: { color: boolean | undefined },
  ctx: CommandContext,
  defaultColor: boolean,
): OutputOptions {
  return {
    color: resolveValue({
      cli: args.color,
      // resolveValueより先に評価することで、既存deployと同様、
      // CLI指定があっても不正値はConfigErrorになる
      env: parseBoolean(ctx.env.ACME_COLOR),
      file: ctx.config.ui?.color,
      defaultValue: defaultColor,
    }),
  };
}
```

共有するのは以下だけです。

- `args.color`、`ACME_COLOR`、`ui.color`の取得
- `parseBoolean`による環境変数の検証
- `resolveValue`による優先順位
- `OutputOptions`の生成

`stdout.isTTY`を使うかどうかは共有関数に判断させません。

### CLI引数の型

既存のコマンド引数型へ同じフィールドを追加します。別の出力型は作りません。

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

CLIパーサーには次の契約を持たせます。

| CLI入力 | `args.color` |
|---|---:|
| `--color` | `true` |
| `--no-color` | `false` |
| どちらも未指定 | `undefined` |

特に、パーサー側で未指定時のdefaultを設定しないことが重要です。`false`をtruthy/falsy判定せず、`undefined`との比較で指定有無を判定します。

### コマンドからの呼び出し

```ts
export function deployCommand(args: DeployArgs, ctx: CommandContext) {
  const output = resolveOutputOptions(
    args,
    ctx,
    ctx.stdout.isTTY,
  );

  return runDeploy(args, output);
}
```

```ts
export function previewCommand(args: PreviewArgs, ctx: CommandContext) {
  const output = resolveOutputOptions(
    args,
    ctx,
    false,
  );

  return runPreview(args, output);
}
```

値の流れは次のとおりです。

```text
--color / --no-color
        ↓ boolean | undefined
  DeployArgs / PreviewArgs
        ↓
resolveOutputOptions(args, ctx, commandDefault)
        ├─ args.color
        ├─ parseBoolean(ctx.env.ACME_COLOR)
        ├─ ctx.config.ui?.color
        └─ deploy: ctx.stdout.isTTY / preview: false
        ↓
resolveValue<boolean>
        ↓ boolean
OutputOptions.color
        ↓
runDeploy / runPreview
```

### テストケース

共通関数のテーブルテストで優先順位を固定します。

| CLI | env | file | default | 結果 |
|---:|---:|---:|---:|---:|
| `true` | `false` | `false` | `false` | `true` |
| `false` | `true` | `true` | `true` | `false` |
| `undefined` | `"true"` | `false` | `false` | `true` |
| `undefined` | `"false"` | `true` | `true` | `false` |
| `undefined` | `undefined` | `true` | `false` | `true` |
| `undefined` | `undefined` | `false` | `true` | `false` |
| `undefined` | `undefined` | `undefined` | `true` | `true` |
| `undefined` | `undefined` | `undefined` | `false` | `false` |

加えて、次をコマンド単位で確認します。

```ts
describe("deployCommand", () => {
  it("設定がないTTYではcolorをtrueにする");
  it("設定がない非TTYではcolorをfalseにする");
  it("--no-colorを明示的なfalseとして扱う");
  it("ACME_COLORが不正ならConfigErrorを投げる");
  it("CLI指定があってもACME_COLORが不正ならConfigErrorを投げる");
});

describe("previewCommand", () => {
  it("設定がないTTYでもcolorをfalseにする");
  it("--colorでcolorをtrueにする");
  it("--no-colorを明示的なfalseとして扱う");
  it("ACME_COLORが不正ならConfigErrorを投げる");
  it("CLI指定があってもACME_COLORが不正ならConfigErrorを投げる");
});
```

最後の「CLI指定があっても不正な環境変数を拒否する」は、現在の`deploy`が`resolveValue`へ渡す前に`parseBoolean`を評価している挙動を維持するための回帰テストです。

### help更新

両コマンドに以下を掲載します。

```text
--color       Enable color output
--no-color    Disable color output

Color precedence:
  CLI (--color/--no-color) > ACME_COLOR > ui.color > command default
```

defaultの説明はコマンドごとに変えます。

```text
deploy default: enabled when stdout is a TTY
preview default: disabled
```

この境界なら、`OutputOptions`と`parseBoolean`は完全に共有され、優先順位も一か所に集約されます。一方、コマンド固有のdefaultや実行処理までは共通化しないため、`deploy`への影響を限定できます。
