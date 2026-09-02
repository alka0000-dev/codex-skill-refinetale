選択状態を `selectedIds` に一本化し、API送信時だけカンマ区切りへ変換します。表示中の一括選択は、表示外の既存選択を維持しつつ重複なく追加します。

```tsx
function useSelection() {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const toggle = (id: string) => {
    setSelectedIds((current) =>
      current.includes(id)
        ? current.filter((value) => value !== id)
        : [...current, id],
    );
  };

  const selectAll = (visibleIds: readonly string[]) => {
    setSelectedIds((current) => [
      ...new Set([...current, ...visibleIds]),
    ]);
  };

  const submit = () =>
    api.search({ selectedIds: selectedIds.join(",") });

  return { selectedIds, toggle, selectAll, submit };
}
```

VitestとReact Testing Libraryを想定した必要最小限のテストです。

```tsx
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";
import { useSelection } from "./useSelection";

vi.mock("./api", () => ({
  api: {
    search: vi.fn(),
  },
}));

describe("useSelection", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("連続した個別選択と解除を現在の選択状態へ反映する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.toggle("item-1");
      result.current.toggle("item-2");
    });

    expect(result.current.selectedIds).toEqual(["item-1", "item-2"]);

    act(() => {
      result.current.toggle("item-1");
    });

    expect(result.current.selectedIds).toEqual(["item-2"]);
  });

  it("表示中の項目を重複なく追加し、最新の選択をカンマ区切りで送信する", () => {
    const { result } = renderHook(() => useSelection());

    act(() => {
      result.current.toggle("selected-on-another-page");
    });

    act(() => {
      result.current.selectAll([
        "visible-1",
        "visible-2",
        "visible-1",
      ]);
    });

    expect(result.current.selectedIds).toEqual([
      "selected-on-another-page",
      "visible-1",
      "visible-2",
    ]);

    act(() => {
      result.current.submit();
    });

    expect(api.search).toHaveBeenCalledWith({
      selectedIds: "selected-on-another-page,visible-1,visible-2",
    });
  });
});
```

変更しない契約も維持されています。

- 個別の選択・解除が可能
- APIには引き続き文字列を送信
- 空選択時は空文字列を送信
- 表示外の選択は一括選択で失われない
- 関数型更新により、同一イベント内の連続更新も欠落しない

作業ディレクトリが空でテスト基盤も存在せず、さらに読み取り専用だったため、ファイル追加とテスト実行はできませんでした。上記2ケースの期待結果が直接的な検証条件です。
