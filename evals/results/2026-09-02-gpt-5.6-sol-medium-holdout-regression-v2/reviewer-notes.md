# Reviewer notes

## Protocol

- 6課題×baseline/RefineTale×3runの36回答を生成した。
- 固定seedで実行順を混ぜ、各fixtureの6回答をA〜Fへ匿名化した。
- judgeには生成条件、対応するpair、過去結果を見せなかった。
- S1〜S5を各0〜2点で採点し、critical failureを先に判定した。
- critical 2件、全低得点回答、代表的満点回答、mapping、traceを手動監査した。

## Manual corrections

Fixture 02の2候補だけを修正した。

- Candidate D / RefineTale run 1: S3 `1 → 2`、total `8 → 9`
- Candidate E / Baseline run 2: S3 `1 → 2`、total `8 → 9`
- outcome: いずれもPassのまま
- 理由: 1回の複製初期化でsuffixを1回追加する要件であり、元の名前がsuffix付きの場合の冪等化は要求されていない。

一次judgeのJSONは変更せず、`review/manual-overrides.json`を集計時に適用した。

## Observed failures and weaknesses

- Fixture 01のbaseline run 1とRefineTale run 1は、汎用retry APIを任意のPOSTへ広げ、冪等性を構造的に要求しなかったためcritical。RefineTale run 1はskill本文の読込traceなし。
- baseline Fixture 03 run 1・2は、署名検証から永続化までの安全工程をVendor Bへ複製しS1=0。
- baseline Fixture 05 run 2は、auditの順序を変え、NDJSON streamでbackpressureを維持しない余地があった。
- baseline Fixture 06の3runはasync rejectionの実行境界testが明示不足。
- RefineTale Fixture 02 run 1はtokenが画面に表示されないことの直接testが不足。

## Interpretation

RefineTaleは17/18 Pass・177/180点で、本文読込runは15/15 Pass・149/150点だった。追加規則は読込時には狙った安全境界と検証完全性へ反映されたが、未読runによるcritical failureが残るため、skill呼び出しの信頼性は別指標として維持する。

