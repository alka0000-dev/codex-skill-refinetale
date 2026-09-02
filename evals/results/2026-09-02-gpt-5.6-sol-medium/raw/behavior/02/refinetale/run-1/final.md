`selectedIds` を唯一の状態とし、API用文字列は送信時に導出します。これで選択状態の同期ずれを防げます。表示外の既存選択は維持する想定です。

```tsx
function useSelection() {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const toggle = (id: string) => {
    setSelectedIds((currentIds) =>
      currentIds.includes(id)
        ? currentIds.filter((value) => value !== id)
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

必要なテストは次の2点です。

```tsx
it("表示中の項目を重複なくすべて選択する", () => {
  const { result } = renderHook(() => useSelection());

  act(() => result.current.toggle("hidden"));
  act(() =>
    result.current.selectAllVisible(["visible-1", "visible-2", "visible-1"]),
  );

  expect(result.current.selectedIds).toEqual([
    "hidden",
    "visible-1",
    "visible-2",
  ]);
});

it("最新の選択状態をカンマ区切りで送信する", () => {
  const { result } = renderHook(() => useSelection());

  act(() =>
    result.current.selectAllVisible(["visible-1", "visible-2"]),
  );
  act(() => result.current.toggle("visible-1"));
  act(() => result.current.submit());

  expect(api.search).toHaveBeenCalledWith({
    selectedIds: "visible-2",
  });
});
```

ただし、作業ディレクトリには対象コード、`package.json`、既存テストがなく、さらに読み取り専用だったため、実ファイルへの適用とテスト実行はできませんでした。対象リポジトリが配置された書き込み可能な環境であれば、そのまま実装・検証できます。
