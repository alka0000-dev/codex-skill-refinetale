最小構成は、複製専用の取得ルートだけを追加し、取得後は既存の新規作成フローへ合流させる形です。`ProjectForm`、validation、dirty判定、エラー処理、作成APIは分岐させません。

## 変更方針

### 1. 複製用の初期値変換を追加

許可した項目だけを `emptyProjectValues()` へ上書きします。除外項目を列挙する方式より、将来 `Project` に機密項目が増えても引き継がれないため安全です。

```ts
export function toCopiedProjectFormValues(
  source: Project,
): ProjectFormValues {
  return {
    ...emptyProjectValues(),
    name: source.name.endsWith(" (copy)")
      ? source.name
      : `${source.name} (copy)`,
    description: source.description,
    memberRoleIds: [...source.memberRoleIds],
    notificationRules: structuredClone(source.notificationRules),
    deploymentTargetId: source.deploymentTargetId,
  };
}
```

これにより以下は入りません。

- `id`
- `createdAt`
- `updatedAt`
- `deployToken`

`emptyProjectValues()` に `deployToken` 相当が存在する場合も、通常の新規作成と同じ空値にします。新規作成画面でトークン入力欄自体が表示される実装なら、既存の `mode === "create"` 条件で非表示にします。

### 2. route loaderを追加

例として `/projects/:projectId/copy` を追加します。

```tsx
export async function copyProjectLoader({ params }: LoaderArgs) {
  return getProject(params.projectId!);
}
```

このルートのローディング表示はフォームを含まないスケルトン等にします。loader完了前に空のフォームを仮表示して、後から `reset()` する実装にはしません。

### 3. loader完了時に一度だけ初期化

loaderの再検証で新しい `Project` オブジェクトが返っても、初期値オブジェクトを差し替えないことが重要です。

```tsx
export function CopyProjectRoute() {
  const sourceProject = useLoaderData() as Project;

  return (
    <CopyProjectForm
      key={sourceProject.id}
      sourceProject={sourceProject}
    />
  );
}

function CopyProjectForm({
  sourceProject,
}: {
  sourceProject: Project;
}) {
  const [initialValues] = useState(() =>
    toCopiedProjectFormValues(sourceProject),
  );

  return (
    <ProjectForm
      mode="create"
      initialValues={initialValues}
      onSubmit={createProject}
    />
  );
}
```

`useState` の初期化関数はマウント時に一度だけ実行されます。

- 同じ複製元のloader再検証: 初期値を保持し、入力を上書きしない
- 別の複製元IDへ遷移: `key` が変わり、新しい初期値で再作成

`useEffect(() => form.reset(initialValues), [initialValues])` のような同期は追加しません。

### 4. 複製への導線を追加

編集画面または既存のプロジェクト操作メニューにリンクを追加します。

```tsx
<Link to={`/projects/${project.id}/copy`}>
  複製して新規作成
</Link>
```

`ProjectForm` は原則変更不要です。複製画面でも次をそのまま利用します。

```tsx
mode="create"
onSubmit={createProject}
```

## 状態とAPI入力

追加する状態は、複製元取得中のroute状態と、loader完了時に固定する `initialValues` だけです。フォーム内部に「複製モード」は持たせません。

送信先・入力は通常の新規作成と完全に共通です。

```ts
await createProject(formValues);
```

payloadへ複製元の `id` や `deployToken`、`createdAt`、`updatedAt`、`sourceProjectId` などは追加しません。`updateProject` や複製専用APIも呼びません。

## テスト

最低限、次を追加します。

1. 初期値変換の単体テスト

- 指定された4項目だけを引き継ぐ
- `name` に ` (copy)` が付く
- 既に末尾が ` (copy)` の場合は重複しない
- `deployToken`、ID、日時が含まれない
- 配列やルールを複製元と同じ参照で保持しない

2. routeのテスト

- loader完了前は `ProjectForm` が表示されない
- loader完了後に `mode="create"` で表示される
- 取得失敗時は既存のrouteエラー表示になる

3. フォーム統合テスト

- 初期表示直後はdirtyではない
- 入力後はdirtyになる
- loaderを再検証しても入力値とdirty状態が維持される
- validationとエラー表示が通常の新規作成と同じ

4. 送信テスト

- `createProject` が呼ばれる
- `updateProject` は呼ばれない
- payloadが通常の新規作成と同じ形である
- 複製元ID、日時、`deployToken` が送られない

なお、`referytale` の対応表は読み取り専用環境のためファイル保存できませんでしたが、設計では「取得中」「一度だけ確定した初期値」「ユーザーが編集するフォーム状態」を分離し、再検証による上書きを防いでいます。
