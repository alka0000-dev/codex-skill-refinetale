作業ツリーに実装コードがなかったため、以下は提示された契約を前提にした最小方針です。

## 変更方針

`selectedIds: string[]` だけを選択状態の正本として残します。`selectedIdsForRequest` は別stateではなく、API送信境界で導出します。

```tsx
const [selectedIds, setSelectedIds] = useState<string[]>([]);

const handleSubmit = () => {
  request({
    // 区切り文字、空配列時の値、並び順は既存契約をそのまま使う
    selectedIds: selectedIds.join(","),
  });
};
```

文字列を複数箇所で使う場合もstateにはせず、単なる導出値にします。

```tsx
const selectedIdsForRequest = selectedIds.join(",");
```

これにより、次を削除できます。

- `selectedIdsForRequest` のstate
- そのsetter
- `selectedIds`との同期処理・`useEffect`
- 個別選択と全選択の双方で配列と文字列を更新する重複経路

シリアライズ規則が単純な`join`ではない場合だけ、既存形式を保つ関数として切り出します。

```ts
const serializeSelectedIds = (selectedIds: string[]) =>
  /* 現在のAPI形式へ変換 */;
```

## 全選択

全選択対象のIDを画面のデータから導出し、追加のboolean stateは持ちません。

```tsx
const selectableIds = items
  .filter((item) => !item.disabled)
  .map((item) => item.id);

const selectedIdSet = new Set(selectedIds);

const isAllSelected =
  selectableIds.length > 0 &&
  selectableIds.every((id) => selectedIdSet.has(id));

const handleToggleAll = () => {
  setSelectedIds(isAllSelected ? [] : selectableIds);
};
```

個別選択も`selectedIds`だけを更新します。

```tsx
const handleToggle = (id: string) => {
  setSelectedIds((currentIds) =>
    currentIds.includes(id)
      ? currentIds.filter((currentId) => currentId !== id)
      : [...currentIds, id],
  );
};
```

フィルターやページングをまたいだ選択を維持する既存契約がある場合、全選択解除で単純に`[]`へせず、現在表示中のIDだけを追加・削除します。その仕様がなければ、上記の単純な実装が最小です。

## 変更契約

変更する挙動：

- 全選択で、選択可能な項目を一括選択・解除できる
- 全件選択済みかどうかが、実際のID集合から決まる

変更しない挙動：

- 個別項目の選択・解除
- APIのフィールド名と文字列形式
- 空選択時の送信値
- IDの送信順序
- 無効項目、フィルター、ページングに関する既存仕様

正本：

- 選択状態：`selectedIds`
- 全選択対象：表示データから導出した`selectableIds`
- 全選択判定：`selectedIds`と`selectableIds`から導出
- API文字列：リクエスト生成境界でのみ変換

## テスト観点

最低限、利用者から観測できる次の契約をテストします。

1. 未選択から個別選択すると、その項目だけが選択表示になる。
2. 個別選択を解除すると、対象IDだけが除外される。
3. 未選択で全選択すると、選択可能な全IDが重複なく選択される。
4. 一部選択中に全選択すると、全IDが選択される。
5. 全件選択中に全選択を押すと、すべて解除される。
6. 全選択後に1件解除すると、全選択表示も解除される。
7. 項目が0件の場合、全選択済みとして扱わない。
8. 無効項目がある場合、全選択の対象と送信値に含まれない。
9. 個別選択と全選択のどちらから操作しても、APIには既存と完全に同じ文字列形式で送られる。
10. 空選択、1件、複数件について、区切り文字・順序・空値が既存契約どおりになる。

内部のstate数や変数名自体はテストせず、UIの選択結果とAPIリクエストを検証します。実コードがないため、テスト実行と具体的な変更箇所の特定は未実施です。
