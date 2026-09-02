作業領域に実装ファイルやテスト環境が存在せず、読み取り専用だったため、ファイルへの反映とテスト実行はできませんでした。以下がそのまま適用できる最小実装です。

```tsx
export function useSelection() {
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

`selectedIdsForRequest` は `selectedIds` から導出できる重複状態なので削除しています。API送信時だけカンマ区切り文字列へ変換します。また、関数形式のstate更新により、同一レンダー中に複数回操作しても古い選択状態を参照しません。

「全選択」は、表示外ですでに選択されている項目を維持しつつ、表示中のIDを重複なく追加する仕様です。

追加すべきテスト例です。

```tsx
import { act, renderHook } from "@testing-library/react";
import { api } from "./api";
import { useSelection } from "./useSelection";

jest.mock("./api", () => ({
  api: {
    search: jest.fn(),
  },
}));

afterEach(() => {
  jest.clearAllMocks();
});

it("連続して項目を切り替えても選択状態がずれない", () => {
  const { result } = renderHook(() => useSelection());

  act(() => {
    result.current.toggle("a");
    result.current.toggle("b");
  });

  expect(result.current.selectedIds).toEqual(["a", "b"]);
});

it("表示外の選択を維持して表示中の項目をすべて選択する", () => {
  const { result } = renderHook(() => useSelection());

  act(() => {
    result.current.toggle("hidden");
    result.current.selectAllVisible(["a", "b", "a"]);
  });

  expect(result.current.selectedIds).toEqual(["hidden", "a", "b"]);
});

it("最新の選択状態をカンマ区切り文字列として送信する", () => {
  const { result } = renderHook(() => useSelection());

  act(() => {
    result.current.selectAllVisible(["a", "b"]);
  });

  act(() => {
    result.current.toggle("a");
  });

  act(() => {
    result.current.submit();
  });

  expect(result.current.selectedIds).toEqual(["b"]);
  expect(api.search).toHaveBeenCalledWith({ selectedIds: "b" });
});
```

これらは、新しい全選択経路、既存の個別切替経路、API形式という3つの観測可能な契約を直接検証します。
