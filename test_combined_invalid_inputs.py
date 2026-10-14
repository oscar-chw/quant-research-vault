"""Error precedence must not bypass safe response initialization."""

import json

import pytest

import shared_notes


@pytest.mark.parametrize(
    "query,limit,pin,code",
    [
        ("", 5, "\udcff", "INVALID_QUERY"),
        ("availability", 0, "\udcff", "INVALID_LIMIT"),
        ("\udcff", 5, "\udcff", "INVALID_QUERY"),
        (None, 5, b"bad-pin", "INVALID_QUERY"),
        ("PCA " * 270_000, 5, "z" * 20_000, "QUERY_TOO_LARGE"),
    ],
    ids=[
        "empty-query",
        "invalid-limit",
        "unicode-query",
        "non-text-query",
        "both-oversized",
    ],
)
def test_combined_invalid_inputs_are_small_utf8_errors_with_prior_precedence(
    query, limit, pin, code
):
    result = shared_notes.search_shared_notes_report(
        query, limit=limit, expected_manifest_sha256=pin
    )
    assert result["status"] == "error" and result["results"] == []
    assert result["error"]["code"] == code
    assert result["expected_manifest_sha256"] is None
    assert len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 1024


def test_valid_pin_is_retained_even_when_query_is_invalid():
    pin = "0" * 64
    result = shared_notes.search_shared_notes_report("", expected_manifest_sha256=pin)
    assert result["error"]["code"] == "INVALID_QUERY"
    assert result["expected_manifest_sha256"] == pin
