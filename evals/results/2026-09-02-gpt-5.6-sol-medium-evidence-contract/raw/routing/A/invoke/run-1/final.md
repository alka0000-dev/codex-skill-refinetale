現状コードは作業ディレクトリに存在しなかったため、以下は提示された状態構成に基づく変更方針です。API文字列の区切り文字・空配列の表現・ID順序は、既存実装をそのまま正本として確認する必要があります。

## 変更方針

`selectedIds: string[]` だけを state として保持します。`selectedIdsForRequest` は同じID集合の通信形式なので、API呼び出し直前に導出します。

```tsx
const [selectedIds, setSelectedIds] = useState<string[]>([]);

const selectedIdsForRequest = serializeSelectedIds(selectedIds);

const handleSubmit = () => {
  request({
    selectedIds: selectedIdsForRequest,
  });
};
```

単純なカンマ区切りが既存契約なら、変換は以下で十分です。

```tsx
const selectedIdsForRequest = selectedIds.join(",");
```

`useEffect` で配列から文字列stateを同期する構成は避けます。更新が1レンダー遅れることや、更新経路の追加による同期漏れを防げるためです。変換が軽ければ `useMemo` も不要です。

全選択の状態も新しいboolean stateにはせず、選択可能なIDから導出します。

```tsx
const selectableIds = items
  .filter((item) => !item.disabled)
  .map((item) => item.id);

const selectedIdSet = new Set(selectedIds);

const isAllSelected =
  selectableIds.length > 0 &&
  selectableIds.every((id) => selectedIdSet.has(id));

const isIndeterminate =
  selectableIds.some((id) => selectedIdSet.has(id)) &&
  !isAllSelected;

const handleSelectAll = () => {
  setSelectedIds((currentIds) => {
    const currentIdSet = new Set(currentIds);
    const allSelected = selectableIds.every((id) =>
      currentIdSet.has(id),
    );

    return allSelected ? [] : selectableIds;
  });
};
```

変更契約は次のとおりです。

- 変更する挙動
  - 全選択操作で、選択可能な全IDを選択できる。
  - 全選択済みで同じ操作をすると解除できる。
  - 一部選択時は中間状態を表示する。

- 変更しない挙動
  - 個別選択・解除の操作。
  - APIへ渡すプロパティ名と文字列形式。
  - 空選択時の送信値。
  - IDの並び順や重複除去に関する既存仕様。

- 正本
  - 選択中のID集合: `selectedIds`
  - 全選択・中間表示: `selectedIds` と選択肢から導出
  - API送信用文字列: API境界で導出

## 先に確認すべき仕様

特に「全選択」の範囲を確定してください。

- 画面に表示されている項目だけか
- フィルター結果全体か
- ページネーションをまたぐ全件か
- disabled項目を除外するか

ページネーションをまたぐ全件を意味する場合、クライアントが全IDを保持していなければ既存の「ID文字列」契約だけでは表現できない可能性があります。その場合は、今回の内部整理とは分けてAPI契約を検討すべきです。

また、絞り込み前に選択した非表示IDを保持する既存仕様なら、全選択解除時に `[]` とせず、現在の対象IDだけを除去します。

## テスト観点

コンポーネントテスト:

1. 初期状態では個別項目も全選択も未選択になる。
2. 個別選択したIDだけが選択状態になる。
3. 未選択から全選択すると、選択可能な全IDが選択される。
4. 一部選択から全選択すると、残りのIDも選択される。
5. 全選択済みから解除すると、対象IDが解除される。
6. 一部選択時に全選択UIが中間状態になる。
7. disabled項目が全選択の対象に含まれない。
8. 選択可能項目が0件の場合、全選択済みとして扱わない。
9. 全選択後に個別項目を解除すると、中間状態へ戻る。
10. API送信時に、既存契約と完全に同じ文字列が渡される。
11. 空選択時にも、既存どおりの値（空文字列、未指定など）が渡される。
12. 項目一覧の更新・絞り込み時に、既存の選択保持／除去方針が維持される。

テストでは内部stateの個数や変数名を固定せず、操作後の表示とAPI引数だけを検証します。実コードがないため、テスト実行と既存のシリアライズ形式の確認は未実施です。
