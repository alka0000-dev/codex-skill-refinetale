# Rule-retention decision

## Decision

評価開始時の`SKILL.md` SHA-256 `873001ea53f54e4e924b7578d71bd721b3e5cf6cce6736a41209ca077874c7bf`を維持し、直前に追加した次の2規則は削除しない。

1. 名前が挙がった変更契約、変更しない契約、除外条件、失敗経路を、検証と期待結果へ1対1で対応づける。
2. 追加の安全条件が必要な共有機構は、その条件を所有・検証できる最小境界からだけ利用させ、汎用APIを広げない。

## Evidence

1つ目の規則は、既知holdoutのJob histogramで不足していた検証経路へ直接対応する。規則追加後の回帰ではRefineTale 3runすべてが、成功、同期throw、async rejectionを個別に検証へ対応づけ、30/30点だった。

2つ目の規則は、既知holdoutのLimited POST retryで発生した、強い安全前提を持つretryを汎用POSTへ広げる失敗へ直接対応する。規則追加後、skill本文を読んだRefineTale 2runは狭い専用境界を選び、各10/10点だった。本文未読の1runだけが同じ安全境界違反を再発した。

今回の公開repository評価では、両規則を含むrevisionが18/18でcorrectness gateを通過し、baseline比で追加source LOCを56.9%減らし、匿名judge得点も87.5%から98.6%へ上げた。少なくとも大きめ機能で過剰実装を抑える主目的への明確な悪影響は観測されなかった。

## Scope of claim

今回の公開repository suiteは、2規則を一つずつ除いた統制ablationではない。したがって、各規則がLOC削減を引き起こしたとは主張しない。ただし、規則ごとに既知の異なる失敗モードと回帰証拠があり、現revisionに悪影響を示す証拠もないため、「不要」と判断して削除する条件は満たさない。

将来削除を再検討するなら、各規則を単独で除いた固定snapshotを用意し、該当する安全・検証fixtureと未知の機能実装課題を同じ条件で比較する。その際も、LOCだけでなくcorrectness gate、critical failure、契約網羅を優先する。
