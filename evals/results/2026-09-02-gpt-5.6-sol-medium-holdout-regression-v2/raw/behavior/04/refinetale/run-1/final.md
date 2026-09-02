変更案は、色設定の解決だけを共通関数へ移し、コマンド固有差分をデフォルト値だけに限定する形が最小です。`command === "preview"`のような分岐や、コマンド別の出力型は追加しません。

## 変更契約

変更する挙動:

- `preview`が`--color`と`--no-color`を受け付ける。
- `preview`も`CLI > ACME_COLOR > ui.color > default`で解決する。
- `preview`のdefaultは常に`false`。

変更しない挙動:

- `deploy`の優先順位とdefaultの`stdout.isTTY`。
- `--no-color`が明示的な`false`として最優先になること。
- `ACME_COLOR`の変換規則と、不正値で`ConfigError`を投げること。
- 最終的に両コマンドが共通の`OutputOptions`を受け取ること。

## 共通処理

既存の`OutputOptions`と`parseBoolean`がある共通モジュールに、次だけを追加します。

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

`defaultColor`はコマンド間に実在する唯一の差分です。コマンド名、strategy、`isPreview`などは不要です。

また、`parseBoolean`は`resolveValue`より先に評価されるため、CLI値が指定されていても不正な`ACME_COLOR`は従来どおり`ConfigError`になります。これは`deploy`の既存挙動を維持するうえで重要です。

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
  // 既存フィールド
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

`PreviewOutputOptions`や`DeployOutputOptions`は作りません。`runPreview`と`runDeploy`はいずれも共通の`OutputOptions`を受け取ります。

## CLI境界

両フラグを別々の状態にせず、同じ`color?: boolean`へ正規化します。

| 入力 | `args.color` |
|---|---:|
| 未指定 | `undefined` |
| `--color` | `true` |
| `--no-color` | `false` |

CLIパーサーにはdefaultを設定しません。ここで`false`をdefaultにすると、未指定でもCLIが設定ファイルや環境変数を上書きしてしまいます。

helpは各コマンドで明示します。

```text
--color / --no-color
  Color output. Precedence: CLI > ACME_COLOR > ui.color > command default.
```

可能ならコマンド固有のdefaultも併記します。

```text
deploy:  command default is stdout.isTTY
preview: command default is false
```

フラグ登録の共通化は、既存CLIフレームワークに共通optionの規約がある場合だけ行います。今回共有すべき本質は値の解決経路であり、2箇所の宣言を隠すためだけの登録ヘルパーは不要です。

## 値の流れ

```text
--color / --no-color
        │ boolean | undefined
        ▼
   args.color ───────────────┐
                             │
ACME_COLOR                   │
 string | undefined          │
        │                    │
        ▼                    │
 parseBoolean                │
 boolean | undefined ────────┤
                             ├─ resolveValue<boolean>
ui.color                     │
 boolean | undefined ────────┤
                             │
deploy: stdout.isTTY         │
preview: false ──────────────┘
                             │
                             ▼
                  OutputOptions.color
                         boolean
                             │
                   ┌─────────┴─────────┐
                   ▼                   ▼
               runDeploy           runPreview
```

## 最小テストケース

| 契約 | テスト入力 | 期待結果 |
|---|---|---|
| `--no-color`を未指定扱いしない | CLI=`false`, env/file/default=`true` | `color === false` |
| CLI優先 | CLI=`true`, env/file=`false` | `color === true` |
| 環境変数優先 | CLI未指定、env=`"false"`、file=`true` | `color === false` |
| ファイル優先 | CLI/env未指定、file=`true`、default=`false` | `color === true` |
| `deploy`のdefault維持 | 全入力未指定、TTY=`true` | `runDeploy`へ`{color:true}` |
| `preview`のdefault差分 | 全入力未指定、TTY=`true` | `runPreview`へ`{color:false}` |
| `deploy`の失敗経路維持 | CLI=`true`、env=`"invalid"` | `ConfigError`、`runDeploy`未呼び出し |
| `preview`の失敗経路 | env=`"invalid"` | `ConfigError`、`runPreview`未呼び出し |
| CLI境界 | `preview --color` / `--no-color` / 未指定 | `true` / `false` / `undefined` |
| help | 両コマンドのhelp | 両flagと優先順位を含む |

`resolveValue`自体の全組み合わせテストや、`parseBoolean`の既存ケースは重複追加しません。今回必要なのは、共通resolverとの接続、コマンドごとのdefault差分、CLIの`false`正規化、失敗時に実行処理へ進まないことの検証です。

なお、作業ディレクトリには実装ファイルやテストが存在しなかったため、上記は提示されたコードを正本とした具体案であり、実行検証は未実施です。
