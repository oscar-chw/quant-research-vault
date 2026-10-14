"""Saved retrieval reports must reproduce their pinned evidence before reuse."""

from __future__ import annotations

import asyncio
import copy
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
PIN = "c15abda5657cc63a953c7d8b8d34f044f0b6dcad09c253a0b9842e5beea4c70a"


def verify(report, **kwargs):
    function = getattr(shared_notes, "verify_shared_notes_report", None)
    assert callable(function), "saved-report verifier is absent"
    return function(report, **kwargs)


def saved(query="PCA training", **kwargs):
    return shared_notes.search_shared_notes_report(query, **kwargs)


@pytest.mark.parametrize(
    "query,limit",
    [("availability", 5), ("PCA banana", 5), ("zirconium", 5), ("training", 1)],
)
@pytest.mark.parametrize("pinned", [False, True])
def test_valid_saved_report_reproduces_source_and_outcome(query, limit, pinned):
    report = saved(query, limit=limit, expected_manifest_sha256=PIN if pinned else None)
    result = verify(report)
    assert result["schema"] == "quant-shared-search-verification/v1"
    assert result["status"] == "verified" and result["error"] is None
    assert result["manifest_sha256"] == PIN
    assert result["document_ids"] == [r["document_id"] for r in report["results"]]
    assert result["replay_limit"] == max(1, len(report["results"]))


@pytest.mark.parametrize(
    "change",
    [
        "quote",
        "line",
        "offset",
        "source_hash",
        "reference",
        "rights",
        "terms",
        "coverage",
        "status",
        "order",
        "omitted_hit",
        "extra_hit",
        "unknown_field",
        "json_type",
    ],
)
def test_single_field_or_structure_change_is_refused(change):
    report = saved()
    hit = report["results"][0]
    if change == "quote":
        hit["evidence"][-1]["text"] = "Fitting on future data is safe."
    elif change == "line":
        hit["evidence"][-1]["line"] += 1
    elif change == "offset":
        hit["evidence"][-1]["start_char"] += 1
    elif change == "source_hash":
        hit["source_sha256"] = "0" * 64
    elif change == "reference":
        hit["source_refs"][0]["revision"] = "different-source"
    elif change == "rights":
        hit["rights"]["license"] = "unverified-license"
    elif change == "terms":
        hit["missing_terms"] = ["invented"]
    elif change == "coverage":
        hit["term_coverage"] = 0.75
    elif change == "status":
        report["status"] = "no_match"
    elif change == "order":
        report["results"].reverse()
    elif change == "omitted_hit":
        report["results"].pop()
    elif change == "extra_hit":
        report["results"].append(copy.deepcopy(hit))
    elif change == "unknown_field":
        report["invented_acceptance"] = True
    else:
        report["truncated"] = 0  # JSON false and zero must not compare equal.
    result = verify(report)
    assert result["status"] == "error"
    assert result["error"]["code"] == "REPORT_MISMATCH"
    assert result["document_ids"] == []


@pytest.mark.parametrize("change", ["manifest", "source", "missing_source"])
def test_changed_or_missing_corpus_is_not_admitted(tmp_path, change):
    notes = tmp_path / "notes"
    shutil.copytree(ROOT / "notes", notes)
    report = saved(root=notes)
    path = notes / "methods/pca-fit-state.md"
    if change == "manifest":
        with (notes / "manifest.json").open("ab") as file:
            file.write(b"\n")
    elif change == "source":
        with path.open("ab") as file:
            file.write(b"Changed content.\n")
    else:
        path.unlink()
    result = verify(report, root=notes)
    assert result["status"] == ("error" if change == "missing_source" else "stale")
    assert result["document_ids"] == [] and result["error"]


@pytest.mark.parametrize(
    "value", [None, [], "report", {"status": "stale"}, {"status": "error"}]
)
def test_nonreport_or_unverified_status_is_an_error(value):
    result = verify(value)
    assert result["status"] == "error" and result["document_ids"] == []


