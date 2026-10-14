# Node 14 — Repair uncited-term reports and invalid saved-report paths

plan: vault-pr
gate: `../_venvs/qrv/bin/python -m pytest -q && ../_venvs/qrv/bin/python -m ruff check . && ../_venvs/qrv/bin/python -m ruff format --check . && ../_venvs/qrv/bin/python -m mypy && python3 ../tools/scan_history.py --since origin/main . && python3 ../tools/check_overlap.py . && git diff --check`
ctx: shared_notes.py,docs/retrieval-report.md,docs/saved-report-verification.md

## Summary 2026-10-14T20:21:40Z — local author (identity omitted)

Hosted577 uncovered-term and saved-path findings reproduced8FAIL2PASS. Distinct uncovered-term windows retain3x512citation budget; unrepresentable claims refused EVIDENCE_LIMIT after existing output-size priority. Independent pinned-span coverage rejects replay-agreeing uncited claims; invalid file paths structured REPORT_UNAVAILABLE. Same-run10PASS with3mutantsKILLED. Initial mypy required covered:set[str]; implementation annotation corrected, no check edits.

## Attempt 2026-10-14T20:21:45Z — local author (identity omitted) — 5s — exit 1

```
........................................................................ [ 45%]
........................................................................ [ 90%]
................                                                         [100%]
160 passed in 4.52s
All checks passed!
unformatted: File would be reformatted
   --> shared_notes.py:285:33
    |
284 |     truncated = any(
    -         window["start_char"] > 0
    -         or window["end_char"] < len(lines[window["line"] - 1])
285 +         window["start_char"] > 0 or window["end_char"] < len(lines[window["line"] - 1])
286 |         for window in windows
    |

1 file would be reformatted, 51 files already formatted
```

## Attempt 2026-10-14T20:22:22Z — local author (identity omitted) — 6s — exit 0

```
........................................................................ [ 45%]
........................................................................ [ 90%]
................                                                         [100%]
160 passed in 4.66s
All checks passed!
52 files already formatted
Success: no issues found in 14 source files
.: clean
overlap: PASS (0 file(s))
```
