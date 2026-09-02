最小方針は、複製を新しいフォームモードにせず、route境界で複製元を通常の `ProjectFormValues` に変換し、その後は既存の新規作成経路へ合流させることです。

## 変更契約

変更する挙動:

- 複製用routeのloaderで複製元を取得する。
- 取得完了後、許可された値だけを初期値にして作成フォームを表示する。
- 初回表示後のloader再検証ではフォームを再初期化しない。

変更しない挙動:

- `ProjectForm` のmodeは `"create" | "edit"` のまま。
- validation、dirty判定、エラー表示、送信処理は既存のものを使う。
- 送信先は `createProject`。更新APIや複製専用APIは作らない。
- 通常作成・編集routeは変更しない。

## 変更箇所

### 1. フォーム値変換層

複製元を直接スプレッドせず、`emptyProjectValues()` を土台に許可フィールドだけを上書きします。これにより、除外項目を誤って引き継ぐ経路が生まれません。

```ts
const COPY_SUFFIX = " (copy)";

function appendCopySuffixOnce(name: string): string {
  return name.endsWith(COPY_SUFFIX) ? name : `${name}${COPY_SUFFIX}`;
}

export function toCopiedProjectFormValues(
  project: Project,
): ProjectFormValues {
  const source = toProjectFormValues(project);

  return {
    ...emptyProjectValues(),
    name: appendCopySuffixOnce(source.name),
    description: source.description,
    memberRoleIds: source.memberRoleIds,
    notificationRules: source.notificationRules,
    deploymentTargetId: source.deploymentTargetId,
  };
}
```

正本は以下のように分かれます。

- 作成時の未設定値・`deployToken` の空値: `emptyProjectValues`
- `Project` からフォーム型への既存変換: `toProjectFormValues`
- 複製対象の選択と名前の加工: `toCopiedProjectFormValues`

`id`、`createdAt`、`updatedAt` はフォーム値へ入れません。`deployToken` は複製元から読まず、`emptyProjectValues()` の作成時既定値を使います。

### 2. `project-routes.tsx`

複製専用routeを追加します。ただしフォーム上は通常のcreateです。

```tsx
export async function cloneProjectLoader({
  params,
}: LoaderFunctionArgs) {
  return getProject(requiredProjectId(params));
}

export function CloneProjectRoute() {
  const project = useLoaderData() as Project;

  return <CloneProjectForm key={project.id} project={project} />;
}

function CloneProjectForm({ project }: { project: Project }) {
  const [initialValues] = useState(() =>
    toCopiedProjectFormValues(project),
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

ルーター側の構成例:

```tsx
{
  path: "/projects/:projectId/copy",
  loader: cloneProjectLoader,
  Component: CloneProjectRoute,
  errorElement: <ProjectLoadError />,
  HydrateFallback: <ProjectLoading />,
}
```

実際のルーターが別のpending UI APIを使う場合は、その既存方式に合わせます。

## 状態と初期化タイミング

追加する状態は、確定した初期値を保持する1つだけです。

```ts
const [initialValues] = useState(() => toCopiedProjectFormValues(project));
```

ライフサイクルは次のとおりです。

1. loader開始中はルーターのloading UIだけを表示する。
2. loader成功後に `CloneProjectForm` がmountする。
3. mount時に一度だけ複製用初期値を作る。
4. 以降のloader再検証ではstate initializerが再実行されないため、入力を上書きしない。
5. 別の複製元へ遷移した場合は `key={project.id}` によりremountし、新しい複製元で初期化する。

`isLoading`、`isInitialized`、`hasUserEdited` のようなbooleanや、loader変更を監視するreset用effectは追加しません。

## `ProjectForm.tsx`

変更不要です。

```tsx
<ProjectForm
  mode="create"
  initialValues={initialValues}
  onSubmit={createProject}
/>
```

複製を `"clone"` modeとして追加すると、ラベル、validation、送信、エラー処理などへ不要な分岐が伝播します。観測可能な差分は初期値だけなので、route境界で通常作成へ合流させます。

## API入力

送信時の経路は通常作成と同一です。

```text
ProjectFormValues
  → 既存validation
  → createProject(values)
  → 既存の新規作成API
```

複製元の `Project` をAPIへ渡さず、更新APIも呼びません。API payloadは、通常作成で既に使われている変換処理をそのまま通します。

## 最小テストと期待結果

| 変更契約・経路 | テスト | 期待結果 |
|---|---|---|
| 引き継ぎ対象 | `toCopiedProjectFormValues` の単体テスト | 4フィールドが複製元と一致する |
| 除外対象 | 同単体テスト | ID・日時は存在せず、`deployToken` は作成時既定値になる |
| 名前加工 | `"Project"` を変換 | `"Project (copy)"` |
| suffix重複防止 | `"Project (copy)"` を変換 | `"Project (copy)"` のまま |
| loader中 | routeテストでloaderを未解決にする | loading UIが表示され、フォームは存在しない |
| loader成功 | loaderを解決する | 作成フォームが複製初期値で表示される |
| loader失敗 | loaderをrejectまたは404にする | error UIが表示され、フォームと送信処理は実行されない |
| 再検証 | 入力変更後に同一IDのloaderを再検証する | ユーザー入力とdirty状態が維持される |
| 複製元変更 | 別IDへ遷移する | 新しい複製元の値で初期化される |
| 送信経路 | 複製フォームをsubmitする | `createProject` が通常作成と同形式の値で1回呼ばれる |
| API除外 | submit payloadを検査する | 元のID・日時・`deployToken`を含まない |
| 共通validation | 複製フォームへ不正値を入力する | 通常作成と同じエラー表示になり、APIは呼ばれない |
| 既存create | 既存routeテスト | 空の初期値、「作成」、`createProject`を維持 |
| 既存edit | 既存routeテスト | 編集初期値、「保存」、`updateProject`を維持 |

テストは変換関数とroute連携に置き、`ProjectForm` 内部で複製専用テストを重複させません。今回は実装ではなく方針提示であり、実テストは未実施です。
