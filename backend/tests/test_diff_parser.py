from app.diff_parser import parse_diff, chunk_files, detect_language, render_for_prompt

MULTI_FILE_DIFF = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,2 +1,3 @@
 import os
+print("hi")
 x = 1
diff --git a/widget.tsx b/widget.tsx
--- a/widget.tsx
+++ b/widget.tsx
@@ -1,1 +1,2 @@
 const a = 1;
+const b = 2;
"""

NEW_FILE_DIFF = """diff --git a/new.py b/new.py
new file mode 100644
--- /dev/null
+++ b/new.py
@@ -0,0 +1,2 @@
+def foo():
+    return 1
"""

DELETED_FILE_DIFF = """diff --git a/old.py b/old.py
deleted file mode 100644
--- a/old.py
+++ /dev/null
@@ -1,1 +0,0 @@
-x = 1
"""

LOCKFILE_DIFF = """diff --git a/package-lock.json b/package-lock.json
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,1 +1,1 @@
-{}
+{"a": 1}
"""

BINARY_DIFF = """diff --git a/logo.png b/logo.png
new file mode 100644
Binary files /dev/null and b/logo.png differ
"""


def test_parses_all_files():
    files = parse_diff(MULTI_FILE_DIFF)
    assert [f.path for f in files] == ["app.py", "widget.tsx"]


def test_language_detection():
    assert detect_language("a.py") == "python"
    assert detect_language("a.js") == "javascript"
    assert detect_language("a.java") == "java"
    assert detect_language("a.txt") is None


def test_typescript_detected_and_reviewable():
    files = parse_diff(MULTI_FILE_DIFF)
    tsx = files[1]
    assert tsx.language == "typescript"
    assert tsx.reviewable is True


def test_line_numbers_for_added_lines():
    files = parse_diff(MULTI_FILE_DIFF)
    app = files[0]
    assert app.added_line_numbers == {2}


def test_skips_lockfiles_and_binaries():
    lock = parse_diff(LOCKFILE_DIFF)[0]
    binary = parse_diff(BINARY_DIFF)[0]
    assert lock.reviewable is False
    assert binary.is_binary is True
    assert binary.reviewable is False


def test_new_and_deleted_file_flags():
    new_file = parse_diff(NEW_FILE_DIFF)[0]
    deleted_file = parse_diff(DELETED_FILE_DIFF)[0]
    assert new_file.is_new is True
    assert deleted_file.is_deleted is True
    assert deleted_file.reviewable is False


def test_chunking_splits_on_budget():
    files = parse_diff(MULTI_FILE_DIFF)
    size = len(render_for_prompt(files[0]))
    chunks = chunk_files(files, max_chars=size)
    assert len(chunks) == 2
    assert chunks[0] == [files[0]]
    assert chunks[1] == [files[1]]


def test_chunking_keeps_all_in_one_when_budget_is_large():
    files = parse_diff(MULTI_FILE_DIFF)
    chunks = chunk_files(files, max_chars=10_000)
    assert len(chunks) == 1
    assert len(chunks[0]) == 2


def test_empty_diff():
    assert parse_diff("") == []
    assert chunk_files([], max_chars=1000) == []
