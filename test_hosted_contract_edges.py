"""Hosted findings must fail before repair, without starting a service."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import shared_notes

ROOT = Path(__file__).parent


@pytest.mark.parametrize("query", ["point", "point bounded"])
def test_title_terms_are_cited_even_with_document_windows(tmp_path, query):
    notes = tmp_path / "notes"
    shutil.copytree(ROOT / "notes", notes)
    path = notes / "manifest.json"
    manifest = json.loads(path.read_text())
    entry = manifest["documents"][0]
    entry["title"] = "Point in time method"
    raw = ("A bounded original note.\n" * 4).encode("utf-8")
    (notes / entry["path"]).write_bytes(raw)
    entry["sha256"] = hashlib.sha256(raw).hexdigest()
    manifest["documents"] = [entry]
    path.write_text(json.dumps(manifest))
    report = shared_notes.search_shared_notes_report(query, root=notes)
    assert report["status"] == "matched"
    windows = report["results"][0]["evidence"]
    assert 1 <= len(windows) <= 3
    assert {"kind": "manifest_title", "text": entry["title"]} in windows
    if "bounded" in query:
        assert any(
            w["kind"] == "source_text" and "bounded" in w["text"] for w in windows
        )
        assert report["results"][0]["evidence_truncated"]
    assert (
        shared_notes.verify_shared_notes_report(report, root=notes)["status"]
        == "verified"
    )


@pytest.mark.parametrize(
    "query",
    ["PCA " * 270_000, "量" * 6000, "\ud800"],
    ids=["oversized", "multibyte-over-budget", "invalid-unicode"],
)
def test_large_or_unencodable_query_is_a_small_safe_error(query):
    report = shared_notes.search_shared_notes_report(query)
    assert report["status"] == "error" and report["results"] == []
    assert report["query"] is None and report["query_terms"] == []
    assert report["error"]["code"] in {"QUERY_TOO_LARGE", "INVALID_QUERY"}
    assert len(json.dumps(report, ensure_ascii=False).encode("utf-8")) < 1024


def test_near_limit_query_produces_a_verifiable_report():
    report = shared_notes.search_shared_notes_report("PCA " * 4000)
    assert report["status"] == "matched"
    assert shared_notes.verify_shared_notes_report(report)["status"] == "verified"


def test_report_budget_includes_metadata_and_result_copies(tmp_path):
    notes = tmp_path / "notes"
    shutil.copytree(ROOT / "notes", notes)
    path = notes / "manifest.json"
    manifest = json.loads(path.read_text())
    template = manifest["documents"][0]
    query = " ".join(f"k{i}" for i in range(2900))
    assert len(query.encode("utf-8")) < 16 * 1024
    rows = []
    for index in range(6):
        row = json.loads(json.dumps(template))
        row.update(
            id=f"size-{index}", path=f"methods/size-{index}.md", title="Original note"
        )
        raw = query.encode("utf-8")
        (notes / row["path"]).write_bytes(raw)
        row["sha256"] = hashlib.sha256(raw).hexdigest()
        if index == 0:
            row["rights"]["size_probe"] = []
        rows.append(row)
    manifest["documents"] = rows
    text = json.dumps(manifest).replace(
        '"size_probe": []', '"size_probe": [' + ",".join(["1e15"] * 48_000) + "]"
    )
    raw = text.encode("utf-8")
    assert len(raw) < shared_notes.MAX_SOURCE_BYTES
    path.write_bytes(raw)
    report = shared_notes.search_shared_notes_report(query, root=notes, limit=6)
    assert report["status"] == "error" and report["results"] == []
    assert report["error"]["code"] == "REPORT_TOO_LARGE"
    assert (
        len(json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"))
        < shared_notes.MAX_REPORT_BYTES
    )


@pytest.mark.parametrize(
    "option,expected", [("--shared-query", 0), ("--shared-note", 1)]
)
def test_empty_shared_cli_value_never_starts_server(option, expected):
    code = """
import runpy, sys, search_mcp
def forbid_server(frame, event, arg):
    if event == "call" and frame.f_code.co_name in {"_acquire_lock", "run_server"}:
        raise AssertionError("explicit shared argument entered server mode")
    return forbid_server
sys.argv = ["search_mcp.py", sys.argv[1], ""]
sys.settrace(forbid_server)
try:
    runpy.run_module("search_mcp", run_name="__main__")
finally:
    sys.settrace(None)
"""
    run = subprocess.run(
        [sys.executable, "-c", code, option],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert run.returncode == expected
    assert "entered server mode" not in run.stderr and "Traceback" not in run.stderr
    if expected == 0:
        assert json.loads(run.stdout) == [] and run.stderr == ""
    else:
        assert run.stdout == "" and "document id not found" in run.stderr
