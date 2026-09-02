`selectedIds` を唯一の state とし、`selectedIdsForRequest` はAPI送信境界で導出するのが最小かつ一貫した方針です。全選択のために新しい選択状態は追加しません。

## 変更契約

変更する挙動:

- 全選択チェックボックスで、現在の選択対象を一括選択・解除できる。
- 一部だけ選択されている場合は `indeterminate` 表示になる。

変更しない挙動:

- 個別選択の操作。
- APIのフィールド名、区切り文字、空選択時の値、IDの順序。
- disabled項目や、フィルター・ページ外のIDの扱い。
- APIを呼ぶタイミング。

状態と変換の正本:

- 選択中のID集合: `selectedIds: Id[]`
- API用文字列: 既存の変換方法を使い、送信直前に `selectedIds` から生成
- 全選択・一部選択: `selectedIds` と選択可能なIDから計算

## 実装方針

```tsx
const [selectedIds, setSelectedIds] = useState<Id[]>([]);

const selectableIds = items
  .filter((item) => !item.disabled)
  .map((item) => item.id);

const selectedIdSet = new Set(selectedIds);

const selectedCount = selectableIds.filter((id) =>
  selectedIdSet.has(id)
).length;

const isAllSelected =
  selectableIds.length > 0 &&
  selectedCount === selectableIds.length;

const isIndeterminate =
  selectedCount > 0 &&
  selectedCount < selectableIds.length;
```

全選択操作は関数形式の更新にします。これにより連続操作でも古いstateを参照しません。

```tsx
const handleSelectAllChange = (checked: boolean) => {
  setSelectedIds((currentIds) => {
    const nextIds = new Set(currentIds);

    for (const id of selectableIds) {
      if (checked) {
        nextIds.add(id);
      } else {
        nextIds.delete(id);
      }
    }

    return [...nextIds];
  });
};
```

この形なら、フィルターやページングで画面外の選択が存在しても保持できます。「全選択」が常に全データを意味するUIなら、選択時に `selectableIds`、解除時に `[]` を設定するだけでも構いません。ここは既存UIの選択範囲に合わせます。

API送信時は、現在使っている変換をそのまま移します。

```tsx
const handleSubmit = () => {
  const selectedIdsForRequest = selectedIds.join(","); // 既存形式を維持

  return apiClient.request({
    selectedIds: selectedIdsForRequest,
  });
};
```

レンダー中にも文字列が必要なら `useMemo` で導出できますが、stateにはしません。

```tsx
const selectedIdsForRequest = useMemo(
  () => selectedIds.join(","),
  [selectedIds]
);
```

`useEffect` で二つのstateを同期する方法は、更新順序や一時的不整合が増えるため避けます。例外は、送信時点の値を後から変更されない「送信スナップショット」として保持する要件がある場合だけです。

## テスト観点

コンポーネントテストでは内部state名ではなく、画面とAPI payloadを検証します。

- 初期状態

  - 個別項目が未選択。
  - 全選択が未チェック。
  - `indeterminate` ではない。
  - 選択可能項目が0件なら全選択をチェック扱いにしない。

- 個別選択

  - 1件選ぶと、その項目だけが選択される。
  - 複数件中の一部選択で全選択が `indeterminate` になる。
  - 最後の未選択項目を選ぶと全選択がチェック状態になる。

- 全選択

  - 全選択をオンにすると、選択可能な全項目が選択される。
  - 全選択をオフにすると、対象範囲の全項目が解除される。
  - disabled項目を全選択へ含めない。
  - 全選択後に1件解除すると `indeterminate` になる。

- 選択範囲

  - フィルターやページングがある場合、画面外の既存選択を意図せず消さない。
  - 選択肢一覧が再取得されたときの扱いは既存仕様を維持する。今回の変更に便乗して無効IDを自動削除しない。

- API契約

  - 個別選択時の送信文字列が変更前と完全に同じ。
  - 全選択時も既存の区切り文字とID順になる。
  - 空選択時の値が既存どおりになる（`""`、未指定、`null`など）。
  - API呼び出し回数や送信タイミングが変わらない。

- 更新の安全性

  - 全選択と個別選択を連続操作しても選択が欠落しない。
  - IDが重複して送信されない。

なお、実装コードが作業ディレクトリに存在しなかったため、今回は具体的な差分作成やテスト実行は行っていません。また、読み取り専用環境のため `.agent/CONTINUITY.md` と `referytale` の対応表も作成できませんでした。
