You are grading six anonymized implementations from an independent forward holdout. Return only the requested structured result.

# User request

# 台帳への一括記帳

`workspace/` の `Ledger` に一括記帳APIを追加してください。

要件:

- `apply_batch(entries)` を追加する。各entryは `(account, delta)` の2要素tupleで、accountは空でないstr、deltaはboolではないint。
- 同一accountが複数回現れ得る。入力順に適用した途中を含め、残高が一度でも0未満になるbatchは `Overdraft` にする。
- entry形式が不正なら `ValueError` にする。
- 失敗したbatchでは、残高と監査ログを一切変更しない。
- 成功時は各entryを入力順に既存の `apply` 経路で反映し、その戻り値のlistを返す。
- `apply` と既存の公開状態の契約を維持する。

`workspace/` のファイルを修正し、workspaceをカレントディレクトリとして `python3 -m unittest discover -s tests` を実行してください。

# Fixture rubric

# Rubric

- S1 (0–2): entryを入力順に評価し、一時的な負残高も含めOverdraftを判定する。2=完全、1=一部、0=判定不能。
- S2 (0–2): 形式と型を事前検証し、不正batchで状態を変えない。2=完全、1=漏れ、0=部分更新。
- S3 (0–2): Overdraft時に残高・監査ログとも原子的に不変。2=完全、1=片方のみ、0=破壊的部分適用。
- S4 (0–2): 成功時は既存applyを唯一の更新境界として順序・戻り値・既存契約を保つ。2=一貫、1=軽微な重複、0=別状態経路。
- S5 (0–2): 自動テストが成功、同一口座順序、入力不正、rollback、回帰を検証して全成功。2=十分、1=部分的、0=失敗/未検証。

Pass=8〜10点かつ0点なし。Borderline=6〜7点、または8点以上でも0点あり。Fail=0〜5点。

Critical failure: 失敗batchが残高または監査ログを変更する、入力順の当座貸越を見逃す、既存applyを破壊する、検証コマンド失敗。採点はrepository最終差分、実挙動、設計境界、検証結果に基づき、識別子名や回答文には基づかない。

# Initial repository

### ledger.py

````text
class Overdraft(Exception):
    pass


class Ledger:
    def __init__(self, balances=None):
        self.balances = dict(balances or {})
        self.audit = []

    def apply(self, account, delta):
        balance = self.balances.get(account, 0) + delta
        if balance < 0:
            raise Overdraft(account)
        self.balances[account] = balance
        self.audit.append((account, delta, balance))
        return balance
````

### tests/test_existing.py

````text
import unittest
from ledger import Ledger, Overdraft


class ExistingTests(unittest.TestCase):
    def test_apply_and_reject_overdraft(self):
        ledger = Ledger({"cash": 5})
        self.assertEqual(ledger.apply("cash", -2), 3)
        with self.assertRaises(Overdraft):
            ledger.apply("cash", -4)
        self.assertEqual(ledger.balances["cash"], 3)
        self.assertEqual(ledger.audit, [("cash", -2, 3)])


if __name__ == "__main__":
    unittest.main()
````

### tests/test_requirements.py

````text
import unittest
from ledger import Ledger, Overdraft


class RequirementTests(unittest.TestCase):
    def test_applies_in_order_and_returns_balances(self):
        ledger = Ledger({"a": 5})
        self.assertEqual(ledger.apply_batch((("a", -2), ("a", 4))), [3, 7])
        self.assertEqual(ledger.audit, [("a", -2, 3), ("a", 4, 7)])

    def test_intermediate_overdraft_is_atomic(self):
        ledger = Ledger({"a": 2})
        before_balances = dict(ledger.balances)
        before_audit = list(ledger.audit)
        with self.assertRaises(Overdraft):
            ledger.apply_batch([("a", -3), ("a", 5)])
        self.assertEqual(ledger.balances, before_balances)
        self.assertEqual(ledger.audit, before_audit)

    def test_invalid_entry_is_atomic(self):
        invalid_batches = [
            [("a", 1), ("", 2)],
            [("a", 1), ("b", True)],
            [("a", 1), ["b", 2]],
            [("a", 1), ("b", 2, 3)],
        ]
        for entries in invalid_batches:
            ledger = Ledger({"a": 1})
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                ledger.apply_batch(entries)
            self.assertEqual(ledger.balances, {"a": 1})
            self.assertEqual(ledger.audit, [])


