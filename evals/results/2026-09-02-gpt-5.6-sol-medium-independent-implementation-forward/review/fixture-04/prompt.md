You are grading six anonymized implementations from an independent forward holdout. Return only the requested structured result.

# User request

# プロフィール保存形式の更新

`workspace/` のプロフィールcodecを、表示名を持つ新形式へ更新してください。

要件:

- `encode(Profile)` は `{"version": 2, "user_id": ..., "display_name": ...}` をJSON化する。
- `Profile` は `user_id` と `display_name` を持つ。新規作成時にdisplay_nameを省略した場合はuser_idを使う。
- `decode` はversion 2を復元する。
- 既存のversion 1 (`{"version":1,"id":...}`) も読み込み、display_nameにはidを使う。
- version欠落、未知version、必須値の欠落または非文字列、空文字列は `InvalidProfile` にする。
- JSON構文エラーも `InvalidProfile` とし、元の例外を外へ漏らさない。
- `Profile("u")` と既存version 1読込の互換性を維持する。

`workspace/` を修正し、workspaceをカレントディレクトリとして `python3 -m unittest discover -s tests` を実行してください。

# Fixture rubric

# Rubric

- S1 (0–2): Profileとencodeがversion 2契約を正確に表現する。2=完全、1=一部、0=新形式なし。
- S2 (0–2): version 1と従来コンストラクタの互換性を維持する。2=完全、1=限定欠落、0=旧データ読込不能。
- S3 (0–2): versionごとのデータ経路を明示的に分け、共通検証・生成へ一貫して合流させる。2=明瞭、1=重複あり、0=曖昧な推測読込。
- S4 (0–2): 構文、version、型、欠落、空文字列をすべてInvalidProfile境界で処理する。2=完全、1=漏れ、0=生例外/誤受理。
- S5 (0–2): 自動テストがv2 round-trip、v1移行、不正入力、回帰を検証し全成功。2=十分、1=部分的、0=失敗/未検証。

Pass=8〜10点かつ0点なし。Borderline=6〜7点、または8点以上でも0点あり。Fail=0〜5点。

Critical failure: version 1を読めない、未知versionを推測で受理する、不正入力から規定外例外を漏らす、検証コマンド失敗。採点は識別子名・回答文ではなくrepositoryの最終差分、挙動、設計境界、検証結果を対象とする。

# Initial repository

### profile_codec.py

````text
import json


class InvalidProfile(Exception):
    pass


class Profile:
    def __init__(self, user_id):
        self.user_id = user_id

    def __eq__(self, other):
        return isinstance(other, Profile) and self.user_id == other.user_id


def encode(profile):
    return json.dumps({"version": 1, "id": profile.user_id}, sort_keys=True)


def decode(raw):
    try:
        data = json.loads(raw)
        if data.get("version") != 1 or not isinstance(data.get("id"), str):
            raise InvalidProfile()
        return Profile(data["id"])
    except (TypeError, ValueError, AttributeError) as error:
        if isinstance(error, InvalidProfile):
            raise
        raise InvalidProfile() from error
````

### tests/test_existing.py

````text
import unittest
from profile_codec import Profile, decode


class ExistingTests(unittest.TestCase):
    def test_reads_v1_profile(self):
        self.assertEqual(decode('{"version": 1, "id": "u1"}'), Profile("u1"))


if __name__ == "__main__":
    unittest.main()
````

### tests/test_requirements.py

````text
import json
import unittest
from profile_codec import InvalidProfile, Profile, decode, encode


class RequirementTests(unittest.TestCase):
    def test_v2_round_trip_and_default_name(self):
        named = Profile("u1", "Ada")
        self.assertEqual(json.loads(encode(named)), {"version": 2, "user_id": "u1", "display_name": "Ada"})
        restored = decode(encode(named))
        self.assertEqual((restored.user_id, restored.display_name), ("u1", "Ada"))
        self.assertEqual(Profile("u2").display_name, "u2")

    def test_migrates_v1(self):
        profile = decode('{"version": 1, "id": "legacy"}')
        self.assertEqual((profile.user_id, profile.display_name), ("legacy", "legacy"))

    def test_rejects_malformed_profiles_with_domain_error(self):
        invalid = [
            "not-json", "[]", "{}", '{"version":3,"id":"x"}',
            '{"version":1,"id":""}', '{"version":1,"id":4}',
            '{"version":2,"user_id":"u"}',
            '{"version":2,"user_id":"","display_name":"n"}',
            '{"version":2,"user_id":"u","display_name":false}',
        ]
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(InvalidProfile):
                decode(raw)


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

