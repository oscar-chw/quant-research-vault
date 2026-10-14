# Node 11 — Reject invalid path strings and prevent unsupported long-title evidence

plan: vault-pr
gate: `../_venvs/qrv/bin/python -m pytest -q && ../_venvs/qrv/bin/python -m ruff check . && ../_venvs/qrv/bin/python -m ruff format --check . && ../_venvs/qrv/bin/python -m mypy && python3 ../tools/scan_history.py --since origin/main . && python3 ../tools/check_overlap.py . && git diff --check`
ctx: shared_notes.py,docs/shared-notes.md

## Summary 2026-10-14T19:52:05Z — local author (identity omitted)

Hosted review5523650730/f946: twoactualP2s invalidNULpath andtitle-prefixmissingterm. New4cases3FAIL1PASS before;4PASS0.93s after, including loader/report/CLI/MCP, root-invalid-path and512-char valid-titlecontrol. Invalidpath ValueError translated while deliberate SharedNotesError preserves original specificreason. Methodtitles>512 Unicodechars refused sofulltitle fits existingv1windowshape; original3shorttitles/pins unchanged. Two source mutantsKILLED withsame-rungreencontrol. Source lint/format/mypyPASS, original137testfiles unchanged; full requiredgate follows.

## Attempt 2026-10-14T19:52:41Z — local author (identity omitted) — 6s — exit 0

```
........................................................................ [ 51%]
.....................................................................    [100%]
141 passed in 4.83s
All checks passed!
46 files already formatted
Success: no issues found in 14 source files
.: clean
overlap: PASS (0 file(s))
```
