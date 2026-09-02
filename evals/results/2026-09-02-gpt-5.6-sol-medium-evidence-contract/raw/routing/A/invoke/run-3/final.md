推奨方針は、`selectedIds` だけを state の正本にし、`selectedIdsForRequest` は API 呼び出し境界で導出することです。これにより同期用の `useEffect` や二重更新が不要になります。

### 変更契約

変更する挙動：

- 全選択・全解除を追加する。
- 一部選択時は全選択 UI を `indeterminate` にする。

変更しない挙動：

- 個別選択・解除。
- API が受け取る文字列の区切り、順序、空選択時の値。
- 選択可能／選択不可の既存ルール。
- 画面遷移などで選択を維持・破棄する既存タイミング。

### 実装方針

```tsx
const [selectedIds, setSelectedIds] = useState<string[]>([]);

const selectedIdSet = useMemo(
  () => new Set(selectedIds),
  [selectedIds],
);

const selectableIds = items
  .filter((item) => !item.disabled)
  .map((item) => item.id);

const allSelected =
  selectableIds.length > 0 &&
  selectableIds.every((id) => selectedIdSet.has(id));

const partiallySelected =
  !allSelected &&
  selectableIds.some((id) => selectedIdSet.has(id));

const handleSelectAll = (checked: boolean) => {
  const selectableIdSet = new Set(selectableIds);

  setSelectedIds((currentIds) =>
    checked
      ? [...new Set([...currentIds, ...selectableIds])]
      : currentIds.filter((id) => !selectableIdSet.has(id)),
  );
};

const handleSubmit = () => {
  api.request({
    // 現在の変換規則をそのまま移動する
    selectedIds: serializeSelectedIds(selectedIds),
  });
};
```

`selectedIdsForRequest` が描画中にも必要なら state ではなく導出値にします。

```tsx
const selectedIdsForRequest = useMemo(
  () => serializeSelectedIds(selectedIds),
  [selectedIds],
);
```

重要なのは、文字列化処理を新しく作り直さず、現在の区切り文字・並び順・空値を扱う既存処理をそのまま関数化または API 呼び出し箇所へ移すことです。

全選択の対象範囲も明文化が必要です。現在表示中の項目だけを対象にする場合、全解除で別ページなどの選択を消さない上記実装が適します。検索結果全体を意味する場合は、未取得ページを含められる API 契約が必要なので、単純なフロントエンド変更では扱えません。

### テスト観点

- 初期状態では選択なし。既存どおりの空文字列または既存の空値が送信される。
- 個別選択・解除後、正しい ID 配列と既存形式の文字列が送信される。
- 全選択で、選択可能な ID が一度ずつ追加される。
- 全解除で、対象範囲の ID だけが削除される。
- 一部選択時は `checked=false`、`indeterminate=true`。
- 全選択時は `checked=true`、`indeterminate=false`。
- 選択不可項目は全選択にも全解除にも含まれない。
- 既に選択済みの項目があっても重複 ID が発生しない。
- 項目一覧が更新されたとき、全選択表示が新しい一覧から再計算される。
- API 送信値の区切り、順序、空値が変更前と完全に一致する。
- 表示範囲だけを全解除する仕様なら、範囲外の選択が維持される。

実コードが作業領域に存在しなかったため、関数名や既存の文字列化仕様、テストフレームワークへの適合は未検証です。また `referytale` の対応表は読み取り専用環境のため保存できず、既存語だけを用いて整理しました。
