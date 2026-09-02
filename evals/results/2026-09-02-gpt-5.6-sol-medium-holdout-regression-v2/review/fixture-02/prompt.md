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

最小構成では、`ProjectForm` に複製モードを追加せず、複製用routeで「新規作成用の初期値」を一度だけ生成します。フォーム上は最後まで通常の `mode="create"` として扱います。

### 変更箇所

- `ProjectForm.tsx`
  - 原則変更なし。
  - `useProjectForm` が後から渡された `initialValues` で自動リセットする実装なら、その挙動は止める必要があります。
- `project-routes.tsx`
  - 複製用routeとloaderを追加。
  - 編集画面に「複製して新規作成」へのリンクを追加。
- 初期値変換関数
  - `toDuplicatedProjectFormValues(project)` を追加。
- API
  - 変更なし。既存の `createProject` を使用。
- route設定
  - 例: `/projects/:projectId/duplicate`

### 引継ぎ対応

`emptyProjectValues()`を土台にすることで、新規作成に不要な値を混入させません。

| 複製元の値 | 新規フォーム初期値 |
|---|---|
| `name` | 末尾に ` (copy)`を1つだけ付与 |
| `description` | 引き継ぐ |
| `memberRoleIds` | 引き継ぐ |
| `notificationRules` | 引き継ぐ |
| `deploymentTargetId` | 引き継ぐ |
| `deployToken` | 通常の新規作成と同じ空値 |
| `id`, `createdAt`, `updatedAt` | フォーム値に含めない |

```ts
function appendCopySuffixOnce(name: string): string {
  return `${name.replace(/(?: \(copy\))+$/, "")} (copy)`;
}

function toDuplicatedProjectFormValues(
  project: Project,
): ProjectFormValues {
  return {
    ...emptyProjectValues(),
    name: appendCopySuffixOnce(project.name),
    description: project.description,
    memberRoleIds: [...project.memberRoleIds],
    notificationRules: structuredClone(project.notificationRules),
    deploymentTargetId: project.deploymentTargetId,
    // deployTokenは複製元から設定しない
  };
}
```

配列とルールはコピーし、フォーム編集によってloaderのデータを直接変更しないようにします。`structuredClone`が利用できない環境なら、`NotificationRule`の構造に合わせた明示的なコピーにします。

### loaderと初期化タイミング

複製元の取得はコンポーネント内の`useEffect`ではなく、route loaderで完了させます。loader待機中はrouter側のpending UIだけを表示し、`ProjectForm`はmountしません。

```tsx
export async function duplicateProjectLoader({
  params,
}: LoaderFunctionArgs) {
  const project = await getProject(params.projectId!);
  return { project };
}

export function DuplicateProjectRoute() {
  const { project } =
    useLoaderData<typeof duplicateProjectLoader>();

  return (
    <DuplicateProjectForm
      key={project.id}
      project={project}
    />
  );
}

function DuplicateProjectForm({
  project,
}: {
  project: Project;
}) {
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

`useState`の遅延初期化により、初期値を作るのはフォーム表示時の一度だけです。同じ複製元についてloaderが再検証され、`project`のオブジェクトが更新されても、ユーザー入力とdirty状態は上書きされません。

`key={project.id}`は、別の複製元へroute遷移した場合だけ新しいフォームとして初期化するために使います。

編集画面には通常のリンクを追加します。

```tsx
export function EditProjectRoute({ project }: { project: Project }) {
  return (
    <>
      <Link to={`/projects/${project.id}/duplicate`}>
        複製して新規作成
      </Link>

      <ProjectForm
        mode="edit"
        initialValues={toProjectFormValues(project)}
        onSubmit={updateProject}
      />
    </>
  );
}
```

### 状態とAPI入力

追加する状態は、複製用route内の固定された`initialValues`だけです。複製元そのものを`ProjectForm`の状態へ持ち込む必要はありません。

送信時は既存の新規作成とまったく同じです。

```ts
createProject(values);
```

`sourceProjectId`、`id`、日時、元の`deployToken`などをpayloadへ追加しません。通常の新規作成が送信前にpayloadを変換している場合も、その既存変換をそのまま通します。

### テスト

最低限、次を確認します。

1. 初期値変換の単体テスト

   - 指定された4項目を引き継ぐ。
   - `deployToken`は通常の新規作成と同じ空値。
   - IDと日時を含まない。
   - `foo`は`foo (copy)`になる。
   - `foo (copy)`や`foo (copy) (copy)`は`foo (copy)`になる。
   - 配列やルールが複製元と同じ参照ではない。

2. routeのテスト

   - loader完了前は複製フォームが表示されない。
   - loader完了後に`mode="create"`で表示される。
   - loader失敗時は既存のrouteエラー表示になる。

3. 再検証のテスト

   - フォーム表示後に名前や説明を編集する。
   - loaderを再検証する。
   - 編集内容、dirty状態、validationエラーが維持される。

4. 送信のテスト

   - `createProject`が呼ばれる。
   - `updateProject`は呼ばれない。
   - payload形式が通常の新規作成と同じ。
   - 複製元の`deployToken`やメタデータが送られない。

これにより、validation・dirty判定・エラー表示は既存の`ProjectForm`／`useProjectForm`をそのまま共用できます。

## Candidate B

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

## Candidate C

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

## Candidate D

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

## Candidate E

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

## Candidate F

最小構成は、`ProjectForm` に複製モードを追加せず、「複製用の新規作成ルート」で初期値だけを組み立てる形です。フォーム、validation、dirty判定、送信処理は通常の新規作成をそのまま利用します。

## 変更箇所

### 1. 複製用の初期値変換

`emptyProjectValues()` を基準に、引き継ぎを許可した値だけを上書きします。これにより、将来 `Project` に項目が追加されても意図せず複製されません。

```tsx
const COPY_SUFFIX = " (copy)";

