# Node 8 — Repair hosted Unicode-span and symlink-loop findings with causal boundary controls

plan: vault-pr
gate: `../_venvs/qrv/bin/python -m pytest -q && ../_venvs/qrv/bin/python -m ruff check . && ../_venvs/qrv/bin/python -m ruff format --check . && ../_venvs/qrv/bin/python -m mypy && python3 ../tools/scan_history.py --since origin/main . && python3 ../tools/check_overlap.py . && git diff --check`
ctx: shared_notes.py,docs/release-review.md

## Summary 2026-10-14T18:49:41Z — local author (identity omitted)

Hosted review5522830959 at6f57773 found twoP2s. New additive witness initially3FAIL/1PASS (Unicode boundary plus source/root loop failures; Straße control passed). Product repair uses one span-aware folded-word policy and guarded path resolution. After repair Unicode2PASS and loader/report/realCLI loop checks reached successful assertions; new MCP fixture then fails AttributeError because its monkeypatch incorrectly targets a nonexistent top-level module attribute. Prepared one-field target correction in logs/hosted-mcp-binding-proposal.patch; every original check/criterion retained. Root confirms wrong-check decision must come directly from human; correction UNAPPLIED. Source Ruff format applied/mypyPASS; full node8 gate and push/re-review held, no acceptance claim. Current nativegoalACTIVE; main stays4631b6b/publicPRhead6f57773 unchanged.

## Summary 2026-10-14T18:52:46Z — local author (identity omitted)

Direct human approved exact one-field newMCPfixture targetcorrection; approved patchBBC713...applied without any assertion/injection change. Four new Unicode/source-root-loop controls nowPASS across loader/report/realCLI/MCP; original published tests and note bytes remain exact6f57773. Prior3FAIL1PASS plus wrongfixture2FAIL2PASS retained; no othercheckchange. Source guards and single span-awarefoldedword policy implemented. Focusedlint/format/mypyPASS; required full node8 gate follows after committing source and privacy-safe evidence.

## Attempt 2026-10-14T18:55:23Z — local author (identity omitted) — 5s — exit 0

```
........................................................................ [ 56%]
........................................................                 [100%]
128 passed in 3.28s
All checks passed!
41 files already formatted
Success: no issues found in 14 source files
.: clean
overlap: PASS (0 file(s))
```