def test_nonfinite_report_value_is_refused():
    report = saved()
    report["results"][0]["term_coverage"] = float("nan")
    result = verify(report)
    assert result["status"] == "error"
    assert result["error"]["code"] == "INVALID_REPORT"


@pytest.mark.parametrize("status", [[], {}, 42])
def test_malformed_status_field_returns_safe_error(status):
    report = saved()
    report["status"] = status
    result = verify(report)
    assert result["status"] == "error"
    assert result["error"]["code"] == "INVALID_REPORT"


def test_verification_does_not_mutate_the_callers_report():
    report = saved()
    original = copy.deepcopy(report)
    result = verify(report)
    assert result["status"] == "verified"
    assert report == original


def test_verifier_checks_source_even_if_producer_repeats_the_bad_quote(monkeypatch):
    report = saved()
    report["results"][0]["evidence"][-1]["text"] = "Fitting on future data is safe."
    monkeypatch.setattr(
        shared_notes,
        "search_shared_notes_report",
        lambda *_args, **_kwargs: copy.deepcopy(report),
    )
    result = verify(report)
    assert result["status"] == "error"
    assert result["error"]["code"] == "REPORT_MISMATCH"


@pytest.mark.parametrize("field", ["title", "rights"])
def test_unserializable_source_metadata_returns_safe_error(tmp_path, field):
    notes = tmp_path / "notes"
    shutil.copytree(ROOT / "notes", notes)
    report = saved(root=notes)
    path = notes / "manifest.json"
    manifest = json.loads(path.read_text())
    if field == "title":
        manifest["documents"][1]["title"] = "\ud800"
    else:
        manifest["documents"][1]["rights"]["invalid_extra_value"] = float("nan")
    path.write_text(json.dumps(manifest), encoding="utf-8")
    pin = hashlib.sha256(path.read_bytes()).hexdigest()
    report["manifest_sha256"] = pin
    for hit in report["results"]:
        hit["manifest_sha256"] = pin
    result = verify(report, root=notes)
    assert result["status"] == "error" and result["document_ids"] == []
    assert result["error"]["code"] == "INVALID_EVIDENCE"


@pytest.mark.parametrize(
    "raw_manifest",
    [b"[" * 2000 + b"0" + b"]" * 2000, b'{"number":' + b"9" * 5000 + b"}"],
)
def test_manifest_parser_limits_return_json_error_without_traceback(
    tmp_path, raw_manifest
):
    notes = tmp_path / "notes"
    shutil.copytree(ROOT / "notes", notes)
    report = saved(root=notes)
    path = notes / "manifest.json"
    path.write_bytes(raw_manifest)
    report["manifest_sha256"] = hashlib.sha256(raw_manifest).hexdigest()
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    run = cli(report_path, "--root", str(notes))
    assert run.returncode == 1
    result = json.loads(run.stdout)
    assert result["status"] == "error" and result["document_ids"] == []
    assert result["error"]["code"] == "INVALID_EVIDENCE"
    assert "Traceback" not in run.stderr


