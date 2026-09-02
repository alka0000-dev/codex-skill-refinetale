You are grading six anonymized implementations from an independent forward holdout. Return only the requested structured result.

# User request

# 在庫移動

`workspace/` の `Inventory` に、別倉庫への在庫移動を追加してください。

要件:

- `source.transfer_to(destination, sku, quantity)` を追加する。
- quantityはboolではない正のint、skuは空でないstr、destinationはInventoryでなければならない。不正値は `ValueError` とし状態を変えない。
- sourceとdestinationが同一なら、有効な入力について何も変更せず監査ログも追加せず、現在の在庫数を返す。
- source在庫が不足なら `InsufficientStock` とし、両倉庫の在庫・監査ログを変えない。
- 成功時はsourceから減算後、destinationへ加算し、それぞれの既存 `adjust` を使う。
- 成功時の戻り値は `(sourceの新在庫数, destinationの新在庫数)`。
- 監査ログの順序と既存adjustの契約を維持する。

`workspace/` の実装を修正し、workspaceをカレントディレクトリとして `python3 -m unittest discover -s tests` を実行してください。

# Fixture rubric

# Rubric

- S1 (0–2): 有効な移動をsource減算→destination加算の順で既存adjust経由により行う。2=完全、1=一部、0=別状態更新/順序違反。
- S2 (0–2): 不足時に両倉庫の在庫と監査ログを完全に不変にする。2=完全、1=片方のみ、0=部分移動。
- S3 (0–2): sku、quantity、destinationを副作用前に厳密検証しboolを拒否する。2=完全、1=漏れ、0=不正値で変更。
- S4 (0–2): 同一倉庫を早期no-opとし、戻り値・監査・既存adjust契約を守る。2=完全、1=一部、0=自己移動の副作用/回帰。
- S5 (0–2): 自動テストが成功、不足、自己移動、不正入力、順序、回帰を検証し全成功。2=十分、1=部分、0=失敗/未検証。

Pass=8〜10点かつ0点なし。Borderline=6〜7点、または8点以上でも0点あり。Fail=0〜5点。

Critical failure: 不足/不正入力でいずれかの状態が変わる、自己移動で監査を増やす、既存adjustを破壊する、検証コマンド失敗。採点対象は識別子名や回答文でなくrepositoryの最終差分、挙動、設計境界、検証結果。

# Initial repository

### inventory.py

````text
class InsufficientStock(Exception):
    pass


class Inventory:
    def __init__(self, stock=None):
        self.stock = dict(stock or {})
        self.audit = []

    def adjust(self, sku, delta):
        updated = self.stock.get(sku, 0) + delta
        if updated < 0:
            raise InsufficientStock(sku)
        self.stock[sku] = updated
        self.audit.append((sku, delta, updated))
        return updated
````

### tests/test_existing.py

````text
import unittest
from inventory import InsufficientStock, Inventory


class ExistingTests(unittest.TestCase):
    def test_adjust(self):
        inventory = Inventory({"book": 3})
        self.assertEqual(inventory.adjust("book", -1), 2)
        with self.assertRaises(InsufficientStock):
            inventory.adjust("book", -3)
        self.assertEqual(inventory.audit, [("book", -1, 2)])


if __name__ == "__main__":
    unittest.main()
````

### tests/test_requirements.py

````text
import unittest
from inventory import InsufficientStock, Inventory


class RequirementTests(unittest.TestCase):
    def test_success_uses_ordered_adjustments(self):
        source = Inventory({"book": 5})
        destination = Inventory({"book": 2})
        self.assertEqual(source.transfer_to(destination, "book", 3), (2, 5))
        self.assertEqual(source.audit, [("book", -3, 2)])
        self.assertEqual(destination.audit, [("book", 3, 5)])

    def test_insufficient_stock_is_atomic(self):
        source = Inventory({"book": 1})
        destination = Inventory({"book": 2})
        with self.assertRaises(InsufficientStock):
            source.transfer_to(destination, "book", 3)
        self.assertEqual((source.stock, source.audit), ({"book": 1}, []))
        self.assertEqual((destination.stock, destination.audit), ({"book": 2}, []))

    def test_same_inventory_is_noop(self):
        inventory = Inventory({"book": 4})
        self.assertEqual(inventory.transfer_to(inventory, "book", 2), 4)
        self.assertEqual((inventory.stock, inventory.audit), ({"book": 4}, []))

    def test_invalid_input_is_atomic(self):
        cases = [("", 1, Inventory()), ("book", 0, Inventory()), ("book", True, Inventory()), ("book", 1, object())]
        for sku, quantity, destination in cases:
            source = Inventory({"book": 3})
            with self.subTest(sku=sku, quantity=quantity), self.assertRaises(ValueError):
                source.transfer_to(destination, sku, quantity)
            self.assertEqual((source.stock, source.audit), ({"book": 3}, []))


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