プロフィールcodecを新形式へ更新しました。

- [profile_codec.py](<EVAL_WORKSPACE>/profile_codec.py)
  - version 2で`user_id`と`display_name`を保存
  - `Profile("u")`の表示名を`"u"`に設定
  - version 1の読み込み互換を維持
  - 欠落・型不正・空文字・未知versionを`InvalidProfile`化
  - JSON構文エラーの元例外を非公開化

検証結果: `python3 -m unittest discover -s tests` — 4件成功。追加の境界値確認も成功しました。

### Final diff

````diff
diff --git a/profile_codec.py b/profile_codec.py
index b14dcfa..aead4bc 100644
--- a/profile_codec.py
+++ b/profile_codec.py
@@ -6,24 +6,54 @@ class InvalidProfile(Exception):
 
 
 class Profile:
-    def __init__(self, user_id):
+    def __init__(self, user_id, display_name=None):
         self.user_id = user_id
+        self.display_name = user_id if display_name is None else display_name
 
     def __eq__(self, other):
-        return isinstance(other, Profile) and self.user_id == other.user_id
+        return (
+            isinstance(other, Profile)
+            and self.user_id == other.user_id
+            and self.display_name == other.display_name
+        )
 
 
 def encode(profile):
-    return json.dumps({"version": 1, "id": profile.user_id}, sort_keys=True)
+    return json.dumps(
+        {
+            "version": 2,
+            "user_id": profile.user_id,
+            "display_name": profile.display_name,
+        },
+        sort_keys=True,
+    )
 
 
 def decode(raw):
     try:
         data = json.loads(raw)
-        if data.get("version") != 1 or not isinstance(data.get("id"), str):
+    except (TypeError, ValueError):
+        raise InvalidProfile() from None
+
+    if not isinstance(data, dict) or type(data.get("version")) is not int:
+        raise InvalidProfile()
+
+    if data["version"] == 1:
+        user_id = data.get("id")
+        if not isinstance(user_id, str) or not user_id:
             raise InvalidProfile()
-        return Profile(data["id"])
-    except (TypeError, ValueError, AttributeError) as error:
-        if isinstance(error, InvalidProfile):
-            raise
-        raise InvalidProfile() from error
+        return Profile(user_id)
+
+    if data["version"] == 2:
+        user_id = data.get("user_id")
+        display_name = data.get("display_name")
+        if (
+            not isinstance(user_id, str)
+            or not user_id
+            or not isinstance(display_name, str)
+            or not display_name
+        ):
+            raise InvalidProfile()
+        return Profile(user_id, display_name)
+
+    raise InvalidProfile()
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

プロフィールcodecを新形式へ更新しました。

- `Profile`に`display_name`を追加し、省略時は`user_id`を使用
- `encode`をversion 2形式へ変更
- version 1／2の復元に対応
- 欠損、不正型、空文字列、未知version、不正JSONを`InvalidProfile`へ統一
- `Profile("u")`とversion 1の互換性を維持

変更: [profile_codec.py](<EVAL_WORKSPACE>/profile_codec.py:8)

検証結果:

```text
Ran 4 tests in 0.000s

OK
```

`py_compile`と`git diff --check`も成功しています。

### Final diff

````diff
diff --git a/profile_codec.py b/profile_codec.py
index b14dcfa..11e9fad 100644
--- a/profile_codec.py
+++ b/profile_codec.py
@@ -6,24 +6,52 @@ class InvalidProfile(Exception):
 
 
 class Profile:
-    def __init__(self, user_id):
+    def __init__(self, user_id, display_name=None):
         self.user_id = user_id
+        self.display_name = user_id if display_name is None else display_name
 
     def __eq__(self, other):
-        return isinstance(other, Profile) and self.user_id == other.user_id
+        return (
+            isinstance(other, Profile)
+            and self.user_id == other.user_id
+            and self.display_name == other.display_name
+        )
 
 
 def encode(profile):
-    return json.dumps({"version": 1, "id": profile.user_id}, sort_keys=True)
+    return json.dumps(
+        {
+            "version": 2,
+            "user_id": profile.user_id,
+            "display_name": profile.display_name,
+        },
+        sort_keys=True,
+    )
 
 
 def decode(raw):
     try:
         data = json.loads(raw)
