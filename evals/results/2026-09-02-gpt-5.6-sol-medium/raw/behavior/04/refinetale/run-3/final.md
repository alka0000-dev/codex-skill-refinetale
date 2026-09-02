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