function toCopiedProjectFormValues(project: Project): ProjectFormValues {
  const empty = emptyProjectValues();

  return {
    ...empty,
    name: project.name.endsWith(COPY_SUFFIX)
      ? project.name
      : `${project.name}${COPY_SUFFIX}`,
    description: project.description,
    memberRoleIds: [...project.memberRoleIds],
    notificationRules: cloneNotificationRules(project.notificationRules),
    deploymentTargetId: project.deploymentTargetId,
  };
}
```

`cloneNotificationRules` は、フォーム操作で元のloaderデータを変更しないよう、`NotificationRule` の構造に応じて配列要素やネスト値をコピーします。

この組み立て方なら以下は引き継がれません。

- `id`
- `createdAt`
- `updatedAt`
- `deployToken`

`deployToken` の初期値は `emptyProjectValues()` と同じ未設定値になります。複製元の値をフォームへ渡してはいけません。

### 2. 複製用routeとloader

```tsx
export async function copyProjectLoader({
  params,
}: LoaderFunctionArgs): Promise<Project> {
  return getProject(params.projectId!);
}

export function CopyProjectRoute() {
  const sourceProject = useLoaderData() as Project;

  return (
    <ProjectForm
      key={`copy:${sourceProject.id}`}
      mode="create"
      initialValues={toCopiedProjectFormValues(sourceProject)}
      onSubmit={createProject}
    />
  );
}
```

route設定では、loaderの初回完了前にはローディング表示だけを出し、`ProjectForm` をマウントしません。

```tsx
{
  path: "/projects/:projectId/copy",
  loader: copyProjectLoader,
  Component: CopyProjectRoute,
  pendingElement: <ProjectLoading />,
}
```

`pendingElement` などの名前は利用中のルーターに合わせます。

### 3. `ProjectForm` の初期値を初回だけ取り込む

loader再検証で新しい `initialValues` オブジェクトが渡されても、フォームを再初期化しないようにします。

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

これにより、同じ複製元IDの再検証ではユーザー入力が保持されます。一方、別の複製元へ遷移した場合は `key` が変わり、新しい初期値でフォームがマウントされます。

編集画面でも別プロジェクト間の遷移が同一コンポーネント上で起こり得るなら、同様にIDをkeyにします。

```tsx
export function EditProjectRoute({ project }: { project: Project }) {
  return (
    <ProjectForm
      key={`edit:${project.id}`}
      mode="edit"
      initialValues={toProjectFormValues(project)}
      onSubmit={updateProject}
    />
  );
}
```

## 状態とAPI入力

追加するフォーム状態はありません。

- `mode` は `"create"`
- 複製元IDはrouteパラメータとloaderだけで扱う
- 複製元の取得結果をフォーム状態と同期し続けない
- 複製時の初期値をdirty判定の基準値とするため、初期表示時はdirtyではない
- validationとエラー表示は既存の`useProjectForm`／`ProjectFields`をそのまま使う

送信は通常の新規作成と完全に同じです。

```tsx
onSubmit={createProject}
```

payloadには複製元IDを追加せず、通常の新規作成用serializerをそのまま使います。`updateProject`や複製専用APIは使用しません。

## 必要なテスト

最低限、以下を追加します。

1. 初期値変換の単体テスト

   - 指定された4項目だけを引き継ぐ
   - `id`、日時、`deployToken`を引き継がない
   - `name`に` (copy)`を付ける
   - すでに` (copy)`で終わる名前には再度付けない
   - 配列や通知ルールが複製元と同じ参照にならない

2. routeテスト

   - loader完了前にフォームが表示されない
   - loader完了後に`mode="create"`のフォームが表示される
   - 送信時に`createProject`が通常の新規作成payloadで呼ばれる
   - `updateProject`や複製専用APIが呼ばれない

3. 再検証テスト

```tsx
// 初期表示
// ユーザーがnameやdescriptionを変更
// 同じproject.idのloaderデータで再レンダー
// ユーザーが入力した値が残っていることを確認
```

4. 共通動作の回帰テスト

   - 複製フォームでも既存validationとエラー表示が動く
   - 初期表示はdirtyではない
   - 入力後はdirtyになる

なお、今回は読み取り専用環境のため、`referytale` が指定する対応表および欠落している `.agent/CONTINUITY.md` の作成は行っていません。
