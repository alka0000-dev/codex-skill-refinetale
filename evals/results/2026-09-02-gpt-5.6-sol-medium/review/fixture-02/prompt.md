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

## Candidate B

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

## Candidate C

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

## Candidate D

`selectedIds` を唯一の状態とし、API用文字列は送信時に導出します。これで選択状態の同期ずれを防げます。表示外の既存選択は維持する想定です。

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

必要なテストは次の2点です。

```tsx
it("表示中の項目を重複なくすべて選択する", () => {
  const { result } = renderHook(() => useSelection());

  act(() => result.current.toggle("hidden"));
  act(() =>
    result.current.selectAllVisible(["visible-1", "visible-2", "visible-1"]),
  );

  expect(result.current.selectedIds).toEqual([
    "hidden",
    "visible-1",
    "visible-2",
  ]);
});

it("最新の選択状態をカンマ区切りで送信する", () => {
  const { result } = renderHook(() => useSelection());

  act(() =>
    result.current.selectAllVisible(["visible-1", "visible-2"]),
  );
  act(() => result.current.toggle("visible-1"));
  act(() => result.current.submit());

  expect(api.search).toHaveBeenCalledWith({
    selectedIds: "visible-2",
  });
});
```

ただし、作業ディレクトリには対象コード、`package.json`、既存テストがなく、さらに読み取り専用だったため、実ファイルへの適用とテスト実行はできませんでした。対象リポジトリが配置された書き込み可能な環境であれば、そのまま実装・検証できます。

## Candidate E

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

## Candidate F

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
