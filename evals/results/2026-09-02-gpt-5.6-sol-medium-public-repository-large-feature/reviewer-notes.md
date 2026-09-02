# Reviewer notes

## Protocol

- 6課題×baseline/RefineTale×3runの36実装を生成した。
- 固定seedで実行順を混ぜ、各課題の6候補をA〜Fへ匿名化した。
- judgeには生成条件、対応pair、skill trace、LOC集計を見せなかった。
- 完成度、既存設計との整合、scope discipline、単一経路を各0〜3点で採点した。
- 同じmodel・推論強度で、独立contextのblind judgeを課題ごとに2回実行した。
- 全18件のjudge不一致、一次judgeの全4件の低criterion、全critical判定を手動監査した。

## Judge disagreement adjudication

4 criterionの完全一致は18/36候補（50.0%）、critical判定の一致は36/36だった。不一致はすべて個別criterionの1点差で、主に次の解釈差だった。

- 既存`Input`を再利用しない小さなnative inputを`coherence=2`とするか3とするか。
- 共有navigationをUser Settingsまで広げた変更を軽微なscope逸脱とするか。
- 未要求のdropzone機能を`scope_discipline=1`とするか2とするか。
- wizardの追加demo、validation、callbackを軽微な余分とするか許容範囲とするか。
- ratingのcontrolled/uncontrolled、hover、form連携を小さな独自機構とするかticket内とするか。

各差はrubric境界の強度差であり、完成度2未満、critical failure、build結果、条件間の方向性を変えなかった。一次judgeを正本として維持し、手動補正は行わなかった。

## Low-score audit

一次judgeで2点未満だった4件を確認し、すべて採点を維持した。

- Date picker / Baseline run 1 / `coherence=1`, `scope_discipline=1`: 480 LOCの独自calendar、month計算、focus管理、controlled/uncontrolled、2種類のchange callback、Today/Clear、locale、week開始設定を追加した。ticketは日付選択componentの追加だけで、既存`Input`とnative date inputで満たせる。
- File dropzone / Baseline run 1 / `scope_discipline=1`: 277 LOCで、size/count制限、format、deduplication、list管理、clear-all、controlled/default APIまで追加した。
- File dropzone / Baseline run 2 / `scope_discipline=1`: 266 LOCのcomponentに加え、dashboardへ未要求のdemoを統合した。
- File dropzone / Baseline run 3 / `scope_discipline=1`: 262 LOCでhard-coded Card UI、validation、deduplication、status、削除、dashboard demoを追加した。

4件はいずれも中核機能とbuildは満たすためcorrectness gateを通した。未完成ではなく、動作する過剰実装としてscope/coherenceだけを減点した判定は妥当と判断した。

## Manual corrections

手動補正は0件。一次judgeのJSONを正本として集計した。critical failureは両judgeとも全36候補でfalseだった。

## Trace and contamination audit

正式runのtraceは次の通りだった。

- baseline: repository-local RefineTale 0/18、global RefineTale 0/18、`referytale` 0/18
- RefineTale: repository-local RefineTale 18/18、global RefineTale 0/18、`referytale` 0/18

先行して実行した36runは、RefineTale条件でrepository-local RefineTale 0/18、global `referytale` 18/18だった。対象を取り違えた汚染runのため採点・集計前に失格とし、公開結果へ混ぜていない。formal runでは明示的なrepository-local pathとglobal skill無効化を加えた。

## Interpretation

baselineは全runで動く実装を作れたが、日付選択、dropzone、wizardで一文ticketを超える独自UI、状態、API、demoを足す傾向があった。RefineTaleは全runのbuildと完成度を保ったまま、既存component、native input、導入済みprimitiveを優先し、実装量とscope逸脱を減らした。

一方、RefineTaleは平均実行時間とoutput tokenを増やした。速度や推論コストより、変更後のコード量と責務の抑制を優先するtrade-offである。
