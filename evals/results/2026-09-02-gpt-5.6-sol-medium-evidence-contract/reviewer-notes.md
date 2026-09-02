# Reviewer notes

## Review protocol

1. 各fixtureのbaseline 3runとRefineTale 3runを固定seedでシャッフルした。
2. 条件とrun番号を隠し、候補A〜Fとして一次採点した。
3. 共通rubric G1〜G7とfixture固有の合格条件を使用した。
4. 空の読み取り専用workspaceであることだけでは減点せず、具体案と必要な検証を提示したかで判定した。
5. 一次採点後に条件を復元し、生回答、fixture、trace、採点根拠を手動で照合した。

## Reviewer

- Primary blind judge: `gpt-5.6-sol`, reasoning effort `medium`
- Manual audit: Codex primary task
- Manual score corrections: 1

## Manual correction

- Fixture 02 candidate C（RefineTale run 2）: `G1`を0から1、`critical_failure`をtrueからfalseへ修正した。
- 理由: `selectAll`がtoggleと同じfunctional更新経路を使わないため、G2、G4、fixture固有条件の不合格は維持した。一方、入力は表示外選択の保持を契約として指定しておらず、選択状態の正本とAPI形式は維持されていたため、外部契約のcritical failureには該当しない。

## Notable failures

- Fixture 01 RefineTale run 2: 共通経路は正しいが、終了日側の無効日付を確認するテストが不足した。
- Fixture 02 RefineTale run 2: 一括選択が配列を直接置換し、toggleと同じfunctional state更新経路にならなかった。

## Observed improvements

- Fixture 03: RefineTale 3/3runが、email、sms、pushの送信先と監査イベント、各失敗段階の副作用抑止を具体化した。
- Fixture 04: RefineTale 3/3runが、認可、無効ID、not found、操作失敗、成功の検証を具体化した。
- Fixture 05: RefineTale 3/3runが、コード変更なしで止まり、現在の検証と見直し条件を示した。

## Interpretation

skill冒頭の「完了時に必ず残す証拠」は、初回に不安定だった検証計画と停止判断を同一fixture上で改善しました。ただし、この修正は初回fixtureの失敗を見て作成しているため、未知のケースへの一般化は独立holdoutで確認する必要があります。