-        if data.get("version") != 1 or not isinstance(data.get("id"), str):
-            raise InvalidProfile()
-        return Profile(data["id"])
-    except (TypeError, ValueError, AttributeError) as error:
-        if isinstance(error, InvalidProfile):
-            raise
-        raise InvalidProfile() from error
+    except (TypeError, ValueError):
+        raise InvalidProfile() from None
+
+    if not isinstance(data, dict) or type(data.get("version")) is not int:
+        raise InvalidProfile()
+
+    if data["version"] == 1:
+        user_id = data.get("id")
+        display_name = user_id
+    elif data["version"] == 2:
+        user_id = data.get("user_id")
+        display_name = data.get("display_name")
+    else:
+        raise InvalidProfile()
+
+    if not _is_non_empty_string(user_id) or not _is_non_empty_string(display_name):
+        raise InvalidProfile()
+
+    return Profile(user_id, display_name)
+
+
+def _is_non_empty_string(value):
+    return isinstance(value, str) and bool(value)
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

プロフィールcodecを新形式へ更新しました。

変更内容:

- `Profile(user_id, display_name=None)` を追加し、省略時は `user_id` を使用
- `encode` をversion 2形式へ変更
- `decode` はversion 1・2を共通の`Profile`へ正規化
- version不正、値の欠落・非文字列・空文字列を`InvalidProfile`化
- JSON構文エラーの元例外を外部へ露出しない
- 等価比較に`display_name`を追加
- 継続記録を作成・更新

対象: [profile_codec.py](<EVAL_WORKSPACE>/profile_codec.py:8)

検証結果:

- version 2 encode/decode・表示名省略: 成功
- version 1互換と`Profile("u")`: 成功
- version欠落・未知version: `InvalidProfile`
- 必須値の欠落・非文字列・空文字列: `InvalidProfile`
- JSON構文エラー: `InvalidProfile`、元例外のcauseなし
- `python3 -m unittest discover -s tests`: **4件すべて成功**
- `py_compile`: 成功
- `git diff --check`: 成功

### Final diff

````diff
diff --git a/profile_codec.py b/profile_codec.py
index b14dcfa..3568528 100644
--- a/profile_codec.py
+++ b/profile_codec.py
@@ -6,24 +6,47 @@ class InvalidProfile(Exception):
 
 
 class Profile:
-    def __init__(self, user_id):
+    def __init__(self, user_id, display_name=None):
         self.user_id = user_id
+        self.display_name = user_id if display_name is None else display_name
 
     def __eq__(self, other):
-        return isinstance(other, Profile) and self.user_id == other.user_id
+        return (
+            isinstance(other, Profile)
+            and self.user_id == other.user_id
+            and self.display_name == other.display_name
+        )
 
 
 def encode(profile):
-    return json.dumps({"version": 1, "id": profile.user_id}, sort_keys=True)
+    return json.dumps(
+        {
+            "version": 2,
+            "user_id": profile.user_id,
+            "display_name": profile.display_name,
+        },
+        sort_keys=True,
+    )
 
 
 def decode(raw):
     try:
         data = json.loads(raw)
-        if data.get("version") != 1 or not isinstance(data.get("id"), str):
-            raise InvalidProfile()
-        return Profile(data["id"])
-    except (TypeError, ValueError, AttributeError) as error:
-        if isinstance(error, InvalidProfile):
-            raise
-        raise InvalidProfile() from error
+    except (TypeError, ValueError):
+        raise InvalidProfile() from None
+
+    if not isinstance(data, dict) or type(data.get("version")) is not int:
+        raise InvalidProfile()
+
+    if data["version"] == 1:
+        user_id = display_name = data.get("id")
+    elif data["version"] == 2:
+        user_id = data.get("user_id")
+        display_name = data.get("display_name")
+    else:
+        raise InvalidProfile()
+
+    if not all(isinstance(value, str) and value for value in (user_id, display_name)):
+        raise InvalidProfile()
+
+    return Profile(user_id, display_name)
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

実装完了しました。

変更内容:

- [profile_codec.py](<EVAL_WORKSPACE>/profile_codec.py:8)
  - `Profile(user_id, display_name=None)` を追加
  - 表示名省略時は `user_id` を使用
  - `encode` をversion 2形式へ更新
  - `decode` でv1/v2を共通表現へ正規化
  - 欠落、非文字列、空文字列、不明version、JSONエラーを `InvalidProfile` に統一
- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py:18)
  - v2の各必須値について、欠落・非文字列・空文字列の検証を補強
- [.agent/CONTINUITY.md](<EVAL_WORKSPACE>/.agent/CONTINUITY.md)
  - 変更契約と検証結果を記録

検証結果:

- v2保存・復元、表示名既定値: 成功
- v1読込と `Profile("u")` 互換: 成功
- 全不正入力とJSON構文エラーの拒否: 成功
- `python3 -m unittest discover -s tests`: **4件成功**
- Python構文コンパイル: 成功
- `git diff --check`: 成功

