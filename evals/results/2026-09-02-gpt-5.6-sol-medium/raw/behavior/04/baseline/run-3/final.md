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
