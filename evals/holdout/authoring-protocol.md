# Holdout authoring protocol

このholdoutは、既存の回帰fixtureを見た後にRefineTaleを調整した影響を避けるため、次の順序で作成・固定した。

1. fresh-contextの独立agentへ、RefineTaleの公開レベルの目的だけを渡した。
2. `work/refinetale`、既存fixture、過去の評価結果、`SKILL.md`本文を読まないよう明示した。
3. agentは既存projectを編集せず、6件の課題、固有基準、critical failure、匿名採点rubricを一時領域へ作成した。
4. 原案の完成後に主担当が初めて全文を確認し、意味を変えない範囲でrunner用の見出しと表記へ整形した。
5. fixtureをhashで固定してから、baselineとRefineTale条件の実行を開始した。
6. fixture確定後は`SKILL.md`を変更しない。holdout結果を見た変更を行う場合、この結果は次revisionの回帰用にのみ使い、新しい独立holdoutを別途作る。

## Authoring record

- 原案作成日: 2026-09-02
- 原案SHA-256: `783f4790177cde20480385c20bd5636911249f337ed9b2ff60d5619c9b4fddfa`
- 固定したRefineTale SHA-256: `ecc498cdf0753453be02ae98fb0e5df9ab6154e49a0ed7f8ecfeb95c1d5c7a89`
- 原案作成者へ開示したもの: RefineTaleの高レベル目的と成果物要件
- 原案作成者へ開示しなかったもの: skill本文、既存fixture、既存run、失敗分析、改善箇所

## Scope

この独立性は、同じ会話履歴を持たないagentによる課題作成と、既存評価資料へのアクセス禁止に基づくプロセス上の独立性である。外部組織や独立した人間の評価者による第三者検証ではない。
