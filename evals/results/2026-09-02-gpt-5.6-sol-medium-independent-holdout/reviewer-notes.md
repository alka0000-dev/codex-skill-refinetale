# Reviewer notes

## Protocol

- 6課題×baseline/RefineTale×3runの36回答を生成した。
- 固定seedで実行順を混ぜ、各fixtureの6回答をA〜Fへ匿名化した。
- judgeには生成条件、対応するpair、過去結果を見せなかった。
- S1〜S5を各0〜2点で採点し、critical failureを先に判定した。
- 低得点回答17件、critical条件、各領域の代表的満点回答、mapping、traceを手動監査した。

## Manual correction

1件だけ修正した。

- Fixture 02 / Candidate D / RefineTale run 1
- S3: `1 → 2`
- total: `8 → 9`
- outcome: Passのまま
- 理由: 入力はsource nameへsuffixを1回付けることを要求しており、sourceが既にsuffix付きの場合の冪等化は要求していない。候補Dは初期化時に1回だけ追加している。

一次judgeのJSONは変更せず、`review/manual-overrides.json`を集計時に適用した。

## Observed failures and weaknesses

- Baseline Fixture 03 run 3: Vendor B用に署名検証から永続化まで全工程を複製し、S1=0でBorderline。
- RefineTale Fixture 01: 3run中2runで汎用POST retry APIの誤用防止が弱く、1runで非空idempotency key保証が仮定だけだった。
- 両条件: 一部runで必須列欠落、token非表示、async rejectionなど固有testが不足した。
- Critical failure: 0件。

## Interpretation

RefineTaleは安全工程の複製を1件減らしたが、全体差は2/180点に留まった。Fixture 01ではbaselineより1点低く、Fixture 02・03・06で各1点高く、Fixture 04・05は同点だった。baselineの契約理解が既に強いため、今回のholdoutは大きな上積みを示していない。
