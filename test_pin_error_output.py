"""Invalid caller pins must never be echoed into unsafe error JSON."""

import json

import pytest

import shared_notes


@pytest.mark.parametrize(
    "pin",
    ["\udcff", b"bad-pin", "z" * (20 * 1024)],
    ids=["invalid-unicode", "non-json-type", "oversized-invalid-pin"],
)
def test_invalid_pin_error_omits_input_and_is_small_utf8_json(pin):
    result = shared_notes.search_shared_notes_report(
        "availability", expected_manifest_sha256=pin
    )
    assert result["status"] == "error" and result["results"] == []
    assert result["error"]["code"] == "INVALID_EVIDENCE"
    assert result["expected_manifest_sha256"] is None
    assert len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 1024
