最小実装は、複製専用APIやフォームモードを増やさず、loaderで取得した `Project` を「新規作成用の初期値」に変換して、既存の `ProjectForm mode="create"` に渡す構成です。

### 変更対象

| 対象 | 変更 |
|---|---|
| `project-routes.tsx` | 複製元をloaderで取得する新規作成ルートを追加 |
| Project→フォーム値の変換関数 | 複製用の変換関数を追加 |
| 編集画面 | 「複製して新規作成」へのリンクまたはボタンを追加 |
| `ProjectForm.tsx` | 原則変更なし |
| 作成API | 変更なし |
| テスト | 変換、loader待機、再検証後の入力保持、送信先を追加 |

### 状態と初期化

追加する状態は、loader完了後に一度だけ確定する新規作成用の `initialValues` だけです。

フォーム表示後のloader再検証で入力を上書きしないよう、routeで最初の値をスナップショット化します。`useProjectForm` にloader結果を直接変換して毎回渡さないのが重要です。

```tsx
function copyName(name: string): string {
  return name.endsWith(" (copy)") ? name : `${name} (copy)`;
}

function toCopiedProjectFormValues(source: Project): ProjectFormValues {
  return {
    ...emptyProjectValues(),
    name: copyName(source.name),
    description: source.description,
    memberRoleIds: [...source.memberRoleIds],
    notificationRules: structuredClone(source.notificationRules),
    deploymentTargetId: source.deploymentTargetId,
  };
}
```

`emptyProjectValues()` を土台にして、引き継ぐフィールドだけを明示的に上書きします。これにより、以下は読み取りません。

- `id`
- `createdAt`
- `updatedAt`
- `deployToken`

特に `deployToken` は変換結果へ含めず、複製画面のフィールドにも渡しません。`ProjectFormValues` に存在する設計なら、複製時は `null` とし、createモードでは表示しないようにします。作成payloadもホワイトリスト方式で組み立てるのが安全です。

### route

React Routerを想定した概略です。

```tsx
export async function copyProjectLoader({ params }: LoaderArgs) {
  return {
    sourceProject: await getProject(params.projectId!),
  };
}

export function CopyProjectRoute() {
  const { sourceProject } = useLoaderData<typeof copyProjectLoader>();

  // このrouteのマウント中は、loader再検証が起きても作り直さない
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

ルート例:

```tsx
{
  path: "/projects/:projectId/copy",
  loader: copyProjectLoader,
  element: <CopyProjectRoute />,
}
```

loader完了前はroute element自体を描画しない構成にします。アプリ側で独自のloading UIを扱う場合も、その間は `ProjectForm` をマウントしません。

編集画面には遷移だけを追加します。

```tsx
<Link to={`/projects/${project.id}/copy`}>
  複製して新規作成
</Link>
```

`ProjectForm` に `"copy"` モードを追加する必要はありません。複製後はあくまで新規作成なので、submit label、validation、dirty判定、エラー表示は既存のcreate動作をそのまま利用できます。

### API入力

送信処理は通常作成と完全に共通です。

```tsx
<ProjectForm
  mode="create"
  initialValues={initialValues}
  onSubmit={createProject}
/>
```

送信先は既存の作成エンドポイント、payloadも既存の `ProjectFormValues` または既存の作成用変換結果です。

複製元IDをpayloadへ追加したり、`updateProject`、複製専用APIを呼んだりしません。

### 必要なテスト

1. 変換関数

- 指定された4項目だけを引き継ぐ
- 配列・ルールが新しい参照になる
- `name` に ` (copy)` が付く
- すでに末尾が ` (copy)` なら重ねて付けない
- `id`、日時、`deployToken` がフォーム値へ入らない

2. route/loader

- loader解決前はフォームが表示されない
- loader解決後にcreateモードで表示される
- `createProject` が `onSubmit` に渡される

3. ユーザー入力の保持

```tsx
// 初回loader結果で表示
await user.clear(screen.getByLabelText("名前"));
await user.type(screen.getByLabelText("名前"), "ユーザー入力");

// loaderを再検証して別オブジェクトを返す
await revalidateLoader();

expect(screen.getByLabelText("名前")).toHaveValue("ユーザー入力");
```

4. 既存フォーム契約

- 複製画面でも既存validationが動く
- 編集後にdirtyになる
- APIエラーが既存形式で表示される
- submit時に通常の作成APIだけが呼ばれる
- `deployToken` が画面にもpayloadにも現れない

なお、`referytale` に沿って責務を整理しましたが、対応表の保存先と `.agent/CONTINUITY.md` は、この環境が読み取り専用のため作成できませんでした。
