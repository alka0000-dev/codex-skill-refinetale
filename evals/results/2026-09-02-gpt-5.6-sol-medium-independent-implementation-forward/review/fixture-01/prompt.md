You are grading six anonymized implementations from an independent forward holdout. Return only the requested structured result.

# User request

# タイムアウト設定の追加

`workspace/` の小さなHTTPクライアントに、リクエスト単位のタイムアウト指定を追加してください。

要件:

- `Client.request(path, timeout=None)` を利用可能にする。
- 有効なタイムアウトは正の有限な秒数（`int` または `float`。`bool` は不可）。
- 優先順位は、リクエスト指定、`Client` 作成時の指定、既定値 `5.0` の順。
- 明示された無効値は、下位の値へフォールバックせず `ValueError` にする。
- transportには従来どおりpathを渡し、解決済みタイムアウトをキーワード引数 `timeout` で渡す。
- 既存の `Client(transport)` と `request(path)` は互換に保つ。

`workspace/` 内の実装を修正し、最後にworkspaceをカレントディレクトリとして `python3 -m unittest discover -s tests` を実行してください。

# Fixture rubric

# Rubric

- S1 (0–2): リクエスト値、クライアント値、既定値の優先順位が全経路で正しい。2=全て、1=一部、0=未対応。
- S2 (0–2): 正の有限なint/floatだけを受理し、bool、0以下、NaN、無限大を明示位置で拒否する。2=完全、1=漏れあり、0=実質未検証。
- S3 (0–2): 解決値が既存transport経路へ一度だけ渡り、別の送信状態や並行経路を増やさない。2=境界が一貫、1=軽微な重複、0=経路分裂。
- S4 (0–2): 従来の生成・呼出し契約と戻り値を維持する。2=回帰なし、1=限定的な互換性欠落、0=既存契約破壊。
- S5 (0–2): repository内の自動テストが要件と回帰を具体的に検証し、全て成功する。2=十分、1=部分的、0=失敗または未検証。

Pass=8〜10点かつ0点なし。Borderline=6〜7点、または8点以上でもいずれかが0点。Fail=0〜5点。

Critical failure: transportを呼べない、無効値で送信が発生する、公開APIを互換性なく削除する、検証コマンドが失敗する。識別子名や回答文ではなく、最終差分、挙動、設計境界、検証結果を採点する。

# Initial repository

### client.py

````text
class Client:
    def __init__(self, transport):
        self._transport = transport

    def request(self, path):
        return self._transport.send(path)
````

### tests/test_existing.py

````text
import unittest
from client import Client


class Transport:
    def __init__(self):
        self.calls = []

    def send(self, path, **options):
        self.calls.append((path, options))
        return "ok"


class ExistingTests(unittest.TestCase):
    def test_request_returns_transport_result(self):
        transport = Transport()
        self.assertEqual(Client(transport).request("/health"), "ok")
        self.assertEqual(transport.calls[0][0], "/health")


if __name__ == "__main__":
    unittest.main()
````

### tests/test_requirements.py

````text
import math
import unittest
from client import Client


class Transport:
    def __init__(self):
        self.calls = []

    def send(self, path, **options):
        self.calls.append((path, options))
        return options["timeout"]


class RequirementTests(unittest.TestCase):
    def test_precedence_and_default(self):
        transport = Transport()
        client = Client(transport, timeout=3)
        self.assertEqual(client.request("/a", timeout=1.5), 1.5)
        self.assertEqual(client.request("/b"), 3)
        self.assertEqual(Client(transport).request("/c"), 5.0)

    def test_invalid_explicit_values_do_not_send_or_fallback(self):
        for value in (0, -1, True, math.nan, math.inf):
            with self.subTest(value=value):
                transport = Transport()
                client = Client(transport, timeout=2)
                with self.assertRaises(ValueError):
                    client.request("/bad", timeout=value)
                self.assertEqual(transport.calls, [])

    def test_invalid_client_value_is_rejected(self):
        for value in (False, 0, float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Client(Transport(), timeout=value)


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

実装しました。

変更内容:

- [client.py](<EVAL_WORKSPACE>/client.py)
  - `Client(transport, timeout=None)` を追加
  - `Client.request(path, timeout=None)` を追加
  - 優先順位を request → Client → `5.0` で解決
  - 正の有限な `int` / `float` のみ許可し、`bool`・非数値・0以下・NaN・無限値は `ValueError`
  - 検証後に `transport.send(path, timeout=...)` を実行
  - 無効値では transport を呼び出さない

- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py)
  - 明示的な `None` のフォールバックを検証
  - 数値型以外の拒否を検証

