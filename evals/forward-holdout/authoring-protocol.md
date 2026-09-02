# Forward holdout authoring protocol

このforward holdoutは、直前のholdout結果を見てRefineTaleを更新した後も、評価課題がその失敗分析へ適合しないよう、次の順序で作成・固定した。

1. プロジェクト外の一時Git workspaceで、会話履歴を持たないephemeral Codex sessionを開始した。
2. 作成者へ開示したのは、RefineTaleの公開レベルの目的、8件という件数、実装可能な小規模repository、S1〜S5 rubric、標準ランタイムだけを使うという成果物要件だけとした。
3. `work/refinetale`、`SKILL.md`、既存fixture、過去のrun、失敗分析、追加した2規則を読まないよう明示した。
4. 作成者が8件と検証を完成させ、sessionが終了するまで、主担当は原案を読まなかった。
5. 作成者は全fixtureについて、既存テストの初期成功と、新要件を含む総合テストの初期失敗を確認した。
6. 主担当は完成後に初めて全文を確認し、意味を変えずそのまま取り込んだ。
7. fixture treeをhashで固定してから、baselineとRefineTale条件の実行を開始する。
8. fixture確定後は評価完了まで`SKILL.md`を変更しない。この結果を見てskillを変更する場合、本holdoutは次revisionでは回帰評価としてのみ扱う。

## Authoring record

- 原案完成日時: `2026-09-02T05:23:37Z`
- 作成session: `gpt-5.6-sol`、推論強度`medium`、ephemeral、隔離した一時workspace
- 原案49ファイルのtree SHA-256: `696974e74f97e8548b6ef5cd0d49460235f2fb3fb4d5f7b98e7d1b9c3df03494`
- 固定fixture tree SHA-256: `a00cd15317c412c1991aa8f7ffd95a1f69c6b84950560cf8434aae767d00afa7`
- 固定したRefineTale SHA-256: `873001ea53f54e4e924b7578d71bd721b3e5cf6cce6736a41209ca077874c7bf`
- 作成者へ開示したもの: 高レベル目的、成果物形式、件数、実行環境の制約
- 作成者へ開示しなかったもの: skill本文、追加規則、既存fixture、既存run、採点結果、失敗分析

## Scope

この独立性は、プロジェクトや会話履歴へアクセスしない一時sessionによる課題作成と、fixture固定後のskill凍結に基づくプロセス上の独立性である。外部組織や独立した人間による第三者検証ではない。課題作成、回答生成、匿名採点には同じmodel familyを使用するため、model family固有の偏りも残る。

