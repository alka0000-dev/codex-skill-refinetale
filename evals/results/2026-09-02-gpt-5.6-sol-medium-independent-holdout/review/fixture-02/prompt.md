You are grading six anonymized answers to an independent holdout evaluation. Return only the requested structured result.

# 02: Reuse the project form for cloning

## Purpose

複製固有の差分を初期値へ閉じ、既存の作成経路とフォーム状態を重複させない設計を選べるか確認する。

## Input

既存のプロジェクト作成・編集画面に「既存プロジェクトから複製して新規作成」を追加します。要件を満たす最小限の実装方針を、変更するコンポーネント、状態、API入力、初期化タイミング、テストが分かる形で示してください。必要なら短い疑似コードを使ってください。

`ProjectForm.tsx`:

```tsx
type ProjectFormProps = {
  mode: "create" | "edit";
  initialValues: ProjectFormValues;
  onSubmit: (values: ProjectFormValues) => Promise<void>;
};

export function ProjectForm(props: ProjectFormProps) {
  const form = useProjectForm(props.initialValues);
  return <ProjectFields form={form} submitLabel={props.mode === "edit" ? "保存" : "作成"} />;
}
```

`project-routes.tsx`:

```tsx
export function NewProjectRoute() {
  return <ProjectForm mode="create" initialValues={emptyProjectValues()} onSubmit={createProject} />;
}

export function EditProjectRoute({ project }: { project: Project }) {
  return <ProjectForm mode="edit" initialValues={toProjectFormValues(project)} onSubmit={updateProject} />;
}
```

`Project`には次の値がある:

```ts
type Project = {
  id: string;
  name: string;
  description: string;
  memberRoleIds: string[];
  notificationRules: NotificationRule[];
  deploymentTargetId: string | null;
  deployToken: string | null;
  createdAt: string;
  updatedAt: string;
};
```

既存契約と新要件:

- 複製元はroute loaderで取得してからフォームを表示する。ローディング中はフォームを表示しない。
- 引き継ぐのは`description`、`memberRoleIds`、`notificationRules`、`deploymentTargetId`。
- `id`、`createdAt`、`updatedAt`、`deployToken`は引き継がず、`deployToken`は画面にも初期表示しない。
- `name`は元の名前に` (copy)`を一度だけ付ける。
- 送信先とpayloadは通常の新規作成と同じ。更新APIや複製専用APIは追加しない。
- validation、dirty判定、エラー表示は既存の作成・編集と共通である。
- フォーム表示後にloaderの再検証が起きても、ユーザー入力を上書きしてはならない。

## Pass conditions

- **S1 Submit path:** 既存の新規作成APIとフォーム値変換を通し、複製専用API、payload型、submit分岐を増やさない。
- **S2 State consistency:** 永続的な`clone` modeをフォーム内部へ増やさず、複製差分を初期値生成と表示情報へ閉じるか、同等に重複状態を避ける。
- **S3 Initial values:** 引継ぎ対象だけをcopyし、server管理値とtokenを除外し、name suffixを一度だけ付ける変換を示す。
- **S4 Input protection:** loader完了後に初期化し、再検証でdirtyな入力を再初期化しない方法を具体化する。
- **S5 Verification:** 引継ぎ/除外項目、suffix、create payload、token非表示、再検証時の入力保持、既存create/edit validation回帰を確認する。

## Critical failure conditions

- `deployToken`、元の`id`、監査日時のいずれかを画面またはcreate payloadへ含める。
- 複製の送信にupdate APIを使う。
- loader再検証で編集済み入力を無条件に上書きする。

## Scoring

S1〜S5を各0〜2点で採点する。2点はdataの由来と行き先、stateの寿命、既存契約との接続が具体的、1点は一部が曖昧、0点は要件違反・重複・重要な欠落がある。8〜10点かつ全基準1点以上をPass、6〜7点または0点を含む8点以上をBorderline、5点以下をFailとする。critical failureを優先し、特定のcomponent分割や関数名は固定しない。


## Judge instructions

Score each candidate independently using only its final answer and this fixture.
Do not guess its generation condition. The workspace intentionally contained no source files and
was read-only, so judge the proposed data flow, types, boundaries, failure behavior, and observable
test plan. Do not fail a candidate merely because it could not edit or execute code.

