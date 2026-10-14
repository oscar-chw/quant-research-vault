# Shared method notes

The optional `search_shared_notes` MCP tool and the CLI read the same
`notes/manifest.json` and its referenced files. They do not use the ChromaDB
paper index. Notes are returned with `document_type: method_note`, never as
arXiv papers. The manifest SHA256 is checked when a caller supplies a pin.

Each `quant-shared-notes/v1` manifest has a non-empty `revision` and a
`documents` list. Every entry has a stable unique `id`, type `method_note`,
title, notes-relative path, lowercase SHA256, source references and rights.
The loader requires a regular in-root source file whose bytes match the hash
and decode as UTF-8. The manifest and each document are limited to 256 KiB.
Rights must declare a license, an `original` or
`original_summary` basis, and public redistribution.
Duplicate JSON fields, non-finite numbers and metadata that cannot be emitted as
UTF-8 JSON are invalid manifests. Conflicting repeated rights fields are refused,
not resolved by choosing the last value.

Use the CLI against the checkout's pinned corpus:

```bash
python search_mcp.py --shared-note quant-pit-cutoffs-v1 \
  --manifest-sha256 c15abda5657cc63a953c7d8b8d34f044f0b6dcad09c253a0b9842e5beea4c70a
python search_mcp.py --shared-query "point in time"
```

In MCP, call `search_shared_notes` with a query; `manifest_sha256` is an
optional exact pin. Paper search remains available as `search_papers`.

Malformed manifests, missing or modified source files, path escapes, stale
pins, and non-public or non-original rights fail with explicit safe errors.
An empty search result remains an empty result.

The server uses the MCP Python SDK 2.3 callback API; the dependency is bounded to
the compatible major version. See the [official low-level server documentation](https://py.sdk.modelcontextprotocol.io/v2/advanced/low-level-server/).

Without a caller-supplied manifest pin, checks establish consistency with the
current local manifest; they do not authenticate an earlier approved corpus.
Reproducible research runs must supply and retain the expected manifest digest.

Explicit empty CLI values still select their requested mode: `--shared-query ''`
prints an empty result, and `--shared-note ''` reports a missing document ID.
They never fall through to server startup.
