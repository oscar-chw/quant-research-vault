"""Hosted review witnesses for exact Unicode excerpts and safe path failures."""

from __future__ import annotations

import asyncio
import functools
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import Client

import search_mcp
import shared_notes

ROOT = Path(__file__).parent


@pytest.mark.parametrize(
    "query,line,needle",
    [
        ("İstanbul", "İstanbul observations.", "İstanbul"),
        ("strasse", "İ " * 400 + "Straße observations.", "Straße"),
    ],
)
def test_folded_word_matches_have_exact_original_source_spans(
    tmp_path, query, line, needle
):
    notes = tmp_path / "notes"
    shutil.copytree(ROOT / "notes", notes)
    manifest_path = notes / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    entry = manifest["documents"][0]
    entry["title"] = "Unrelated method"
    document = f"id: {entry['id']}\ntitle: {entry['title']}\n\n{line}\n"
    raw = document.encode("utf-8")
    (notes / entry["path"]).write_bytes(raw)
    entry["sha256"] = hashlib.sha256(raw).hexdigest()
    manifest["documents"] = [entry]
    manifest_path.write_text(json.dumps(manifest))
    report = shared_notes.search_shared_notes_report(query, root=notes)
    assert report["status"] == "matched"
    assert len(report["results"]) == 1
    evidence = report["results"][0]["evidence"]
    assert all(item["kind"] == "source_text" for item in evidence)
    assert any(needle in item["text"] for item in evidence)
    for item in evidence:
        original = document.splitlines()[item["line"] - 1]
        assert item["text"] == original[item["start_char"] : item["end_char"]]
        assert 0 <= item["start_char"] < item["end_char"] <= len(original)
        assert len(item["text"]) <= 512
    verified = shared_notes.verify_shared_notes_report(report, root=notes)
    assert verified["status"] == "verified"


@pytest.mark.parametrize("loop", ["source", "root"])
def test_symlink_loops_are_bounded_errors_in_loader_report_cli_and_mcp(
    tmp_path, monkeypatch, loop
):
    notes = tmp_path / "notes"
    shutil.copytree(ROOT / "notes", notes)
    if loop == "source":
        path = notes / "methods/pit-cutoffs.md"
        path.unlink()
        path.symlink_to(path.name)
    else:
        path = tmp_path / "root-loop"
        path.symlink_to(path.name)
        notes = path
    with pytest.raises(shared_notes.SharedNotesError) as error:
        shared_notes.load_shared_notes(notes)
    assert error.value.code == "INVALID_EVIDENCE"
    report = shared_notes.search_shared_notes_report("availability", root=notes)
    assert report["status"] == "error" and report["results"] == []
    assert report["error"]["code"] == "INVALID_EVIDENCE"
    run = subprocess.run(
        [sys.executable, "-S", "shared_notes.py", "availability", "--root", str(notes)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert run.returncode == 1 and run.stderr == ""
    output = json.loads(run.stdout)
    assert output["status"] == "error" and output["results"] == []
    assert output["error"]["code"] == "INVALID_EVIDENCE"

    class EmptyCollection:
        def count(self):
            return 0

    monkeypatch.setattr(search_mcp, "load_config", lambda: {})
    monkeypatch.setattr(search_mcp, "get_collection", lambda _cfg: EmptyCollection())
    monkeypatch.setattr(search_mcp, "get_db", lambda _cfg: None)
    monkeypatch.setattr(
        search_mcp.shared_notes,
        "search_shared_notes_report",
        functools.partial(shared_notes.search_shared_notes_report, root=notes),
    )

    async def check():
        async with Client(search_mcp.build_server(), raise_exceptions=True) as client:
            result = await client.call_tool(
                "search_shared_notes_report", {"query": "availability"}
            )
            payload = json.loads(result.content[0].text)
            assert result.is_error
            assert payload["status"] == "error" and payload["results"] == []
            assert payload["error"]["code"] == "INVALID_EVIDENCE"

    asyncio.run(check())
