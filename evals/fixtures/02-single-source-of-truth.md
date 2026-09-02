# 02: Keep one source of truth

## Purpose

同じ意味を持つUI状態を二重管理せず、外部形式を送信境界で導出できるかを確認する。

## Input

次のReact hookに「表示中の項目をすべて選択する」機能を追加してください。APIには引き続きカンマ区切り文字列を送信します。選択状態がずれないようにし、必要なテストを追加してください。

```tsx
function useSelection() {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [selectedIdsForRequest, setSelectedIdsForRequest] = useState("");

  const toggle = (id: string) => {
    const next = selectedIds.includes(id)
      ? selectedIds.filter((value) => value !== id)
      : [...selectedIds, id];
    setSelectedIds(next);
    setSelectedIdsForRequest(next.join(","));
  };

  const submit = () => api.search({ selectedIds: selectedIdsForRequest });

  return { selectedIds, toggle, submit };
}
```

## Pass conditions

- 選択状態の正本を1つにする。
- API用のカンマ区切り文字列は送信境界で導出する。
- 同期用effectや第三のboolean状態を追加しない。
- 「表示中をすべて選択」と個別toggleが同じ状態更新経路を使う。
- テストは選択結果と送信値を確認し、内部の状態同期手順に固定しない。
