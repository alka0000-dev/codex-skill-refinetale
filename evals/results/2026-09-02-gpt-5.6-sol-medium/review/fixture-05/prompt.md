You are grading six anonymized answers to one coding-skill evaluation. Apply the rubric strictly and return only the requested structured result. Do not guess which condition produced an answer.

# 05: Stop when already minimal

## Purpose

対象が既に要求を十分単純に満たす場合、将来予測に基づく不要な変更を行わず止まれるかを確認する。

## Input

次のコードを、将来 `archived` が追加されるかもしれない点を考慮してリファクタリングしてください。ただし現在の仕様は、下書きだけが編集可能で、公開済みは編集不可です。現在必要な変更だけを行ってください。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

## Pass conditions

- 現在の実装が仕様を直接表現していることを認識する。
- コード、型、テストへ不要な変更を加えない。
- 未確定の `archived`、feature flag、fallback、状態表を先行実装しない。
- 変更しない理由と、将来仕様が確定した時点で見直す条件を簡潔に示す。
- 「リファクタリング」という依頼語だけを理由に差分を作らない。


## Scoring rules

Score each item as `1` (satisfied), `0` (not satisfied), or `-1` (not applicable).

- G1 Contract fidelity: preserves requested external contracts, inputs, outputs, errors, and events.
- G2 Change contract: clearly handles what changes, what must not change, and allowed variation.
- G3 Canonical ownership: keeps one source of truth for the same state or decision.
- G4 Variation isolation: isolates only real differences and does not duplicate common processing.
- G5 No speculative implementation: adds no unrequested future extension, fallback, flag, or abstraction.
- G6 Safety preservation: does not weaken authorization, validation, audit, or failure behavior.
- G7 Verification and stop: identifies necessary verification and stops when no change is needed.

Use only evidence present in the candidate's final answer. Do not reward a promise to finish later.
The workspace intentionally lacked source files and was read-only. Do not fail a candidate merely
for reporting that limitation if it still provides the requested concrete solution and verification
plan. Missing implementation guidance or missing required test coverage can still fail the relevant
criterion. `overall_pass` requires every applicable G score and the fixture-specific conditions to
equal 1. G1 is always critical; G6 is critical when applicable.


## Candidate A

リファクタリングは不要です。現在の実装がすでに最小かつ適切です。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

`draft` だけを許可する許可リスト方式なので、将来 `archived` が型へ追加されても自動的に編集不可になります。現時点で `archived`、`switch`、設定マップなどを先行追加する必要はありません。

## Candidate B

現状のコードがすでに要件を満たしているため、変更は不要です。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

許可する状態を `draft` に限定しているため、将来 `archived` が追加されても自動的に `false` になります。現時点で `archived` の追加や `switch`、編集可能ステータス一覧などを導入するのは先回りした実装です。

## Candidate C

将来状態が追加された際に判断漏れをコンパイルエラーで検出できるよう、現在の2状態だけを明示します。`archived` 自体はまだ追加しません。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  switch (status) {
    case "draft":
      return true;
    case "published":
      return false;
    default: {
      const exhaustiveCheck: never = status;
      return exhaustiveCheck;
    }
  }
}
```

将来 `ArticleStatus` に `archived` を追加すると `exhaustiveCheck` で型エラーになり、その時点で編集可否を明示的に決められます。

なお、`referytale` の事前表は環境が読み取り専用のため保存できず、今回は新しい抽象名を導入しない最小変更として整理しました。

## Candidate D

リファクタリング不要です。現状の実装がすでに最小で、将来 `archived` が追加されても自然に編集不可になります。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

`archived` が正式な仕様になった時点で、型だけを変更します。

```ts
type ArticleStatus = "draft" | "published" | "archived";
```

`canEdit` は変更不要です。現時点で `archived`、分岐、許可状態の配列などを追加すると、未確定仕様の先行実装になるため行いません。

## Candidate E

リファクタリングは不要です。現在の実装が「編集可能な状態だけを許可する」という最小の許可リストになっています。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

将来 `archived` を型へ追加しても、自動的に編集不可になります。

```ts
type ArticleStatus = "draft" | "published" | "archived";
```

`switch`、編集不可状態の一覧、将来用の分岐などは現時点では不要です。現在のコードが要件を満たしつつ、安全側へ閉じる最小実装です。

## Candidate F

変更は不要です。現在の実装は許可する状態を `draft` に限定しているため、将来 `archived` が追加されても自動的に編集不可になります。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

`switch` や編集不可ステータスの列挙を追加すると、未確定の将来仕様を先回りすることになります。現状の許可リスト方式が、現在の仕様を最小かつ安全に表現しています。新しい名称も不要だったため、`referytale` による対応表の作成対象にはしていません。
