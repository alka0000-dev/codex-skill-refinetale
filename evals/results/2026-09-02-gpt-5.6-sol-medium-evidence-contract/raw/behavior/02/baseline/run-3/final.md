実装先のファイルが存在せず、ワークスペースも読み取り専用だったため、変更の適用・テスト実行はできませんでした。適用すべき差分は次のとおりです。

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
    api.search({
      selectedIds: selectedIds.join(","),
    });

  return { selectedIds, toggle, selectAllVisible, submit };
}
```

ポイントは、`selectedIdsForRequest` をstateとして保持しないことです。送信値を`selectedIds`から都度生成するため、個別選択と一括選択で同期がずれません。関数形式のstate更新により、同一イベント中に更新が連続しても失われません。

JestとTesting Libraryを使う場合のテスト例です。

```tsx
import { act, renderHook } from "@testing-library/react";

describe("useSelection", () => {
  beforeEach(() => {
    jest.spyOn(api, "search").mockReset();
  });

  it("表示中の項目をすべて選択し、表示外の選択を維持する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.toggle("hidden");
      result.current.selectAllVisible(["visible-1", "visible-2"]);
    });

    expect(result.current.selectedIds).toEqual([
      "hidden",
      "visible-1",
      "visible-2",
    ]);
  });

  it("重複するIDを追加しない", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.selectAllVisible(["1", "1", "2"]);
      result.current.selectAllVisible(["1", "2"]);
    });

    expect(result.current.selectedIds).toEqual(["1", "2"]);
  });

  it("最新の選択状態をカンマ区切り文字列で送信する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.selectAllVisible(["1", "2", "3"]);
      result.current.toggle("2");
    });

    act(() => {
      result.current.submit();
    });

    expect(api.search).toHaveBeenCalledWith({
      selectedIds: "1,3",
    });
  });
});
```

`referytale`の事前対応表と`.agent/CONTINUITY.md`も、読み取り専用のため作成できませんでした。書き込み可能な実装ファイル一式が提供されれば、この差分を適用してテストまで検証できます。
