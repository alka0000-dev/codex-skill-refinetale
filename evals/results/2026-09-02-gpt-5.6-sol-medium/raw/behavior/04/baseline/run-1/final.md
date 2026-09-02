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
