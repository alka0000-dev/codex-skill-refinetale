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

共通化する対象は「管理者認可 → ID検証 → 存在確認 → 操作 → 監査 → 204」の順序です。

```ts
type ProjectId = ReturnType<typeof parseProjectId>;
type ProjectOperation = (id: ProjectId) => Promise<unknown>;
type ProjectAuditEvent = "project.archived" | "project.deleted";

async function executeExistingProjectOperation(
  req: Request,
  operation: ProjectOperation,
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
  return executeExistingProjectOperation(
    req,
    (id) => repository.archive(id),
    "project.archived",
  );
}

export async function deleteProject(req: Request) {
  return executeExistingProjectOperation(
    req,
    (id) => repository.delete(id),
    "project.deleted",
  );
}
```

`operation` が正常終了した後にだけ `audit.record` へ進むため、archive/delete が例外を投げた場合は監査イベントが記録されません。既存の認可・入力検証・404条件・レスポンスstatus・イベント名・処理順序も維持しています。

作業領域に対象のTypeScriptファイルがなく読み取り専用だったため、実ファイルの変更とテスト実行は行っていません。

## Candidate B

共通化するのは「認可 → ID検証 → 存在確認 → 操作 → 監査 → 204」の流れです。操作と監査イベントは同じ引数として渡し、実行順を固定します。

```ts
type ProjectId = ReturnType<typeof parseProjectId>;
type ProjectOperation = (id: ProjectId) => Promise<void>;
type ProjectAuditEvent = "project.archived" | "project.deleted";

async function executeProjectOperation(
  req: Request,
  operation: ProjectOperation,
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

これにより既存契約を維持できます。

- `repository.archive/delete` が失敗した場合、`audit.record` は呼ばれない
- 404の場合も監査イベントは記録されない
- 認可と入力検証の順序は変わらない
- 成功時の監査イベント名と204レスポンスは変わらない
- repositoryメソッドは直接渡さずクロージャで呼ぶため、`this` 依存があっても壊れない

`referytale` の対応表は読み取り専用環境のため保存できず、提示コードを一次情報として命名と処理順序のみ照合しました。実ファイルの変更は行っていません。

## Candidate C

共通経路を1つにし、実際の差分だけを引数にします。操作が失敗した場合、`audit.record` には到達しません。

```ts
async function performProjectOperation(
  req: Request,
  operation: (
    id: ReturnType<typeof parseProjectId>,
  ) => Promise<unknown>,
  auditEvent: Parameters<typeof audit.record>[0],
) {
  await requireAdmin(req.user);

  const id = parseProjectId(req.params.id);
  const project = await repository.get(id);

  if (!project) return response(404);

  await operation(id);
  await audit.record(auditEvent, id);

  return response(204);
}

export function archiveProject(req: Request) {
  return performProjectOperation(
    req,
    id => repository.archive(id),
    "project.archived",
  );
}

export function deleteProject(req: Request) {
  return performProjectOperation(
    req,
    id => repository.delete(id),
    "project.deleted",
  );
}
```

維持される契約:

- 管理者認可後に入力検証
- 対象が存在しない場合は404で終了
- archive/delete失敗時は監査を記録しない
- 成功時だけ対応する監査イベントを記録
- 成功レスポンスは204
- 監査記録失敗時に204を返さない点も従来どおり

最低限必要な検証は、archive/deleteそれぞれについて「成功時の操作・監査名・204」、共通経路について「認可失敗、ID不正、404、repository操作失敗では監査なし」です。

作業ディレクトリには実装・テストファイルが存在せず、かつ読み取り専用だったため、パッチ適用とテスト実行はできていません。上記は提示コードに対する置換案です。RefineTaleの方針に従い、種別enum、`switch`、strategy mapなどの追加構造は設けていません。

## Candidate D

外部契約は変えず、認可・検証・存在確認・レスポンスを共通化し、操作と監査イベントだけを差分として渡します。

```ts
async function handleProjectMutation(
  req: Request,
  mutate: (
    id: ReturnType<typeof parseProjectId>,
  ) => Promise<void>,
  auditEvent: "project.archived" | "project.deleted",
) {
  await requireAdmin(req.user);

  const id = parseProjectId(req.params.id);

  if (!(await repository.get(id))) {
    return response(404);
  }

  await mutate(id);
  await audit.record(auditEvent, id);

  return response(204);
}

