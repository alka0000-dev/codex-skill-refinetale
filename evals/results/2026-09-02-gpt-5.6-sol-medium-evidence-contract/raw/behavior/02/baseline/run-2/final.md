作業ディレクトリが空かつ読み取り専用だったため、ファイルへの直接反映とテスト実行はできませんでした。実装は次の形になります。

```tsx
function useSelection() {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const toggle = (id: string) => {
    setSelectedIds((currentSelectedIds) =>
      currentSelectedIds.includes(id)
        ? currentSelectedIds.filter((value) => value !== id)
        : [...currentSelectedIds, id],
    );
  };

  const selectAllVisible = (visibleIds: string[]) => {
    setSelectedIds((currentSelectedIds) => {
      const nextSelectedIds = new Set(currentSelectedIds);

      visibleIds.forEach((id) => nextSelectedIds.add(id));

      return nextSelectedIds.size === currentSelectedIds.length
        ? currentSelectedIds
        : [...nextSelectedIds];
    });
  };

  const submit = () =>
    api.search({
      selectedIds: selectedIds.join(","),
    });

  return { selectedIds, toggle, selectAllVisible, submit };
}
```

`selectedIdsForRequest` を削除し、`selectedIds` だけを状態の正本にしています。これにより画面表示とAPI送信値のずれを防げます。また、functional update により、同じイベント内で複数回更新しても選択が欠落しません。一括選択では非表示項目の既存選択を維持し、表示中IDの重複は除去します。

VitestとTesting Libraryを想定したテスト例です。

```tsx
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";
import { useSelection } from "./useSelection";

vi.mock("./api", () => ({
  api: {
    search: vi.fn(),
  },
}));

describe("useSelection", () => {
  beforeEach(() => {
    vi.mocked(api.search).mockReset();
  });

  it("複数の項目を同じ更新内で選択できる", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.toggle("item-1");
      result.current.toggle("item-2");
    });

    expect(result.current.selectedIds).toEqual(["item-1", "item-2"]);
  });

  it("表示中の項目を重複なくすべて選択し、既存の選択を維持する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.toggle("hidden-item");
    });

    act(() => {
      result.current.selectAllVisible([
        "visible-1",
        "visible-2",
        "visible-1",
      ]);
    });

    expect(result.current.selectedIds).toEqual([
      "hidden-item",
      "visible-1",
      "visible-2",
    ]);
  });

  it("最新の選択状態をカンマ区切り文字列として送信する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.selectAllVisible(["item-1", "item-2"]);
    });

    act(() => {
      result.current.toggle("item-1");
    });

    result.current.submit();

    expect(api.search).toHaveBeenCalledWith({
      selectedIds: "item-2",
    });
  });

  it("選択がない場合は空文字列を送信する", () => {
    const { result } = renderHook(() => useSelection());

    result.current.submit();

    expect(api.search).toHaveBeenCalledWith({
      selectedIds: "",
    });
  });
});
```
