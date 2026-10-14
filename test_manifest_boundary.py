"""A malformed manifest must not admit ambiguous rights or invalid JSON metadata."""

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


@pytest.mark.parametrize(
    "defect",
    ["duplicate_rights", "nonfinite_value", "surrogate_title", "overflow_value"],
)
def test_malformed_manifest_is_refused_by_report_cli_and_note_loader(tmp_path, defect):
    notes = tmp_path / "notes"
    shutil.copytree(ROOT / "notes", notes)
    manifest_path = notes / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if defect == "surrogate_title":
        manifest["documents"][0]["title"] = "\ud800"
        raw = json.dumps(manifest).encode("utf-8")
    elif defect == "duplicate_rights":
        raw = (
            json.dumps(manifest)
            .replace(
                '"redistribution": "public"',
                '"redistribution": "private", "redistribution": "public"',
                1,
            )
            .encode("utf-8")
        )
    else:
        manifest["documents"][0]["rights"]["invalid_extra_value"] = 0
        number = "NaN" if defect == "nonfinite_value" else "1e309"
        raw = (
            json.dumps(manifest)
            .replace('"invalid_extra_value": 0', '"invalid_extra_value": ' + number)
            .encode("utf-8")
        )
    manifest_path.write_bytes(raw)
    pin = hashlib.sha256(raw).hexdigest()

    with pytest.raises(shared_notes.SharedNotesError) as error:
        shared_notes.load_shared_notes(notes, expected_manifest_sha256=pin)
    assert error.value.code == "INVALID_EVIDENCE"

    result = shared_notes.search_shared_notes_report(
        "availability", root=notes, expected_manifest_sha256=pin
    )
    assert result["status"] == "error" and result["results"] == []
    assert result["error"]["code"] == "INVALID_EVIDENCE"
    run = subprocess.run(
        [
            sys.executable,
            "-S",
            "shared_notes.py",
            "availability",
            "--root",
            str(notes),
            "--manifest-sha256",
            pin,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert run.returncode == 1
    output = json.loads(run.stdout, parse_constant=lambda value: pytest.fail(value))
    assert output["status"] == "error" and output["results"] == []
    assert output["error"]["code"] == "INVALID_EVIDENCE"
    assert run.stderr == ""

    shutil.copyfile(ROOT / "notes/manifest.json", manifest_path)
    restored = shared_notes.search_shared_notes_report("availability", root=notes)
    assert restored["status"] == "matched" and restored["results"]