if __name__ == "__main__":
    unittest.main()
````

## Judge instructions

Score each candidate independently using the initial repository, final diff, verification output,
final answer, and fixture rubric. Do not guess its generation condition. Repository behavior and
the actual diff take precedence over claims in the final answer. A nonzero verification result is
evidence of an incomplete result, but apply the fixture's S1-S5 and critical conditions rather than
inventing new requirements.

Score S1 through S5 from 0 to 2 exactly as defined by the fixture. `total` must equal their sum.
If any critical failure condition is met, set `critical_failure` to true and `outcome` to
`critical_failure`. Otherwise use: pass = total 8-10 with every S at least 1; borderline = total
6-7, or total 8-10 with any S equal to 0; fail = total 0-5. Evidence must name concrete satisfied
and missing behavior from the diff or verification. Do not reward headings, verbosity, identifier
spelling, or terminology by itself.


## Candidate A

### Final answer

`Ledger.apply_batch(entries)` を実装しました。

- 全entryを事前検証し、不正形式は `ValueError`
- 複製残高で入力順にシミュレーションし、途中の負残高は `Overdraft`
- 検証失敗時は残高・監査ログとも無変更
- 成功時のみ既存の `apply` を入力順に呼び出し、戻り値のlistを返却
- 既存の `apply` 契約は変更なし

変更箇所:

- [ledger.py](<EVAL_WORKSPACE>/ledger.py:18)
- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:6)

検証結果:

- 正常系・同一account・入力順・戻り値・監査ログ: 成功
- 既存 `apply` 経路の利用: 成功
- 途中当座貸越時の原子性: 成功
- tuple形式、空／非文字列account、bool／非int deltaの拒否と原子性: 成功
- 既存 `apply` 契約: 成功
- `python3 -m unittest discover -s tests`: **5 tests passed**
- バイトコードコンパイル、`git diff --check`: 成功

### Final diff

````diff
diff --git a/ledger.py b/ledger.py
index cf73458..91fc053 100644
--- a/ledger.py
+++ b/ledger.py
@@ -14,3 +14,25 @@ class Ledger:
         self.balances[account] = balance
         self.audit.append((account, delta, balance))
         return balance
+
+    def apply_batch(self, entries):
+        validated_entries = []
+        balances = dict(self.balances)
+
+        for entry in entries:
+            if not isinstance(entry, tuple) or len(entry) != 2:
+                raise ValueError("each entry must be an (account, delta) tuple")
+
+            account, delta = entry
+            if not isinstance(account, str) or not account:
+                raise ValueError("account must be a non-empty string")
+            if isinstance(delta, bool) or not isinstance(delta, int):
+                raise ValueError("delta must be an integer")
+
+            balance = balances.get(account, 0) + delta
+            if balance < 0:
+                raise Overdraft(account)
+            balances[account] = balance
+            validated_entries.append(entry)
+
+        return [self.apply(account, delta) for account, delta in validated_entries]
diff --git a/tests/test_requirements.py b/tests/test_requirements.py
index 37180c5..d2abb2b 100644
--- a/tests/test_requirements.py
+++ b/tests/test_requirements.py
@@ -8,6 +8,20 @@ class RequirementTests(unittest.TestCase):
         self.assertEqual(ledger.apply_batch((("a", -2), ("a", 4))), [3, 7])
         self.assertEqual(ledger.audit, [("a", -2, 3), ("a", 4, 7)])
 
+    def test_success_uses_apply_for_each_entry(self):
+        class RecordingLedger(Ledger):
+            def __init__(self):
+                super().__init__()
+                self.applied = []
+
+            def apply(self, account, delta):
+                self.applied.append((account, delta))
+                return super().apply(account, delta)
+
+        ledger = RecordingLedger()
+        self.assertEqual(ledger.apply_batch((("a", 1), ("b", 2))), [1, 2])
+        self.assertEqual(ledger.applied, [("a", 1), ("b", 2)])
+
     def test_intermediate_overdraft_is_atomic(self):
         ledger = Ledger({"a": 2})
         before_balances = dict(ledger.balances)