在庫移動を実装しました。

- [inventory.py](<EVAL_WORKSPACE>/inventory.py:18)
  - destination・sku・quantityを副作用前に検証
  - 同一倉庫は在庫・監査ログを変更せず現在値を返却
  - 不足時は既存 `adjust` の `InsufficientStock` により両倉庫を変更しない
  - 成功時は source、destination の順で既存 `adjust` を実行し、新在庫の組を返却
- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:26)
  - 非str・空sku、非正数・非int・bool quantity、不正destinationについて、両倉庫が変更されないことを検証

検証結果:

- `python3 -m compileall -q inventory.py tests`: 成功
- `python3 -m unittest discover -s tests`: **5 tests、すべて成功**
- `git diff --check`: 成功
- 既存 `adjust` の契約と監査ログ形式は未変更です。

### Final diff

````diff
diff --git a/inventory.py b/inventory.py
index 2059edc..4a540a1 100644
--- a/inventory.py
+++ b/inventory.py
@@ -14,3 +14,19 @@ class Inventory:
         self.stock[sku] = updated
         self.audit.append((sku, delta, updated))
         return updated
+
+    def transfer_to(self, destination, sku, quantity):
+        if (
+            not isinstance(destination, Inventory)
+            or not isinstance(sku, str)
+            or not sku
+            or isinstance(quantity, bool)
+            or not isinstance(quantity, int)
+            or quantity <= 0
+        ):
+            raise ValueError
+
+        if self is destination:
+            return self.stock.get(sku, 0)
+
+        return self.adjust(sku, -quantity), destination.adjust(sku, quantity)
diff --git a/tests/test_requirements.py b/tests/test_requirements.py
index 2d4ecdd..070432f 100644
--- a/tests/test_requirements.py
+++ b/tests/test_requirements.py
@@ -24,12 +24,22 @@ class RequirementTests(unittest.TestCase):
         self.assertEqual((inventory.stock, inventory.audit), ({"book": 4}, []))
 
     def test_invalid_input_is_atomic(self):
-        cases = [("", 1, Inventory()), ("book", 0, Inventory()), ("book", True, Inventory()), ("book", 1, object())]
+        cases = [
+            (None, 1, Inventory({"book": 2})),
+            ("", 1, Inventory({"book": 2})),
+            ("book", 0, Inventory({"book": 2})),
+            ("book", -1, Inventory({"book": 2})),
+            ("book", 1.0, Inventory({"book": 2})),
+            ("book", True, Inventory({"book": 2})),
+            ("book", 1, object()),
+        ]
         for sku, quantity, destination in cases:
             source = Inventory({"book": 3})
             with self.subTest(sku=sku, quantity=quantity), self.assertRaises(ValueError):
                 source.transfer_to(destination, sku, quantity)
             self.assertEqual((source.stock, source.audit), ({"book": 3}, []))
+            if isinstance(destination, Inventory):
+                self.assertEqual((destination.stock, destination.audit), ({"book": 2}, []))
 
 
 if __name__ == "__main__":
````

### Verification

- Command: `python3 -m unittest discover -s tests`
- Exit: `0`
- Timed out: `False`

````text

.....
----------------------------------------------------------------------
Ran 5 tests in 0.000s

OK
````

## Candidate B

### Final answer

`Inventory.transfer_to` を [inventory.py](<EVAL_WORKSPACE>/inventory.py:18) に追加しました。

- 入力値を状態変更前に検証
- 同一倉庫は在庫・監査ログを変更せず現在庫を返却
- 在庫不足時の原子性を維持
- 成功時は source → destination の順に既存 `adjust` を使用
- 成功時は両倉庫の新在庫数を返却

検証結果:

- `python3 -m unittest discover -s tests`: 5件成功
- `py_compile`: 成功
- `git diff --check`: 成功

### Final diff

````diff
diff --git a/inventory.py b/inventory.py
index 2059edc..a2f0b67 100644
--- a/inventory.py
+++ b/inventory.py
@@ -14,3 +14,21 @@ class Inventory:
         self.stock[sku] = updated
         self.audit.append((sku, delta, updated))
         return updated
+
+    def transfer_to(self, destination, sku, quantity):
+        if not isinstance(destination, Inventory):
+            raise ValueError("destination must be an Inventory")
+        if not isinstance(sku, str) or not sku:
+            raise ValueError("sku must be a non-empty string")
+        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
+            raise ValueError("quantity must be a positive integer")
+
+        if destination is self:
+            return self.stock.get(sku, 0)
+
+        if self.stock.get(sku, 0) < quantity:
+            raise InsufficientStock(sku)
+
+        source_stock = self.adjust(sku, -quantity)
+        destination_stock = destination.adjust(sku, quantity)
+        return source_stock, destination_stock
````

