# Traceable shared-note retrieval report

Status: local implementation passes the full offline quality gate and real MCP
path. Root approved the one-field correction to a newly authored test; the original
failure is retained. Root later accepted7a157bc for the scoped67tests/format/types.
Release controls remain in force; saved-report verification is a separate successor.

The report is additive. Existing load_shared_notes/search_shared_notes, MCP
search_shared_notes and its CLI retain their495f0d4 contracts and corpus bytes.
New library function: shared_notes.search_shared_notes_report(query, root=notes,
limit=5, expected_manifest_sha256=None). New stdlib-only CLI: python shared_notes.py
QUERY [--root PATH] [--limit N] [--manifest-sha256 HEX]. New MCP tool:
search_shared_notes_report with query/limit/manifest_sha256.

Output schema: quant-shared-search-report/v1. Status is matched when at least one
note covers every effective literal query term and no eligible note is omitted;
partial when only some terms match or limit omits eligible notes; no_match when
the valid corpus has no matching note; stale on exact manifest/source hash mismatch;
error on invalid input, unavailable or malformed evidence. stale/error have no
results and make CLI exit1 / MCP isError true. no_match is a valid query and exit0.

English function words are discarded using a fixed published set. Other terms
match exactly, case-insensitively; no stemming, synonym, semantic or answer-quality
claim. Results are ordered by literal term coverage then stable document ID.
Limits are1..20. Partial results identify missing terms and output truncation.

Each result keeps document_id/type, title, original rights, source/manifest hashes
and immutable upstream source_refs. Bounded evidence windows quote exact original
note text with one-based line numbers and zero-based character offsets. At most
three windows per note,512characters per window; omitted matching lines/text are
declared. Title-only matches explicitly cite manifest metadata, not source text.
Upstream source_refs are provenance for the original summary, not fetched/verified
new upstream lines. No model calls, paper/index access or writes occur during a query.

The frozen cases include PCA/training, unsupported options pricing, a partial query,
no match, truncated results, exact excerpt reconstruction, malformed/missing/stale
evidence and real CLI/MCP interfaces. These are functional query-to-source controls
over three checked original summaries, not a retrieval benchmark.

## Reproduce a query-to-source result

```bash
python3 shared_notes.py "PCA training" \
  --manifest-sha256 c15abda5657cc63a953c7d8b8d34f044f0b6dcad09c253a0b9842e5beea4c70a
```

The first result is `quant-pca-fit-state-v1`, with both `pca` and `training`
matched. Its citation retains source SHA256
`80909971fff591ec83115ab252ed10c300cf86c24d47bf56eb7ae9e83eb748ff` and
the manifest digest. An evidence window points to the original summary at
line4, including the training-only transform rule. Reconstruct any window
as `document.splitlines()[line - 1][start_char:end_char]` from the verified
note returned by `load_shared_notes`. The quote's source is the original
summary; `source_refs` retains its immutable public-code provenance.

```bash
python3 shared_notes.py "PCA banana"           # partial; missing_terms: ["banana"]
python3 shared_notes.py "how do I price options"  # no_match; results: []
python3 shared_notes.py "training" --limit 1  # partial; truncated: true
python3 shared_notes.py "PCA" --manifest-sha256 0000000000000000000000000000000000000000000000000000000000000000
# stale; results: []; exit1. Verify the expected corpus before updating a pin.
```

The new MCP tool accepts the same query/limit/pin fields. `stale` and `error`
are explicit tool errors; valid no-match or partial retrieval is not a transport
failure. The legacy tool and its envelopes remain available for current consumers.

Stopwords: `a an and are as at be by can do does for from how i in is it of on
or the to was what when where which with`. An empty effective query is an error;
it is not a request to return every note. Input limit is1..20. No corpus is fetched,
index opened or model called by the library or the report CLI.

Queries are limited to 16 KiB of UTF-8 before tokenization. Oversized input returns
`QUERY_TOO_LARGE`; invalid Unicode returns `INVALID_QUERY`. Both omit the raw query
and evidence. Successful reports also fit the verifier's existing 1 MiB budget,
including the report CLI's UTF-8 JSON formatting and trailing newline. Aggregate
metadata/result copies that exceed it return `REPORT_TOO_LARGE` with no results.
This is a serialized-output bound, not a total memory bound.

When any matched term occurs only in the manifest title, the report includes a
labelled `manifest_title` excerpt alongside document windows. It reserves room
within the existing three-window limit and discloses omitted document windows.
