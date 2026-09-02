ワークスペースが読み取り専用かつソースファイルが存在しないため、実際の編集・テスト実行はできませんでした。以下が適用すべき実装です。

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

  const selectAll = (visibleIds: string[]) => {
    setSelectedIds((currentIds) => [
      ...new Set([...currentIds, ...visibleIds]),
    ]);
  };

  const submit = () =>
    api.search({
      selectedIds: selectedIds.join(","),
    });

  return { selectedIds, toggle, selectAll, submit };
}
```

ポイントは次の2点です。

- API用文字列を別のstateにせず、`selectedIds`から送信時に生成する
- functional updateを使い、同一レンダー中に複数操作されても更新が欠落しないようにする

「表示中をすべて選択」は、別ページなどで既に選択したIDを維持しつつ、表示中IDを追加する仕様としています。

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
    vi.mocked(api.search).mockClear();
  });

  it("複数の項目を続けて選択できる", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.toggle("item-1");
      result.current.toggle("item-2");
    });

    expect(result.current.selectedIds).toEqual(["item-1", "item-2"]);
  });

  it("表示中の項目を既存の選択へ追加する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.toggle("other-page-item");
      result.current.selectAll([
        "visible-item-1",
        "visible-item-2",
        "visible-item-1",
      ]);
    });

    expect(result.current.selectedIds).toEqual([
      "other-page-item",
      "visible-item-1",
      "visible-item-2",
    ]);
  });

  it("全選択後も個別に選択解除できる", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.selectAll(["item-1", "item-2"]);
      result.current.toggle("item-1");
    });

    expect(result.current.selectedIds).toEqual(["item-2"]);
  });

  it("最新の選択状態をカンマ区切り文字列として送信する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.selectAll(["item-1", "item-2"]);
    });

    act(() => {
      result.current.submit();
    });

    expect(api.search).toHaveBeenCalledWith({
      selectedIds: "item-1,item-2",
    });
  });
});
```

読み取り専用制約により、`referytale` の対応表や必須の `.agent/CONTINUITY.md` も作成できていません。書き込み可能な実ファイル一式があれば、この差分を適用してビルド・リント・テストまで検証できます。
