最小構成は、`ProjectForm` に複製モードを追加せず、「複製元から作った初期値で通常の新規作成フォームを開く」形です。`mode` は `"create"`、送信処理も `createProject` のままにします。

## 変更する箇所

### 1. 初期値変換関数を追加

`Project` 全体を展開せず、引き継ぐ項目だけを明示的にコピーします。

```tsx
function toCopiedProjectFormValues(
  source: Project,
): ProjectFormValues {
  return {
    ...emptyProjectValues(),
    name: `${source.name} (copy)`,
    description: source.description,
    memberRoleIds: [...source.memberRoleIds],
    notificationRules: source.notificationRules.map(copyNotificationRule),
    deploymentTargetId: source.deploymentTargetId,
  };
}
```

`copyNotificationRule` は、`NotificationRule` の構造に応じて既存のコピー関数を使うか、変更可能な入れ子がある場合はそこまでコピーします。

重要なのは次の点です。

- `id`、`createdAt`、`updatedAt` はフォーム値へ入れない
- `deployToken` は複製元から読まない
- `emptyProjectValues()` を土台にして、通常の新規作成と同じ未設定値を使う
- `name` への付与は初期化時に一度だけ行う

複製元が `Sample (copy)` なら、新たな複製の名前は `Sample (copy) (copy)` です。「一度だけ」は、1回の複製操作につき末尾へ1回付与し、再検証のたびに追加しないという意味です。

### 2. 複製用routeを追加

例として `/projects/:projectId/copy` を追加します。

```tsx
export async function copyProjectLoader({
  params,
}: LoaderArgs) {
  return {
    sourceProject: await getProject(params.projectId),
  };
}

export function CopyProjectRoute() {
  const { sourceProject } =
    useLoaderData<typeof copyProjectLoader>();

  return (
    <CopyProjectForm
      key={sourceProject.id}
      sourceProject={sourceProject}
    />
  );
}
```

loader完了前はrouteのpending表示だけを出し、`CopyProjectRoute`、したがって`ProjectForm`を描画しません。取得失敗時は既存のroute error boundaryへ流します。

### 3. 初期値を最初の表示時に固定

loaderの再検証で新しい`Project`オブジェクトが返っても、フォームへ渡す`initialValues`を作り直さないようにします。

```tsx
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

`useMemo(..., [sourceProject])` は使いません。再検証で依存値が変わり、フォーム実装によってはユーザー入力を再初期化する可能性があるためです。

`key={sourceProject.id}` により、同じ複製元の再検証では状態を維持し、別の複製元IDへ遷移した場合だけ新しい初期値でマウントし直します。

## 状態とAPI

追加する状態は、複製route内の固定された`initialValues`だけです。`ProjectForm`や`useProjectForm`には複製専用状態を追加しません。

APIの使い分けは次のとおりです。

| タイミング | API入力 | 用途 |
|---|---|---|
| route loader | 複製元の`projectId` | 既存プロジェクトの取得 |
| フォーム送信 | 通常の`ProjectFormValues` | `createProject`による新規作成 |

複製専用APIや`updateProject`は使用しません。作成payloadにも複製元IDや日時、複製元の`deployToken`を追加しません。

## 既存コンポーネントへの影響

`ProjectForm.tsx`は変更不要です。

```tsx
<ProjectForm
  mode="create"
  initialValues={initialValues}
  onSubmit={createProject}
/>
```

として利用するため、以下は既存の作成・編集と共通のままです。

- validation
- dirty判定
- エラー表示
- submit label
- 送信中状態

複製された値がフォームの初期値になるため、表示直後はdirtyではありません。

## 最小限のテスト

1. 初期値変換の単体テスト

- 指定された4項目を引き継ぐ
- 名前に` (copy)`を1回追加する
- `id`、日時、`deployToken`を引き継がない
- 配列やルールを複製元と同じ参照にしない

2. routeテスト

- loader待機中はフォームを表示しない
- loader完了後に`mode="create"`で表示する
- 取得エラーは既存のエラー表示へ流れる

3. 再検証テスト

```tsx
// 初期表示: "Original (copy)"
// ユーザーが名前を "My project" に変更
// loaderを再検証
expect(nameInput).toHaveValue("My project");
```

併せて、再検証後に`description`などの入力も維持されることを確認します。

4. 送信テスト

- `createProject`だけが呼ばれる
- 通常の新規作成と同じpayload形式になる
- `updateProject`や複製専用APIが呼ばれない

これにより、既存フォームには手を入れず、複製元の取得・初期値生成・再検証からの保護だけをroute側へ追加できます。