### Final diff

````diff
diff --git a/profile_codec.py b/profile_codec.py
index b14dcfa..3e8f5fe 100644
--- a/profile_codec.py
+++ b/profile_codec.py
@@ -6,24 +6,47 @@ class InvalidProfile(Exception):
 
 
 class Profile:
-    def __init__(self, user_id):
+    def __init__(self, user_id, display_name=None):
         self.user_id = user_id
+        self.display_name = user_id if display_name is None else display_name
 
     def __eq__(self, other):
-        return isinstance(other, Profile) and self.user_id == other.user_id
+        return (
+            isinstance(other, Profile)
+            and self.user_id == other.user_id
+            and self.display_name == other.display_name
+        )
 
 
 def encode(profile):
-    return json.dumps({"version": 1, "id": profile.user_id}, sort_keys=True)
+    return json.dumps(
+        {
+            "version": 2,
+            "user_id": profile.user_id,
+            "display_name": profile.display_name,
+        },
+        sort_keys=True,
+    )
 
 
 def decode(raw):
     try:
         data = json.loads(raw)
-        if data.get("version") != 1 or not isinstance(data.get("id"), str):
-            raise InvalidProfile()
-        return Profile(data["id"])
-    except (TypeError, ValueError, AttributeError) as error:
-        if isinstance(error, InvalidProfile):
-            raise
-        raise InvalidProfile() from error
+    except (TypeError, ValueError):
+        raise InvalidProfile() from None
+
+    if not isinstance(data, dict) or type(data.get("version")) is not int:
+        raise InvalidProfile()
+
+    if data["version"] == 1:
+        user_id = display_name = data.get("id")
+    elif data["version"] == 2:
+        user_id = data.get("user_id")
+        display_name = data.get("display_name")
+    else:
+        raise InvalidProfile()
+
+    if any(not isinstance(value, str) or not value for value in (user_id, display_name)):
+        raise InvalidProfile()
+
+    return Profile(user_id, display_name)
diff --git a/tests/test_requirements.py b/tests/test_requirements.py
index 51af7b6..378b305 100644
--- a/tests/test_requirements.py
+++ b/tests/test_requirements.py
@@ -20,7 +20,10 @@ class RequirementTests(unittest.TestCase):
             "not-json", "[]", "{}", '{"version":3,"id":"x"}',
             '{"version":1,"id":""}', '{"version":1,"id":4}',
             '{"version":2,"user_id":"u"}',
+            '{"version":2,"display_name":"name"}',
+            '{"version":2,"user_id":4,"display_name":"name"}',
             '{"version":2,"user_id":"","display_name":"n"}',
+            '{"version":2,"user_id":"u","display_name":""}',
             '{"version":2,"user_id":"u","display_name":false}',
         ]
         for raw in invalid:
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

実装完了しました。

変更:

- [profile_codec.py](<EVAL_WORKSPACE>/profile_codec.py)
  - `Profile(user_id, display_name=None)`へ更新
  - 省略時は`display_name = user_id`
  - `encode`をversion 2形式へ更新
  - version 1/2を共通内部形式へ正規化して復元
  - 欠落・未知version・非文字列・空文字列・JSONエラーを`InvalidProfile`化
- [test_requirements.py](<EVAL_WORKSPACE>/tests/test_requirements.py)
  - 各必須値の欠落・型違反・空文字列を追加検証

検証結果:

- version 2保存・復元: 成功
- `Profile("u")`の互換性: 成功
- version 1読込と表示名補完: 成功
- 全無効入力の`InvalidProfile`化: 成功
- `python3 -m unittest discover -s tests`: 4件成功
- `py_compile`: 成功
- `git diff --check`: 成功

### Final diff

````diff
diff --git a/profile_codec.py b/profile_codec.py
index b14dcfa..a45d72c 100644
--- a/profile_codec.py
+++ b/profile_codec.py
@@ -6,24 +6,48 @@ class InvalidProfile(Exception):
 
 
 class Profile:
-    def __init__(self, user_id):
+    def __init__(self, user_id, display_name=None):
         self.user_id = user_id
+        self.display_name = user_id if display_name is None else display_name
 
     def __eq__(self, other):
-        return isinstance(other, Profile) and self.user_id == other.user_id
+        return (
+            isinstance(other, Profile)
+            and self.user_id == other.user_id
+            and self.display_name == other.display_name
+        )
 
 
 def encode(profile):
-    return json.dumps({"version": 1, "id": profile.user_id}, sort_keys=True)
+    return json.dumps(
+        {
+            "version": 2,
+            "user_id": profile.user_id,
+            "display_name": profile.display_name,
+        },
+        sort_keys=True,
+    )
 
 
 def decode(raw):
     try:
         data = json.loads(raw)
