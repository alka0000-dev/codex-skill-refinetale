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
