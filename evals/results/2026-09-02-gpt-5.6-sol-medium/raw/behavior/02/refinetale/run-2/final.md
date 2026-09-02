作業ディレクトリにソースコードやテスト設定がなく、読み取り専用のため、実ファイルへの反映とテスト実行はできませんでした。適用すべき実装は次の形です。

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

重要なのは、`selectedIdsForRequest` を削除した点です。選択状態の正本を `selectedIds` 一つにし、API送信時だけカンマ区切りへ変換するため、二つのstateがずれません。また関数型更新により、同一イベント内で複数回更新しても古い選択状態を参照しません。

追加すべきテスト例です。

```tsx
import { act, renderHook } from "@testing-library/react";

describe("useSelection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("複数の個別選択を同一更新内でも保持する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.toggle("item-1");
      result.current.toggle("item-2");
    });

    expect(result.current.selectedIds).toEqual(["item-1", "item-2"]);
  });

  it("表示中の項目を重複なくすべて選択し、表示外の選択を維持する", () => {
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

  it("現在の選択状態をカンマ区切り文字列で送信する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.selectAllVisible(["item-1", "item-2"]);
    });

    act(() => {
      result.current.toggle("item-1");
    });

    act(() => {
      result.current.submit();
    });

    expect(api.search).toHaveBeenCalledWith({
      selectedIds: "item-2",
    });
  });
});
```

ここでは、フィルタ変更などで表示外になった既存選択は維持する仕様としています。
