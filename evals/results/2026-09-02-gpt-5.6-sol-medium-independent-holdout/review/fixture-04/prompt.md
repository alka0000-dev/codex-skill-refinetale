You are grading six anonymized answers to an independent holdout evaluation. Return only the requested structured result.

# 04: Share CLI color resolution

## Purpose

共通の設定解決経路を再利用し、コマンド間の実差分だけをdefaultへ限定できるか確認する。

## Input

`preview`コマンドにも`--color` / `--no-color`を追加してください。既存の設定優先順位と`deploy`の挙動を変えず、2コマンドで必要な共通処理だけを共有する変更案を示してください。値がどこからどこへ渡るか、型とテストケースが分かる程度に具体化してください。

共通resolver:

```ts
export function resolveValue<T>({
  cli,
  env,
  file,
  defaultValue,
}: {
  cli: T | undefined;
  env: T | undefined;
  file: T | undefined;
  defaultValue: T;
}): T {
  if (cli !== undefined) return cli;
  if (env !== undefined) return env;
  if (file !== undefined) return file;
  return defaultValue;
}
```

既存のboolean parser:

```ts
export function parseBoolean(value: string | undefined): boolean | undefined {
  if (value === undefined) return undefined;
  if (value === "true" || value === "1") return true;
  if (value === "false" || value === "0") return false;
  throw new ConfigError(`invalid boolean: ${value}`);
}
```

現在の`deploy`:

```ts
type OutputOptions = { color: boolean };

export function deployCommand(args: DeployArgs, ctx: CommandContext) {
  const output: OutputOptions = {
    color: resolveValue({
      cli: args.color,
      env: parseBoolean(ctx.env.ACME_COLOR),
      file: ctx.config.ui?.color,
      defaultValue: ctx.stdout.isTTY,
    }),
  };
  return runDeploy(args, output);
}
```

新要件:

- `preview`でもCLI > `ACME_COLOR` > `ui.color` > defaultの優先順位を使う。
- `--no-color`は`false`であり、未指定として扱わない。
- `deploy`のdefaultは従来どおり`stdout.isTTY`、`preview`はTTYでも`false`。
- `OutputOptions`と`parseBoolean`は両コマンドで共通。コマンドごとの別型を追加しない。
- 不正な環境変数値はどちらでも既存の`ConfigError`にする。
- helpには両flagと優先順位を記載する。

## Pass conditions

- **S1 Precedence reuse:** 両commandが`resolveValue`と`parseBoolean`を通り、手書き優先順位やcommand固有parserを追加しない。
- **S2 Preserve false:** `undefined`と`false`を区別し、各層の明示的falseを下位値へfall throughさせない。
- **S3 Isolate real variation:** deployはTTY、previewはfalseというdefault差だけを引数または呼び出し位置で表現し、deployを変えない。
- **S4 Type and data path:** `OutputOptions`を共用し、解決済み`color`を既存出力処理へ一度だけ渡し、並行する設定状態やcommand固有型を作らない。
- **S5 Verification and help:** 優先順位、明示的false、不正env、各default、deploy回帰、help表示の期待結果を具体化する。

## Critical failure conditions

- `args.color || ...`などでfalseを未指定扱いする。
- deployのdefaultを常にfalseへ変える。
- 不正な`ACME_COLOR`を黙ってdefaultへ置き換える。

## Scoring

S1〜S5を各0〜2点で採点する。2点は値の優先順位、false、実差分、共有型、検証を追跡できる、1点は一部不明確、0点は優先順位不一致・false消失・既存挙動変更・重複状態/型がある。8〜10点かつ0点なしをPass、6〜7点または0点を含む8点以上をBorderline、5点以下をFailとする。critical failureを最優先し、関数名や配置の完全一致は求めない。


## Judge instructions

Score each candidate independently using only its final answer and this fixture.
Do not guess its generation condition. The workspace intentionally contained no source files and
was read-only, so judge the proposed data flow, types, boundaries, failure behavior, and observable
test plan. Do not fail a candidate merely because it could not edit or execute code.

Score S1 through S5 from 0 to 2 exactly as defined by the fixture. `total` must equal their sum.
If any critical failure condition is met, set `critical_failure` to true and `outcome` to
`critical_failure`. Otherwise use: pass = total 8-10 with every S at least 1; borderline = total
6-7, or total 8-10 with any S equal to 0; fail = total 0-5. Evidence must name concrete satisfied
and missing behavior. Do not reward headings, verbosity, or terminology by itself.


