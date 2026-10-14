"""Late hosted path/title witnesses preserve the existing report shape."""

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


def test_escaped_nul_source_path_is_a_bounded_error(tmp_path, monkeypatch):
    notes = tmp_path / "notes"
    shutil.copytree(ROOT / "notes", notes)
    path = notes / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["documents"][0]["path"] = "methods/missing\0.md"
    path.write_text(json.dumps(manifest))
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
    assert json.loads(run.stdout)["error"]["code"] == "INVALID_EVIDENCE"

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
            assert result.is_error
            assert (
                json.loads(result.content[0].text)["error"]["code"]
                == "INVALID_EVIDENCE"
            )

    asyncio.run(check())


def test_nul_root_argument_is_a_safe_library_error(tmp_path):
    root = str(tmp_path) + "\0"
    with pytest.raises(shared_notes.SharedNotesError):
        shared_notes.load_shared_notes(root)
    report = shared_notes.search_shared_notes_report("availability", root=root)
    assert report["status"] == "error" and report["results"] == []
    assert report["error"]["code"] == "INVALID_EVIDENCE"


@pytest.mark.parametrize(
    "length", [512, 608], ids=["max-title-control", "overlong-title"]
)
def test_title_budget_keeps_every_title_match_inside_evidence(tmp_path, length):
    notes = tmp_path / "notes"
    shutil.copytree(ROOT / "notes", notes)
    path = notes / "manifest.json"
    manifest = json.loads(path.read_text())
    entry = manifest["documents"][0]
    entry["title"] = "x" * (length - 7) + " needle"
    raw = b"A bounded original note.\n"
    (notes / entry["path"]).write_bytes(raw)
    entry["sha256"] = hashlib.sha256(raw).hexdigest()
    manifest["documents"] = [entry]
    path.write_text(json.dumps(manifest))
    report = shared_notes.search_shared_notes_report("needle bounded", root=notes)
    if length > 512:
        assert report["status"] == "error" and report["results"] == []
        assert report["error"]["code"] == "INVALID_EVIDENCE"
    else:
        assert report["status"] == "matched"
        windows = report["results"][0]["evidence"]
        assert any(
            w["kind"] == "manifest_title" and "needle" in w["text"] for w in windows
        )
        assert (
            shared_notes.verify_shared_notes_report(report, root=notes)["status"]
            == "verified"
        )