検証結果:

```text
python3 -m unittest discover -s tests

Ran 4 tests in 0.000s
OK
```

優先順位、有効値、無効値の早期拒否、path・timeout の送信、既存 API の互換性をそれぞれテストで確認済みです。

### Final diff

````diff
diff --git a/client.py b/client.py
index 3528ffe..5556456 100644
--- a/client.py
+++ b/client.py
@@ -1,6 +1,29 @@
+import math
+
+
+_DEFAULT_TIMEOUT = 5.0
+
+
+def _resolve_timeout(timeout, fallback):
+    if timeout is None:
+        return fallback
+    if (
+        isinstance(timeout, bool)
+        or not isinstance(timeout, (int, float))
+        or timeout <= 0
+        or isinstance(timeout, float) and not math.isfinite(timeout)
+    ):
+        raise ValueError("timeout must be a positive finite number")
+    return timeout
+
+
 class Client:
-    def __init__(self, transport):
+    def __init__(self, transport, timeout=None):
         self._transport = transport
+        self._timeout = _resolve_timeout(timeout, _DEFAULT_TIMEOUT)
 
-    def request(self, path):
-        return self._transport.send(path)
+    def request(self, path, timeout=None):
+        return self._transport.send(
+            path,
+            timeout=_resolve_timeout(timeout, self._timeout),
+        )
diff --git a/tests/test_requirements.py b/tests/test_requirements.py
index 6c65800..87d81ae 100644
--- a/tests/test_requirements.py
+++ b/tests/test_requirements.py
@@ -18,10 +18,11 @@ class RequirementTests(unittest.TestCase):
         client = Client(transport, timeout=3)
         self.assertEqual(client.request("/a", timeout=1.5), 1.5)
         self.assertEqual(client.request("/b"), 3)
+        self.assertEqual(client.request("/none", timeout=None), 3)
         self.assertEqual(Client(transport).request("/c"), 5.0)
 
     def test_invalid_explicit_values_do_not_send_or_fallback(self):
-        for value in (0, -1, True, math.nan, math.inf):
+        for value in (0, -1, True, "1", math.nan, math.inf):
             with self.subTest(value=value):
                 transport = Transport()
                 client = Client(transport, timeout=2)
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

タイムアウト設定を [client.py](<EVAL_WORKSPACE>/client.py) に追加しました。

- 優先順位: リクエスト指定 → Client指定 → `5.0`
- 正の有限な `int` / `float` のみ許可（`bool` は拒否）
- 無効な明示値は `ValueError`
- transportへ `send(path, timeout=resolved_timeout)` として送信
- 既存APIとの互換性を維持

検証結果:

```text
Ran 4 tests in 0.000s

OK
```

構文チェックと `git diff --check` も成功しています。

### Final diff

````diff
diff --git a/client.py b/client.py
index 3528ffe..f4fec3e 100644
--- a/client.py
+++ b/client.py
@@ -1,6 +1,29 @@
+import math
+
+
+DEFAULT_TIMEOUT = 5.0
+
+
+def _validate_timeout(timeout):
+    if (
+        isinstance(timeout, bool)
+        or not isinstance(timeout, (int, float))
+        or not math.isfinite(timeout)
+        or timeout <= 0
+    ):
+        raise ValueError("timeout must be a positive finite number of seconds")
+    return timeout
+
+
 class Client:
-    def __init__(self, transport):
+    def __init__(self, transport, timeout=None):
         self._transport = transport
+        self._timeout = (
+            DEFAULT_TIMEOUT if timeout is None else _validate_timeout(timeout)
+        )
 
-    def request(self, path):
-        return self._transport.send(path)
+    def request(self, path, timeout=None):
+        resolved_timeout = (
+            self._timeout if timeout is None else _validate_timeout(timeout)
+        )
+        return self._transport.send(path, timeout=resolved_timeout)
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

タイムアウト指定を追加しました。

