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
