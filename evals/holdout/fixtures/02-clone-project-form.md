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
