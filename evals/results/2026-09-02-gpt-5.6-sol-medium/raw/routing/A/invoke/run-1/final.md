結論として、選択状態の正本は `selectedIds: string[]` のみにし、`selectedIdsForRequest` はAPI送信直前に導出します。全選択状態もstateに追加せず、選択可能なID一覧と `selectedIds` から計算します。

## 変更方針

### 変更する挙動

- 「全選択」で、現在選択可能な項目をすべて選択する。
- すべて選択済みなら、「全解除」として空配列に戻す。
- 一部選択時は全選択UIを中間状態にする。

### 維持する契約

- APIへ渡すフィールド名と型は変更しない。
- IDの区切り文字、並び順、空選択時の値は現行処理を維持する。
- 個別項目の選択・解除動作を維持する。
- disabled項目がある場合は、既存の選択可否を維持する。

### 状態と変換の正本

```tsx
const [selectedIds, setSelectedIds] = useState<string[]>([]);

const selectableIds = items
  .filter((item) => !item.disabled)
  .map((item) => item.id);

const allSelected =
  selectableIds.length > 0 &&
  selectableIds.every((id) => selectedIds.includes(id));

const partiallySelected =
  !allSelected &&
  selectableIds.some((id) => selectedIds.includes(id));

const handleToggleAll = () => {
  setSelectedIds((currentIds) => {
    const isAllSelected = selectableIds.every((id) =>
      currentIds.includes(id),
    );

    return isAllSelected ? [] : selectableIds;
  });
};

const handleSubmit = () => {
  apiClient.request({
    // 区切り文字や空配列時の表現は現行契約に合わせる
    selectedIds: selectedIds.join(","),
  });
};
```

`selectedIdsForRequest` をコンポーネント内でも参照する必要があるなら、stateではなく単なる導出値にします。

```tsx
const selectedIdsForRequest = selectedIds.join(",");
```

計算が軽いため、通常は `useMemo` も不要です。

注意点は次のとおりです。

- APIがIDの順序に意味を持つなら、`selectableIds` または従来の選択順のどちらを使うか現行仕様に合わせる。
- 全解除時に、選択可能項目だけ解除するのか、disabledを含む全IDを消すのかを既存仕様から確定する。
- 項目一覧が検索やページングで絞られる場合、「全選択」が表示中だけか、取得済み全件かを明確にする。
- 項目一覧更新時に消えたIDを自動除去する処理は、既存挙動でない限り今回追加しない。

## テスト観点

内部state名ではなく、利用者操作とAPI引数を検証します。

1. 個別選択

- 未選択の項目を選ぶと選択表示になる。
- 選択済み項目を解除すると未選択になる。
- 複数項目を選択できる。

2. 全選択

- 未選択状態から実行すると、選択可能な全項目が選択される。
- 一部選択状態から実行すると、残りも選択される。
- 全選択済みから実行すると解除される。
- 項目が0件でもエラーにならず、全選択扱いにならない。
- disabled項目がある場合、選択対象にならない。

3. 表示状態

- 0件選択では未チェック。
- 一部選択では `indeterminate`。
- 全件選択ではチェック済み。
- 個別解除後、全選択表示が中間状態へ戻る。

4. API契約

- 個別選択後、従来と同じ区切り文字・順序で送信される。
- 全選択後、対象IDが重複なく送信される。
- 全解除後、従来どおりの空値が送信される。
- 選択変更前の古い文字列が送られない。
- API payloadに新しい内部用フィールドを増やしていない。

5. 項目一覧の変化

- 再レンダー後も選択状態が不必要に初期化されない。
- フィルターやページングがある場合、その仕様どおりの範囲だけが全選択される。
- 同じIDが入力に重複し得るなら、送信値を重複させない責務をデータ取得側とUI側のどちらが持つか確認する。

対象コードが作業ディレクトリになかったため、区切り文字・空値・順序・全選択範囲は未確認です。また、`referytale` が要求する対応表は読み取り専用環境のため保存できませんでした。実装時には、現行API呼び出しと既存テストを正本としてこの4点を確定する必要があります。
