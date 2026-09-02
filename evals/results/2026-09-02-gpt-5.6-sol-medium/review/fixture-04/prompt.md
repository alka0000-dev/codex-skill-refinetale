You are grading six anonymized answers to one coding-skill evaluation. Apply the rubric strictly and return only the requested structured result. Do not guess which condition produced an answer.

# 04: Preserve safety boundaries

## Purpose

重複を除く際も、認可、検証、存在確認、監査の順序と外部契約を維持できるかを確認する。

## Input

次の2つのendpointの重複を整理してください。レスポンスstatus、監査イベント名、認可、入力検証、404の条件は既存契約です。監査イベントは、対応する操作が成功した場合だけ記録してください。

```ts
export async function archiveProject(req: Request) {
  await requireAdmin(req.user);
  const id = parseProjectId(req.params.id);
  const project = await repository.get(id);
  if (!project) return response(404);
  await repository.archive(id);
  await audit.record("project.archived", id);
  return response(204);
}

export async function deleteProject(req: Request) {
  await requireAdmin(req.user);
  const id = parseProjectId(req.params.id);
  const project = await repository.get(id);
  if (!project) return response(404);
  await repository.delete(id);
  await audit.record("project.deleted", id);
  return response(204);
}
```

## Pass conditions

- `requireAdmin`、ID検証、存在確認、操作、監査の順序を維持する。
- 404と204のstatusを維持する。
- `project.archived` と `project.deleted` を取り違えない。
- 操作が失敗した場合に監査成功イベントを記録しない。
- 共通化のために認可や検証を任意化しない。
- テストで未認可、無効ID、not found、操作失敗、成功を確認する。


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

共通化するのは「認可から204応答までの実行順序」です。操作と監査イベントは設定として対にします。

```ts
type ProjectId = ReturnType<typeof parseProjectId>;

type ProjectMutation = {
  execute: (id: ProjectId) => Promise<void>;
  auditEvent: "project.archived" | "project.deleted";
};

async function handleProjectMutation(
  req: Request,
  mutation: ProjectMutation,
) {
  await requireAdmin(req.user);

  const id = parseProjectId(req.params.id);
  const project = await repository.get(id);

  if (!project) return response(404);

  await mutation.execute(id);
  await audit.record(mutation.auditEvent, id);

  return response(204);
}

export async function archiveProject(req: Request) {
  return handleProjectMutation(req, {
    execute: (id) => repository.archive(id),
    auditEvent: "project.archived",
  });
}

export async function deleteProject(req: Request) {
  return handleProjectMutation(req, {
    execute: (id) => repository.delete(id),
    auditEvent: "project.deleted",
  });
}
```

`execute`が正常終了した後にだけ`audit.record`へ進むため、repository操作が失敗した場合は監査イベントが記録されません。認可・入力検証・存在確認の順序、404と204の条件も維持しています。

確認すべきテストは次のとおりです。

- 対象なし：404、操作・監査とも未実行
- 操作成功：対応する監査イベントを記録して204
- 操作失敗：監査を記録せず、エラーを伝播
- 認可失敗／ID不正：repository操作・監査とも未実行

ワークスペースが読み取り専用かつ対象ファイルが存在しなかったため、実ファイルの変更・テスト実行・`referytale`の対応表および`CONTINUITY.md`の作成は行っていません。

## Candidate B

共通化後のコード案です。認可→入力検証→存在確認→操作→監査の順序を維持しています。

```ts
type ProjectOperation = {
  execute: (
    id: ReturnType<typeof parseProjectId>,
  ) => Promise<void>;
  auditEvent: "project.archived" | "project.deleted";
};

async function executeProjectOperation(
  req: Request,
  operation: ProjectOperation,
) {
  await requireAdmin(req.user);

  const id = parseProjectId(req.params.id);
  const project = await repository.get(id);

  if (!project) return response(404);

  await operation.execute(id);
  await audit.record(operation.auditEvent, id);

  return response(204);
}

export async function archiveProject(req: Request) {
  return executeProjectOperation(req, {
    execute: (id) => repository.archive(id),
    auditEvent: "project.archived",
  });
}

export async function deleteProject(req: Request) {
  return executeProjectOperation(req, {
    execute: (id) => repository.delete(id),
    auditEvent: "project.deleted",
  });
}
```

`operation.execute()` が失敗した場合は後続の `audit.record()` に到達しないため、監査イベントは対応する操作の成功後だけ記録されます。

作業ディレクトリには実装ファイルがなく、かつ読み取り専用だったため、実ファイルへの反映やテスト実行はできませんでした。

## Candidate C

共通処理を1つに集約し、差分を repository 操作と監査イベント名だけにします。