### Verification

- Command: `python3 -m unittest discover -s tests`
- Exit: `0`
- Timed out: `False`

````text

.....
----------------------------------------------------------------------
Ran 5 tests in 0.000s

OK
````

## Candidate C

### Final answer

在庫移動を実装しました。

- [inventory.py](<EVAL_WORKSPACE>/inventory.py:18)
  - destination・SKU・quantity を副作用前に検証
  - 同一倉庫は在庫数を返して無変更
  - 在庫不足は両倉庫・監査ログとも無変更
  - 成功時は source、destination の順で既存 `adjust` を使用
- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:26)
  - 非文字列SKU、負数quantity、destination側の不変条件を追加検証

検証結果:

- `python3 -m unittest discover -s tests`: 全5テスト成功
- 構文コンパイル: 成功
- `git diff --check`: 成功

入力不正、同一倉庫、在庫不足、成功時の戻り値・更新順序・監査ログ、既存 `adjust` 契約をそれぞれ確認済みです。

### Final diff

````diff
diff --git a/inventory.py b/inventory.py
index 2059edc..614d5c6 100644
--- a/inventory.py
+++ b/inventory.py
@@ -14,3 +14,24 @@ class Inventory:
         self.stock[sku] = updated
         self.audit.append((sku, delta, updated))
         return updated
+
+    def transfer_to(self, destination, sku, quantity):
+        if (
+            not isinstance(destination, Inventory)
+            or not isinstance(sku, str)
+            or not sku
+            or not isinstance(quantity, int)
+            or isinstance(quantity, bool)
+            or quantity <= 0
+        ):
+            raise ValueError
+
+        if self is destination:
+            return self.stock.get(sku, 0)
+
+        if self.stock.get(sku, 0) < quantity:
+            raise InsufficientStock(sku)
+
+        source_stock = self.adjust(sku, -quantity)
+        destination_stock = destination.adjust(sku, quantity)
+        return source_stock, destination_stock
diff --git a/tests/test_requirements.py b/tests/test_requirements.py
index 2d4ecdd..d373042 100644
--- a/tests/test_requirements.py
+++ b/tests/test_requirements.py
@@ -24,12 +24,21 @@ class RequirementTests(unittest.TestCase):
         self.assertEqual((inventory.stock, inventory.audit), ({"book": 4}, []))
 
     def test_invalid_input_is_atomic(self):
-        cases = [("", 1, Inventory()), ("book", 0, Inventory()), ("book", True, Inventory()), ("book", 1, object())]
+        cases = [
+            ("", 1, Inventory({"book": 2})),
+            (None, 1, Inventory({"book": 2})),
+            ("book", 0, Inventory({"book": 2})),
+            ("book", -1, Inventory({"book": 2})),
+            ("book", True, Inventory({"book": 2})),
+            ("book", 1, object()),
+        ]
         for sku, quantity, destination in cases:
             source = Inventory({"book": 3})
             with self.subTest(sku=sku, quantity=quantity), self.assertRaises(ValueError):
                 source.transfer_to(destination, sku, quantity)
             self.assertEqual((source.stock, source.audit), ({"book": 3}, []))
+            if isinstance(destination, Inventory):
+                self.assertEqual((destination.stock, destination.audit), ({"book": 2}, []))
 
 
 if __name__ == "__main__":
````

### Verification

- Command: `python3 -m unittest discover -s tests`
- Exit: `0`
- Timed out: `False`

````text

.....
----------------------------------------------------------------------
Ran 5 tests in 0.000s

OK
````

## Candidate D

### Final answer

実装完了しました。

変更:

- [inventory.py](<EVAL_WORKSPACE>/inventory.py:18) に `Inventory.transfer_to` を追加
- 入力不正: `ValueError`、両倉庫無変更
- 同一倉庫: 在庫・監査ログ無変更で現在数を返却
- 在庫不足: `InsufficientStock`、両倉庫無変更
- 成功: source、destination の順で既存 `adjust` を呼び、更新後在庫数のタプルを返却
- [.agent/CONTINUITY.md](<EVAL_WORKSPACE>/.agent/CONTINUITY.md) に判断・検証結果を記録

検証結果:

- `python3 -m unittest discover -s tests`
  - 5件すべて成功
- 追加境界検証
  - 非文字列SKU、bool・ゼロ・負数・非整数quantityを拒否
  - 同一倉庫、不足時の状態・既存監査ログを維持
  - source → destination の `adjust` 呼び出し順を確認