@@ -20,7 +34,9 @@ class RequirementTests(unittest.TestCase):
     def test_invalid_entry_is_atomic(self):
         invalid_batches = [
             [("a", 1), ("", 2)],
+            [("a", 1), (1, 2)],
             [("a", 1), ("b", True)],
+            [("a", 1), ("b", 1.5)],
             [("a", 1), ["b", 2]],
             [("a", 1), ("b", 2, 3)],
         ]
````

### Verification

- Command: `python3 -m unittest discover -s tests`
- Exit: `0`
- Timed out: `False`

````text

....
----------------------------------------------------------------------
Ran 4 tests in 0.000s

OK
````

## Candidate B

### Final answer

`Ledger.apply_batch(entries)` を実装しました。

- 全entryを事前検証し、不正形式は `ValueError`
- 入力順で仮計算し、途中で負残高なら `Overdraft`
- 失敗時は残高・監査ログを完全復元
- 成功時は既存の `self.apply` 経路で反映し、戻り値をリスト化
- `bool` はdeltaとして拒否

変更ファイル: [ledger.py](<EVAL_WORKSPACE>/ledger.py)

検証結果:

```text
Ran 4 tests in 0.000s
OK
```

`python3 -m py_compile` と `git diff --check` も成功しています。

### Final diff

````diff
diff --git a/ledger.py b/ledger.py
index cf73458..be22b2b 100644
--- a/ledger.py
+++ b/ledger.py
@@ -14,3 +14,35 @@ class Ledger:
         self.balances[account] = balance
         self.audit.append((account, delta, balance))
         return balance
+
+    def apply_batch(self, entries):
+        try:
+            entries = list(entries)
+        except TypeError as error:
+            raise ValueError("entries must be iterable") from error
+
+        pending_balances = dict(self.balances)
+        for entry in entries:
+            if not isinstance(entry, tuple) or len(entry) != 2:
+                raise ValueError("each entry must be a two-element tuple")
+
+            account, delta = entry
+            if not isinstance(account, str) or not account:
+                raise ValueError("account must be a non-empty string")
+            if isinstance(delta, bool) or not isinstance(delta, int):
+                raise ValueError("delta must be an integer other than bool")
+
+            balance = pending_balances.get(account, 0) + delta
+            if balance < 0:
+                raise Overdraft(account)
+            pending_balances[account] = balance
+
+        original_balances = dict(self.balances)
+        original_audit = list(self.audit)
+        try:
+            return [self.apply(account, delta) for account, delta in entries]
+        except Exception:
+            self.balances.clear()
+            self.balances.update(original_balances)
+            self.audit[:] = original_audit
+            raise
````

### Verification

- Command: `python3 -m unittest discover -s tests`
- Exit: `0`
- Timed out: `False`

````text

....
----------------------------------------------------------------------
Ran 4 tests in 0.000s

OK
````

## Candidate C

### Final answer

`Ledger.apply_batch(entries)` を実装しました。[ledger.py](<EVAL_WORKSPACE>/ledger.py:17)

- 不正entry → `ValueError`、状態・監査ログ変更なし
- 途中残高が負 → `Overdraft`、状態・監査ログ変更なし
- 同一accountを含め入力順に仮残高を検証
- 成功時のみ既存 `apply` 経路で順番に反映
- 空batchは `[]`
- 既存 `apply` の契約を維持

検証結果:

- 指定コマンド: `python3 -m unittest discover -s tests`
- 4テストすべて成功
- 既存apply、成功順序、不正entryの原子性、途中当座貸越の原子性を確認
- 追加境界確認、`py_compile`、`git diff --check` も成功しました。

### Final diff

````diff
diff --git a/ledger.py b/ledger.py
index cf73458..b0ef08a 100644
--- a/ledger.py
+++ b/ledger.py
@@ -14,3 +14,30 @@ class Ledger:
         self.balances[account] = balance
         self.audit.append((account, delta, balance))
         return balance
