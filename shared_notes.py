"""Load and search the vault's public, hash-pinned original method notes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

DEFAULT_SHARED_NOTES_ROOT = Path(__file__).parent / "notes"
MANIFEST_NAME = "manifest.json"
SCHEMA = "quant-shared-notes/v1"
MAX_SOURCE_BYTES = 256 * 1024
MAX_TITLE_CHARS = 512
REPORT_SCHEMA = "quant-shared-search-report/v1"
VERIFICATION_SCHEMA = "quant-shared-search-verification/v1"
MAX_REPORT_BYTES = 1024 * 1024
MAX_QUERY_BYTES = 16 * 1024
QUERY_STOPWORDS = frozenset(
    "a an and are as at be by can do does for from how i in is it of on or the to was what when where which with".split()
)


class SharedNotesError(ValueError):
    """A safe, actionable failure while reading the shared-note manifest."""

    def __init__(self, message: str, *, code: str = "INVALID_EVIDENCE"):
        super().__init__(message)
        self.code = code


def _valid_source_ref(ref: Any) -> bool:
    if not isinstance(ref, dict) or not all(
        isinstance(ref.get(key), str) and ref[key].strip()
        for key in ("uri", "kind", "revision")
    ):
        return False
    try:
        return bool(urlsplit(ref["uri"]).scheme)
    except ValueError:
        return False


def _load_shared_snapshot(
    root: str | Path = DEFAULT_SHARED_NOTES_ROOT,
    *,
    expected_manifest_sha256: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Validate the manifest and return its verified method-note envelopes."""
    if expected_manifest_sha256 is not None and (
        not isinstance(expected_manifest_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", expected_manifest_sha256)
    ):
        raise SharedNotesError("manifest pin must be a lowercase SHA256 digest")
    try:
        vault_root = Path(root).resolve()
    except (OSError, RuntimeError, ValueError):
        raise SharedNotesError("vault root could not be resolved") from None
    manifest_path = vault_root / MANIFEST_NAME
    try:
        with manifest_path.open("rb") as manifest_file:
            manifest_bytes = manifest_file.read(MAX_SOURCE_BYTES + 1)
    except FileNotFoundError:
        raise SharedNotesError("manifest not found") from None
    except OSError:
        raise SharedNotesError("manifest could not be read") from None
    if len(manifest_bytes) > MAX_SOURCE_BYTES:
        raise SharedNotesError("manifest exceeds 256 KiB limit")

    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if expected_manifest_sha256 and manifest_sha256 != expected_manifest_sha256:
        raise SharedNotesError("manifest SHA256 mismatch", code="MANIFEST_CHANGED")
    try:
        manifest = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=_unique_report_fields,
            parse_constant=_reject_report_constant,
        )
        # Escaped surrogates and overflowing numbers can decode but cannot form
        # finite UTF-8 JSON metadata for the note consumer or report CLI.
        json.dumps(manifest, allow_nan=False, ensure_ascii=False).encode("utf-8")
    except (ValueError, RecursionError):
        raise SharedNotesError("invalid manifest: expected UTF-8 JSON") from None
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema") != SCHEMA
        or not isinstance(manifest.get("revision"), str)
        or not manifest["revision"].strip()
        or not isinstance(manifest.get("documents"), list)
    ):
        raise SharedNotesError("invalid manifest schema or revision")

    results = []
    seen_ids = set()
    for entry in manifest["documents"]:
        if not isinstance(entry, dict):
            raise SharedNotesError("invalid document entry")
        document_id = entry.get("id")
        if not isinstance(document_id, str) or not document_id.strip():
            raise SharedNotesError("invalid document id")
        if document_id in seen_ids:
            raise SharedNotesError(f"duplicate document id: {document_id}")
        seen_ids.add(document_id)
        if entry.get("document_type") != "method_note":
            raise SharedNotesError(f"unsupported document type for {document_id}")
        title = entry.get("title")
        source_path = entry.get("path")
        source_sha256 = entry.get("sha256")
        source_refs = entry.get("source_refs")
        rights = entry.get("rights")
        if (
            not isinstance(title, str)
            or not title.strip()
            or not isinstance(source_path, str)
            or not source_path
            or Path(source_path).is_absolute()
            or not isinstance(source_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", source_sha256)
            or not isinstance(source_refs, list)
            or not source_refs
            or not all(_valid_source_ref(ref) for ref in source_refs)
            or not isinstance(rights, dict)
        ):
            raise SharedNotesError(f"invalid metadata for {document_id}")
        if len(title) > MAX_TITLE_CHARS:
            raise SharedNotesError(f"title exceeds 512 character limit: {document_id}")
        basis = rights.get("basis")
        if (
            not isinstance(rights.get("license"), str)
            or not rights["license"].strip()
            or not isinstance(basis, str)
            or basis not in {"original", "original_summary"}
            or rights.get("redistribution") != "public"
        ):
            raise SharedNotesError(
                f"document {document_id} lacks declared public original rights"
            )

        try:
            source = (vault_root / source_path).resolve()
            if not source.is_relative_to(vault_root):
                raise SharedNotesError(f"source path escapes vault root: {document_id}")
            if not source.exists():
                raise SharedNotesError(
                    f"source file unavailable: {document_id}"
                ) from None
            if not source.is_file():
                raise SharedNotesError(f"source is not a regular file: {document_id}")
            with source.open("rb") as source_file:
                source_bytes = source_file.read(MAX_SOURCE_BYTES + 1)
        except SharedNotesError:
            raise
        except (OSError, RuntimeError, ValueError):
            raise SharedNotesError(f"source file unavailable: {document_id}") from None
        if len(source_bytes) > MAX_SOURCE_BYTES:
            raise SharedNotesError(f"source exceeds 256 KiB limit: {document_id}")
        if hashlib.sha256(source_bytes).hexdigest() != source_sha256:
            raise SharedNotesError(
                f"source SHA256 mismatch: {document_id}", code="SOURCE_CHANGED"
            )
        try:
            document = source_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise SharedNotesError(f"source is not UTF-8: {document_id}") from None

        results.append(
            {
                "document_id": document_id,
                "document_type": "method_note",
                "title": title,
                "document": document,
                "source_sha256": source_sha256,
                "manifest_sha256": manifest_sha256,
                "source_refs": source_refs,
                "rights": rights,
            }
        )
    return manifest_sha256, results


def load_shared_notes(
    root: str | Path = DEFAULT_SHARED_NOTES_ROOT,
    *,
    expected_manifest_sha256: str | None = None,
) -> list[dict[str, Any]]:
    """Return the unchanged v1 envelopes from one verified manifest snapshot."""
    return _load_shared_snapshot(
        root, expected_manifest_sha256=expected_manifest_sha256
    )[1]


def search_shared_notes(
    query: str,
    *,
    root: str | Path = DEFAULT_SHARED_NOTES_ROOT,
    limit: int = 5,
    expected_manifest_sha256: str | None = None,
) -> list[dict[str, Any]]:
    """Rank method notes by matching query terms in title and verified text."""
    if not isinstance(query, str):
        raise SharedNotesError("query must be text")
    if type(limit) is not int or not 0 <= limit <= 20:
        raise SharedNotesError("limit must be an integer between 0 and 20")
    notes = load_shared_notes(root, expected_manifest_sha256=expected_manifest_sha256)
    terms = set(re.findall(r"\w+", query.casefold()))
    if not terms:
        return []
    ranked = []
    for note in notes:
        haystack = set(
            re.findall(r"\w+", f"{note['title']} {note['document']}".casefold())
        )
        score = len(terms & haystack) / len(terms)
        if score:
            ranked.append((score, note))
    ranked.sort(key=lambda item: (-item[0], item[1]["document_id"]))
    return [note for _, note in ranked[: max(0, limit)]]


def _folded_word_spans(text: str) -> list[tuple[str, int, int]]:
    """Tokenize folded text, mapping length-changing folds to original offsets."""
    original_positions = []
    for index, char in enumerate(text):
        original_positions.extend([index] * len(char.casefold()))
    return [
        (
            match.group(),
            original_positions[match.start()],
            original_positions[match.end() - 1] + 1,
        )
        for match in re.finditer(r"\w+", text.casefold())
    ]


def _evidence_windows(
    note: dict[str, Any], terms: set[str]
) -> tuple[list[dict[str, Any]], bool]:
    windows: list[dict[str, Any]] = []
    truncated = False
    document_terms = {
        term for term, _start, _end in _folded_word_spans(note["document"])
    }
    title_needed = bool(terms - document_terms)
    source_window_limit = 2 if title_needed else 3
    for number, line in enumerate(note["document"].splitlines(), start=1):
        matches = [
            start for term, start, _end in _folded_word_spans(line) if term in terms
        ]
        if not matches:
            continue
        if len(windows) == source_window_limit:
            truncated = True
            break
        # Offsets refer to original Unicode text, never a length-changing casefolded copy.
        start = max(0, matches[0] - 96)
        end = min(len(line), start + 512)
        windows.append(
            {
                "kind": "source_text",
                "line": number,
                "start_char": start,
                "end_char": end,
                "text": line[start:end],
            }
        )
        truncated |= start > 0 or end < len(line)
    if title_needed or not windows:
        title = note["title"]
        windows.append({"kind": "manifest_title", "text": title[:512]})
        truncated |= len(title) > 512
    return windows, truncated


def search_shared_notes_report(
    query: object,
    *,
    root: str | Path = DEFAULT_SHARED_NOTES_ROOT,
    limit: int = 5,
    expected_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Report literal query coverage and exact evidence, without changing legacy search."""
    result: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "query": query if isinstance(query, str) else None,
        "query_terms": [],
        "status": "error",
        "manifest_sha256": None,
        "expected_manifest_sha256": expected_manifest_sha256,
        "results": [],
        "total_matches": 0,
        "truncated": False,
        "partial_reasons": [],
        "error": None,
    }
    if not isinstance(query, str):
        result["error"] = {"code": "INVALID_QUERY", "message": "query must be text"}
        return result
    try:
        too_large = (
            len(query) > MAX_QUERY_BYTES or len(query.encode("utf-8")) > MAX_QUERY_BYTES
        )
    except UnicodeEncodeError:
        result["query"] = None
        result["error"] = {
            "code": "INVALID_QUERY",
            "message": "query must be UTF-8 text",
        }
        return result
    if too_large:
        result["query"] = None
        result["error"] = {
            "code": "QUERY_TOO_LARGE",
            "message": "query exceeds 16 KiB UTF-8 limit",
        }
        return result
    terms = {term for term, _start, _end in _folded_word_spans(query)} - QUERY_STOPWORDS
    result["query_terms"] = sorted(terms)
    if not terms:
        result["error"] = {
            "code": "INVALID_QUERY",
            "message": "query must contain a term beyond punctuation and function words",
        }
        return result
    if type(limit) is not int or not 1 <= limit <= 20:
        result["error"] = {
            "code": "INVALID_LIMIT",
            "message": "limit must be an integer between 1 and 20",
        }
        return result
    try:
        manifest_hash, notes = _load_shared_snapshot(
            root, expected_manifest_sha256=expected_manifest_sha256
        )
    except SharedNotesError as exc:
        result["status"] = (
            "stale" if exc.code in {"MANIFEST_CHANGED", "SOURCE_CHANGED"} else "error"
        )
        result["error"] = {"code": exc.code, "message": str(exc)}
        return result
    result["manifest_sha256"] = manifest_hash
    ranked = []
    for note in notes:
        present = {
            term
            for term, _start, _end in _folded_word_spans(
                f"{note['title']} {note['document']}"
            )
        }
        matched = terms & present
        if not matched:
            continue
        evidence, evidence_truncated = _evidence_windows(note, matched)
        missing = terms - present
        hit = {
            key: note[key]
            for key in (
                "document_id",
                "document_type",
                "title",
                "source_sha256",
                "manifest_sha256",
                "source_refs",
                "rights",
            )
        }
        hit.update(
            match_status="partial" if missing else "matched",
            matched_terms=sorted(matched),
            missing_terms=sorted(missing),
            term_coverage=len(matched) / len(terms),
            evidence=evidence,
            evidence_truncated=evidence_truncated,
        )
        ranked.append(hit)
    ranked.sort(key=lambda hit: (-hit["term_coverage"], hit["document_id"]))
    result["total_matches"] = len(ranked)
    result["results"] = ranked[:limit]
    result["truncated"] = len(ranked) > limit
    if not ranked:
        result["status"] = "no_match"
        return result
    if ranked[0]["missing_terms"]:
        result["partial_reasons"].append("query_terms")
    if result["truncated"]:
        result["partial_reasons"].append("limit")
    result["status"] = "partial" if result["partial_reasons"] else "matched"
    # Match the CLI's actual UTF-8 output including its trailing newline, so
    # the saved file also fits the verifier's existing 1 MiB read bound.
    if (
        len(json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8")) + 1
        > MAX_REPORT_BYTES
    ):
        result.update(
            status="error",
            results=[],
            total_matches=0,
            truncated=False,
            partial_reasons=[],
            error={
                "code": "REPORT_TOO_LARGE",
                "message": "report exceeds 1 MiB serialized limit",
            },
        )
    return result


def _verification_error(
    code: str, message: str, *, status: str = "error"
) -> dict[str, Any]:
    return {
        "schema": VERIFICATION_SCHEMA,
        "status": status,
        "manifest_sha256": None,
        "report_sha256": None,
        "document_ids": [],
        "replay_limit": None,
        "error": {"code": code, "message": message},
    }


def _canonical_report(report: object) -> bytes:
    # Serialized comparison distinguishes JSON booleans/numbers that Python equality conflates.
    return json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _citations_match_sources(hits: list[Any], notes: list[dict[str, Any]]) -> bool:
    """Reconstruct source evidence directly, without calling the report producer."""
    indexed = {note["document_id"]: note for note in notes}
    seen = set()
    for hit in hits:
        if not isinstance(hit, dict):
            return False
        identifier = hit.get("document_id")
        if (
            not isinstance(identifier, str)
            or identifier not in indexed
            or identifier in seen
        ):
            return False
        seen.add(identifier)
        note = indexed[identifier]
        for key in (
            "document_id",
            "document_type",
            "title",
            "source_sha256",
            "manifest_sha256",
            "source_refs",
            "rights",
        ):
            if _canonical_report(hit.get(key)) != _canonical_report(note[key]):
                return False
        evidence = hit.get("evidence")
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= 3:
            return False
        lines = note["document"].splitlines()
        for window in evidence:
            if not isinstance(window, dict):
                return False
            if window.get("kind") == "manifest_title":
                if (
                    set(window) != {"kind", "text"}
                    or window["text"] != note["title"][:512]
                ):
                    return False
            elif window.get("kind") == "source_text":
                if set(window) != {"kind", "line", "start_char", "end_char", "text"}:
                    return False
                number, start, end = (
                    window["line"],
                    window["start_char"],
                    window["end_char"],
                )
                if any(type(value) is not int for value in (number, start, end)):
                    return False
                if not 1 <= number <= len(lines):
                    return False
                line = lines[number - 1]
                if not 0 <= start < end <= len(line) or end - start > 512:
                    return False
                if window["text"] != line[start:end]:
                    return False
            else:
                return False
    return True


def verify_shared_notes_report(
    report: object, *, root: str | Path = DEFAULT_SHARED_NOTES_ROOT
) -> dict[str, Any]:
    """Reproduce a saved v1 response against its pinned sources and current lexical policy."""
    if not isinstance(report, dict):
        return _verification_error("INVALID_REPORT", "report must be a JSON object")
    try:
        encoded = _canonical_report(report)
    except (TypeError, ValueError, RecursionError):
        return _verification_error(
            "INVALID_REPORT", "report must contain finite JSON values"
        )
    if len(encoded) > MAX_REPORT_BYTES:
        return _verification_error("REPORT_TOO_LARGE", "report exceeds 1 MiB limit")
    if report.get("schema") != REPORT_SCHEMA or report.get("status") not in (
        "matched",
        "partial",
        "no_match",
    ):
        return _verification_error(
            "INVALID_REPORT", "expected a source-backed v1 retrieval report"
        )
    pin = report.get("manifest_sha256")
    if not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{64}", pin):
        return _verification_error(
            "INVALID_REPORT", "report must record its manifest SHA256"
        )
    original_pin = report.get("expected_manifest_sha256")
    if original_pin is not None and original_pin != pin:
        return _verification_error(
            "REPORT_MISMATCH", "declared input pin conflicts with report corpus"
        )
    hits = report.get("results")
    if not isinstance(hits, list) or len(hits) > 20:
        return _verification_error(
            "INVALID_REPORT", "results must be an array of at most 20 notes"
        )
    try:
        _, notes = _load_shared_snapshot(root, expected_manifest_sha256=pin)
    except SharedNotesError as exc:
        return _verification_error(
            exc.code,
            str(exc),
            status="stale"
            if exc.code in {"MANIFEST_CHANGED", "SOURCE_CHANGED"}
            else "error",
        )
    try:
        citations_match = _citations_match_sources(hits, notes)
    except (TypeError, ValueError, RecursionError):
        return _verification_error(
            "INVALID_EVIDENCE", "source metadata is not finite UTF-8 JSON"
        )
    if not citations_match:
        return _verification_error(
            "REPORT_MISMATCH", "citations do not reconstruct from the pinned sources"
        )
    # v1 records returned hits but not the requested limit; validate the visible response cap.
    replay_limit = max(1, len(hits))
    reproduced = search_shared_notes_report(
        report.get("query"), root=root, limit=replay_limit, expected_manifest_sha256=pin
    )
    if reproduced["error"]:
        return _verification_error(
            reproduced["error"]["code"],
            reproduced["error"]["message"],
            status=reproduced["status"],
        )
    # An originally unpinned lookup is verified with the actual digest it recorded.
    reproduced["expected_manifest_sha256"] = original_pin
    if _canonical_report(reproduced) != encoded:
        return _verification_error(
            "REPORT_MISMATCH",
            "report does not reproduce its pinned sources and current v1 policy",
        )
    return {
        "schema": VERIFICATION_SCHEMA,
        "status": "verified",
        "manifest_sha256": pin,
        "report_sha256": hashlib.sha256(encoded).hexdigest(),
        "document_ids": [hit["document_id"] for hit in reproduced["results"]],
        "replay_limit": replay_limit,
        "error": None,
    }


def _unique_report_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _reject_report_constant(_value: str) -> None:
    raise ValueError("nonfinite JSON value")


def verify_shared_notes_report_file(
    path: str | Path, *, root: str | Path = DEFAULT_SHARED_NOTES_ROOT
) -> dict[str, Any]:
    """Bound reads and reject ambiguous JSON before source verification."""
    try:
        with Path(path).open("rb") as file:
            raw = file.read(MAX_REPORT_BYTES + 1)
    except OSError:
        return _verification_error(
            "REPORT_UNAVAILABLE", "report file could not be read"
        )
    if len(raw) > MAX_REPORT_BYTES:
        return _verification_error(
            "REPORT_TOO_LARGE", "report file exceeds 1 MiB limit"
        )
    try:
        report = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_report_fields,
            parse_constant=_reject_report_constant,
        )
    except (ValueError, RecursionError):
        return _verification_error(
            "INVALID_REPORT", "report must be unambiguous finite UTF-8 JSON"
        )
    return verify_shared_notes_report(report, root=root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Trace literal matches to verified original method notes."
    )
    parser.add_argument("query", nargs="?")
    parser.add_argument(
        "--verify-report",
        type=Path,
        metavar="JSON",
        help="Verify a saved retrieval report",
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_SHARED_NOTES_ROOT)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--manifest-sha256")
    args = parser.parse_args()
    if args.verify_report is not None:
        if (
            args.query is not None
            or args.limit is not None
            or args.manifest_sha256 is not None
        ):
            parser.error(
                "--verify-report uses saved report fields; do not also supply query, limit or manifest pin"
            )
        response = verify_shared_notes_report_file(args.verify_report, root=args.root)
    elif args.query is not None:
        response = search_shared_notes_report(
            args.query,
            root=args.root,
            limit=args.limit if args.limit is not None else 5,
            expected_manifest_sha256=args.manifest_sha256,
        )
    else:
        parser.error("provide a query or --verify-report JSON")
    print(json.dumps(response, ensure_ascii=False, indent=2))
    raise SystemExit(1 if response["status"] in {"stale", "error"} else 0)
