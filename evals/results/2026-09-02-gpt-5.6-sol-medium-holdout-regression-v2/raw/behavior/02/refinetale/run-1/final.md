最小方針は、複製を新しいフォーム種別にせず、route 境界で複製元を通常の新規作成用 `ProjectFormValues` に一度だけ変換することです。`ProjectForm`、validation、送信経路は変更しません。

## 変更契約

変更する挙動:

- 複製元を loader で取得し、取得完了後に新規作成フォームを表示する。
- 指定された項目だけを初期値へ引き継ぐ。
- 同じ複製元の loader 再検証では、表示済みフォームを再初期化しない。
- 送信には既存の `createProject` を使う。

変更しない挙動:

- 通常の新規作成と編集。
- `ProjectForm` の validation、dirty 判定、エラー表示。
- 新規作成APIのエンドポイントとpayload。
- `mode` は `"create" | "edit"` のまま。`"duplicate"` は追加しない。

## 変更箇所

### 1. フォーム値の変換関数

フォーム値への変換を所有している既存モジュールに、複製用変換を追加します。除外項目を消す方式ではなく、空の新規作成値へ引継ぎ許可項目だけを設定します。

```ts
export function toDuplicatedProjectFormValues(
  project: Project,
): ProjectFormValues {
  // 既存のフォーム向け変換が値の正規化や配列のコピーを担っている想定
  const source = toProjectFormValues(project);

  return {
    ...emptyProjectValues(),
    name: `${project.name} (copy)`,
    description: source.description,
    memberRoleIds: source.memberRoleIds,
    notificationRules: source.notificationRules,
    deploymentTargetId: source.deploymentTargetId,
  };
}
```

これにより次が構造的に除外されます。

- `id`
- `createdAt`
- `updatedAt`
- `deployToken`

`ProjectFormValues` に `deployToken` が存在する場合も、値は `emptyProjectValues()` と同じ空値になります。複製元のtokenを一度フォーム値へ入れてから消す経路は作りません。

`name` のsuffix付与はこの変換の初回実行時だけです。loader再検証のたびに現在のフォーム名へ追加する処理は置きません。

### 2. 複製route

`project-routes.tsx` に複製routeを追加します。loaderは通常のプロジェクト取得処理を再利用します。

```tsx
export async function duplicateProjectLoader({ params }: LoaderArgs) {
  return getProject(params.projectId);
}

export function DuplicateProjectRoute() {
  const sourceProject = useLoaderData<typeof duplicateProjectLoader>();

  return (
    <DuplicateProjectForm
      key={sourceProject.id}
      sourceProject={sourceProject}
    />
  );
}

function DuplicateProjectForm({
  sourceProject,
}: {
  sourceProject: Project;
}) {
  const [initialValues] = useState(() =>
    toDuplicatedProjectFormValues(sourceProject),
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

`key` は複製元の `id` だけにします。

- 同じプロジェクトの再検証: `id` が変わらないためフォームを維持
- 別の複製元へ遷移: `id` が変わるため新しい初期値で再生成
- `updatedAt` やloader結果オブジェクトを `key` にしない

loaderの初回取得中はrouteの既存pending UIを表示し、`DuplicateProjectForm`をmountしません。再検証中は、すでにmount済みのフォームをpending UIへ置き換えないようにします。

loaderが失敗した場合は既存のroute error boundaryへ流し、空値フォームへのfallbackは行いません。

### 3. 褢製への導線

複製元の `id` を所有する編集画面またはそのrouteコンテナに、複製routeへのリンクを追加します。

```tsx
<Link to={`/projects/${project.id}/duplicate`}>
  複製して新規作成
</Link>
```

これはフィールドや送信処理ではないため、`ProjectForm`へ `onDuplicate` などの任意propsは追加しません。

`ProjectForm.tsx` 自体は変更不要です。

## 状態と初期化タイミング

追加するのは、複製route内の不変な初期値スナップショットだけです。

- loader状態: routerが所有
- 初期値スナップショット: `DuplicateProjectForm` の初回mount時に一度生成
- 編集中の値、dirty、validation、errors: 既存の `useProjectForm` が所有
- 複製元Projectを別のReact stateへコピーしない
- `useEffect`による `reset()` や初期値同期は追加しない

初期値スナップショットとフォーム状態は、前者がmount時だけの入力、後者がユーザーによって更新される値という異なるライフサイクルを持ちます。

## API入力

送信経路は通常の新規作成と完全に同じです。

```tsx
<ProjectForm
  mode="create"
  initialValues={initialValues}
  onSubmit={createProject}
/>
```

更新APIや複製専用API、`sourceProjectId`、`duplicate: true` などの追加payloadは不要です。

## 最小テスト

| 契約・経路 | 検証 | 期待結果 |
|---|---|---|
| 引継ぎ項目 | 変換関数へ全項目入りProjectを渡す | 指定4項目だけが元の値になる |
| 除外項目 | 同じ変換関数でtoken等を確認 | `id`、日時はフォーム値に入らず、tokenは通常の空値 |
| 名前 | `name: "Alpha"`を変換 | `"Alpha (copy)"` |
| 初回loading | loaderを未解決にするrouteテスト | pending UIだけが表示され、フォームは表示されない |
| loader失敗 | loaderをreject/404にする | error boundaryが表示され、フォームとcreate APIは実行されない |
| 初期表示 | loader解決後のrouteテスト | `mode="create"`相当の表示と複製初期値になる |
| 再検証 | nameをユーザーが変更後、同じIDのloaderを再検証 | ユーザー入力、dirty、エラー状態が保持される |
| 複製元変更 | 別IDの複製routeへ遷移 | 新しい複製元から初期化される |
| validation | 必須値を不正にして送信 | 既存と同じエラーが出て、`createProject`は呼ばれない |
| 正常送信 | 値を編集して送信 | `createProject`だけが現在のフォーム値で1回呼ばれる |
| 既存create | 既存routeテスト | 空値から開始し、従来どおりcreate APIへ送信 |
| 既存edit | 既存routeテスト | プロジェクト値から開始し、従来どおりupdate APIへ送信 |

実ファイルは作業領域に提供されていなかったため、今回は提示コードを正本とした実装方針と必要テストの特定までです。