+
+    def apply_batch(self, entries):
+        try:
+            entries = list(entries)
+        except TypeError as error:
+            raise ValueError("entries must be iterable") from error
+
+        for entry in entries:
+            if (
+                not isinstance(entry, tuple)
+                or len(entry) != 2
+                or not isinstance(entry[0], str)
+                or not entry[0]
+                or not isinstance(entry[1], int)
+                or isinstance(entry[1], bool)
+            ):
+                raise ValueError("entry must be a non-empty account and integer delta tuple")
+
+        balances = dict(self.balances)
+        for entry in entries:
+            account, delta = entry
+            balance = balances.get(account, 0) + delta
+            if balance < 0:
+                raise Overdraft(account)
+            balances[account] = balance
+
+        return [self.apply(account, delta) for account, delta in entries]
````

### Verification

- Command: `python3 -m unittest discover -s tests`
- Exit: `0`
- Timed out: `False`

````text

....
----------------------------------------------------------------------
Ran 4 tests in 0.000s

OK
````

## Candidate D

### Final answer

`Ledger.apply_batch(entries)` を [ledger.py](<EVAL_WORKSPACE>/ledger.py:17) に追加しました。

- 全entryを事前検証し、不正形式は `ValueError`
- 一時残高で入力順に試算し、途中で負になる場合は `Overdraft`
- 失敗時は残高・監査ログを変更しない
- 成功時のみ既存の `apply` を入力順に呼び、戻り値のリストを返す
- 空batch、生成器、非iterable入力も確認済み

検証結果:

```text
Ran 4 tests in 0.000s

OK
```

構文検査と `git diff --check` も成功しています。

### Final diff

````diff
diff --git a/ledger.py b/ledger.py
index cf73458..613e7c7 100644
--- a/ledger.py
+++ b/ledger.py
@@ -14,3 +14,29 @@ class Ledger:
         self.balances[account] = balance
         self.audit.append((account, delta, balance))
         return balance
+
+    def apply_batch(self, entries):
+        try:
+            entries = list(entries)
+        except TypeError as error:
+            raise ValueError("entries must be iterable") from error
+
+        for entry in entries:
+            if (
+                not isinstance(entry, tuple)
+                or len(entry) != 2
+                or not isinstance(entry[0], str)
+                or not entry[0]
+                or not isinstance(entry[1], int)
+                or isinstance(entry[1], bool)
+            ):
+                raise ValueError("each entry must be a valid (account, delta) tuple")
+
+        pending_balances = dict(self.balances)
+        for account, delta in entries:
+            balance = pending_balances.get(account, 0) + delta
+            if balance < 0:
+                raise Overdraft(account)
+            pending_balances[account] = balance
+
+        return [self.apply(account, delta) for account, delta in entries]
````

### Verification

- Command: `python3 -m unittest discover -s tests`
- Exit: `0`
- Timed out: `False`

````text

....
----------------------------------------------------------------------
Ran 4 tests in 0.000s

OK
````

## Candidate E

### Final answer

`Ledger.apply_batch(entries)` を追加しました。

- 全entryを事前検証し、不正形式は `ValueError`
- 入力順で途中残高を計算し、負残高は `Overdraft`
- 検証失敗時は残高・監査ログを変更しない
- 成功時は既存の `apply` 経由で反映し、戻り値をリスト化

変更: [ledger.py](<EVAL_WORKSPACE>/ledger.py:18)

検証結果:

```text
Ran 4 tests in 0.000s
OK
```

構文コンパイルと `git diff --check` も成功しています。

### Final diff

````diff
diff --git a/ledger.py b/ledger.py
index cf73458..318a28c 100644
--- a/ledger.py
+++ b/ledger.py
@@ -14,3 +14,26 @@ class Ledger:
         self.balances[account] = balance
         self.audit.append((account, delta, balance))
         return balance
+
+    def apply_batch(self, entries):
+        validated_entries = []
+        projected_balances = dict(self.balances)
+
+        for entry in entries:
+            if not isinstance(entry, tuple) or len(entry) != 2:
+                raise ValueError("each entry must be an (account, delta) tuple")
+
+            account, delta = entry
+            if not isinstance(account, str) or not account:
+                raise ValueError("account must be a non-empty string")
+            if isinstance(delta, bool) or not isinstance(delta, int):
+                raise ValueError("delta must be an integer")
+
+            balance = projected_balances.get(account, 0) + delta
+            if balance < 0:
+                raise Overdraft(account)
+
+            projected_balances[account] = balance
+            validated_entries.append(entry)
+
+        return [self.apply(account, delta) for account, delta in validated_entries]
````

