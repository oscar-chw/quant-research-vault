# Verify a saved retrieval report against its sources

User: a researcher retaining a query-to-source report for review or reuse. Input:
an existing quant-shared-search-report/v1 JSON report and the pinned original note
corpus. Output: a quant-shared-search-verification/v1 result, with verified, stale
or error status and safe reason. Practical value: refuse an altered quote, citation,
rights record, missing/extra result or misleading outcome before it is reused.

This successor preserves accepted7a157bc. Existing reports/consumer envelopes and
their CLI remain unchanged. New library: verify_shared_notes_report(report, root=notes).
New opt-in CLI: python shared_notes.py --verify-report REPORT.json [--root NOTES].
New read-only MCP tool: verify_shared_notes_report with an object-valued report.

## Acceptance before implementation

1. Valid matched/partial/no_match reports verify against the exact source manifest.
   An unpinned query still records its actual manifest digest, which verification pins.
2. Altered quote, line/character location, source digest/reference, rights, query
   terms, coverage, ranking/results, status, truncation or unknown fields fail.
   Compare JSON types strictly: false/0 and true/1 are distinct.
3. Changed source bytes or a changed manifest produce stale with no admitted results;
   missing/unreadable/invalid corpus produces error, never a successful empty lookup.
4. A report originally marked stale/error is not a valid source-backed retrieval report.
5. CLI reads at most1MiB+1bytes before parsing; reject oversize, malformed UTF-8/JSON,
   duplicate JSON keys, nonfinite numbers, excessive nesting and non-object input.
   Error messages reveal neither file contents nor provider diagnostics.
6. Real CLI/library/MCP normal and negative paths agree; valid report restored after
   a failure verifies again. All original67tests and corpus bytes remain intact.

The verifier first reconstructs citations directly from the pinned source text
and manifest metadata, independently of the report producer. It then replays the
existing v1 lexical policy and compares the complete typed report with the reproduced
result. A producer and verifier agreeing on the same bad quote is insufficient.
v1 does not store the requested result limit;
the replay cap is derived from the number returned (minimum1). This checks the
visible response and truncation claim; it does not reconstruct an unrecorded request
parameter. Output states the replay cap. Source loading retains all existing rights,
hash, UTF-8 and path checks. The reported query is data, never an executable instruction.

The verifier establishes consistency with the caller's pinned local corpus and
current v1 policy. It cannot authenticate the report's author/time, prove source
claims true, recover missing sources, certify upstream currency or establish semantic
relevance. A fully recomputed report for a different query is another valid report.
No model/index/network call, corpus ingestion or persistent service is required.

## Use the actual CLI

```bash
python3 -S shared_notes.py "PCA training" \
  --manifest-sha256 c15abda5657cc63a953c7d8b8d34f044f0b6dcad09c253a0b9842e5beea4c70a > pca-report.json
python3 -S shared_notes.py --verify-report pca-report.json
```

Output includes status verified, the same manifest digest, document IDs
quant-pca-fit-state-v1 / quant-ols-validation-v1, the canonical report digest and
replay_limit2. Canonical digest ignores JSON formatting/key order; it does not
authenticate an author or preserve the original file's whitespace bytes.

Edit an evidence window in the saved file and rerun: exit1, status error,
code REPORT_MISMATCH. Restore the report and rerun: exit0/verified. Changed note
bytes or a mismatched manifest produce stale; missing or invalid report paths use REPORT_UNAVAILABLE;
oversized files use REPORT_TOO_LARGE; invalid UTF-8/JSON, repeated keys, nonfinite
numbers and excessive nesting use INVALID_REPORT. Messages omit input contents.
Malformed source metadata uses INVALID_EVIDENCE; it is never admitted as verified.
Source reconstruction also checks complete matched-term coverage independently of
policy replay. A reproducible selection that omits a claimed term is refused.

The library canonicalizes caller-supplied objects before checking encoded size;
the1MiB bound on disk reads applies to the file/CLI path, not total process RSS or
already allocated Python objects. Verification holds returned-result order and
JSON value types fixed. An originally unpinned query is pinned to its recorded
manifest for verification. A no-match report can verify with zero document IDs.
The optional MCP tool takes an object-valued report; verified returns normally,
stale/error are tool errors. MCP retains its existing server startup dependencies.

Evaluation: fixed valid report plus single-field broken copies in the same run;
an independent quote reconstruction and source-digest oracle; stale/missing corpus;
strict input and failure/recovery controls. No performance or general retrieval-quality
claim. Stop for an actual guard refusal or genuinely wrong check; preserve every failure.
