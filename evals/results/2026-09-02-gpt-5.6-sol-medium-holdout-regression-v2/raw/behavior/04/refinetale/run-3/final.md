変更案は、色設定の解決だけを共通関数にし、defaultの決定は各コマンドに残す構成です。これなら`deploy`の既存挙動を維持しつつ、コマンド別の型や分岐を増やしません。

## 変更契約

変更する挙動:

- `preview`が`--color`と`--no-color`を受け付ける。
- `preview`も`CLI > ACME_COLOR > ui.color > default`で解決する。
- `preview`のdefaultはTTYに関係なく`false`。

変更しない挙動:

- `deploy`の優先順位。
- `deploy`のdefaultである`ctx.stdout.isTTY`。
- `parseBoolean`が受理する値と、`ConfigError`を投げる挙動。
- 不正な`ACME_COLOR`は、CLI指定の有無にかかわらず検証される現在の評価順序。

共通処理:

- `ACME_COLOR`のパース。
- 4入力の優先順位解決。
- `{ color: boolean }`への正規化。

実際の差分:

- `deploy`が渡すdefault: `ctx.stdout.isTTY`
- `preview`が渡すdefault: `false`
- 最後に呼ぶ処理: `runDeploy` / `runPreview`

## 共通処理

`OutputOptions`と`parseBoolean`が現在置かれている共通モジュールに、次だけを追加します。

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

`envColor`は生の`string | undefined`で受け取ります。これにより、`parseBoolean`の呼び出しも両コマンドで一か所になります。

`resolveValue<boolean>`だけを直接共有し、各コマンドで`parseBoolean`とオブジェクト生成を繰り返す案は、設定経路が二重になるため避けます。一方、`CommandContext`やコマンド種別を共通関数へ渡す必要はありません。defaultの違いを共通関数内で分岐させないためです。

## コマンド側

```ts
export type DeployArgs = {
  // 既存フィールド
  color: boolean | undefined;
};

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
export type PreviewArgs = {
  // 既存フィールド
  color: boolean | undefined;
};

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

`PreviewOutputOptions`のような別型は追加せず、`runPreview`も共有の`OutputOptions`を受け取ります。

```ts
function runPreview(
  args: PreviewArgs,
  output: OutputOptions,
) {
  // ...
}
```

値の流れは次の一本です。

```text
CLIのcolor?: boolean ─┐
ACME_COLOR?: string ── parseBoolean ─┤
ui.color?: boolean ──────────────────┼─ resolveValue<boolean>
コマンド固有default: boolean ────────┘
                                      ↓
                            OutputOptions.color
                                      ↓
                           runDeploy / runPreview
```

## CLI境界

両フラグは同じ`args.color`へ正規化します。

```text
--color     → args.color = true
--no-color  → args.color = false
未指定      → args.color = undefined
```

重要なのは、`--no-color`をtruthy判定や`||`で処理しないことです。`resolveValue`は`undefined`だけを未指定とするため、`false`はそのまま最優先で採用されます。

CLIライブラリの定義では、両コマンドに同じ説明を設定します。

```text
--color       Enable colored output
--no-color    Disable colored output

Priority: --color/--no-color > ACME_COLOR > ui.color > command default
```

必要ならdefaultの差も各helpに明記します。

```text
deploy default: enabled when stdout is a TTY
preview default: disabled
```

## 最小テストケース

| 契約 | 入力 | 期待結果 |
|---|---|---|
| CLIが最優先 | `cliColor: true`, env `"false"`, file `false` | `color: true` |
| `--no-color`を未指定扱いしない | `cliColor: false`, env `"true"`, file `true`, default `true` | `color: false` |
| envがfileより優先 | CLI未指定、env `"false"`, file `true` | `color: false` |
| fileがdefaultより優先 | CLI・env未指定、file `false`, default `true` | `color: false` |
| `deploy`のdefault維持 | 全設定未指定、`stdout.isTTY: true/false` | それぞれ`true/false`で`runDeploy`を呼ぶ |
| `preview`のdefault | 全設定未指定、`stdout.isTTY: true` | `false`で`runPreview`を呼ぶ |
| 共通の失敗経路 | `ACME_COLOR="invalid"` | `ConfigError("invalid boolean: invalid")`、runnerは呼ばれない |
| 既存評価順序の維持 | CLI指定あり、`ACME_COLOR="invalid"` | 同じ`ConfigError`、runnerは呼ばれない |
| CLI境界 | `preview --color` / `preview --no-color` / 未指定 | `true` / `false` / `undefined` |
| help | `deploy --help`、`preview --help` | 両flag、優先順位、各defaultを表示 |

不正な環境変数のテストは、共有関数だけでなく両コマンドについて「runnerが呼ばれない」ことを確認します。これが`ConfigError`の伝播と副作用抑止を直接保証します。

今回はリポジトリが空で読み取り専用だったため、実装・テスト実行・`.agent/CONTINUITY.md`および`referytale`対応表の作成は行っていません。上記は提示されたコードを正本とした変更案です。
