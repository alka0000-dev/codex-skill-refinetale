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

## Candidate B

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

## Candidate C

変更案は、`color` の解決処理を1関数へ集約し、各コマンドには実際に異なるdefault値だけを残す形が最小です。

## 変更契約

変更する挙動:

- `preview` が `--color` / `--no-color` を受け付ける。
- `preview` の優先順位を `CLI > ACME_COLOR > ui.color > false` にする。
- 不正な `ACME_COLOR` は `preview` でも `ConfigError` にする。
- 両コマンドのhelpにフラグと優先順位を記載する。

変更しない挙動:

- `deploy` の優先順位は変えない。
- `deploy` のdefaultは引き続き `ctx.stdout.isTTY`。
- `parseBoolean` の受理値と失敗型を変えない。
- `runDeploy`へ渡す `OutputOptions` の形を変えない。
- CLIが指定されていても不正な環境変数を検証する、現在の`deploy`の挙動を維持する。

共通処理:

- CLI値、環境変数、設定ファイル、defaultの解決。
- `ACME_COLOR`のboolean変換。
- `OutputOptions`の生成。

差分処理:

- `deploy`: `defaultColor = ctx.stdout.isTTY`
- `preview`: `defaultColor = false`

## 共通実装

`OutputOptions`と`parseBoolean`が現在置かれている共通モジュールに、次だけを追加します。

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

export function resolveOutputOptions(
  cliColor: boolean | undefined,
  ctx: CommandContext,
  defaultColor: boolean,
): OutputOptions {
  // resolveValueを呼ぶ前に評価し、既存どおり不正な環境変数を必ず拒否する。
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

`parseBoolean`を遅延評価してはいけません。たとえばCLI値があるときに環境変数のparseを省略すると、現在の`deploy`では失敗する不正値が成功するようになり、挙動が変わります。

`OutputResolverOptions`のような追加型や、コマンド別resolver、strategy、コマンド種別の分岐は不要です。

## コマンド側

```ts
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
export function previewCommand(args: PreviewArgs, ctx: CommandContext) {
  const output = resolveOutputOptions(
    args.color,
    ctx,
    false,
  );

  return runPreview(args, output);
}
```

`DeployOutputOptions`や`PreviewOutputOptions`は追加せず、両方とも既存の`OutputOptions`を使います。

値の経路は次の1本です。

```text
--color / --no-color
        ↓
args.color: true | false | undefined
        ↓
resolveOutputOptions
  ├─ ACME_COLOR → parseBoolean → boolean | undefined
  ├─ ui.color                 → boolean | undefined
  └─ command default          → boolean
        ↓
resolveValue<boolean>
        ↓
OutputOptions.color: boolean
        ↓
runDeploy / runPreview
```

`--no-color`は`args.color === false`として渡します。`args.color || undefined`のようなtruthy変換は使用しません。

## CLI定義とhelp

利用中のCLIライブラリのnegatable option機能を使い、2つの独立したbooleanへ分けず、同じ`color`フィールドへ格納します。

期待されるparse結果:

```ts
preview --color     // args.color === true
preview --no-color  // args.color === false
preview             // args.color === undefined
```

両コマンドのhelpには、少なくとも次を記載します。

```text
--color       Enable colored output
--no-color    Disable colored output

Color precedence:
  command-line flag > ACME_COLOR > ui.color > command default
```

加えてdefault差を明記します。

```text
deploy default: stdout is a TTY
preview default: disabled
```

## 最小テストケース

| 契約 | テスト入力 | 期待結果 |
|---|---|---|
| CLI最優先・`false`保持 | `cliColor=false`, env=`true`, file=`true` | `color=false` |
| 環境変数優先 | CLI未指定、env=`false`, file=`true` | `color=false` |
| ファイル優先 | CLI/env未指定、file=`true` | `color=true` |
| deployのdefault維持 | 全入力未指定、`stdout.isTTY=true` | `runDeploy`へ`{ color: true }` |
| deploy非TTY | 全入力未指定、`stdout.isTTY=false` | `runDeploy`へ`{ color: false }` |
| preview固有default | 全入力未指定、`stdout.isTTY=true` | `runPreview`へ`{ color: false }` |
| deployの失敗経路維持 | CLI=`true`, env=`invalid` | `ConfigError("invalid boolean: invalid")`、`runDeploy`未実行 |
| previewの失敗経路 | CLI=`true`, env=`invalid` | 同じ`ConfigError`、`runPreview`未実行 |
| CLI正規化 | `preview --no-color` | `args.color === false` |
| help | `deploy --help`, `preview --help` | 両flag、優先順位、各defaultを表示 |

優先順位の全組み合わせを両コマンドで重複テストする必要はありません。共通resolverで優先順位と`false`を検証し、コマンドテストではそれぞれのdefault、失敗時にrunnerが呼ばれないこと、正しい`OutputOptions`の受け渡しだけを確認します。

作業ツリーには実装ファイルやコミットが存在しなかったため、コード変更・ビルド・テスト実行はしていません。実ファイルが提供された場合は、既存CLIライブラリのoption記法とテスト配置に合わせてこの案を適用する必要があります。

## Candidate D

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

## Candidate E

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

## Candidate F

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
