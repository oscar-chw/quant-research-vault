# Review the shared-note interfaces

This PR carries the accepted note-reader, lexical-report and saved-report verifier
into the public checkout. The paper-ingestion pipeline remains a separate workflow.
No paper corpus, vector index, private lecture material or model result is bundled.

## Try a complete offline workflow

From the repository root, no installed third-party dependencies are needed for
these commands:

```bash
python3 -S shared_notes.py "PCA training" \
  --manifest-sha256 c15abda5657cc63a953c7d8b8d34f044f0b6dcad09c253a0b9842e5beea4c70a > pca-report.json
python3 -S shared_notes.py --verify-report pca-report.json
python3 -S shared_notes.py "how do I price options"
python3 -S shared_notes.py "PCA banana"
```

The saved PCA report verifies with two document IDs. The options query has no
matching effective terms. The last query reports the supported PCA term and the
unsupported `banana` term. Edit a quoted excerpt in the saved report: verification
returns `REPORT_MISMATCH` and exit 1. Restore the original report: it verifies
again. These are source and policy checks over the three original notes.

## What remains compatible

The `quant-shared-notes/v1` manifest and existing `search_shared_notes` envelope
retain their fields, rights, references and digests. The report and verifier are
separate opt-in interfaces. Existing paper tools remain available over MCP;
their compatibility is covered by the original search tests. Optional consumers
can continue to pin the manifest and read selected notes directly without importing
this repository's code. Changing a consumer's experiment or approval workflow
belongs in that consumer's repo.

The notes are original summaries with declared MIT rights, not copies of the
upstream papers, course lectures or book text. References identify provenance;
the report excerpts quote the local summary. Hash verification does not prove
source truth, legal authenticity, semantic relevance or upstream freshness.

## Evidence and preserved failures

- [Accepted baseline hashes](evidence/public-note-interfaces-2026-10-15/accepted-source.json)
  record the locally reviewed 22 source, test, configuration and note files.
  Historical root checks passed 120 tests, lint, format and types. The public
  candidate keeps 21 pins; its manifest parser has a separate reviewed repair:
  [candidate delta](evidence/public-note-interfaces-2026-10-15/candidate-delta.json).
- [Fixed retrieval controls](evidence/public-note-interfaces-2026-10-15/retrieval-controls.json)
  and [retrieval mutants](evidence/public-note-interfaces-2026-10-15/retrieval-mutants.json)
  exercise partial, absent, stale and bounded evidence behavior.
- [Same-run verification controls](evidence/public-note-interfaces-2026-10-15/verification-controls.json)
  compare valid reports with altered quotes, citations, outcome and JSON types.
  [Verifier mutants](evidence/public-note-interfaces-2026-10-15/verification-mutants.json)
  were killed by named behavior assertions; their target functions remain unchanged.
- [Malformed-manifest refusal and restoration](evidence/public-note-interfaces-2026-10-15/manifest-recovery.json)
  exercises actual CLI errors and recovery without changing runtime limits.
- [Preserved failures](evidence/public-note-interfaces-2026-10-15/preserved-failures.json)
  record the earlier negative results and raw receipt digests. Machine-specific
  histories stay on the original local branches; those branches were not rewritten.
- [PR review finding and causal repair](evidence/public-note-interfaces-2026-10-15/manifest-review-repair.json)
  records four failing manifest cases before the repair, then passing loader,
  report API, CLI and restoration controls. Duplicate rights keys, non-finite
  numbers and unencodable Unicode metadata are refused rather than emitted.
  [Original regression output](evidence/public-note-interfaces-2026-10-15/manifest-review-red.log)
  remains intact. Original tests and runtime limits were unchanged.

These historical checks apply to their recorded code hashes. The PR's CI checks
the full published candidate using the unchanged [quality workflow](../.github/workflows/quality.yml).
CI success applies to the checked revision; it is not merge approval.

Hosted review also found a Unicode token/excerpt mismatch and symlink-loop errors:
[recorded findings and initial regression/control](evidence/public-note-interfaces-2026-10-15/hosted-review-findings.json).
The report now maps case-folded word spans back to original Unicode character
offsets before quoting. Path resolution failures become explicit invalid-evidence
results, including source and root loops. These follow-up changes require their
own final hosted review and CI; the earlier parser acceptance remains scoped.

The next hosted review found missing title evidence in mixed title/body matches,
successful reports larger than the verifier can admit, and empty explicit shared
CLI options selecting server mode. The
[causal regression receipt](evidence/public-note-interfaces-2026-10-15/hosted-contract-edges-red.json)
preserves seven failures and two controls before repair. Nine cases now pass;
[four source mutants](evidence/public-note-interfaces-2026-10-15/contract-mutation-controls.json)
isolate missing title evidence, relaxed query/output bounds and the wrong CLI mode.
The CLI witness blocks server entry before lock acquisition, so no live service
is started during verification. Earlier findings remain recorded.

The CLI's file reader stops at 1 MiB plus one byte before rejecting oversized
reports. This is a disk-read bound, not a total memory cap. The v1 search report
does not record the caller's requested result limit: replay derives and reports
its visible-result cap. Verification cannot authenticate an author or report time.
No general retrieval quality, token savings, predictive result or alpha is claimed.

The next review isolated invalid path strings and title matches outside the
512-character prefix. The [negative receipt](evidence/public-note-interfaces-2026-10-15/late-path-title-red.json)
records three failures and a maximum-length title control. Invalid source/root
path strings now return explicit errors. Method-note titles are limited to 512
Unicode characters; complete title evidence keeps the existing v1 shape. Current
three-note manifests/pins remain unchanged. [Source mutants](evidence/public-note-interfaces-2026-10-15/late-path-title-controls.json)
verify both failure classes; their old negative results remain available.

Invalid pin inputs are omitted from error output so unencodable or opaque values
do not break UTF-8 JSON. [Negative cases](evidence/public-note-interfaces-2026-10-15/pin-error-red.json)
and a [same-run mutant/control](evidence/public-note-interfaces-2026-10-15/pin-error-controls.json)
retain the proof; valid and stale expected hashes preserve their prior behavior.