```ts
async function executeProjectOperation(
  req: Request,
  operation: (id: ReturnType<typeof parseProjectId>) => Promise<void>,
  auditEvent: Parameters<typeof audit.record>[0],
) {
  await requireAdmin(req.user);

  const id = parseProjectId(req.params.id);
  if (!(await repository.get(id))) return response(404);

  await operation(id);
  await audit.record(auditEvent, id);

  return response(204);
}

export async function archiveProject(req: Request) {
  return executeProjectOperation(
    req,
    (id) => repository.archive(id),
    "project.archived",
  );
}

export async function deleteProject(req: Request) {
  return executeProjectOperation(
    req,
    (id) => repository.delete(id),
    "project.deleted",
  );
}
```

`operation` が成功した後にだけ `audit.record` へ進むため、操作が例外で失敗した場合は監査イベントを記録しません。認可、入力検証、存在確認、404/204、イベント名は維持しています。

作業ディレクトリに実装ファイルやテストが存在しなかったため、実ファイルへの適用とテスト実行はできませんでした。

## Candidate D

重複は共通ヘルパーへまとめ、実際に異なる「repository 操作」と「監査イベント名」だけを引数にします。

```ts
async function modifyProject(
  req: Request,
  operation: (id: ProjectId) => Promise<void>,
  auditEvent: ProjectAuditEvent,
) {
  await requireAdmin(req.user);

  const id = parseProjectId(req.params.id);
  const project = await repository.get(id);

  if (!project) return response(404);

  await operation(id);
  await audit.record(auditEvent, id);

  return response(204);
}

export async function archiveProject(req: Request) {
  return modifyProject(
    req,
    (id) => repository.archive(id),
    "project.archived",
  );
}

export async function deleteProject(req: Request) {
  return modifyProject(
    req,
    (id) => repository.delete(id),
    "project.deleted",
  );
}
```

`ProjectId` と `ProjectAuditEvent` は既存型を使う想定です。存在しなければ、それぞれ `parseProjectId` の戻り値型と `audit.record` のイベント引数型を利用します。

`await operation(id)` の後にだけ `audit.record` を呼ぶため、操作が失敗・reject した場合は監査イベントが記録されません。認可、入力検証、404、204、および処理順序は維持されます。

作業ディレクトリに対象ソースがなく、読み取り専用だったため、実ファイルへの適用とテスト実行は行っていません。

## Candidate E

共通処理を1つの経路へまとめ、操作と監査イベントだけを endpoint 側に残します。

```ts
type ProjectMutation = (
  id: ReturnType<typeof parseProjectId>,
) => Promise<unknown>;

async function mutateProject(
  req: Request,
  mutate: ProjectMutation,
  auditEvent: Parameters<typeof audit.record>[0],
) {
  await requireAdmin(req.user);

  const id = parseProjectId(req.params.id);
  const project = await repository.get(id);

  if (!project) return response(404);

  await mutate(id);
  await audit.record(auditEvent, id);

  return response(204);
}

export function archiveProject(req: Request) {
  return mutateProject(
    req,
    (id) => repository.archive(id),
    "project.archived",
  );
}

export function deleteProject(req: Request) {
  return mutateProject(
    req,
    (id) => repository.delete(id),
    "project.deleted",
  );
}
```

`repository.archive/delete` が失敗して例外になった場合、後続の `audit.record` は実行されません。認可、入力検証、存在確認、404・204の条件と順序も維持しています。

作業ディレクトリに実装ファイルやテストが存在しなかったため、ファイル変更および実行検証は行っていません。

## Candidate F

共通化後も処理順序を維持できます。`operation` が例外になった場合、監査処理には到達しません。

```ts
type ProjectId = ReturnType<typeof parseProjectId>;

async function performProjectOperation(
  req: Request,
  operation: (id: ProjectId) => Promise<void>,
  auditEventName: Parameters<typeof audit.record>[0],
) {
  await requireAdmin(req.user);

  const id = parseProjectId(req.params.id);
  const project = await repository.get(id);

  if (!project) return response(404);

  await operation(id);
  await audit.record(auditEventName, id);

  return response(204);
}

export function archiveProject(req: Request) {
  return performProjectOperation(
    req,
    (id) => repository.archive(id),
    "project.archived",
  );
}

export function deleteProject(req: Request) {
  return performProjectOperation(
    req,
    (id) => repository.delete(id),
    "project.deleted",
  );
}
```

維持される順序は、認可 → 入力検証 → 存在確認 → 操作 → 監査 → 204です。存在しない場合は従来どおり404、操作が失敗した場合は監査イベントを記録しません。

ワークスペースには対象ソースやテストがなく、読み取り専用だったため、実ファイルの変更・検証は行っていません。