## Candidate A

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

## Candidate B

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

## Candidate C

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

## Candidate D

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

## Candidate E

変更案は、`OutputOptions` の生成だけを共通化し、コマンド固有差分を `defaultColor` に限定する形が最小です。`deploy` の既存評価順序—including CLI指定時にも不正な環境変数を検査する挙動—も維持できます。

## 変更契約

変更する挙動:

- `preview` が `--color` / `--no-color` を受け取る。
- `preview` も `CLI > ACME_COLOR > ui.color > default` で解決する。
- `preview` の全未指定時はTTYでも `false`。

変更しない挙動:

- `deploy` の優先順位とデフォルト `ctx.stdout.isTTY`。
- `--no-color` が明示値 `false` としてCLI最優先になること。
- `parseBoolean` が不正値を `ConfigError` にすること。
- `OutputOptions` は `{ color: boolean }` の単一共通型。

共通処理:

- `ACME_COLOR` のパース。
- 4入力の優先順位解決。
- `OutputOptions` の生成。

差分処理:

- `deploy`: `defaultColor = ctx.stdout.isTTY`
- `preview`: `defaultColor = false`

## 共通処理

`OutputOptions` の既存所有モジュールへ、次の関数を置きます。コマンド別の型やstrategyは追加しません。

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

`parseBoolean(ctx.env.ACME_COLOR)` は `resolveValue` の呼び出し前に評価されます。したがって、現在の `deploy` と同様、CLI値が指定されていても環境変数が不正なら `ConfigError` になります。

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
  // 既存プロパティ
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

値の経路は次の一本だけです。

```text
--color / --no-color ─┐
ACME_COLOR ─parseBoolean─┤
config.ui.color ────────┼─ resolveValue ─ { color: boolean } ─ runDeploy/runPreview
コマンド固有default ───┘
```

CLI登録では次の値を保証します。

- `--color` → `args.color === true`
- `--no-color` → `args.color === false`
- どちらも未指定 → `args.color === undefined`

未指定を `false` に初期化すると環境変数や設定ファイルを常に上書きしてしまうため、CLIパーサー側のデフォルトは必ず `undefined` にします。

## help

既存の `deploy` のflag登録を `preview` にも適用し、両コマンドに以下を記載します。

```text
--color       Enable colored output
--no-color    Disable colored output

Priority: CLI > ACME_COLOR > ui.color > command default.
deploy defaults to stdout TTY detection; preview defaults to no color.
```

CLIライブラリに共通option登録の仕組みが既にある場合だけ登録処理も再利用します。help文言の共有だけを目的とした新しい抽象化は不要です。

## 最小テスト

共通resolverのテーブルテスト:

| CLI | env | file | default | 結果 |
|---:|---:|---:|---:|---:|
| `false` | `"true"` | `true` | `true` | `false` |
| `undefined` | `"false"` | `true` | `true` | `false` |
| `undefined` | `undefined` | `false` | `true` | `false` |
| `undefined` | `undefined` | `undefined` | `true` | `true` |

追加で以下を確認します。

```ts
it("throws ConfigError for an invalid ACME_COLOR", () => {
  expect(() =>
    resolveOutputOptions({
      cliColor: true,
      ctx: contextWithEnv({ ACME_COLOR: "yes" }),
      defaultColor: false,
    }),
  ).toThrow(ConfigError);
});
```

CLI境界:

- `preview --color` → `args.color === true`
- `preview --no-color` → `args.color === false`
- flag未指定 → `args.color === undefined`
- 両コマンドのhelpに両flagと優先順位が含まれる

コマンド連携:

- `deploy`、全設定なし、TTY → `runDeploy(..., { color: true })`
- `preview`、全設定なし、TTY → `runPreview(..., { color: false })`
- `deploy` と `preview` のそれぞれで `ACME_COLOR="invalid"` → `ConfigError`、runnerは呼ばれない

作業ツリーには実装コード・`package.json`・既存テストがなく、かつ読み取り専用だったため、変更およびテスト実行はしていません。実コードが提示された場合は、既存のファイル配置とCLIライブラリに合わせてこの契約を具体的な差分へ落とせます。

## Candidate F

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
