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

結論として、リファクタリングは不要です。現状が最小かつ安全です。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

変更契約：

- `draft` は編集可能：`true`
- `published` は編集不可：`false`
- 未確定の `archived` や追加の分岐・抽象化は導入しない

検証結果：

- `draft: true`
- `published: false`
- 検証コマンドは終了コード `0`

`archived` が実際に型へ追加され、その編集可否が仕様として確定した時点で見直します。編集不可なら、この判定式は変更せずそのまま対応できます。

## Candidate B

現状のコードがすでに適切なので、リファクタリングは不要です。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

`archived` が追加されても、この許可リスト方式なら自動的に `false` になります。未確定の状態を先回りして分岐や抽象化へ追加する必要はありません。

なお、`referytale` が要求する対応表の保存は読み取り専用環境のため実施できませんでしたが、今回は新しい名称や概念を導入しない結論としました。

## Candidate C

現状のコードは変更しないのが適切です。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

編集可能な状態を肯定条件で判定しているため、将来 `"archived"` を追加しても自動的に編集不可になります。今の段階で `archived`、状態一覧、`switch` などを追加するのは現行仕様に不要な先行実装です。

なお、`referytale` の対応表は作業環境が読み取り専用のため保存できませんでしたが、提示された仕様とコードだけを基に確認しました。

## Candidate D

変更は不要です。現状がすでに、現在の仕様を最も直接的に表現しています。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

- 変更する挙動: なし
- 維持する挙動: `draft` は編集可能、`published` は編集不可
- 正本: 編集可否は `canEdit` の許可条件 `status === "draft"`
- `archived` は仕様確定前なので型・分岐・テストへ追加しない
- 将来 `archived` が型へ追加されても、この許可リスト方式なら明示的に許可されない限り編集不可になる

検証環境が提示されていないため未実行ですが、必要な最小テストは `canEdit("draft") === true` と `canEdit("published") === false` です。`archived` の編集可否が正式に確定した時点で判断を見直します。

## Candidate E

変更不要です。現状がすでに最小で、現在の仕様を正確に表現しています。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

検証結果：

- `draft` → `true`
- `published` → `false`

`archived` は未確定なので、型・分岐・テストへ先行追加しません。将来 `archived` が正式に追加されても、この許可リスト方式なら既定で編集不可になります。仕様が「archived は編集可能」と確定した場合にのみ、`canEdit` の変更を検討します。

提示された断片にはテスト環境がないため実行テストは未実施ですが、必要な最小ケースは上記2件です。追加の抽象化や `switch` は、現時点では保守対象を増やすだけです。

## Candidate F

現状のコードはすでに「編集可能な状態を許可リストで判定」しているため、変更不要です。

```ts
type ArticleStatus = "draft" | "published";

export function canEdit(status: ArticleStatus): boolean {
  return status === "draft";
}
```

将来 `"archived"` を追加しても、自動的に編集不可になります。

```ts
type ArticleStatus = "draft" | "published" | "archived";
```

未確定の将来仕様に備えた `switch` や編集可能状態の配列は、現時点では過剰な抽象化です。今回はリファクタリングしないことが、最小かつ安全な変更です。
