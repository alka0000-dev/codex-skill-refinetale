最小構成は、複製用Routeと変換関数だけを追加し、既存の`ProjectForm`を`mode="create"`のまま再利用する方針です。

## 変更範囲

| 対象 | 変更 |
|---|---|
| Route定義 | 複製元IDを受け取る新規作成Routeとloaderを追加 |
| `project-routes.tsx` | `CopyProjectRoute`を追加 |
| 変換処理 | `Project`から複製用の`ProjectFormValues`を作る関数を追加 |
| `ProjectForm.tsx` | 原則変更なし |
| API | 追加・変更なし。`createProject`を使用 |
| テスト | 変換関数、loader、再検証、送信先を追加確認 |

## データの流れ

1. Route loaderが複製元の`Project`を取得する。
2. loader完了後にだけ`CopyProjectRoute`を表示する。
3. 複製元から許可された値だけを`ProjectFormValues`へ変換する。
4. 変換結果を、そのフォームインスタンスの初期値として一度だけ固定する。
5. `ProjectForm`を`mode="create"`かつ`onSubmit={createProject}`で表示する。

## 複製用初期値

除外漏れを防ぐため、`Project`全体をコピーして削除するのではなく、`emptyProjectValues()`を基準に引継ぎ対象だけを明示的に設定します。

```tsx
const COPY_SUFFIX = " (copy)";

function toCopiedProjectFormValues(project: Project): ProjectFormValues {
  return {
    ...emptyProjectValues(),

    name: project.name.endsWith(COPY_SUFFIX)
      ? project.name
      : `${project.name}${COPY_SUFFIX}`,

    description: project.description,
    memberRoleIds: [...project.memberRoleIds],
    notificationRules: structuredClone(project.notificationRules),
    deploymentTargetId: project.deploymentTargetId,

    // ProjectFormValuesに存在する場合も空値のままにする
    deployToken: null,
  };
}
```

これにより、以下は初期値にも混入しません。

- `id`
- `createdAt`
- `updatedAt`
- `deployToken`

`notificationRules`はフォームによる破壊的変更がloaderキャッシュへ波及しないよう、配列だけでなく要素も複製します。既存のルール変換関数があれば、`structuredClone`よりそちらを優先します。

## Routeと初期化タイミング

loaderの再検証で新しい`Project`オブジェクトが返ってもフォームを再初期化しないよう、初期値をフォーム表示時に固定します。

```tsx
export async function copyProjectLoader({
  params,
}: LoaderFunctionArgs): Promise<Project> {
  return getProject(params.sourceProjectId!);
}

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

`key={sourceProject.id}`の意味は次のとおりです。

- 同じ複製元のloader再検証：コンポーネントを維持し、ユーザー入力を保持
- 別の複製元IDへの遷移：コンポーネントを再作成し、新しい初期値を使用

Route loaderが解決するまでRoute要素自体を描画しない構成にし、待機中は既存のルーター用ローディングUIを表示します。`ProjectForm`内部で取得を開始する実装にはしません。

## 状態とAPI

フォームの状態は既存の`useProjectForm`だけで管理します。複製元Projectをフォーム状態へ保持する必要はありません。

送信時は通常の新規作成と完全に同じです。

```tsx
<ProjectForm
  mode="create"
  initialValues={initialValues}
  onSubmit={createProject}
/>
```

したがって、更新APIや複製専用API、`sourceProjectId`のような追加payloadは不要です。`ProjectForm`をそのまま使うため、validation、dirty判定、エラー表示も既存実装を共有できます。複製値を初期状態として初期化するので、表示直後のdirtyは`false`です。

## 必要なテスト

1. 変換関数の単体テスト

   - 引継ぎ対象4項目が設定される
   - `name`へ` (copy)`が付く
   - 既に末尾が` (copy)`なら重複しない
   - `id`、日時、`deployToken`が混入しない
   - 配列やルールが複製元と同じ参照にならない

2. Routeテスト

   - loader解決前はフォームが表示されない
   - 解決後は`mode="create"`で表示される
   - loaderエラー時は既存のRouteエラー表示になる

3. 再検証テスト

   - フォーム表示後に名前や説明を編集する
   - 同じ複製元IDでloaderを再検証する
   - 編集済みの入力が維持される

4. 送信テスト

   - `createProject`だけが呼ばれる
   - `updateProject`は呼ばれない
   - payload形式が通常の新規作成と同じ
   - 複製元のID、日時、トークンが送信されない

5. 共通挙動の確認

   - 初期表示時はdirtyでない
   - 編集後はdirtyになる
   - validationと送信エラーが通常の作成画面と同じように表示される

この構成なら、既存の作成・編集画面には手を入れず、複製固有の責務を「loader」「初期値変換」「初回だけの初期化」に限定できます。
