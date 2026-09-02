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
