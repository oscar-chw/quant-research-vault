# Node 12 — Reject and omit invalid pins before error serialization

plan: vault-pr
gate: `../_venvs/qrv/bin/python -m pytest -q && ../_venvs/qrv/bin/python -m ruff check . && ../_venvs/qrv/bin/python -m ruff format --check . && ../_venvs/qrv/bin/python -m mypy && python3 ../tools/scan_history.py --since origin/main . && python3 ../tools/check_overlap.py . && git diff --check`
ctx: shared_notes.py

## Summary 2026-10-14T20:00:50Z — local author (identity omitted)

Direct UTF8errorprobe reproduced invalidpin echo notencodable. Three additivecases3FAIL before;3PASS0.02s after. Invalidpin gate nowreturnsINVALID_EVIDENCE with expectedpinNone, preserving all valid/stalepin behavior. Same-run greencontrol/echo-invalid-pin source mutantKILLED. Original141testfiles andnotes unchanged; full requiredgate follows. No new assertion edits or permissive serialization.
