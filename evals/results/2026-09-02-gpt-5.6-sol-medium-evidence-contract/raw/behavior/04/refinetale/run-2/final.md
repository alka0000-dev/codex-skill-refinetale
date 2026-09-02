共通経路を1つにし、実際の差分だけを引数にします。操作が失敗した場合、`audit.record` には到達しません。

```ts
async function performProjectOperation(
  req: Request,
  operation: (
    id: ReturnType<typeof parseProjectId>,
  ) => Promise<unknown>,
  auditEvent: Parameters<typeof audit.record>[0],
) {
  await requireAdmin(req.user);

  const id = parseProjectId(req.params.id);
  const project = await repository.get(id);

  if (!project) return response(404);

  await operation(id);
  await audit.record(auditEvent, id);

  return response(204);
}

export function archiveProject(req: Request) {
  return performProjectOperation(
    req,
    id => repository.archive(id),
    "project.archived",
  );
}

export function deleteProject(req: Request) {
  return performProjectOperation(
    req,
    id => repository.delete(id),
    "project.deleted",
  );
}
```

維持される契約:

- 管理者認可後に入力検証
- 対象が存在しない場合は404で終了
- archive/delete失敗時は監査を記録しない
- 成功時だけ対応する監査イベントを記録
- 成功レスポンスは204
- 監査記録失敗時に204を返さない点も従来どおり

最低限必要な検証は、archive/deleteそれぞれについて「成功時の操作・監査名・204」、共通経路について「認可失敗、ID不正、404、repository操作失敗では監査なし」です。

作業ディレクトリには実装・テストファイルが存在せず、かつ読み取り専用だったため、パッチ適用とテスト実行はできていません。上記は提示コードに対する置換案です。RefineTaleの方針に従い、種別enum、`switch`、strategy mapなどの追加構造は設けていません。
