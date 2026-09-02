# Reviewer notes

## Protocol

- 8課題×baseline/RefineTale×3runの48実装を生成した。
- 固定seedで実行順を混ぜ、各fixtureの6候補をA〜Fへ匿名化した。
- judgeには生成条件、対応するpair、skill traceを見せなかった。
- S1〜S5を各0〜2点で採点し、critical failureを先に判定した。
- 同じmodel・推論強度で、独立contextのblind judgeをfixtureごとに2回実行した。
- 3件のjudge不一致、一次judgeの全5件の低得点、全critical判定を手動監査した。

## Judge disagreement adjudication

完全一致は45/48候補（93.8%）、critical判定の一致は48/48だった。不一致は次の3件で、すべてFixture 03のS2 `2対1`だった。

- Candidate A / RefineTale run 1
- Candidate B / Baseline run 2
- Candidate E / Baseline run 3

いずれも形式・型検証と仮残高のOverdraft判定を、状態を変更しない同じ事前走査で行う。先行entryがOverdraftで後続entryも不正な場合、二次judgeは後続不正を優先した`ValueError`を要求したが、promptとrubricは競合時の例外優先順位を指定していない。入力順で最初に観測したOverdraftを送出しても、不正値による状態変更はなく、明示された原子性と入力順制約を満たす。そのため一次judgeのS2=2を維持した。

## Low-score audit

一次judgeで2点未満だった5件を確認し、すべて採点を維持した。

- Fixture 01 / Baseline run 1 / S2=1: 正のintにも`math.isfinite`を直接適用し、極端に大きい有効intで`OverflowError`となる。
- Fixture 01 / RefineTale run 1 / S2=1: 同じく極端に大きい有効intを受理できない。
- Fixture 04 / Baseline run 2 / S3=1: version 1と2が分岐内で個別に検証・生成され、共通生成経路へ合流しない。
- Fixture 04 / Baseline run 3 / S3=1: 共通文字列検証はあるが、version別分岐から個別に`Profile`を生成してreturnする。
- Fixture 04 / RefineTale run 3 / S4=1: JSON構文エラーを`InvalidProfile`へ変換するが、元例外を明示的なcauseとして残す。

固定検証は上記の境界を網羅しておらず、5件とも終了コード0だった。rubricはテスト成功だけでなく最終差分と実挙動を採点対象にしているため、該当criterionだけを1点とした判定は妥当と判断した。

## Manual corrections

手動補正は0件。一次judgeのJSONを正本とし、空の`review/manual-overrides.json`を集計へ適用した。

## Skill trace

RefineTale条件の本文読込traceは22/24だった。Fixture 07 run 2とFixture 08 run 1はtraceがなかったが、両runとも検証成功・10/10・Passだった。差し替えず主要集計へ含めた。

## Interpretation

固定検証とrubric Passは両条件とも24/24で、RefineTaleの改善は得点1点に限られた。実装評価を追加したことで応答レベル評価の不足は補えたが、本suiteには強い天井効果があり、優位性を主張できない。境界欠陥がテスト成功後にも残ったことから、今後は課題数を増やす前に、極端値、例外のcause、共通経路といった固定テストの観測範囲を事前に強化する余地がある。
