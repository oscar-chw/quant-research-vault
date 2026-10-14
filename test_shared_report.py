"""Fixed-source retrieval, citation reconstruction and real interface acceptance."""

from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import Client

import search_mcp
import shared_notes
from test_quality import _shared_note_fixture

PIN = "c15abda5657cc63a953c7d8b8d34f044f0b6dcad09c253a0b9842e5beea4c70a"
ROOT = Path(__file__).parent


def report(query, **kwargs):
    function = getattr(shared_notes, "search_shared_notes_report", None)
    assert callable(function), "traceable shared-note report is absent"
    return function(query, **kwargs)


@pytest.mark.parametrize(
    "query,status,first_id,missing",
    [
        ("availability", "matched", "quant-pit-cutoffs-v1", []),
        ("PCA training", "matched", "quant-pca-fit-state-v1", []),
        ("PCA banana", "partial", "quant-pca-fit-state-v1", ["banana"]),
        ("how do I price options", "no_match", None, []),
        ("zirconium", "no_match", None, []),
    ],
)
def test_fixed_source_queries_disclose_coverage(query, status, first_id, missing):
    result = report(query, expected_manifest_sha256=PIN)
    assert result["schema"] == "quant-shared-search-report/v1"
    assert result["status"] == status
    assert result["manifest_sha256"] == PIN
    assert result["error"] is None
    if first_id:
        first = result["results"][0]
        assert first["document_id"] == first_id
        assert first["missing_terms"] == missing
        assert set(first["matched_terms"] + first["missing_terms"]) == set(
            result["query_terms"]
        )
    else:
        assert result["results"] == [] and result["total_matches"] == 0


def test_every_quote_reconstructs_from_verified_source():
    notes = {n["document_id"]: n for n in shared_notes.load_shared_notes()}
    result = report("training data cutoff costs", expected_manifest_sha256=PIN)
    assert result["results"]
    for hit in result["results"]:
        note = notes[hit["document_id"]]
        assert hit["source_sha256"] == note["source_sha256"]
        assert hit["source_refs"] == note["source_refs"]
        assert hit["rights"] == note["rights"]
        assert hit["document_type"] == "method_note"
        assert 0 < len(hit["evidence"]) <= 3
        for excerpt in hit["evidence"]:
            assert excerpt["kind"] == "source_text"
            line = note["document"].splitlines()[excerpt["line"] - 1]
            assert excerpt["text"] == line[excerpt["start_char"] : excerpt["end_char"]]
            assert len(excerpt["text"]) <= 512


def test_limit_discloses_omitted_matches():
    result = report("training", limit=1)
    assert result["total_matches"] == 2
    assert len(result["results"]) == 1
    assert result["truncated"] is True and result["status"] == "partial"
    assert "limit" in result["partial_reasons"]


def test_long_unicode_lines_are_bounded_and_citable(tmp_path):
    text = "審" * 800 + " cutoff " + "查" * 800
    root, _, _ = _shared_note_fixture(tmp_path, text=text)
    result = report("cutoff", root=root)
    hit = result["results"][0]
    snippet = hit["evidence"][0]
    assert len(snippet["text"]) <= 512 and "cutoff" in snippet["text"]
    assert snippet["text"] == text[snippet["start_char"] : snippet["end_char"]]
    assert hit["evidence_truncated"] is True


def test_title_only_match_cites_metadata_not_invented_source_lines(tmp_path):
    root, _, _ = _shared_note_fixture(tmp_path, text="A bounded original note.")
    result = report("point time", root=root)
    snippet = result["results"][0]["evidence"][0]
    assert snippet["kind"] == "manifest_title"
    assert snippet["text"] == "Point in time method"
    assert "line" not in snippet


@pytest.mark.parametrize("query", [None, 42, "", "...", "the and in"])
def test_invalid_or_content_free_query_is_an_error(query):
    result = report(query)
    assert result["status"] == "error" and result["results"] == []
    assert result["error"]["code"] == "INVALID_QUERY"


@pytest.mark.parametrize("limit", [0, -1, True, 1.5, "3", 21])
def test_invalid_limit_is_an_error(limit):
    result = report("PCA", limit=limit)
    assert result["status"] == "error" and result["results"] == []
    assert result["error"]["code"] == "INVALID_LIMIT"


@pytest.mark.parametrize(
    "mutation,status",
    [("pin", "stale"), ("source", "stale"), ("missing", "error"), ("rights", "error")],
)
def test_bad_evidence_never_becomes_no_match_or_partial(tmp_path, mutation, status):
    root, manifest_path, manifest = _shared_note_fixture(tmp_path)
    pin = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if mutation == "source":
        (root / "methods/note.md").write_text("Changed source.")
    elif mutation == "missing":
        (root / "methods/note.md").unlink()
    elif mutation == "rights":
        manifest["documents"][0]["rights"]["redistribution"] = "private"
        manifest_path.write_text(json.dumps(manifest))
        pin = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    result = report(
        "point time",
        root=root,
        expected_manifest_sha256="0" * 64 if mutation == "pin" else pin,
    )
    assert result["status"] == status
    assert result["results"] == [] and result["error"]


def test_missing_manifest_is_error_not_no_match(tmp_path):
    result = report("point time", root=tmp_path)
    assert result["status"] == "error" and result["results"] == []


def test_legacy_queries_remain_exactly_495f0d4():
    baseline = json.loads(
        (
            ROOT / "docs/evidence/retrieval-report-2026-10-14/legacy-495f0d4.json"
        ).read_text()
    )
    for query, expected in baseline.items():
        assert shared_notes.search_shared_notes(query) == expected


def test_real_cli_query_and_stale_pin(tmp_path):
    command = [
        sys.executable,
        "shared_notes.py",
        "PCA banana",
        "--manifest-sha256",
        PIN,
    ]
    result = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, timeout=15
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "partial" and payload["results"][0][
        "missing_terms"
    ] == ["banana"]
    stale = subprocess.run(
        [*command[:-1], "0" * 64], cwd=ROOT, capture_output=True, text=True, timeout=15
    )
    assert stale.returncode == 1
    assert json.loads(stale.stdout)["status"] == "stale"
    # The report path must work without importing the paper/search/provider stack.
    isolated = subprocess.run(
        [sys.executable, "-S", "shared_notes.py", "availability"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert (
        isolated.returncode == 0 and json.loads(isolated.stdout)["status"] == "matched"
    )


def test_real_mcp_report_and_argument_error(monkeypatch):
    class EmptyCollection:
        def count(self):
            return 0

    monkeypatch.setattr(search_mcp, "load_config", lambda: {})
    monkeypatch.setattr(search_mcp, "get_collection", lambda _cfg: EmptyCollection())
    monkeypatch.setattr(search_mcp, "get_db", lambda _cfg: None)

    async def check():
        async with Client(search_mcp.build_server(), raise_exceptions=True) as client:
            listed = await client.list_tools()
            assert "search_shared_notes_report" in {t.name for t in listed.tools}
            result = await client.call_tool(
                "search_shared_notes_report",
                {"query": "PCA banana", "manifest_sha256": PIN},
            )
            assert not result.is_error
            assert json.loads(result.content[0].text)["status"] == "partial"
            invalid = await client.call_tool("search_shared_notes_report", {})
            assert invalid.is_error
            assert (
                json.loads(invalid.content[0].text)["error"]["code"] == "INVALID_QUERY"
            )

    asyncio.run(check())