- [client.py](<EVAL_WORKSPACE>/client.py:7)
  - 優先順位: リクエスト指定 → Client指定 → `5.0`
  - 正の有限な `int` / `float` のみ許可（`bool` は拒否）
  - 無効な明示値は transport 呼び出し前に `ValueError`
  - `send(path, timeout=resolved_timeout)` で送信

- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:15)
  - 優先順位と既定値
  - `None` の未指定扱い
  - 数値境界・非数値・`bool` の拒否
  - 無効時にフォールバック・送信しないこと
  - 既存呼び出しの互換性

検証結果:

```text
python3 -m unittest discover -s tests
Ran 4 tests
OK
```

`git diff --check` も成功しています。プロジェクトには個別のビルド・lint設定はありません。

### Final diff

````diff
diff --git a/client.py b/client.py
index 3528ffe..e244d19 100644
--- a/client.py
+++ b/client.py
@@ -1,6 +1,27 @@
+import math
+
+
+DEFAULT_TIMEOUT = 5.0
+
+
+def _resolve_timeout(timeout, fallback):
+    if timeout is None:
+        return fallback
+    if (
+        isinstance(timeout, bool)
+        or not isinstance(timeout, (int, float))
+        or timeout <= 0
+        or isinstance(timeout, float) and not math.isfinite(timeout)
+    ):
+        raise ValueError("timeout must be a positive finite number")
+    return timeout
+
+
 class Client:
-    def __init__(self, transport):
+    def __init__(self, transport, timeout=None):
         self._transport = transport
+        self._timeout = _resolve_timeout(timeout, DEFAULT_TIMEOUT)
 
-    def request(self, path):
-        return self._transport.send(path)
+    def request(self, path, timeout=None):
+        timeout = _resolve_timeout(timeout, self._timeout)
+        return self._transport.send(path, timeout=timeout)
diff --git a/tests/test_requirements.py b/tests/test_requirements.py
index 6c65800..106e0f7 100644
--- a/tests/test_requirements.py
+++ b/tests/test_requirements.py
@@ -17,11 +17,12 @@ class RequirementTests(unittest.TestCase):
         transport = Transport()
         client = Client(transport, timeout=3)
         self.assertEqual(client.request("/a", timeout=1.5), 1.5)
-        self.assertEqual(client.request("/b"), 3)
+        self.assertEqual(client.request("/b", timeout=None), 3)
         self.assertEqual(Client(transport).request("/c"), 5.0)
+        self.assertEqual(Client(transport, timeout=None).request("/d"), 5.0)
 
     def test_invalid_explicit_values_do_not_send_or_fallback(self):
-        for value in (0, -1, True, math.nan, math.inf):
+        for value in (0, -1, True, math.nan, math.inf, -math.inf, "1", 1 + 0j):
             with self.subTest(value=value):
                 transport = Transport()
                 client = Client(transport, timeout=2)
@@ -30,7 +31,7 @@ class RequirementTests(unittest.TestCase):
                 self.assertEqual(transport.calls, [])
 
     def test_invalid_client_value_is_rejected(self):
-        for value in (False, 0, float("-inf")):
+        for value in (False, 0, -1, math.nan, math.inf, -math.inf, "1", 1 + 0j):
             with self.subTest(value=value):
                 with self.assertRaises(ValueError):
                     Client(Transport(), timeout=value)
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

タイムアウト設定を追加しました。

- `Client(transport, timeout=None)` に対応
- 優先順位: リクエスト指定 → Client指定 → `5.0`
- 正の有限な `int` / `float` のみ許可し、`bool` や無効値は `ValueError`
- transportへ `send(path, timeout=resolved_timeout)` で渡す
- 既存APIとの互換性を維持

変更: [client.py](<EVAL_WORKSPACE>/client.py)

検証結果:

```text
Ran 4 tests in 0.000s

OK
```

構文検査と `git diff --check` も成功しています。

### Final diff

````diff
diff --git a/client.py b/client.py
index 3528ffe..93a7756 100644
--- a/client.py
+++ b/client.py
@@ -1,6 +1,29 @@
+import math
+
+
 class Client:
-    def __init__(self, transport):
+    DEFAULT_TIMEOUT = 5.0
+
+    def __init__(self, transport, timeout=None):
         self._transport = transport
+        self._timeout = (
+            self.DEFAULT_TIMEOUT if timeout is None else self._validate_timeout(timeout)
+        )
+
+    def request(self, path, timeout=None):
+        resolved_timeout = (
+            self._timeout if timeout is None else self._validate_timeout(timeout)
+        )
+        return self._transport.send(path, timeout=resolved_timeout)
 
