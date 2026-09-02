選択状態を `selectedIds` のみに集約し、API 送信時にだけカンマ区切りへ変換します。

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

必要最小限のテスト例です。

```tsx
import { act, renderHook } from "@testing-library/react";
import { api } from "./api";
import { useSelection } from "./useSelection";

jest.mock("./api", () => ({
  api: {
    search: jest.fn(),
  },
}));

describe("useSelection", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("連続した個別選択を失わない", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.toggle("1");
      result.current.toggle("2");
    });

    expect(result.current.selectedIds).toEqual(["1", "2"]);
  });

  it("既存の選択を保ちながら表示中の項目をすべて選択する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.toggle("hidden");
    });

    act(() => {
      result.current.selectAllVisible(["visible-1", "visible-2", "visible-1"]);
    });

    expect(result.current.selectedIds).toEqual([
      "hidden",
      "visible-1",
      "visible-2",
    ]);
  });

  it("最新の選択状態をカンマ区切りでAPIへ送信する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.selectAllVisible(["1", "2"]);
    });

    act(() => {
      result.current.toggle("1");
    });

    result.current.submit();

    expect(api.search).toHaveBeenCalledWith({
      selectedIds: "2",
    });
  });
});
```

`selectedIdsForRequest` をなくしたため、2つの state が非同期更新でずれる経路はありません。作業ディレクトリには対象ファイルやテスト環境がなく、読み取り専用だったため、実ファイルへの適用とテスト実行は未実施です。
