## goal: Finalise the accepted vault note interfaces through a review branch, Codex review, pull request and CI pinned to its head; main stays held

Done-condition: `plan gate vault-pr 7` requires the PR head to equal the local HEAD and its remote checks to pass. Local quality, privacy and independent Codex source review must pass first. Merge remains held.

- [x] 1. Analyse: what is actually being asked, and what would prove it done | gate: phase-check.py vault-pr analysis
      2026-10-14T18:07:33Z exit 0 in 0s [7b91752d] — phase analysis: OK (130 words)
- [x] 2. Research: what ALREADY solves this, prior art, unknowns resolved or deferred | needs: 1 | gate: phase-check.py vault-pr research
      2026-10-14T18:07:33Z exit 1 in 0s [4edd2ebc] — PHASE GATE FAILED — `## research` cites 1 concrete sources / what to do: name at least two specific things you read — a URL, a file, a command and its output. `existing: none applicable` still has to say WHAT you checked, and those names count as sources.
      2026-10-14T18:07:58Z exit 0 in 0s [163b9570] — phase research: OK (106 words)
- [x] 3. Plan, with acceptance tests written before any implementation | needs: 2 | gate: phase-check.py vault-pr plan
      2026-10-14T18:07:34Z exit 0 in 0s [37ead372] — phase plan: OK (139 words)
- [x] 4. Finalise: scope, gates and done-condition agreed | needs: 3 | gate: grep -q '^APPROVED' plan/vault-pr.md
      2026-10-14T18:07:34Z exit 0 in 0s [da39a3ee] — (no output)

<!-- Implementation nodes go below; each declares needs: 4 so no code starts
     before scope is agreed. Every node needs a gate. Mark anything with an
     irreversible effect `risk: irreversible` and the orchestrator will hold it
     for a human instead of running it unattended. -->

- [x] 5. Prepare the public candidate from accepted code, verify quality and privacy | needs: 4 | ctx: README.md,docs/release-review.md | owner: codex-vault-pr | gate: ../_venvs/qrv/bin/python -m pytest -q && ../_venvs/qrv/bin/python -m ruff check . && ../_venvs/qrv/bin/python -m ruff format --check . && ../_venvs/qrv/bin/python -m mypy && python3 ../tools/scan_history.py --since origin/main . && python3 ../tools/check_overlap.py . && git diff --check
      2026-10-14T18:17:20Z exit 1 in 67s [3b177b43] — FAILED test_saved_report.py::test_original_corpus_and_checks_remain_byte_identical / FAILED test_shared_report.py::test_legacy_queries_remain_exactly_495f0d4 - Fi... / 2 failed, 122 passed in 59.73s
      2026-10-14T18:18:31Z exit 0 in 5s [665d2d44] — Success: no issues found in 14 source files / .: clean / overlap: PASS (0 file(s))
- [x] 6. Record independent Codex review of the public implementation diff | needs: 5 | ctx: docs/release-review.md | owner: codex-vault-pr | gate: test -s review/vault-pr.md && grep -q '^VERDICT: ADVANCE' review/vault-pr.md
      2026-10-14T18:19:44Z exit 0 in 0s [da39a3ee] — (no output)
- [x] 7. Open the review PR and verify successful remote CI at the exact final head | needs: 6 | ctx: docs/release-review.md | owner: codex-vault-pr | gate: test "$(gh pr view codex/vault-pr-20261015 --repo oscar-chw/quant-research-vault --json headRefOid --jq .headRefOid)" = "$(git rev-parse HEAD)" && gh pr checks codex/vault-pr-20261015 --repo oscar-chw/quant-research-vault
      2026-10-14T18:23:59Z exit 0 in 2s [6cbe285e] — test pass 39s https://github.com/oscar-chw/quant-research-vault/actions/runs/38614448277/job/116025810396

## analysis

Oscar requested that the GitHub repositories be finalised through a PR and CI,
with no direct push to main. The vault's accepted local implementation includes
three original method notes, compatible note consumers, traceable lexical search
reports and saved-report verification. The public base predates those interfaces.
The accepted branch also contains machine-specific evidence paths, which must not
be published. Its history and every failed check stay intact locally; a separate
review branch starts from the existing public base and copies the accepted source
and tests. This changes publication packaging, not the approved implementation.

done when: the unchanged quality suite, public-range privacy scan and independent
Codex source review pass; a PR is attached and its passing remote checks are bound
to the exact final head. No merge or public-main acceptance is inferred.

## research

existing: inspected public main4631b6b, accepted source8bfa47e and final handoff
fa346f8; README.md, .github/workflows/quality.yml, docs/shared-notes.md,
test_quality.py, test_shared_report.py and test_saved_report.py; original120-test suite,
three-note manifest, prior source/tampering/mutation controls and root acceptance.
GitHub currently has no open vault PR. The existing quality workflow already runs
on pull requests, so its controls need no change. Production-code, standards and
verify-before-done skills are in use. The existing privacy scanner rejected the
accepted history with nine machine-path findings; that red result is retained.
Code and source hashes will be compared with the accepted checkpoint. Only
publishable evidence summaries and presentation need preparation. Existing source
consumers remain in their owning repos; their claims need source-linked scope.

## plan