-        if data.get("version") != 1 or not isinstance(data.get("id"), str):
-            raise InvalidProfile()
-        return Profile(data["id"])
-    except (TypeError, ValueError, AttributeError) as error:
-        if isinstance(error, InvalidProfile):
-            raise
+    except (TypeError, ValueError) as error:
         raise InvalidProfile() from error
+
+    if not isinstance(data, dict) or type(data.get("version")) is not int:
+        raise InvalidProfile()
+
+    if data["version"] == 1:
+        user_id = data.get("id")
+        display_name = user_id
+    elif data["version"] == 2:
+        user_id = data.get("user_id")
+        display_name = data.get("display_name")
+    else:
+        raise InvalidProfile()
+
+    if any(not isinstance(value, str) or not value for value in (user_id, display_name)):
+        raise InvalidProfile()
+
+    return Profile(user_id, display_name)
diff --git a/tests/test_requirements.py b/tests/test_requirements.py
index 51af7b6..cc07c6e 100644
--- a/tests/test_requirements.py
+++ b/tests/test_requirements.py
@@ -17,10 +17,13 @@ class RequirementTests(unittest.TestCase):
 
     def test_rejects_malformed_profiles_with_domain_error(self):
         invalid = [
-            "not-json", "[]", "{}", '{"version":3,"id":"x"}',
+            "not-json", "[]", "{}", '{"version":true,"id":"x"}',
+            '{"version":3,"id":"x"}', '{"version":1}',
             '{"version":1,"id":""}', '{"version":1,"id":4}',
             '{"version":2,"user_id":"u"}',
             '{"version":2,"user_id":"","display_name":"n"}',
+            '{"version":2,"user_id":false,"display_name":"n"}',
+            '{"version":2,"user_id":"u","display_name":""}',
             '{"version":2,"user_id":"u","display_name":false}',
         ]
         for raw in invalid:
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

プロフィールcodecを更新しました。

- [profile_codec.py](<EVAL_WORKSPACE>/profile_codec.py)
  - version 2のencode/decodeに対応
  - `display_name`省略時は`user_id`を使用
  - version 1の読込互換性を維持
  - 必須値・version・JSON構文を厳密に検証
  - JSON例外を外部へ漏らさず`InvalidProfile`へ変換

検証結果:

```text
Ran 4 tests
OK
```

追加の境界値確認、構文解析、`git diff --check`も成功しています。

### Final diff

````diff
diff --git a/profile_codec.py b/profile_codec.py
index b14dcfa..722f538 100644
--- a/profile_codec.py
+++ b/profile_codec.py
@@ -6,24 +6,52 @@ class InvalidProfile(Exception):
 
 
 class Profile:
-    def __init__(self, user_id):
+    def __init__(self, user_id, display_name=None):
         self.user_id = user_id
+        self.display_name = user_id if display_name is None else display_name
 
     def __eq__(self, other):
-        return isinstance(other, Profile) and self.user_id == other.user_id
+        return (
+            isinstance(other, Profile)
+            and self.user_id == other.user_id
+            and self.display_name == other.display_name
+        )
 
 
 def encode(profile):
-    return json.dumps({"version": 1, "id": profile.user_id}, sort_keys=True)
+    return json.dumps(
+        {
+            "version": 2,
+            "user_id": profile.user_id,
+            "display_name": profile.display_name,
+        },
+        sort_keys=True,
+    )
+
+
+def _require_non_empty_string(data, key):
+    value = data.get(key)
+    if not isinstance(value, str) or not value:
+        raise InvalidProfile()
+    return value
 
 
 def decode(raw):
     try:
         data = json.loads(raw)
-        if data.get("version") != 1 or not isinstance(data.get("id"), str):
+        if not isinstance(data, dict):
+            raise InvalidProfile()
+
+        version = data.get("version")
+        if type(version) is not int:
             raise InvalidProfile()
-        return Profile(data["id"])
-    except (TypeError, ValueError, AttributeError) as error:
-        if isinstance(error, InvalidProfile):
-            raise
-        raise InvalidProfile() from error
+        if version == 1:
+            user_id = _require_non_empty_string(data, "id")
+            return Profile(user_id)
+        if version == 2:
+            user_id = _require_non_empty_string(data, "user_id")
+            display_name = _require_non_empty_string(data, "display_name")
+            return Profile(user_id, display_name)
+        raise InvalidProfile()
+    except (TypeError, ValueError):
+        raise InvalidProfile() from None
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
