You are grading six anonymized answers to one coding-skill evaluation. Apply the rubric strictly and return only the requested structured result. Do not guess which condition produced an answer.

# 02: Keep one source of truth

## Purpose

同じ意味を持つUI状態を二重管理せず、外部形式を送信境界で導出できるかを確認する。

## Input

次のReact hookに「表示中の項目をすべて選択する」機能を追加してください。APIには引き続きカンマ区切り文字列を送信します。選択状態がずれないようにし、必要なテストを追加してください。

```tsx
function useSelection() {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [selectedIdsForRequest, setSelectedIdsForRequest] = useState("");

  const toggle = (id: string) => {
    const next = selectedIds.includes(id)
      ? selectedIds.filter((value) => value !== id)
      : [...selectedIds, id];
    setSelectedIds(next);
    setSelectedIdsForRequest(next.join(","));
  };

  const submit = () => api.search({ selectedIds: selectedIdsForRequest });

  return { selectedIds, toggle, submit };
}
```

## Pass conditions

- 選択状態の正本を1つにする。
- API用のカンマ区切り文字列は送信境界で導出する。
- 同期用effectや第三のboolean状態を追加しない。
- 「表示中をすべて選択」と個別toggleが同じ状態更新経路を使う。
- テストは選択結果と送信値を確認し、内部の状態同期手順に固定しない。


## Scoring rules

Score each item as `1` (satisfied), `0` (not satisfied), or `-1` (not applicable).

- G1 Contract fidelity: preserves requested external contracts, inputs, outputs, errors, and events.
- G2 Change contract: clearly handles what changes, what must not change, and allowed variation.
- G3 Canonical ownership: keeps one source of truth for the same state or decision.
- G4 Variation isolation: isolates only real differences and does not duplicate common processing.
- G5 No speculative implementation: adds no unrequested future extension, fallback, flag, or abstraction.
- G6 Safety preservation: does not weaken authorization, validation, audit, or failure behavior.
- G7 Verification and stop: identifies necessary verification and stops when no change is needed.

Use only evidence present in the candidate's final answer. Do not reward a promise to finish later.
The workspace intentionally lacked source files and was read-only. Do not fail a candidate merely
for reporting that limitation if it still provides the requested concrete solution and verification
plan. Missing implementation guidance or missing required test coverage can still fail the relevant
criterion. `overall_pass` requires every applicable G score and the fixture-specific conditions to
equal 1. G1 is always critical; G6 is critical when applicable.


## Candidate A

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

## Candidate B

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

## Candidate C

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

## Candidate D

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

## Candidate E

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

## Candidate F

作業ディレクトリにはReactソースやテスト設定がなく、さらに読み取り専用のため、実ファイルへの変更・テスト実行はできませんでした。実装方針は、API用文字列を別stateにせず、選択IDから導出して状態ずれを防ぐ形です。

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
      ...new Set([...currentIds, ...visibleIds]),
    ]);
  };

  const submit = () =>
    api.search({ selectedIds: selectedIds.join(",") });

  return { selectedIds, toggle, selectAllVisible, submit };
}
```

必要なテストケースは以下です。

- 個別項目を選択・選択解除できる
- 表示中のIDを一括選択できる
- 既に選択済みのIDが重複しない
- 表示範囲外の既存選択を維持する
- APIへ現在の選択IDをカンマ区切りで送る
- 一括選択後の内容がAPI送信値へ反映される

`selectedIdsForRequest` を削除して `selectedIds.join(",")` から都度生成するため、2つのstateが異なる値になる問題を構造的に防げます。適用と検証には、対象リポジトリをこの作業領域へ配置し、書き込み可能にする必要があります。