Score S1 through S5 from 0 to 2 exactly as defined by the fixture. `total` must equal their sum.
If any critical failure condition is met, set `critical_failure` to true and `outcome` to
`critical_failure`. Otherwise use: pass = total 8-10 with every S at least 1; borderline = total
6-7, or total 8-10 with any S equal to 0; fail = total 0-5. Evidence must name concrete satisfied
and missing behavior. Do not reward headings, verbosity, or terminology by itself.


## Candidate A

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

## Candidate B

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

## Candidate C

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

## Candidate D

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

## Candidate E

最小構成は、複製専用の取得ルートだけを追加し、取得後は既存の新規作成フローへ合流させる形です。`ProjectForm`、validation、dirty判定、エラー処理、作成APIは分岐させません。

## 変更方針

### 1. 複製用の初期値変換を追加

許可した項目だけを `emptyProjectValues()` へ上書きします。除外項目を列挙する方式より、将来 `Project` に機密項目が増えても引き継がれないため安全です。

```ts
export function toCopiedProjectFormValues(
  source: Project,
): ProjectFormValues {
  return {
    ...emptyProjectValues(),
    name: source.name.endsWith(" (copy)")
      ? source.name
      : `${source.name} (copy)`,
    description: source.description,
    memberRoleIds: [...source.memberRoleIds],
    notificationRules: structuredClone(source.notificationRules),
    deploymentTargetId: source.deploymentTargetId,
  };
}
```

これにより以下は入りません。

- `id`
- `createdAt`
- `updatedAt`
- `deployToken`

`emptyProjectValues()` に `deployToken` 相当が存在する場合も、通常の新規作成と同じ空値にします。新規作成画面でトークン入力欄自体が表示される実装なら、既存の `mode === "create"` 条件で非表示にします。

### 2. route loaderを追加

例として `/projects/:projectId/copy` を追加します。

```tsx
export async function copyProjectLoader({ params }: LoaderArgs) {
  return getProject(params.projectId!);
}
```

このルートのローディング表示はフォームを含まないスケルトン等にします。loader完了前に空のフォームを仮表示して、後から `reset()` する実装にはしません。

### 3. loader完了時に一度だけ初期化

loaderの再検証で新しい `Project` オブジェクトが返っても、初期値オブジェクトを差し替えないことが重要です。

```tsx
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

`useState` の初期化関数はマウント時に一度だけ実行されます。

- 同じ複製元のloader再検証: 初期値を保持し、入力を上書きしない
- 別の複製元IDへ遷移: `key` が変わり、新しい初期値で再作成

`useEffect(() => form.reset(initialValues), [initialValues])` のような同期は追加しません。

### 4. 複製への導線を追加

編集画面または既存のプロジェクト操作メニューにリンクを追加します。

```tsx
<Link to={`/projects/${project.id}/copy`}>
  複製して新規作成
</Link>
```

`ProjectForm` は原則変更不要です。複製画面でも次をそのまま利用します。

```tsx
mode="create"
onSubmit={createProject}
```

## 状態とAPI入力

追加する状態は、複製元取得中のroute状態と、loader完了時に固定する `initialValues` だけです。フォーム内部に「複製モード」は持たせません。

送信先・入力は通常の新規作成と完全に共通です。

```ts
await createProject(formValues);
```

payloadへ複製元の `id` や `deployToken`、`createdAt`、`updatedAt`、`sourceProjectId` などは追加しません。`updateProject` や複製専用APIも呼びません。

## テスト

最低限、次を追加します。

1. 初期値変換の単体テスト

- 指定された4項目だけを引き継ぐ
- `name` に ` (copy)` が付く
- 既に末尾が ` (copy)` の場合は重複しない
- `deployToken`、ID、日時が含まれない
- 配列やルールを複製元と同じ参照で保持しない

2. routeのテスト

- loader完了前は `ProjectForm` が表示されない
- loader完了後に `mode="create"` で表示される
- 取得失敗時は既存のrouteエラー表示になる

3. フォーム統合テスト

- 初期表示直後はdirtyではない
- 入力後はdirtyになる
- loaderを再検証しても入力値とdirty状態が維持される
- validationとエラー表示が通常の新規作成と同じ

4. 送信テスト

- `createProject` が呼ばれる
- `updateProject` は呼ばれない
- payloadが通常の新規作成と同じ形である
- 複製元ID、日時、`deployToken` が送られない

なお、`referytale` の対応表は読み取り専用環境のためファイル保存できませんでしたが、設計では「取得中」「一度だけ確定した初期値」「ユーザーが編集するフォーム状態」を分離し、再検証による上書きを防いでいます。

## Candidate F

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
