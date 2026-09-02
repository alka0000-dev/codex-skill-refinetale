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
