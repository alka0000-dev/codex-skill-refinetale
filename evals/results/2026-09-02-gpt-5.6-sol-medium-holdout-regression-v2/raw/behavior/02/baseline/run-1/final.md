最小構成は、`ProjectForm` に複製モードを追加せず、「複製用の新規作成ルート」で初期値だけを組み立てる形です。フォーム、validation、dirty判定、送信処理は通常の新規作成をそのまま利用します。

## 変更箇所

### 1. 複製用の初期値変換

`emptyProjectValues()` を基準に、引き継ぎを許可した値だけを上書きします。これにより、将来 `Project` に項目が追加されても意図せず複製されません。

```tsx
const COPY_SUFFIX = " (copy)";

function toCopiedProjectFormValues(project: Project): ProjectFormValues {
  const empty = emptyProjectValues();

  return {
    ...empty,
    name: project.name.endsWith(COPY_SUFFIX)
      ? project.name
      : `${project.name}${COPY_SUFFIX}`,
    description: project.description,
    memberRoleIds: [...project.memberRoleIds],
    notificationRules: cloneNotificationRules(project.notificationRules),
    deploymentTargetId: project.deploymentTargetId,
  };
}
```

`cloneNotificationRules` は、フォーム操作で元のloaderデータを変更しないよう、`NotificationRule` の構造に応じて配列要素やネスト値をコピーします。

この組み立て方なら以下は引き継がれません。

- `id`
- `createdAt`
- `updatedAt`
- `deployToken`

`deployToken` の初期値は `emptyProjectValues()` と同じ未設定値になります。複製元の値をフォームへ渡してはいけません。

### 2. 複製用routeとloader

```tsx
export async function copyProjectLoader({
  params,
}: LoaderFunctionArgs): Promise<Project> {
  return getProject(params.projectId!);
}

export function CopyProjectRoute() {
  const sourceProject = useLoaderData() as Project;

  return (
    <ProjectForm
      key={`copy:${sourceProject.id}`}
      mode="create"
      initialValues={toCopiedProjectFormValues(sourceProject)}
      onSubmit={createProject}
    />
  );
}
```

route設定では、loaderの初回完了前にはローディング表示だけを出し、`ProjectForm` をマウントしません。

```tsx
{
  path: "/projects/:projectId/copy",
  loader: copyProjectLoader,
  Component: CopyProjectRoute,
  pendingElement: <ProjectLoading />,
}
```

`pendingElement` などの名前は利用中のルーターに合わせます。

### 3. `ProjectForm` の初期値を初回だけ取り込む

loader再検証で新しい `initialValues` オブジェクトが渡されても、フォームを再初期化しないようにします。

```tsx
export function ProjectForm(props: ProjectFormProps) {
  const initialValues = useRef(props.initialValues).current;
  const form = useProjectForm(initialValues);

  return (
    <ProjectFields
      form={form}
      submitLabel={props.mode === "edit" ? "保存" : "作成"}
    />
  );
}
```

これにより、同じ複製元IDの再検証ではユーザー入力が保持されます。一方、別の複製元へ遷移した場合は `key` が変わり、新しい初期値でフォームがマウントされます。

編集画面でも別プロジェクト間の遷移が同一コンポーネント上で起こり得るなら、同様にIDをkeyにします。

```tsx
export function EditProjectRoute({ project }: { project: Project }) {
  return (
    <ProjectForm
      key={`edit:${project.id}`}
      mode="edit"
      initialValues={toProjectFormValues(project)}
      onSubmit={updateProject}
    />
  );
}
```

## 状態とAPI入力

追加するフォーム状態はありません。

- `mode` は `"create"`
- 複製元IDはrouteパラメータとloaderだけで扱う
- 複製元の取得結果をフォーム状態と同期し続けない
- 複製時の初期値をdirty判定の基準値とするため、初期表示時はdirtyではない
- validationとエラー表示は既存の`useProjectForm`／`ProjectFields`をそのまま使う

送信は通常の新規作成と完全に同じです。

```tsx
onSubmit={createProject}
```

payloadには複製元IDを追加せず、通常の新規作成用serializerをそのまま使います。`updateProject`や複製専用APIは使用しません。

## 必要なテスト

最低限、以下を追加します。

1. 初期値変換の単体テスト

   - 指定された4項目だけを引き継ぐ
   - `id`、日時、`deployToken`を引き継がない
   - `name`に` (copy)`を付ける
   - すでに` (copy)`で終わる名前には再度付けない
   - 配列や通知ルールが複製元と同じ参照にならない

2. routeテスト

   - loader完了前にフォームが表示されない
   - loader完了後に`mode="create"`のフォームが表示される
   - 送信時に`createProject`が通常の新規作成payloadで呼ばれる
   - `updateProject`や複製専用APIが呼ばれない

3. 再検証テスト

```tsx
// 初期表示
// ユーザーがnameやdescriptionを変更
// 同じproject.idのloaderデータで再レンダー
// ユーザーが入力した値が残っていることを確認
```

4. 共通動作の回帰テスト

   - 複製フォームでも既存validationとエラー表示が動く
   - 初期表示はdirtyではない
   - 入力後はdirtyになる

なお、今回は読み取り専用環境のため、`referytale` が指定する対応表および欠落している `.agent/CONTINUITY.md` の作成は行っていません。
