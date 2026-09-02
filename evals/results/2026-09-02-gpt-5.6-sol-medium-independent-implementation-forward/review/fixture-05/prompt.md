You are grading six anonymized implementations from an independent forward holdout. Return only the requested structured result.

# User request

# 請求書の一括公開

`workspace/` の請求書サービスに、一括公開を追加してください。

要件:

- `InvoiceService.publish_all(invoices)` を追加し、公開結果を入力順のlistで返す。
- 各invoiceは既存の `render` で生成し、既存publisherの `publish(invoice_id, body)` で公開する。
- 全invoiceのrenderが成功した後にだけ、最初のpublishを行う。
- render失敗時は例外をそのまま送出し、1件もpublishしない。
- publish失敗時は例外をそのまま送出し、後続invoiceをpublishしない（既に成功した外部公開は取り消さない）。
- 空入力は空listを返し、publisherを呼ばない。
- 既存の `publish_one` の契約を維持する。

`workspace/` の実装を修正し、workspaceをカレントディレクトリとして `python3 -m unittest discover -s tests` を実行してください。

# Fixture rubric

# Rubric

- S1 (0–2): 全件render完了後にのみpublishを開始し、render失敗で外部副作用がない。2=完全、1=限定漏れ、0=部分公開。
- S2 (0–2): publishを入力順に行い、失敗直後に終了して後続を呼ばない。2=完全、1=順序/終了に漏れ、0=継続公開。
- S3 (0–2): 既存renderとpublisher境界を再利用し、準備済みデータを単一経路で渡す。2=一貫、1=重複、0=別実装で契約逸脱。
- S4 (0–2): 戻り値、空入力、publish_oneの互換性が正しい。2=完全、1=一部、0=回帰。
- S5 (0–2): 自動テストが準備失敗、公開失敗、順序、空、回帰を検証し全成功。2=十分、1=部分、0=失敗/未検証。

Pass=8〜10点かつ0点なし。Borderline=6〜7点、または8点以上でも0点あり。Fail=0〜5点。

Critical failure: render完了前に公開する、公開失敗後も継続する、既存publish_oneを破壊する、検証コマンド失敗。識別子名や回答文でなくrepositoryの最終差分、挙動、設計境界、検証結果を採点する。

# Initial repository

### invoices.py

````text
class InvoiceService:
    def __init__(self, publisher):
        self.publisher = publisher

    def render(self, invoice):
        if "id" not in invoice or "amount" not in invoice:
            raise ValueError("invalid invoice")
        return f"invoice={invoice['id']};amount={invoice['amount']}"

    def publish_one(self, invoice):
        body = self.render(invoice)
        return self.publisher.publish(invoice["id"], body)
````

### tests/test_existing.py

````text
import unittest
from invoices import InvoiceService


class Publisher:
    def __init__(self):
        self.calls = []

    def publish(self, invoice_id, body):
        self.calls.append((invoice_id, body))
        return "receipt:" + invoice_id


class ExistingTests(unittest.TestCase):
    def test_publish_one(self):
        publisher = Publisher()
        result = InvoiceService(publisher).publish_one({"id": "a", "amount": 10})
        self.assertEqual(result, "receipt:a")
        self.assertEqual(publisher.calls, [("a", "invoice=a;amount=10")])


if __name__ == "__main__":
    unittest.main()
````

### tests/test_requirements.py

````text
import unittest
from invoices import InvoiceService


class Publisher:
    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on

    def publish(self, invoice_id, body):
        self.calls.append((invoice_id, body))
        if invoice_id == self.fail_on:
            raise RuntimeError("publish failed")
        return "receipt:" + invoice_id


class TrackingService(InvoiceService):
    def __init__(self, publisher, events):
        super().__init__(publisher)
        self.events = events

    def render(self, invoice):
        self.events.append("render:" + invoice.get("id", "missing"))
        return super().render(invoice)


