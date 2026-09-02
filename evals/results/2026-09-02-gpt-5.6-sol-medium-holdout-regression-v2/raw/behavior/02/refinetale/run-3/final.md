結論として、`ProjectForm`に`duplicate`モードを追加せず、複製元を「新規作成用の初期値」へ変換して既存の作成経路へ合流させるのが最小です。

前提として、編集画面などから複製ルートへ遷移する導線を追加します。実際のリポジトリには対象ファイルが存在しなかったため、以下は提示されたコードを基準にした実装方針です。

## 変更契約

変更する挙動:

- 複製ルートのloaderが元プロジェクトを取得する。
- 初回loader完了後だけ、複製用初期値で作成フォームを表示する。
- 名前は末尾に` (copy)`がなければ付加する。
- 指定された4項目だけを元プロジェクトから引き継ぐ。
- 同じプロジェクトのloader再検証ではフォームを初期化し直さない。

変更しない挙動:

- 通常の新規作成は`emptyProjectValues()`を使う。
- 編集は`toProjectFormValues(project)`と更新APIを使う。
- 複製の送信は既存の`createProject`を使う。
- validation、dirty、エラー表示は`useProjectForm`と`ProjectFields`に残す。
- `ProjectFormValues`やAPI payloadに複製元IDを追加しない。

## 変更箇所

### 1. フォーム値変換

フォーム値変換を所有している既存モジュールへ、`toCopiedProjectFormValues`を追加します。

`emptyProjectValues()`を土台にすることで、`deployToken`を含む新規作成時のデフォルト値を維持しつつ、引き継ぐ項目をホワイトリスト化します。

```ts
const COPY_SUFFIX = " (copy)";

export function toCopiedProjectFormValues(
  project: Project,
): ProjectFormValues {
  return {
    ...emptyProjectValues(),
    name: project.name.endsWith(COPY_SUFFIX)
      ? project.name
      : `${project.name}${COPY_SUFFIX}`,
    description: project.description,
    memberRoleIds: [...project.memberRoleIds],
    notificationRules: project.notificationRules.map((rule) => ({
      ...rule,
    })),
    deploymentTargetId: project.deploymentTargetId,
  };
}
```

`NotificationRule`にネストした可変値がある場合は、既存のフォーム値変換関数で必要な深さまでコピーします。汎用的な`structuredClone`は追加しません。

この実装では次の値を明示的に引き継ぎません。

- `id`
- `createdAt`
- `updatedAt`
- `deployToken`

`deployToken`は`emptyProjectValues()`の空値のままなので、元のトークンが初期表示されません。

### 2. 複製ルート

複製元取得には既存のプロジェクト取得APIを使います。複製専用APIは追加しません。

```tsx
export async function duplicateProjectLoader({
  params,
}: LoaderFunctionArgs) {
  return getProject(requiredProjectId(params));
}

export function DuplicateProjectRoute() {
  const project = useLoaderData<typeof duplicateProjectLoader>();

  return (
    <DuplicateProjectForm
      key={project.id}
      sourceProject={project}
    />
  );
}

function DuplicateProjectForm({
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

初期値を`useMemo([project])`で作ると、再検証でloader結果のオブジェクトが変わった際にフォーム初期値も変わります。setterを持たない`useState`にすることで、初回表示時のスナップショットを保持します。

`key={project.id}`には別の責務があります。

- 同じIDの再検証: keyが変わらず、ユーザー入力を保持する。
- 別の複製元IDへのルート遷移: keyが変わり、新しい複製元で初期化する。

これはフォームの編集状態とは異なるライフサイクルを持つ、必要な1つの初期値状態です。

### 3. ルート設定と画面導線

例として次のようなルートを追加します。

```tsx
{
  path: "/projects/:projectId/duplicate",
  loader: duplicateProjectLoader,
  element: <DuplicateProjectRoute />,
  pendingElement: <ProjectFormLoading />,
  errorElement: <ProjectRouteError />,
}
```

初回loader中の`pendingElement`には`ProjectForm`を含めません。再検証中は既にマウント済みのフォームを維持して構いません。

編集画面のアクション領域など、既存のナビゲーション責務を持つコンポーネントに次のリンクを追加します。

```tsx
<Link to={`/projects/${project.id}/duplicate`}>
  複製して新規作成
</Link>
```

`ProjectForm`自体は変更しません。複製元IDや画面遷移をフォームに持たせる必要がないためです。

## 状態とデータ経路

```text
projectId
  → loader
  → Project
  → toCopiedProjectFormValues（初回のみ）
  → ProjectFormValues
  → 既存useProjectForm
  → 既存createProject
```

追加しないもの:

- `mode: "duplicate"`
- `isDuplicate` boolean
- 複製元を保持するフォーム状態
- 複製専用payload
- 更新APIへの分岐
- loader結果をフォームへ同期する`useEffect`

API入力は通常の新規作成と完全に同じです。

```ts
createProject(values: ProjectFormValues)
```

`sourceProjectId`などはpayloadへ含めません。

## 必要なテスト

| 契約・経路 | テスト | 期待結果 |
|---|---|---|
| 引き継ぎ対象 | `toCopiedProjectFormValues`へ全項目入りのProjectを渡す | `description`、`memberRoleIds`、`notificationRules`、`deploymentTargetId`が一致 |
| 除外対象 | 同じ変換テスト | `id`と日時はフォーム値に存在せず、`deployToken`は新規作成時の空値 |
| 通常の名前 | `name: "Alpha"`を変換 | `"Alpha (copy)"` |
| 既にコピー名 | `name: "Alpha (copy)"`を変換 | `"Alpha (copy)"`のままで二重付加されない |
| loader待機中 | loaderを未解決にしたルートテスト | ローディング表示のみでフォームが存在しない |
| loader失敗 | loaderをrejectまたは404にする | エラー境界が表示され、フォームとcreate API呼び出しがない |
| loader成功 | loaderをresolveする | `mode="create"`のフォームが複製初期値で表示される |
| 再検証 | フォーム入力後、同じIDのloaderを再検証する | 入力値とdirty状態が保持される |
| 別IDへの遷移 | Aの複製画面からBの複製ルートへ遷移 | Bの値で新しく初期化される |
| 送信経路 | 複製フォームを送信 | `createProject`だけが通常の新規payloadで1回呼ばれる |
| API不変条件 | 同じ送信テスト | 更新APIと複製専用APIは呼ばれず、`sourceProjectId`も送られない |
| validation・エラー | 複製初期値を不正値にして送信 | 既存の作成フォームと同じエラー表示になり、create APIは呼ばれない |
| 通常作成の回帰 | `NewProjectRoute`の既存テスト | 空初期値とcreate APIが維持される |
| 編集の回帰 | `EditProjectRoute`の既存テスト | 編集初期値とupdate APIが維持される |

validationやdirtyの詳細な組み合わせは複製ルート側で重複テストせず、仕様を所有する`ProjectForm`／`useProjectForm`の既存テストで保証します。複製ルートでは「同じフォームへ接続されていること」と「再検証で状態が保持されること」だけを検証すれば十分です。
