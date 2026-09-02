# 06: Routing boundaries

## Purpose

RefineTaleを明示しない状態で、適用すべき依頼には呼び出され、短い定型説明には呼び出されないことを確認する。

## Input

### A: expected invocation

Reactの選択UIで、配列の `selectedIds` とAPI送信用文字列の `selectedIdsForRequest` を別々にstate管理しています。全選択機能を追加したいので、既存契約を維持しながら状態の重複を整理し、変更方針とテスト観点を出してください。

### B: expected non-invocation

初心者向けに、feature flagとは何かを3文で説明してください。コード変更や設計レビューは不要です。

## Pass conditions

- 入力Aでは、trace上でRefineTaleが呼び出される。
- 入力Aでは、契約、状態の正本、変換境界を先に整理してから変更方針を示す。
- 入力Bでは、trace上でRefineTaleが呼び出されない。
- 入力Bでは、依頼どおり3文の短い説明を返す。
- 入力AとBを別タスクで実行し、片方の文脈をもう片方へ持ち込まない。
