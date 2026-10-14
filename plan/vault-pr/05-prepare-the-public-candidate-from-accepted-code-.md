# Node 5 — Prepare the public candidate from accepted code, verify quality and privacy

plan: vault-pr
gate: `../_venvs/qrv/bin/python -m pytest -q && ../_venvs/qrv/bin/python -m ruff check . && ../_venvs/qrv/bin/python -m ruff format --check . && ../_venvs/qrv/bin/python -m mypy && python3 ../tools/scan_history.py --since origin/main . && python3 ../tools/check_overlap.py . && git diff --check`
ctx: README.md,docs/release-review.md

## Summary 2026-10-14T18:15:31Z — local author (identity omitted)

Public-base candidate preserves accepted branch and all historical failures. Independent Codex review found ambiguous/nonfinite/unencodable manifest metadata; additive4-case witness failed before strict JSON/UTF8 parser repair and passed after, including realCLI and restoration. Original120tests/corpus/21other baselinepins unchanged. Historical metadata is labelled; public copies omit machine identifiers while raw records remain local. Full unchanged quality/history/overlap gate follows on committed candidate.