class RequirementTests(unittest.TestCase):
    def test_prepares_all_before_publishing(self):
        events = []
        publisher = Publisher()
        original_publish = publisher.publish
        publisher.publish = lambda invoice_id, body: (events.append("publish:" + invoice_id), original_publish(invoice_id, body))[1]
        service = TrackingService(publisher, events)
        result = service.publish_all([{"id": "a", "amount": 1}, {"id": "b", "amount": 2}])
        self.assertEqual(result, ["receipt:a", "receipt:b"])
        self.assertEqual(events, ["render:a", "render:b", "publish:a", "publish:b"])

    def test_render_failure_publishes_nothing(self):
        publisher = Publisher()
        with self.assertRaises(ValueError):
            InvoiceService(publisher).publish_all([{"id": "a", "amount": 1}, {"id": "bad"}])
        self.assertEqual(publisher.calls, [])

    def test_publish_failure_stops_following_items(self):
        publisher = Publisher(fail_on="b")
        with self.assertRaises(RuntimeError):
            InvoiceService(publisher).publish_all([
                {"id": "a", "amount": 1}, {"id": "b", "amount": 2}, {"id": "c", "amount": 3}
            ])
        self.assertEqual([call[0] for call in publisher.calls], ["a", "b"])

    def test_empty_input(self):
        publisher = Publisher()
        self.assertEqual(InvoiceService(publisher).publish_all([]), [])
        self.assertEqual(publisher.calls, [])


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

実装しました。[invoices.py](<EVAL_WORKSPACE>/invoices.py:14) に `InvoiceService.publish_all` を追加しています。

検証結果:

- 入力順の結果返却・全render後のpublish開始: 成功
- render失敗時にpublish 0件・例外伝播: 成功
- publish失敗時に後続停止・既存公開は維持: 成功
- 空入力で空list・publish 0件: 成功
- 既存`publish_one`契約: 成功
- `python3 -m unittest discover -s tests`: 5件成功
- `py_compile`、`git diff --check`: 成功

既存テストが全要件を直接検証していたため、テストコードの追加変更はありません。

### Final diff

````diff
diff --git a/invoices.py b/invoices.py
index 423570f..34bc424 100644
--- a/invoices.py
+++ b/invoices.py
@@ -10,3 +10,7 @@ class InvoiceService:
     def publish_one(self, invoice):
         body = self.render(invoice)
         return self.publisher.publish(invoice["id"], body)
+
+    def publish_all(self, invoices):
+        rendered = [(invoice, self.render(invoice)) for invoice in invoices]
+        return [self.publisher.publish(invoice["id"], body) for invoice, body in rendered]
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

`InvoiceService.publish_all(invoices)` を追加しました。

- 全件の render 成功後に publish を開始
- 入力順で公開し、結果を list で返却
- render / publish の例外をそのまま送出
- publish 失敗後は後続処理を停止
- 空入力では publisher を呼ばず `[]` を返却
- `publish_one` は変更なし

変更: [invoices.py](<EVAL_WORKSPACE>/invoices.py:13)

検証結果:

```text
Ran 5 tests in 0.000s

OK
```

`py_compile` と `git diff --check` も成功しています。

### Final diff

````diff
diff --git a/invoices.py b/invoices.py
index 423570f..6087beb 100644
--- a/invoices.py
+++ b/invoices.py
@@ -10,3 +10,14 @@ class InvoiceService:
     def publish_one(self, invoice):
         body = self.render(invoice)
         return self.publisher.publish(invoice["id"], body)
+
+    def publish_all(self, invoices):
+        rendered_invoices = []
+        for invoice in invoices:
+            body = self.render(invoice)
+            rendered_invoices.append((invoice["id"], body))
+
+        return [
+            self.publisher.publish(invoice_id, body)
+            for invoice_id, body in rendered_invoices
+        ]
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

`InvoiceService.publish_all(invoices)` を [invoices.py](<EVAL_WORKSPACE>/invoices.py:14) に追加しました。

- 全件render完了後、入力順にpublish
- render／publish例外はそのまま送出
- publish失敗後の後続処理を停止
- 空入力は `[]`
- `publish_one` は変更なし

検証結果:

```text
python3 -m unittest discover -s tests
Ran 5 tests
OK
```

Python構文コンパイルと `git diff --check` も成功しています。

### Final diff

