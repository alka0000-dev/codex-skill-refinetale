作業ディレクトリに実装ファイルやテスト環境がなく、さらに読み取り専用だったため、実ファイルへの適用とテスト実行はできませんでした。適用すべき最小実装は次のとおりです。

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
    setSelectedIds(visibleIds);
  };

  const submit = () =>
    api.search({ selectedIds: selectedIds.join(",") });

  return { selectedIds, toggle, selectAll, submit };
}
```

`selectedIdsForRequest` を削除し、選択状態の正本を `selectedIds` だけにしています。API固有のカンマ区切り変換は送信境界に限定されるため、個別選択と一括選択で送信用stateがずれません。

必要な最小テスト例です。

```tsx
import { act, renderHook } from "@testing-library/react";

jest.mock("./api", () => ({
  api: {
    search: jest.fn(),
  },
}));

describe("useSelection", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("個別に選択・解除でき、現在の選択を送信する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.toggle("1");
      result.current.toggle("2");
    });

    expect(result.current.selectedIds).toEqual(["1", "2"]);

    act(() => {
      result.current.toggle("1");
    });
    act(() => {
      result.current.submit();
    });

    expect(result.current.selectedIds).toEqual(["2"]);
    expect(api.search).toHaveBeenCalledWith({ selectedIds: "2" });
  });

  it("表示中の項目をすべて選択し、カンマ区切りで送信する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.selectAll(["1", "2", "3"]);
    });
    act(() => {
      result.current.submit();
    });

    expect(result.current.selectedIds).toEqual(["1", "2", "3"]);
    expect(api.search).toHaveBeenCalledWith({
      selectedIds: "1,2,3",
    });
  });

  it("一括選択後の個別解除を送信値へ反映する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.selectAll(["1", "2", "3"]);
    });
    act(() => {
      result.current.toggle("2");
    });
    act(() => {
      result.current.submit();
    });

    expect(result.current.selectedIds).toEqual(["1", "3"]);
    expect(api.search).toHaveBeenCalledWith({
      selectedIds: "1,3",
    });
  });
});
```

変更契約として、個別toggleとAPI形式は維持し、新たに表示中ID全体への置換を追加しています。一括選択後の個別解除まで検証することで、二重state由来の同期ずれがないことを直接保証します。