-    def request(self, path):
-        return self._transport.send(path)
+    @staticmethod
+    def _validate_timeout(timeout):
+        is_positive_int = (
+            isinstance(timeout, int) and not isinstance(timeout, bool) and timeout > 0
+        )
+        is_positive_finite_float = (
+            isinstance(timeout, float) and math.isfinite(timeout) and timeout > 0
+        )
+        if not (is_positive_int or is_positive_finite_float):
+            raise ValueError("timeout must be a positive finite int or float")
+        return timeout
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

実装しました。

変更内容:

- `Client(transport, timeout=None)` を追加
- `request(path, timeout=None)` を追加
- 優先順位: リクエスト指定 → Client指定 → `5.0`
- 正の有限な `int` / `float` のみ許可し、`bool` や無効値は `ValueError`
- transportへ `send(path, timeout=resolved_timeout)` として伝達
- 既存の呼び出し方との互換性を維持

変更ファイル: [client.py](<EVAL_WORKSPACE>/client.py)

検証結果:

```text
python3 -m unittest discover -s tests

Ran 4 tests in 0.000s
OK
```

構文検査も成功しています。

### Final diff

````diff
diff --git a/client.py b/client.py
index 3528ffe..746cd65 100644
--- a/client.py
+++ b/client.py
@@ -1,6 +1,26 @@
+import math
+
+
+DEFAULT_TIMEOUT = 5.0
+
+
+def _validate_timeout(timeout):
+    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
+        raise ValueError("timeout must be a positive finite number")
+    if timeout <= 0 or (isinstance(timeout, float) and not math.isfinite(timeout)):
+        raise ValueError("timeout must be a positive finite number")
+    return timeout
+
+
 class Client:
-    def __init__(self, transport):
+    def __init__(self, transport, timeout=None):
         self._transport = transport
+        self._timeout = (
+            DEFAULT_TIMEOUT if timeout is None else _validate_timeout(timeout)
+        )
 
-    def request(self, path):
-        return self._transport.send(path)
+    def request(self, path, timeout=None):
+        resolved_timeout = (
+            self._timeout if timeout is None else _validate_timeout(timeout)
+        )
+        return self._transport.send(path, timeout=resolved_timeout)
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

変更内容:

- [client.py](<EVAL_WORKSPACE>/client.py)
  - `Client.request(path, timeout=None)` を追加
  - 優先順位をリクエスト指定 → Client指定 → `5.0` で解決
  - 正の有限な `int` / `float` のみ許可し、`bool` 等は `ValueError`
  - 無効値ではtransportを呼び出さず、フォールバックもしない
  - `transport.send(path, timeout=resolved_timeout)` で転送
  - 既存の呼び出し方と戻り値を維持

検証結果:

- リクエスト値・Client値・既定値: 成功
- 無効なリクエスト値の拒否と送信抑止: 成功
- 無効なClient値の拒否: 成功
- path、戻り値、既存API互換: 成功
- 構文検査: 成功
- Ruff: 未導入、lint設定なし
- 指定コマンド: **4テストすべて成功**

```text
Ran 4 tests in 0.000s

OK
```

### Final diff

````diff
diff --git a/client.py b/client.py
index 3528ffe..47dbeec 100644
--- a/client.py
+++ b/client.py
@@ -1,6 +1,29 @@
+import math
+
+
+_DEFAULT_TIMEOUT = 5.0
+
+
+def _validate_timeout(timeout):
+    if (
+        isinstance(timeout, bool)
+        or not isinstance(timeout, (int, float))
+        or not math.isfinite(timeout)
+        or timeout <= 0
+    ):
+        raise ValueError("timeout must be a positive finite number")
+    return timeout
+
+
 class Client:
-    def __init__(self, transport):
+    def __init__(self, transport, timeout=None):
         self._transport = transport
+        self._timeout = (
+            _DEFAULT_TIMEOUT if timeout is None else _validate_timeout(timeout)
+        )
 
-    def request(self, path):
-        return self._transport.send(path)
+    def request(self, path, timeout=None):
+        resolved_timeout = (
+            self._timeout if timeout is None else _validate_timeout(timeout)
+        )
+        return self._transport.send(path, timeout=resolved_timeout)
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