````diff
diff --git a/invoices.py b/invoices.py
index 423570f..6087beb 100644
--- a/invoices.py
+++ b/invoices.py
@@ -10,3 +10,14 @@ class InvoiceService:
     def publish_one(self, invoice):
         body = self.render(invoice)
         return self.publisher.publish(invoice["id"], body)
+
+    def publish_all(self, invoices):
+        rendered_invoices = []
+        for invoice in invoices:
+            body = self.render(invoice)
+            rendered_invoices.append((invoice["id"], body))
+
+        return [
+            self.publisher.publish(invoice_id, body)
+            for invoice_id, body in rendered_invoices
+        ]
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

[invoices.py](<EVAL_WORKSPACE>/invoices.py:14) に `InvoiceService.publish_all` を追加しました。

検証結果:

- 入力順の結果・全件 render 後の publish: 成功
- render 失敗時に publish 0件: 成功
- publish 失敗時に後続を停止: 成功
- 空入力で空 list・publish 0件: 成功
- 既存 `publish_one` 契約: 成功
- `python3 -m unittest discover -s tests`: 5件成功
- 構文検証、`git diff --check`: 成功

例外処理や空入力専用分岐は追加せず、既存例外をそのまま伝播させる実装です。

### Final diff

````diff
diff --git a/invoices.py b/invoices.py
index 423570f..6087beb 100644
--- a/invoices.py
+++ b/invoices.py
@@ -10,3 +10,14 @@ class InvoiceService:
     def publish_one(self, invoice):
         body = self.render(invoice)
         return self.publisher.publish(invoice["id"], body)
+
+    def publish_all(self, invoices):
+        rendered_invoices = []
+        for invoice in invoices:
+            body = self.render(invoice)
+            rendered_invoices.append((invoice["id"], body))
+
+        return [
+            self.publisher.publish(invoice_id, body)
+            for invoice_id, body in rendered_invoices
+        ]
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

`InvoiceService.publish_all` を [invoices.py](<EVAL_WORKSPACE>/invoices.py:14) に追加しました。

- 全件render完了後、入力順にpublishして結果を返す
- render失敗時はpublishせず、例外をそのまま送出
- publish失敗時は後続を停止し、成功済み公開は維持
- 空入力は `[]`、publisher呼び出しなし
- `publish_one` は変更なし
- 不要な条件分岐や例外変換は追加なし

検証結果:

```text
$ python3 -m unittest discover -s tests
.....
Ran 5 tests in 0.000s

OK
```

`git diff --check` も成功しています。

### Final diff

````diff
diff --git a/invoices.py b/invoices.py
index 423570f..6087beb 100644
--- a/invoices.py
+++ b/invoices.py
@@ -10,3 +10,14 @@ class InvoiceService:
     def publish_one(self, invoice):
         body = self.render(invoice)
         return self.publisher.publish(invoice["id"], body)
+
+    def publish_all(self, invoices):
+        rendered_invoices = []
+        for invoice in invoices:
+            body = self.render(invoice)
+            rendered_invoices.append((invoice["id"], body))
+
+        return [
+            self.publisher.publish(invoice_id, body)
+            for invoice_id, body in rendered_invoices
+        ]
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

`InvoiceService.publish_all` を追加しました。[invoices.py](<EVAL_WORKSPACE>/invoices.py:14)

- 全件render完了後に入力順でpublish
- render／publish例外をそのまま送出
- publish失敗後の処理を停止
- 空入力は空list
- `publish_one` は変更なし

検証結果:

```text
Ran 5 tests
OK
```

`py_compile` と `git diff --check` も成功しています。

### Final diff

````diff
diff --git a/invoices.py b/invoices.py
index 423570f..6087beb 100644
--- a/invoices.py
+++ b/invoices.py
@@ -10,3 +10,14 @@ class InvoiceService:
     def publish_one(self, invoice):
         body = self.render(invoice)
         return self.publisher.publish(invoice["id"], body)
+
+    def publish_all(self, invoices):
+        rendered_invoices = []
+        for invoice in invoices:
+            body = self.render(invoice)
+            rendered_invoices.append((invoice["id"], body))
+
+        return [
+            self.publisher.publish(invoice_id, body)
+            for invoice_id, body in rendered_invoices
+        ]
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