Copy accepted runtime, tests, dependency bounds and original note bytes to a new
branch from public main. Preserve the completed local retrieval plan on its
accepted branch. Refresh stale README release language and expose concrete offline
inputs, outputs and limits. Reuse accepted controls; do not rerun expensive work.
Run the unchanged suite and the privacy scanner on committed candidate history.
Obtain an independent Codex review of the public implementation diff, then push
only the review branch, create and attach a draft PR, and check CI against its
head. Record failures exactly and repair causes, with no check changes. Stop at
the reviewable PR; Oscar's review precedes any merge.

APPROVED 2026-10-15 Oscar via root coordination: "Use a PR and CI; no direct main push". This approves review-branch publication and PR creation, not merge, deployment, visibility changes or private evidence publication.

## Hosted review follow-up

Root accepted the scoped manifest parser repair at6f57773, preserving its original
124-test and exact-head CI receipts. Hosted review5522830959 at that same head
found two P2 defects: folded Unicode token boundaries could disagree with evidence
spans, and symlink-loop resolution could escape bounded errors. Both findings
require causal regressions and implementation repair; original tests and notes
remain immutable. The local source-review milestone above does not mean hosted
review completed without findings. Keep the PR draft and retain both findings.

Hosted review5523196482 at e92e172 found three further P2 defects: mixed title/body
evidence omitted title-only terms, successful report production could exceed the
verifier's size bound, and empty explicit shared CLI options could start server
mode. Node9 stays open. Repair these actual contract failures, preserving the
earlier128-test result and all previous findings.

Hosted review5523650730 at f946531 added two actual P2s: NUL source paths escape
as ValueError, and title-prefix clipping can omit the title-only matched term.
The previous oversize-query thread remains historical, already repaired. Preserve
the137-test gate and fix the two new contract gaps without changing citation shape.

Direct error-serialization probing found invalid manifest pins echo unencodable
strings/opaque values. Preserve the141-test gate and make this error path safe.
- [x] 12. Reject and omit invalid pins before error serialization | needs: 11 | ctx: shared_notes.py | owner: codex-vault-pr | gate: ../_venvs/qrv/bin/python -m pytest -q && ../_venvs/qrv/bin/python -m ruff check . && ../_venvs/qrv/bin/python -m ruff format --check . && ../_venvs/qrv/bin/python -m mypy && python3 ../tools/scan_history.py --since origin/main . && python3 ../tools/check_overlap.py . && git diff --check
      2026-10-14T20:01:30Z exit 0 in 8s [f08458a4] — Success: no issues found in 14 source files / .: clean / overlap: PASS (0 file(s))

- [x] 11. Reject invalid path strings and prevent unsupported long-title evidence | needs: 10 | ctx: shared_notes.py,docs/shared-notes.md | owner: codex-vault-pr | gate: ../_venvs/qrv/bin/python -m pytest -q && ../_venvs/qrv/bin/python -m ruff check . && ../_venvs/qrv/bin/python -m ruff format --check . && ../_venvs/qrv/bin/python -m mypy && python3 ../tools/scan_history.py --since origin/main . && python3 ../tools/check_overlap.py . && git diff --check
      2026-10-14T19:52:41Z exit 0 in 6s [a5007d7b] — Success: no issues found in 14 source files / .: clean / overlap: PASS (0 file(s))

- [x] 10. Repair mixed-title evidence, producer budgets and explicit-empty CLI routing | needs: 8 | ctx: shared_notes.py,search_mcp.py,docs/release-review.md | owner: codex-vault-pr | gate: ../_venvs/qrv/bin/python -m pytest -q && ../_venvs/qrv/bin/python -m ruff check . && ../_venvs/qrv/bin/python -m ruff format --check . && ../_venvs/qrv/bin/python -m mypy && python3 ../tools/scan_history.py --since origin/main . && python3 ../tools/check_overlap.py . && git diff --check
      2026-10-14T19:31:52Z exit 0 in 7s [3a84fd71] — Success: no issues found in 14 source files / .: clean / overlap: PASS (0 file(s))

- [x] 8. Repair hosted Unicode-span and symlink-loop findings with causal boundary controls | needs: 7 | ctx: shared_notes.py,docs/release-review.md | owner: codex-vault-pr | gate: ../_venvs/qrv/bin/python -m pytest -q && ../_venvs/qrv/bin/python -m ruff check . && ../_venvs/qrv/bin/python -m ruff format --check . && ../_venvs/qrv/bin/python -m mypy && python3 ../tools/scan_history.py --since origin/main . && python3 ../tools/check_overlap.py . && git diff --check
      2026-10-14T18:55:23Z exit 0 in 5s [79886841] — Success: no issues found in 14 source files / .: clean / overlap: PASS (0 file(s))
- [>] 9. Finish hosted review and refreshed exact-head PR checks, retaining earlier findings | needs: 8 | ctx: docs/release-review.md | owner: codex-vault-pr | lease: 2026-10-14T18:58:19Z | gate: test -s logs/vault-hosted-final.json && test "$(gh pr view codex/vault-pr-20261015 --repo oscar-chw/quant-research-vault --json headRefOid --jq .headRefOid)" = "$(git rev-parse HEAD)" && gh pr checks codex/vault-pr-20261015 --repo oscar-chw/quant-research-vault