- `py_compile`、`git diff --check` 成功
- 既存 `adjust` のテストも成功し、既存契約を維持しています。

### Final diff

````diff
diff --git a/inventory.py b/inventory.py
index 2059edc..443bb3a 100644
--- a/inventory.py
+++ b/inventory.py
@@ -14,3 +14,24 @@ class Inventory:
         self.stock[sku] = updated
         self.audit.append((sku, delta, updated))
         return updated
+
+    def transfer_to(self, destination, sku, quantity):
+        if (
+            not isinstance(destination, Inventory)
+            or not isinstance(sku, str)
+            or not sku
+            or not isinstance(quantity, int)
+            or isinstance(quantity, bool)
+            or quantity <= 0
+        ):
+            raise ValueError
+
+        if destination is self:
+            return self.stock.get(sku, 0)
+
+        if self.stock.get(sku, 0) < quantity:
+            raise InsufficientStock(sku)
+
+        source_stock = self.adjust(sku, -quantity)
+        destination_stock = destination.adjust(sku, quantity)
+        return source_stock, destination_stock
````

### Verification

- Command: `python3 -m unittest discover -s tests`
- Exit: `0`
- Timed out: `False`

````text

.....
----------------------------------------------------------------------
Ran 5 tests in 0.000s

OK
````

## Candidate E

### Final answer

在庫移動を [inventory.py](<EVAL_WORKSPACE>/inventory.py:17) に実装しました。

- 入力値を変更前に検証
- 同一倉庫は無変更・監査ログなし
- 在庫不足時は両倉庫とも無変更
- 成功時は source→destination の順で既存 `adjust` を使用
- 成功時は両倉庫の新在庫数を返却

検証結果:

```text
Ran 5 tests in 0.000s
OK
```

`py_compile` と `git diff --check` も成功しています。

### Final diff

````diff
diff --git a/inventory.py b/inventory.py
index 2059edc..b35cd7c 100644
--- a/inventory.py
+++ b/inventory.py
@@ -14,3 +14,20 @@ class Inventory:
         self.stock[sku] = updated
         self.audit.append((sku, delta, updated))
         return updated
+
+    def transfer_to(self, destination, sku, quantity):
+        if not isinstance(destination, Inventory):
+            raise ValueError("destination must be an Inventory")
+        if not isinstance(sku, str) or not sku:
+            raise ValueError("sku must be a non-empty string")
+        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
+            raise ValueError("quantity must be a positive integer")
+
+        if self is destination:
+            return self.stock.get(sku, 0)
+        if self.stock.get(sku, 0) < quantity:
+            raise InsufficientStock(sku)
+
+        source_stock = self.adjust(sku, -quantity)
+        destination_stock = destination.adjust(sku, quantity)
+        return source_stock, destination_stock
````

### Verification

- Command: `python3 -m unittest discover -s tests`
- Exit: `0`
- Timed out: `False`

````text

.....
----------------------------------------------------------------------
Ran 5 tests in 0.000s

OK
````

## Candidate F

### Final answer

`Inventory.transfer_to` を追加しました。[inventory.py](<EVAL_WORKSPACE>/inventory.py:18)

対応内容:

- destination・sku・quantity の入力検証
- 同一倉庫間の no-op
- 在庫不足時の原子性維持
- 既存 `adjust` を source → destination の順で使用
- 成功時に両倉庫の新在庫数を返却

検証結果:

- `python3 -m unittest discover -s tests`: 5件成功
- Python構文検証: 成功
- `git diff --check`: 成功

### Final diff

````diff
diff --git a/inventory.py b/inventory.py
index 2059edc..cdf746d 100644
--- a/inventory.py
+++ b/inventory.py
@@ -14,3 +14,21 @@ class Inventory:
         self.stock[sku] = updated
         self.audit.append((sku, delta, updated))
         return updated
+
+    def transfer_to(self, destination, sku, quantity):
+        if not isinstance(destination, Inventory):
+            raise ValueError("destination must be an Inventory")
+        if not isinstance(sku, str) or not sku:
+            raise ValueError("sku must be a non-empty string")
+        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
+            raise ValueError("quantity must be a positive integer")
+
+        source_quantity = self.stock.get(sku, 0)
+        if destination is self:
+            return source_quantity
+        if source_quantity < quantity:
+            raise InsufficientStock(sku)
+
+        source_quantity = self.adjust(sku, -quantity)
+        destination_quantity = destination.adjust(sku, quantity)
+        return source_quantity, destination_quantity
````

### Verification

- Command: `python3 -m unittest discover -s tests`
- Exit: `0`
- Timed out: `False`

````text

.....
----------------------------------------------------------------------
Ran 5 tests in 0.000s

OK
````