export function archiveProject(req: Request) {
  return handleProjectMutation(
    req,
    (id) => repository.archive(id),
    "project.archived",
  );
}

export function deleteProject(req: Request) {
  return handleProjectMutation(
    req,
    (id) => repository.delete(id),
    "project.deleted",
  );
}
```

変更契約は次のとおりです。

- 変更するもの：重複していた処理経路を `handleProjectMutation` に一本化
- 変更しないもの：認可、入力検証、404条件、204レスポンス、イベント名、副作用の順序
- 操作固有の差分：
  - archive → `repository.archive` / `project.archived`
  - delete → `repository.delete` / `project.deleted`
- 操作が失敗した場合：`await mutate(id)` で中断するため監査されない
- 存在しない場合：404で早期終了し、操作も監査も実行されない

作業ディレクトリに実装やテストが存在せず読み取り専用だったため、適用・実行検証はできませんでした。最低限、両endpointについて以下の確認が必要です。

- 成功：対応する操作→対応する監査の順に実行され、204
- 操作失敗：監査されず、204も返さない
- 対象なし：404、操作・監査とも未実行
- 認可失敗／ID不正：後続処理が未実行
- 監査失敗：操作は完了済みだが204には到達しない（既存どおり）

## Candidate E

共通フローを1つにし、差分は「repository操作」と「監査イベント」の組だけにします。

```ts
type ProjectOperation = {
  execute: (id: ReturnType<typeof parseProjectId>) => Promise<void>;
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

変更契約：

- 変更する挙動：なし。内部の重複だけを整理。
- 維持する挙動：管理者認可、ID検証、存在確認、404、204、監査イベント名。
- 共通処理：認可 → ID検証 → 取得 → 404判定 → 操作 → 監査 → 204。
- 差分処理：repository操作と、その成功に対応する監査イベント。
- 正本：処理順序は `executeProjectOperation`、操作とイベントの対応は各endpoint。

`operation.execute` を `await` してから監査するため、archive/deleteが失敗した場合は監査されません。なお、既存どおり監査記録が失敗した場合は204を返しません。

対象ファイルやテストが作業領域に存在しないため実行検証はできませんでした。最低限、各操作について次を確認する必要があります。

- 存在しないID：404、操作と監査は未実行。
- repository操作失敗：監査は未実行、204も未返却。
- 操作成功：対応するイベントを同じIDで記録し、204。
- archiveはdeleteを呼ばず、deleteはarchiveを呼ばない。
- 認可失敗・ID検証失敗：取得、操作、監査はいずれも未実行。

## Candidate F

共通処理を「存在するプロジェクトへの変更」として抽出できます。変更処理が例外なく完了した後にだけ監査を記録します。

```ts
type ProjectId = ReturnType<typeof parseProjectId>;
type ProjectAuditEvent = "project.archived" | "project.deleted";

async function mutateExistingProject(
  req: Request,
  mutate: (id: ProjectId) => Promise<unknown>,
  auditEvent: ProjectAuditEvent,
) {
  await requireAdmin(req.user);

  const id = parseProjectId(req.params.id);
  const project = await repository.get(id);

  if (!project) return response(404);

  await mutate(id);
  await audit.record(auditEvent, id);

  return response(204);
}

export async function archiveProject(req: Request) {
  return mutateExistingProject(
    req,
    (id) => repository.archive(id),
    "project.archived",
  );
}

export async function deleteProject(req: Request) {
  return mutateExistingProject(
    req,
    (id) => repository.delete(id),
    "project.deleted",
  );
}
```

これにより既存の処理順序を維持します。

1. 管理者認可
2. IDの解析・検証
3. 存在確認と404
4. archive/delete
5. 成功時のみ対応する監査イベント
6. 204

`repository.archive/delete` が reject した場合、`audit.record` は実行されません。なお、読み取り専用環境のため `referytale` の対応表ファイル作成と実ファイルへの反映は行っていません。
