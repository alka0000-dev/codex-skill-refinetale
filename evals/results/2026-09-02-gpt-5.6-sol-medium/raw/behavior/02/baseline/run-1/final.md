作業ディレクトリが空で読み取り専用だったため、実ファイルへの変更とテスト実行はできませんでした。適用すべき変更は以下です。

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
      ...currentIds,
      ...visibleIds.filter((id) => !currentIds.includes(id)),
    ]);
  };

  const submit = () =>
    api.search({
      selectedIds: selectedIds.join(","),
    });

  return { selectedIds, toggle, selectAllVisible, submit };
}
```

ポイントは、`selectedIdsForRequest` という重複状態を削除し、送信時に `selectedIds` からカンマ区切り文字列を生成することです。また、functional updateにより、同一イベント内で複数回操作しても選択状態が失われません。

VitestとTesting Libraryを使う場合のテスト例です。

```tsx
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  api: {
    search: vi.fn(),
  },
}));

import { api } from "./api";
import { useSelection } from "./useSelection";

describe("useSelection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("表示中の未選択項目をすべて選択する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.toggle("already-selected");
      result.current.selectAllVisible(["visible-1", "visible-2"]);
    });

    expect(result.current.selectedIds).toEqual([
      "already-selected",
      "visible-1",
      "visible-2",
    ]);
  });

  it("すでに選択されている表示中の項目を重複させない", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.selectAllVisible(["visible-1", "visible-2"]);
      result.current.selectAllVisible(["visible-1", "visible-2"]);
    });

    expect(result.current.selectedIds).toEqual(["visible-1", "visible-2"]);
  });

  it("同じ更新内で複数の項目を切り替えても選択状態を失わない", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.toggle("first");
      result.current.toggle("second");
    });

    expect(result.current.selectedIds).toEqual(["first", "second"]);
  });

  it("現在の選択状態をカンマ区切り文字列として送信する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.selectAllVisible(["visible-1", "visible-2"]);
    });

    act(() => {
      result.current.toggle("visible-1");
      result.current.submit();
    });

    expect(api.search).toHaveBeenCalledWith({
      selectedIds: "visible-2",
    });
  });
});
```

`referytale` が要求する事前対応表も、読み取り専用かつ空のリポジトリだったため作成できていません。書き込み可能な対象ファイル一式があれば、既存のAPI・テスト規約へ合わせて適用できます。
