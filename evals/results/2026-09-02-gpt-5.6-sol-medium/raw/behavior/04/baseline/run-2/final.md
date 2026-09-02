共通化するのは「認可から204応答までの実行順序」です。操作と監査イベントは設定として対にします。

```ts
type ProjectId = ReturnType<typeof parseProjectId>;

type ProjectMutation = {
  execute: (id: ProjectId) => Promise<void>;
  auditEvent: "project.archived" | "project.deleted";
};

async function handleProjectMutation(
  req: Request,
  mutation: ProjectMutation,
) {
  await requireAdmin(req.user);

  const id = parseProjectId(req.params.id);
  const project = await repository.get(id);

  if (!project) return response(404);

  await mutation.execute(id);
  await audit.record(mutation.auditEvent, id);

  return response(204);
}

export async function archiveProject(req: Request) {
  return handleProjectMutation(req, {
    execute: (id) => repository.archive(id),
    auditEvent: "project.archived",
  });
}

export async function deleteProject(req: Request) {
  return handleProjectMutation(req, {
    execute: (id) => repository.delete(id),
    auditEvent: "project.deleted",
  });
}
```

`execute`が正常終了した後にだけ`audit.record`へ進むため、repository操作が失敗した場合は監査イベントが記録されません。認可・入力検証・存在確認の順序、404と204の条件も維持しています。

確認すべきテストは次のとおりです。

- 対象なし：404、操作・監査とも未実行
- 操作成功：対応する監査イベントを記録して204
- 操作失敗：監査を記録せず、エラーを伝播
- 認可失敗／ID不正：repository操作・監査とも未実行

ワークスペースが読み取り専用かつ対象ファイルが存在しなかったため、実ファイルの変更・テスト実行・`referytale`の対応表および`CONTINUITY.md`の作成は行っていません。
