最小方針は、複製を第3のフォームモードにしないことです。route loaderで取得した複製元を一度だけ`ProjectFormValues`へ変換し、その後は既存の`mode="create"`へ合流させます。

## 変更契約

変更する挙動:

- 複製用routeへ遷移すると、loader完了後に作成フォームを表示する。
- 指定された項目だけを複製元から初期設定する。
- 名前はフォーム初期化時に`${project.name} (copy)`とする。
- 再検証後も表示済みフォームの値を維持する。

変更しない挙動:

- 通常の新規作成・編集の初期値。
- `ProjectForm`のvalidation、dirty判定、エラー表示、送信処理。
- 新規作成APIとpayload形式。
- 編集API。
- `deployToken`を含む機密値の扱い。

## 変更箇所

### 1. 複製用の値変換

既存の`toProjectFormValues`は編集用の変換として維持します。複製は許可リスト方式で別変換を追加します。

```ts
export function toDuplicatedProjectFormValues(
  project: Project,
): ProjectFormValues {
  return {
    ...emptyProjectValues(),
    name: `${project.name} (copy)`,
    description: project.description,
    memberRoleIds: project.memberRoleIds,
    notificationRules: project.notificationRules,
    deploymentTargetId: project.deploymentTargetId,
  };
}
```

`...project`してから除外する方式は使いません。将来`Project`へ機密項目が増えた場合にも、意図せず複製しないためです。

この変換では以下を代入しません。

- `id`
- `createdAt`
- `updatedAt`
- `deployToken`

`deployToken`の初期値は通常の新規作成と同じく`emptyProjectValues()`が正本です。通常の作成フォームで表示しない設計なら、複製だけの表示分岐も追加しません。

なお、`name`は「複製元の現在名へ1回追加」と解釈します。複製元がすでに`A (copy)`なら、結果は`A (copy) (copy)`です。再検証のたびに追加されることはありません。

### 2. 複製用routeとloader

route loaderはフォームの描画前に複製元を解決します。

```tsx
export async function duplicateProjectLoader({
  params,
}: LoaderArgs): Promise<Project> {
  return getProject(params.projectId);
}

export function DuplicateProjectRoute() {
  const project = useLoaderData() as Project;

  return (
    <DuplicateProjectForm
      key={project.id}
      project={project}
    />
  );
}

function DuplicateProjectForm({ project }: { project: Project }) {
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

route定義の例:

```tsx
{
  path: "/projects/:projectId/duplicate",
  loader: duplicateProjectLoader,
  element: <DuplicateProjectRoute />,
}
```

loaderをdeferせず、routerのpending UIを使います。したがって、取得中に複製フォームが空値や仮値で表示される期間はありません。

### 3. 初期化タイミングと状態

追加する状態は`DuplicateProjectForm`の`initialValues`だけです。

- loader初回解決時に一度だけ作る。
- 同じ`project.id`の再検証では更新しない。
- ユーザーが編集する現在値は、既存の`useProjectForm`だけが所有する。
- 別の複製元IDへ遷移した場合は`key={project.id}`により初期化し直す。

この状態とフォーム状態は重複ではありません。

- `initialValues`: dirty判定の基準となる固定スナップショット
- `useProjectForm`の状態: ユーザーが変更する現在値

`useEffect(() => form.reset(loaderData), [loaderData])`のような同期は追加しません。これが再検証で入力を上書きする直接原因になるためです。

### 4. `ProjectForm`

変更不要です。

```tsx
<ProjectForm
  mode="create"
  initialValues={duplicatedValues}
  onSubmit={createProject}
/>
```

複製は作成フォームなので、表示ラベルも既存どおり「作成」です。`mode: "duplicate"`、`isDuplicating`、複製専用validationなどは追加しません。

### 5. API入力

送信経路は通常の新規作成と完全に共通です。

```text
loaderのProject
  → 許可項目だけProjectFormValuesへ変換
  → 既存ProjectForm
  → 既存createProject(values)
  → 通常の新規作成payload
```

追加しないもの:

- 更新API呼び出し
- 複製専用API
- `sourceProjectId`などの追加payload
- 元の`deployToken`
- 複製専用のpayload型

通常の作成payloadが`deployToken: null`などの既定値を含む場合は、その通常契約をそのまま維持します。

## 最小テスト

| 対象 | 確認内容 | 期待結果 |
|---|---|---|
| 値変換の単体テスト | 指定された4項目と名前 | 名前に` (copy)`が1回追加され、4項目が一致する |
| 値変換の単体テスト | 非引き継ぎ項目 | `id`、日時、元の`deployToken`が初期値へ入らない |
| routeテスト | loader待機中 | 複製フォームが表示されない |
| routeテスト | loader成功後 | `mode="create"`相当のフォームが複製値で表示され、初期dirtyはfalse |
| routeテスト | loader再検証 | 入力変更後に再検証しても、名前・各フィールドが上書きされない |
| route/送信テスト | 複製フォーム送信 | `createProject`が現在のフォーム値で呼ばれ、`updateProject`は呼ばれない |
| 既存回帰テスト | 通常作成・編集 | 従来の初期値、submit先、validation、dirty、エラー表示が変わらない |

validationやエラーの全パターンを複製routeでも再テストする必要はありません。`ProjectForm`が共通であることと、複製routeがそのフォームへ正しい初期値・`createProject`を渡す境界だけを検証します。

今回は実装ではなく方針提示であり、実リポジトリに対象コードがなかったためテストは未実施です。上記テストが実装時に必要となる直接的な検証範囲です。
