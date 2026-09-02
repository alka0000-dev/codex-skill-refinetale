外部契約は変えず、認可・検証・存在確認・レスポンスを共通化し、操作と監査イベントだけを差分として渡します。

```ts
async function handleProjectMutation(
  req: Request,
  mutate: (
    id: ReturnType<typeof parseProjectId>,
  ) => Promise<void>,
  auditEvent: "project.archived" | "project.deleted",
) {
  await requireAdmin(req.user);

  const id = parseProjectId(req.params.id);

  if (!(await repository.get(id))) {
    return response(404);
  }

  await mutate(id);
  await audit.record(auditEvent, id);

  return response(204);
}

export function archiveProject(req: Request) {
  return handleProjectMutation(
    req,
    (id) => repository.archive(id),
    "project.archived",
  );
}

export function deleteProject(req: Request) {
  return handleProjectMutation(
    req,
    (id) => repository.delete(id),
    "project.deleted",
  );
}
```

変更契約は次のとおりです。

- 変更するもの：重複していた処理経路を `handleProjectMutation` に一本化
- 変更しないもの：認可、入力検証、404条件、204レスポンス、イベント名、副作用の順序
- 操作固有の差分：
  - archive → `repository.archive` / `project.archived`
  - delete → `repository.delete` / `project.deleted`
- 操作が失敗した場合：`await mutate(id)` で中断するため監査されない
- 存在しない場合：404で早期終了し、操作も監査も実行されない

作業ディレクトリに実装やテストが存在せず読み取り専用だったため、適用・実行検証はできませんでした。最低限、両endpointについて以下の確認が必要です。

- 成功：対応する操作→対応する監査の順に実行され、204
- 操作失敗：監査されず、204も返さない
- 対象なし：404、操作・監査とも未実行
- 認可失敗／ID不正：後続処理が未実行
- 監査失敗：操作は完了済みだが204には到達しない（既存どおり）