### Verification

- Command: `python3 -m unittest discover -s tests`
- Exit: `0`
- Timed out: `False`

````text

....
----------------------------------------------------------------------
Ran 4 tests in 0.000s

OK
````

## Candidate F

### Final answer

実装完了しました。

- [ledger.py](<EVAL_WORKSPACE>/ledger.py:18)
  - 全entryを副作用前に検証
  - 入力順の途中残高を事前計算し、負数なら `Overdraft`
  - 成功時のみ既存 `apply` 経路で順次反映し、戻り値をリスト化
- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:6)
  - 成功時の順序・戻り値・監査ログ
  - 途中当座貸越の原子性
  - tuple、account、deltaの不正形式と原子性
  - 空batch
  - 既存 `apply` 経路の利用
- `.agent/CONTINUITY.md` も作成・更新済みです。

検証結果:

```text
python3 -m unittest discover -s tests
Ran 6 tests in 0.000s
OK
```

既存 `apply` の当座貸越時の残高・監査ログ契約も既存テストで維持されています。`git diff --check` も成功しました。

### Final diff

````diff
diff --git a/ledger.py b/ledger.py
index cf73458..bc89b62 100644
--- a/ledger.py
+++ b/ledger.py
@@ -14,3 +14,27 @@ class Ledger:
         self.balances[account] = balance
         self.audit.append((account, delta, balance))
         return balance
+
+    def apply_batch(self, entries):
+        batch = list(entries)
+
+        for entry in batch:
+            if not isinstance(entry, tuple) or len(entry) != 2:
+                raise ValueError("each entry must be an (account, delta) tuple")
+            account, delta = entry
+            if (
+                not isinstance(account, str)
+                or not account
+                or not isinstance(delta, int)
+                or isinstance(delta, bool)
+            ):
+                raise ValueError("invalid account or delta")
+
+        projected_balances = dict(self.balances)
+        for account, delta in batch:
+            balance = projected_balances.get(account, 0) + delta
+            if balance < 0:
+                raise Overdraft(account)
+            projected_balances[account] = balance
+
+        return [self.apply(account, delta) for account, delta in batch]
diff --git a/tests/test_requirements.py b/tests/test_requirements.py
index 37180c5..ad92448 100644
--- a/tests/test_requirements.py
+++ b/tests/test_requirements.py
@@ -20,7 +20,10 @@ class RequirementTests(unittest.TestCase):
     def test_invalid_entry_is_atomic(self):
         invalid_batches = [
             [("a", 1), ("", 2)],
+            [("a", -2), ("", 2)],
+            [("a", 1), (1, 2)],
             [("a", 1), ("b", True)],
+            [("a", 1), ("b", 2.0)],
             [("a", 1), ["b", 2]],
             [("a", 1), ("b", 2, 3)],
         ]
@@ -31,6 +34,26 @@ class RequirementTests(unittest.TestCase):
             self.assertEqual(ledger.balances, {"a": 1})
             self.assertEqual(ledger.audit, [])
 
+    def test_empty_batch_has_no_effect(self):
+        ledger = Ledger({"a": 1})
+        self.assertEqual(ledger.apply_batch([]), [])
+        self.assertEqual(ledger.balances, {"a": 1})
+        self.assertEqual(ledger.audit, [])
+
+    def test_success_uses_apply_path(self):
+        class RecordingLedger(Ledger):
+            def __init__(self, balances=None):
+                super().__init__(balances)
+                self.calls = []
+
+            def apply(self, account, delta):
+                self.calls.append((account, delta))
+                return super().apply(account, delta)
+
+        ledger = RecordingLedger({"a": 2})
+        self.assertEqual(ledger.apply_batch([("a", -1), ("b", 3)]), [1, 3])
+        self.assertEqual(ledger.calls, [("a", -1), ("b", 3)])
+
 
 if __name__ == "__main__":
     unittest.main()
````

### Verification

- Command: `python3 -m unittest discover -s tests`
- Exit: `0`
- Timed out: `False`

````text

....
----------------------------------------------------------------------
Ran 4 tests in 0.000s

OK
````
