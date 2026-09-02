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
