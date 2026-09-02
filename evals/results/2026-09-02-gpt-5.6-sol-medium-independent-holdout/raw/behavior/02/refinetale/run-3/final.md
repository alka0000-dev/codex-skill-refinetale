複製は新しいフォームモードにせず、**route境界で複製元を新規作成用の初期値へ変換するだけ**にします。`ProjectForm`、validation、送信経路は既存の新規作成へ合流させるのが最小です。

## 変更契約

変更する挙動:

- 編集画面などから「複製して新規作成」routeへ遷移できる。
- loader完了後、複製用初期値で新規作成フォームを一度だけ初期化する。
- 指定された4項目だけを引き継ぎ、名前へ ` (copy)` を重複なく付加する。
- loader再検証後もフォームの入力を維持する。

変更しない挙動:

- 通常の新規作成と編集の初期値。
- `ProjectForm`のvalidation、dirty判定、エラー表示。
- 新規作成のAPI、payload、成功・失敗時の処理。
- 編集の更新API。

## 変更箇所

### 1. フォーム値変換

既存の`toProjectFormValues`と同じ変換モジュールに、複製専用の境界変換を1つ追加します。

```ts
export function toCopiedProjectFormValues(
  project: Project,
): ProjectFormValues {
  const source = toProjectFormValues(project);

  return {
    ...emptyProjectValues(),
    name: source.name.endsWith(" (copy)")
      ? source.name
      : `${source.name} (copy)`,
    description: source.description,
    memberRoleIds: source.memberRoleIds,
    notificationRules: source.notificationRules,
    deploymentTargetId: source.deploymentTargetId,
  };
}
```

ポイント:

- `emptyProjectValues()`を土台にして、引継ぎ対象を明示的に許可します。
- `deployToken`は元データから読まず、空の初期値のままにします。
- `id`、`createdAt`、`updatedAt`は`ProjectFormValues`へ入りません。
- 配列やルールをフォーム側で破壊的に変更する実装なら、既存の`toProjectFormValues`内でコピーする責務を維持します。複製変換だけに別のコピー方法を追加しません。

### 2. 複製route

`project-routes.tsx`へ複製routeを追加します。フォーム上の実処理は新規作成と同じです。

```tsx
export function DuplicateProjectRoute({
  project,
}: {
  project: Project;
}) {
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

route設定では、複製元取得用loaderと、フォームを含まないローディング表示を設定します。

```tsx
{
  path: "/projects/:projectId/duplicate",
  loader: loadProject,
  pendingElement: <ProjectLoading />,
  element: <DuplicateProjectRoute />,
}
```

実際のrouter APIに合わせて記法は調整しますが、境界は次のとおりです。

1. loader開始
2. ローディング表示（`ProjectForm`は未mount）
3. loader成功
4. 複製初期値を一度だけ作成
5. `ProjectForm`を`mode="create"`でmount

loader失敗時もフォームは表示せず、既存のroute error UIへ流します。

### 3. 複製導線

既存のプロジェクト編集画面またはアクションメニューに、複製routeへのリンクだけを追加します。

```tsx
<Link to={`/projects/${project.id}/duplicate`}>
  複製して新規作成
</Link>
```

ここではデータ取得や初期値生成を行いません。

## 状態と再検証

追加する状態は、`DuplicateProjectRoute`の「初回loader結果から作った初期値スナップショット」1つだけです。

`useState`の遅延初期化にする理由は、loader再検証によって新しい`project`オブジェクトが渡されても、`ProjectForm`へ新しい初期値を渡さないためです。現在入力中のフォーム状態とはライフサイクルと意味が異なるため、このスナップショットは重複状態ではありません。

次は追加しません。

- `"duplicate"`という`ProjectForm`のmode
- `isDuplicate` boolean
- 複製元IDを保持するフォーム状態
- props変更を監視する`useEffect`
- route再検証時の`reset`
- route要素への`project.updatedAt`などを使った`key`

特に`useEffect(() => form.reset(initialValues), ...)`はユーザー入力を上書きするため禁止です。

## API入力

送信は通常の新規作成と完全に同じです。

```tsx
<ProjectForm
  mode="create"
  initialValues={initialValues}
  onSubmit={createProject}
/>
```

payloadにも以下は追加しません。

- `sourceProjectId`
- `cloneFrom`
- 元プロジェクトの`id`
- `deployToken`
- 作成・更新日時

複製元の取得はloaderの読み取り、送信は既存の新規作成APIという2つの境界に限定します。更新APIや複製専用APIは不要です。

## 最小テスト

実コードが提示されていないため実行はしていません。実装時には以下を直接保証します。

| テスト場所 | ケース | 期待結果 |
|---|---|---|
| 初期値変換の単体テスト | 全項目を持つProjectを変換 | 指定4項目だけ引継ぎ、tokenは空、ID・日時なし |
| 初期値変換の単体テスト | `Alpha` | `Alpha (copy)` |
| 初期値変換の単体テスト | `Alpha (copy)` | `Alpha (copy)`のまま |
| routeテスト | loader保留中 | ローディングだけ表示され、フォームなし |
| routeテスト | loader失敗 | フォームと作成API呼び出しなし |
| routeテスト | loader成功 | 複製初期値を初期値としてフォーム表示 |
| routeテスト | 入力後にloader再検証 | 入力値とdirty状態を維持 |
| route/API連携テスト | 複製フォーム送信 | `createProject`が通常の作成payloadで呼ばれ、`updateProject`は未呼び出し |
| 既存テスト | 通常作成・編集 | 初期値、validation、エラー表示、各APIが従来どおり |

複製専用にvalidationやエラー表示のテスト一式をコピーする必要はありません。`ProjectForm mode="create"`へ合流することをrouteテストで確認し、共通仕様は既存の`ProjectForm`テストを正本とします。

RefineTaleの観点では、実際の差分を「loader」「複製初期値変換」「初回スナップショット」に閉じ込め、フォーム内部とAPI経路を増やさない方針です。
