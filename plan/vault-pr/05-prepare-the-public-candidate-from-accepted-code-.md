# Node 5 — Prepare the public candidate from accepted code, verify quality and privacy

plan: vault-pr
gate: `../_venvs/qrv/bin/python -m pytest -q && ../_venvs/qrv/bin/python -m ruff check . && ../_venvs/qrv/bin/python -m ruff format --check . && ../_venvs/qrv/bin/python -m mypy && python3 ../tools/scan_history.py --since origin/main . && python3 ../tools/check_overlap.py . && git diff --check`
ctx: README.md,docs/release-review.md

## Summary 2026-10-14T18:15:31Z — local author (identity omitted)

Public-base candidate preserves accepted branch and all historical failures. Independent Codex review found ambiguous/nonfinite/unencodable manifest metadata; additive4-case witness failed before strict JSON/UTF8 parser repair and passed after, including realCLI and restoration. Original120tests/corpus/21other baselinepins unchanged. Historical metadata is labelled; public copies omit machine identifiers while raw records remain local. Full unchanged quality/history/overlap gate follows on committed candidate.

## Attempt 2026-10-14T18:17:20Z — local author (identity omitted) — 67s — exit 1

```
........................................................................ [ 58%]
.......................F.........................F..                     [100%]
=================================== FAILURES ===================================
____________ test_original_corpus_and_checks_remain_byte_identical _____________

    def test_original_corpus_and_checks_remain_byte_identical():
        baseline = json.loads(
            (
                ROOT / "docs/evidence/retrieval-report-2026-10-14/preserved-controls.json"
>           ).read_text()
              ^^^^^^^^^^^
        )

test_saved_report.py:357: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
<python-runtime>/lib/python3.11/pathlib.py:1058: in read_text
    with self.open(mode='r', encoding=encoding, errors=errors) as f:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = PosixPath('<workspace>/docs/evidence/retrieval-report-2026-10-14/preserved-controls.json')
mode = 'r', buffering = -1, encoding = 'locale', errors = None, newline = None

    def open(self, mode='r', buffering=-1, encoding=None,
             errors=None, newline=None):
        """
        Open the file pointed by this path and return a file object, as
        the built-in open() function does.
        """
        if "b" not in mode:
            encoding = io.text_encoding(encoding)
>       return io.open(self, mode, buffering, encoding, errors, newline)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       FileNotFoundError: [Errno 2] No such file or directory: '<workspace>/docs/evidence/retrieval-report-2026-10-14/preserved-controls.json'

<python-runtime>/lib/python3.11/pathlib.py:1044: FileNotFoundError
__________________ test_legacy_queries_remain_exactly_495f0d4 __________________

    def test_legacy_queries_remain_exactly_495f0d4():
        baseline = json.loads(
            (
                ROOT / "docs/evidence/retrieval-report-2026-10-14/legacy-495f0d4.json"
>           ).read_text()
              ^^^^^^^^^^^
        )

test_shared_report.py:149: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
<python-runtime>/lib/python3.11/pathlib.py:1058: in read_text
    with self.open(mode='r', encoding=encoding, errors=errors) as f:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = PosixPath('<workspace>/docs/evidence/retrieval-report-2026-10-14/legacy-495f0d4.json')
mode = 'r', buffering = -1, encoding = 'locale', errors = None, newline = None

    def open(self, mode='r', buffering=-1, encoding=None,
             errors=None, newline=None):
        """
        Open the file pointed by this path and return a file object, as
        the built-in open() function does.
        """
        if "b" not in mode:
            encoding = io.text_encoding(encoding)
>       return io.open(self, mode, buffering, encoding, errors, newline)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       FileNotFoundError: [Errno 2] No such file or directory: '<workspace>/docs/evidence/retrieval-report-2026-10-14/legacy-495f0d4.json'

<python-runtime>/lib/python3.11/pathlib.py:1044: FileNotFoundError
=========================== short test summary info ============================
FAILED test_saved_report.py::test_original_corpus_and_checks_remain_byte_identical
FAILED test_shared_report.py::test_legacy_queries_remain_exactly_495f0d4 - Fi...
2 failed, 122 passed in 59.73s
```

## Summary 2026-10-14T18:18:25Z — local author (identity omitted)

First full public-candidate gate failed2tests/122passed because packaging omitted legacy-495f0d4.json and preserved-controls.json required by unchanged compatibility assertions. Restored both exact original fixture bytes from preservedfa346f8. Original test files remain byte-identical; no test/gate/assertion change. Removed only an accidental extra blank line in the new public red-output copy, retaining its raw bytes locally. Failed full gate remains recorded; corrected packaging rerun follows.
