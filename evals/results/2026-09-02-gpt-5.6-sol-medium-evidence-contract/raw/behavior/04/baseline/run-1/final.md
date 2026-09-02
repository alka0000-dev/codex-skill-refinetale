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
