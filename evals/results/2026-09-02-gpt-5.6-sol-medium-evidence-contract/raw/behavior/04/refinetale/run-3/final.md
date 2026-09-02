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
