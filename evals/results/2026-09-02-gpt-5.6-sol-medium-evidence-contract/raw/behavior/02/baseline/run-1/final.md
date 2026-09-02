作業ディレクトリにはReactソースやテスト設定がなく、さらに読み取り専用のため、実ファイルへの変更・テスト実行はできませんでした。実装方針は、API用文字列を別stateにせず、選択IDから導出して状態ずれを防ぐ形です。

```tsx
function useSelection() {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const toggle = (id: string) => {
    setSelectedIds((currentIds) =>
      currentIds.includes(id)
        ? currentIds.filter((currentId) => currentId !== id)
        : [...currentIds, id],
    );
  };

  const selectAllVisible = (visibleIds: string[]) => {
    setSelectedIds((currentIds) => [
      ...new Set([...currentIds, ...visibleIds]),
    ]);
  };

  const submit = () =>
    api.search({ selectedIds: selectedIds.join(",") });

  return { selectedIds, toggle, selectAllVisible, submit };
}
```

必要なテストケースは以下です。

- 個別項目を選択・選択解除できる
- 表示中のIDを一括選択できる
- 既に選択済みのIDが重複しない
- 表示範囲外の既存選択を維持する
- APIへ現在の選択IDをカンマ区切りで送る
- 一括選択後の内容がAPI送信値へ反映される

`selectedIdsForRequest` を削除して `selectedIds.join(",")` から都度生成するため、2つのstateが異なる値になる問題を構造的に防げます。適用と検証には、対象リポジトリをこの作業領域へ配置し、書き込み可能にする必要があります。
