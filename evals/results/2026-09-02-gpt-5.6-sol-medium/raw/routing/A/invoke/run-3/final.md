方針は、`selectedIds: string[]` だけを選択状態の正本として残し、`selectedIdsForRequest` はAPI送信境界で既存形式へ変換することです。同期用の`useEffect`や2つ目のstateは不要になります。

### 変更契約

変更する挙動：

- 全選択操作で、対象となる選択肢のIDを一括選択できる
- すべて選択済みなら、同じ操作で一括解除できる
- 一部選択時は全選択UIを`indeterminate`表示にする

変更しない挙動：

- 個別選択・解除
- APIへ送るフィールド名と文字列形式
- IDの並び順、区切り文字、空選択時の値
- 選択不可項目の扱い

### 状態と変換

```tsx
const [selectedIds, setSelectedIds] = useState<string[]>([]);

const selectableIds = options
  .filter((option) => !option.disabled)
  .map((option) => option.id);

const isAllSelected =
  selectableIds.length > 0 &&
  selectableIds.every((id) => selectedIds.includes(id));

const isIndeterminate =
  !isAllSelected &&
  selectableIds.some((id) => selectedIds.includes(id));

const handleToggleAll = () => {
  setSelectedIds((currentIds) => {
    const selectedIdSet = new Set(currentIds);
    const allSelected = selectableIds.every((id) =>
      selectedIdSet.has(id),
    );

    if (allSelected) {
      const selectableIdSet = new Set(selectableIds);
      return currentIds.filter((id) => !selectableIdSet.has(id));
    }

    return [
      ...currentIds,
      ...selectableIds.filter((id) => !selectedIdSet.has(id)),
    ];
  });
};
```

送信時だけ既存契約へ変換します。

```tsx
const handleSubmit = () => {
  apiClient.request({
    selectedIds: serializeSelectedIds(selectedIds),
  });
};
```

`serializeSelectedIds`は、現在の`selectedIdsForRequest`生成処理をそのまま移す想定です。単純な契約なら`selectedIds.join(existingDelimiter)`で十分です。描画ごとの変換コストが問題にならない限り、`useMemo`も必要ありません。

重要なのは、「全選択」の対象範囲を既存UIの意味に合わせることです。フィルター結果だけ、現在ページだけ、全ページの全件、のいずれかを先に確定させます。ここを曖昧にしたまま実装すると、UIと送信内容が食い違います。

### テスト観点

UIの観測可能な挙動：

- 0件から全選択すると、選択可能な全IDが選択される
- 一部選択から全選択すると、未選択IDだけが追加され、重複しない
- 全選択済みで操作すると、対象IDがすべて解除される
- 個別解除後は全選択が解除状態かつ`indeterminate`になる
- 選択肢が0件なら、全選択操作は無効またはno-opになる
- disabled項目は全選択・全解除の対象にならない
- 対象外の既存選択がある場合、それを誤って削除しない
- 選択肢の更新後も、全選択状態が現在の対象集合から導出される

API契約：

- 個別選択時の送信文字列が変更前と完全に同じ
- 全選択時に全IDが既存の順序・区切り文字で送られる
- 空選択時の値が既存契約どおりになる
- 送信直前の最新選択が使われ、同期漏れが起きない

テストでは`selectedIdsForRequest`という内部変数の有無を確認せず、ユーザー操作後のチェック状態とAPIへ渡されたpayloadを確認します。

対象コードが作業ディレクトリになかったため、実装・ビルド・既存テストとの照合は未実施です。
