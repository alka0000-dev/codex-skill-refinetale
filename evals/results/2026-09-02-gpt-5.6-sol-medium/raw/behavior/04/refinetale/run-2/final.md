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
