最小方針は、複製を第3のフォーム mode にせず、route 境界で `Project` を新規作成用の `ProjectFormValues` に変換し、直後に既存の create 経路へ合流させることです。

## 変更契約

変更する挙動:

- 複製 route が複製元を loader で取得する。
- 取得完了後、指定項目だけを初期値にして新規作成フォームを表示する。
- loader 再検証では表示済みフォームを再初期化しない。

変更しない挙動:

- `ProjectForm` の mode は `"create" | "edit"` のまま。
- validation、dirty 判定、エラー表示、submit 処理は既存と共通。
- 送信先は `createProject`、payload も通常作成と同じ。
- 通常の新規作成・編集経路は維持する。

## 変更箇所

### 1. Project → 複製初期値の変換

既存のフォーム値変換を所有するファイルに `toDuplicatedProjectFormValues` を追加します。

`Project` を丸ごと spread せず、`emptyProjectValues()` を起点に引き継ぐ項目だけを明示します。これにより、現在および将来追加される機密項目が偶然複製されません。

```ts
const COPY_SUFFIX = " (copy)";

export function toDuplicatedProjectFormValues(
  project: Project,
): ProjectFormValues {
  return {
    ...emptyProjectValues(),
    name: project.name.endsWith(COPY_SUFFIX)
      ? project.name
      : `${project.name}${COPY_SUFFIX}`,
    description: project.description,
    memberRoleIds: [...project.memberRoleIds],
    notificationRules: project.notificationRules.map((rule) => ({ ...rule })),
    deploymentTargetId: project.deploymentTargetId,
  };
}
```

この変換では以下を設定しません。

- `id`
- `createdAt`
- `updatedAt`
- `deployToken`

`deployToken` が `ProjectFormValues` に含まれる場合も、`emptyProjectValues()` の空値を維持します。複製用の個別リセット処理は追加しません。

### 2. 複製 route と loader

既存のプロジェクト取得処理を loader から再利用します。

```tsx
export async function duplicateProjectLoader({ params }: LoaderArgs) {
  return getProject(params.projectId);
}

export function DuplicateProjectRoute() {
  const project = useLoaderData() as Project;

  return (
    <ProjectForm
      key={project.id}
      mode="create"
      initialValues={toDuplicatedProjectFormValues(project)}
      onSubmit={createProject}
    />
  );
}
```

route 定義側で loader と pending UI を設定します。loader が完了するまで route component が描画されない構成なら、追加の `isLoading` state は不要です。

`key={project.id}` は別の複製元へ遷移した場合だけフォームを作り直すためのものです。同じ ID の loader 再検証では remount しません。

### 3. 初期値を初回マウント時に固定

`useProjectForm` が props の変更時に reset する可能性があるなら、`ProjectForm` が「initial」の意味を明示的に所有します。

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

これにより、loader 再検証で新しい `initialValues` オブジェクトが渡ってもユーザー入力は維持されます。`useProjectForm` が既にマウント時だけ初期値を読む契約を保証しているなら、この変更は不要です。

追加する状態はフォーム自身だけです。`isDuplicate`、`sourceProject`、`hasInitialized` などの状態や boolean は追加しません。

## データ経路

```text
duplicate route loader
  → Project
  → toDuplicatedProjectFormValues
  → ProjectForm(mode="create")
  → 既存 validation / dirty / error
  → createProject(ProjectFormValues)
```

編集API、複製専用API、複製専用payloadは追加しません。

## 最小テスト

| 対象 | 確認内容 | 期待結果 |
|---|---|---|
| 変換関数 | 通常名の複製 | `name` が `元名 (copy)` |
| 変換関数 | 既に ` (copy)` で終わる名前 | suffix が重複しない |
| 変換関数 | 引き継ぎ項目 | 指定された4項目だけ一致 |
| 変換関数 | 非引き継ぎ項目 | `deployToken` は空、ID・日時はフォーム値に入らない |
| 複製 route | loader 未完了 | フォームが表示されない |
| 複製 route | loader 完了 | `mode="create"` で初期値が表示される |
| 複製 route | 入力後に同じIDを再検証 | ユーザー入力、dirty、エラー状態が維持される |
| 複製 route | submit | 通常作成と同じ `createProject` が同じ形式のpayloadで1回呼ばれる |
| 既存経路 | 通常作成・編集 | 従来の初期値、ラベル、submit先が変わらない |

validation の全ケースを複製 route 用に重複させる必要はありません。共通フォームの既存テストを維持し、複製 route では「同じフォーム経路に接続されていること」と「再検証で上書きされないこと」だけを確認します。

今回は提示コードに対する実装方針のため、実際のテスト実行はしていません。実装時には上記ケースと既存の create/edit テスト、型チェック、lint、build の成功を完了条件にします。
