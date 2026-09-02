最小構成では、`ProjectForm` に複製モードを追加せず、複製用routeで「新規作成用の初期値」を一度だけ生成します。フォーム上は最後まで通常の `mode="create"` として扱います。

### 変更箇所

- `ProjectForm.tsx`
  - 原則変更なし。
  - `useProjectForm` が後から渡された `initialValues` で自動リセットする実装なら、その挙動は止める必要があります。
- `project-routes.tsx`
  - 複製用routeとloaderを追加。
  - 編集画面に「複製して新規作成」へのリンクを追加。
- 初期値変換関数
  - `toDuplicatedProjectFormValues(project)` を追加。
- API
  - 変更なし。既存の `createProject` を使用。
- route設定
  - 例: `/projects/:projectId/duplicate`

### 引継ぎ対応

`emptyProjectValues()`を土台にすることで、新規作成に不要な値を混入させません。

| 複製元の値 | 新規フォーム初期値 |
|---|---|
| `name` | 末尾に ` (copy)`を1つだけ付与 |
| `description` | 引き継ぐ |
| `memberRoleIds` | 引き継ぐ |
| `notificationRules` | 引き継ぐ |
| `deploymentTargetId` | 引き継ぐ |
| `deployToken` | 通常の新規作成と同じ空値 |
| `id`, `createdAt`, `updatedAt` | フォーム値に含めない |

```ts
function appendCopySuffixOnce(name: string): string {
  return `${name.replace(/(?: \(copy\))+$/, "")} (copy)`;
}

function toDuplicatedProjectFormValues(
  project: Project,
): ProjectFormValues {
  return {
    ...emptyProjectValues(),
    name: appendCopySuffixOnce(project.name),
    description: project.description,
    memberRoleIds: [...project.memberRoleIds],
    notificationRules: structuredClone(project.notificationRules),
    deploymentTargetId: project.deploymentTargetId,
    // deployTokenは複製元から設定しない
  };
}
```

配列とルールはコピーし、フォーム編集によってloaderのデータを直接変更しないようにします。`structuredClone`が利用できない環境なら、`NotificationRule`の構造に合わせた明示的なコピーにします。

### loaderと初期化タイミング

複製元の取得はコンポーネント内の`useEffect`ではなく、route loaderで完了させます。loader待機中はrouter側のpending UIだけを表示し、`ProjectForm`はmountしません。

```tsx
export async function duplicateProjectLoader({
  params,
}: LoaderFunctionArgs) {
  const project = await getProject(params.projectId!);
  return { project };
}

export function DuplicateProjectRoute() {
  const { project } =
    useLoaderData<typeof duplicateProjectLoader>();

  return (
    <DuplicateProjectForm
      key={project.id}
      project={project}
    />
  );
}

function DuplicateProjectForm({
  project,
}: {
  project: Project;
}) {
  const [initialValues] = useState(() =>
    toDuplicatedProjectFormValues(project),
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

`useState`の遅延初期化により、初期値を作るのはフォーム表示時の一度だけです。同じ複製元についてloaderが再検証され、`project`のオブジェクトが更新されても、ユーザー入力とdirty状態は上書きされません。

`key={project.id}`は、別の複製元へroute遷移した場合だけ新しいフォームとして初期化するために使います。

編集画面には通常のリンクを追加します。

```tsx
export function EditProjectRoute({ project }: { project: Project }) {
  return (
    <>
      <Link to={`/projects/${project.id}/duplicate`}>
        複製して新規作成
      </Link>

      <ProjectForm
        mode="edit"
        initialValues={toProjectFormValues(project)}
        onSubmit={updateProject}
      />
    </>
  );
}
```

### 状態とAPI入力

追加する状態は、複製用route内の固定された`initialValues`だけです。複製元そのものを`ProjectForm`の状態へ持ち込む必要はありません。

送信時は既存の新規作成とまったく同じです。

```ts
createProject(values);
```

`sourceProjectId`、`id`、日時、元の`deployToken`などをpayloadへ追加しません。通常の新規作成が送信前にpayloadを変換している場合も、その既存変換をそのまま通します。

### テスト

最低限、次を確認します。

1. 初期値変換の単体テスト

   - 指定された4項目を引き継ぐ。
   - `deployToken`は通常の新規作成と同じ空値。
   - IDと日時を含まない。
   - `foo`は`foo (copy)`になる。
   - `foo (copy)`や`foo (copy) (copy)`は`foo (copy)`になる。
   - 配列やルールが複製元と同じ参照ではない。

2. routeのテスト

   - loader完了前は複製フォームが表示されない。
   - loader完了後に`mode="create"`で表示される。
   - loader失敗時は既存のrouteエラー表示になる。

3. 再検証のテスト

   - フォーム表示後に名前や説明を編集する。
   - loaderを再検証する。
   - 編集内容、dirty状態、validationエラーが維持される。

4. 送信のテスト

   - `createProject`が呼ばれる。
   - `updateProject`は呼ばれない。
   - payload形式が通常の新規作成と同じ。
   - 複製元の`deployToken`やメタデータが送られない。

これにより、validation・dirty判定・エラー表示は既存の`ProjectForm`／`useProjectForm`をそのまま共用できます。