def cli(path, *args):
    return subprocess.run(
        [sys.executable, "-S", "shared_notes.py", "--verify-report", str(path), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_cli_saved_report_failure_and_recovery(tmp_path):
    path = tmp_path / "report.json"
    original = saved()
    path.write_text(json.dumps(original), encoding="utf-8")
    run = cli(path)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["status"] == "verified"
    changed = copy.deepcopy(original)
    changed["results"][0]["evidence"][-1]["text"] = "Changed citation."
    path.write_text(json.dumps(changed), encoding="utf-8")
    run = cli(path)
    assert run.returncode == 1 and json.loads(run.stdout)["status"] == "error"
    path.write_text(json.dumps(original), encoding="utf-8")
    run = cli(path)
    assert run.returncode == 0 and json.loads(run.stdout)["status"] == "verified"


@pytest.mark.parametrize(
    "content",
    [
        b"not JSON",
        b"\xff",
        b"[]",
        b'{"status":"matched","status":"no_match"}',
        b'{"value":NaN}',
        b'{"value":1e999}',
        b"[" * 2000 + b"]" * 2000,
    ],
)
def test_cli_bad_serialization_is_safe_error(tmp_path, content):
    path = tmp_path / "report.json"
    path.write_bytes(content)
    run = cli(path)
    assert run.returncode == 1
    result = json.loads(run.stdout)
    assert result["status"] == "error" and result["document_ids"] == []
    assert "Traceback" not in run.stderr


def test_cli_missing_and_oversized_input_is_error(tmp_path):
    missing = cli(tmp_path / "absent.json")
    assert missing.returncode == 1
    assert json.loads(missing.stdout)["error"]["code"] == "REPORT_UNAVAILABLE"
    path = tmp_path / "report.json"
    path.write_bytes(b" " * (1024 * 1024 + 1))
    oversized = cli(path)
    assert oversized.returncode == 1
    assert json.loads(oversized.stdout)["error"]["code"] == "REPORT_TOO_LARGE"


def test_duplicate_key_in_an_otherwise_valid_report_is_refused(tmp_path):
    report = saved()
    raw = json.dumps(report)[:-1] + ',"status":"matched"}'
    assert (
        json.loads(raw) == report
    )  # A permissive last-key-wins parser would accept it.
    path = tmp_path / "duplicate.json"
    path.write_text(raw, encoding="utf-8")
    result = shared_notes.verify_shared_notes_report_file(path)
    assert result["status"] == "error"
    assert result["error"]["code"] == "INVALID_REPORT"
    run = cli(path)
    assert run.returncode == 1 and json.loads(run.stdout)["status"] == "error"


def test_large_file_read_stops_at_the_declared_byte_bound(tmp_path, monkeypatch):
    path = tmp_path / "large.json"
    path.write_bytes(b" " * (2 * 1024 * 1024))
    original_open = Path.open
    observed = []

    class ReadProbe:
        def __enter__(self):
            self.file = original_open(path, "rb")
            return self

        def __exit__(self, *_args):
            self.file.close()

        def read(self, *args):
            data = self.file.read(*args)
            observed.append(len(data))
            return data

    def open_probe(target, *args, **kwargs):
        return ReadProbe() if target == path else original_open(target, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_probe)
    result = shared_notes.verify_shared_notes_report_file(path)
    assert result["error"]["code"] == "REPORT_TOO_LARGE"
    assert observed == [1024 * 1024 + 1]


def test_real_mcp_verification_and_tamper_error(monkeypatch):
    class EmptyCollection:
        def count(self):
            return 0

    monkeypatch.setattr(search_mcp, "load_config", lambda: {})
    monkeypatch.setattr(search_mcp, "get_collection", lambda _cfg: EmptyCollection())
    monkeypatch.setattr(search_mcp, "get_db", lambda _cfg: None)

    async def check():
        async with Client(search_mcp.build_server(), raise_exceptions=True) as client:
            listed = await client.list_tools()
            assert "verify_shared_notes_report" in {tool.name for tool in listed.tools}
            report = saved()
            result = await client.call_tool(
                "verify_shared_notes_report", {"report": report}
            )
            assert (
                not result.is_error
                and json.loads(result.content[0].text)["status"] == "verified"
            )
            report["results"][0]["source_sha256"] = "0" * 64
            changed = await client.call_tool(
                "verify_shared_notes_report", {"report": report}
            )
            assert changed.is_error
            assert (
                json.loads(changed.content[0].text)["error"]["code"]
                == "REPORT_MISMATCH"
            )
            missing = await client.call_tool("verify_shared_notes_report", {})
            assert missing.is_error

    asyncio.run(check())


def test_original_corpus_and_checks_remain_byte_identical():
    baseline = json.loads(
        (
            ROOT / "docs/evidence/retrieval-report-2026-10-14/preserved-controls.json"
        ).read_text()
    )
    for name, expected in baseline["files"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
