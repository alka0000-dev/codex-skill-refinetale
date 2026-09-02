選択状態を `selectedIds` のみに一本化し、API用のカンマ区切り文字列は送信時に生成します。これにより二重管理によるずれを防げます。

```tsx
import { useCallback, useState } from "react";

export function useSelection() {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const toggle = useCallback((id: string) => {
    setSelectedIds((currentIds) =>
      currentIds.includes(id)
        ? currentIds.filter((currentId) => currentId !== id)
        : [...currentIds, id],
    );
  }, []);

  const selectAllVisible = useCallback((visibleIds: readonly string[]) => {
    setSelectedIds((currentIds) => {
      const nextIds = [...new Set([...currentIds, ...visibleIds])];

      return nextIds.length === currentIds.length ? currentIds : nextIds;
    });
  }, []);

  const submit = useCallback(
    () => api.search({ selectedIds: selectedIds.join(",") }),
    [selectedIds],
  );

  return {
    selectedIds,
    toggle,
    selectAllVisible,
    submit,
  };
}
```

`selectAllVisible` は、画面外ですでに選択されている項目を維持しながら、表示中のIDを重複なく追加します。

VitestとReact Testing Libraryを使う場合のテスト例です。

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
    vi.clearAllMocks();
  });

  it("項目の選択と選択解除を切り替える", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.toggle("item-1");
    });

    expect(result.current.selectedIds).toEqual(["item-1"]);

    act(() => {
      result.current.toggle("item-1");
    });

    expect(result.current.selectedIds).toEqual([]);
  });

  it("既存の選択を維持して表示中の項目をすべて選択する", () => {
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

  it("一括選択後の個別解除を反映したカンマ区切り文字列を送信する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.selectAllVisible(["item-1", "item-2", "item-3"]);
    });

    act(() => {
      result.current.toggle("item-2");
    });

    act(() => {
      result.current.submit();
    });

    expect(api.search).toHaveBeenCalledWith({
      selectedIds: "item-1,item-3",
    });
  });
});
```

現在のワークスペースには実装ファイルやテスト設定がなく、かつ読み取り専用だったため、パッチ適用とテスト実行は行えていません。
