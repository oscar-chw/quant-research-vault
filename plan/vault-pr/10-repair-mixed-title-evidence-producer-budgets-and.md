# Node 10 — Repair mixed-title evidence, producer budgets and explicit-empty CLI routing

plan: vault-pr
gate: `../_venvs/qrv/bin/python -m pytest -q && ../_venvs/qrv/bin/python -m ruff check . && ../_venvs/qrv/bin/python -m ruff format --check . && ../_venvs/qrv/bin/python -m mypy && python3 ../tools/scan_history.py --since origin/main . && python3 ../tools/check_overlap.py . && git diff --check`
ctx: shared_notes.py,search_mcp.py,docs/release-review.md

## Summary 2026-10-14T19:31:44Z — local author (identity omitted)

Hosted review5523196482/e92 found3P2s: mixed-title evidence, unverifiable oversize producer output, falsey emptyCLI options startingserver. Nine new cases reproduced7FAIL2PASS; now9PASS1.57s. Four targeted source mutants killed with same-run greencontrol; server witness blocks entry before lock acquisition. Implemented titlewindowreservationwithin3,16KiB UTF8query admission/no invalidecho, actual prettyUTF8report+newline1MiBbudget, and presence-based emptyCLI mode selection. Only case displayIDs shortened for readable diagnostics; assertions/inputvalues unchanged. Source format/lint/mypyPASS. Original128tests/notes preserved; full required gate follows after committed publication-safe evidence.
