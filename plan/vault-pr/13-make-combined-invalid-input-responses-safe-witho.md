# Node 13 — Make combined-invalid-input responses safe without changing error precedence

plan: vault-pr
gate: `../_venvs/qrv/bin/python -m pytest -q && ../_venvs/qrv/bin/python -m ruff check . && ../_venvs/qrv/bin/python -m ruff format --check . && ../_venvs/qrv/bin/python -m mypy && python3 ../tools/scan_history.py --since origin/main . && python3 ../tools/check_overlap.py . && git diff --check`
ctx: shared_notes.py

## Summary 2026-10-14T20:12:25Z — local author (identity omitted)

Root577combined-invalid-error receipt reproduced3failures; expanded5invalidcases+validpincontrol5FAIL1PASS before. Safe echoedpin nowcomputed atresultinitialization, preserving query/limit/UTF8/oversizeerror precedence and validpin echo. Combined6+priorpin3PASS0.04s, source mutationKILLED. No assertion/gate/precedence changes; original144checks/notes unchanged. Full requiredgate follows.

## Attempt 2026-10-14T20:16:24Z — local author (identity omitted) — 6s — exit 0

```
........................................................................ [ 48%]
........................................................................ [ 96%]
......                                                                   [100%]
150 passed in 4.84s
All checks passed!
50 files already formatted
Success: no issues found in 14 source files
.: clean
overlap: PASS (0 file(s))
```
