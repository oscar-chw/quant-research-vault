"""A report's claimed terms must fit its exact, bounded citations."""

import copy
import json
import re

import pytest

import shared_notes
from test_quality import _shared_note_fixture


@pytest.mark.parametrize(
    "text,query,status",
    [
        ("alpha " + " " * 600 + " beta", "alpha beta", "matched"),
        ("alpha\n" * 4 + "beta", "alpha beta", "matched"),
        ("alpha " + " " * 600 + " beta", "point alpha beta", "matched"),
        ("alpha " + " " * 600 + " beta", "alpha beta banana", "partial"),
    ],
    ids=["distant-one-line", "repeated-prefix", "title-and-distant", "partial"],
)
def test_every_claimed_term_has_complete_visible_evidence(
    tmp_path, text, query, status
):
    root, _, _ = _shared_note_fixture(tmp_path, text=text)
    report = shared_notes.search_shared_notes_report(query, root=root)
    assert report["status"] == status
    hit = report["results"][0]
    windows = hit["evidence"]
    assert 1 <= len(windows) <= 3
    visible = set()
    for window in windows:
        assert len(window["text"]) <= 512
        visible.update(re.findall(r"\w+", window["text"].casefold()))
    assert set(hit["matched_terms"]) <= visible
    assert (
        shared_notes.verify_shared_notes_report(report, root=root)["status"]
        == "verified"
    )


@pytest.mark.parametrize(
    "text,query",
    [
        ("\n".join(["alpha", "beta", "gamma", "delta"]), "alpha beta gamma delta"),
        ("x" * 600, "x" * 600),
    ],
    ids=["more-than-three-separated-terms", "term-longer-than-window"],
)
def test_unrepresentable_claims_are_bounded_errors(tmp_path, text, query):
    root, _, _ = _shared_note_fixture(tmp_path, text=text)
    report = shared_notes.search_shared_notes_report(query, root=root)
    assert report["status"] == "error" and report["results"] == []
    assert report["error"]["code"] == "EVIDENCE_LIMIT"
    assert len(json.dumps(report, ensure_ascii=False).encode("utf-8")) < 16 * 1024


def test_verifier_refuses_uncited_claim_even_if_replay_agrees(tmp_path, monkeypatch):
    root, _, _ = _shared_note_fixture(tmp_path, text="alpha beta")
    report = shared_notes.search_shared_notes_report("alpha beta", root=root)
    assert (
        shared_notes.verify_shared_notes_report(report, root=root)["status"]
        == "verified"
    )
    changed = copy.deepcopy(report)
    changed["results"][0]["evidence"] = [
        {
            "kind": "source_text",
            "line": 1,
            "start_char": 0,
            "end_char": 5,
            "text": "alpha",
        }
    ]
    monkeypatch.setattr(
        shared_notes, "search_shared_notes_report", lambda *_a, **_kw: changed
    )
    outcome = shared_notes.verify_shared_notes_report(changed, root=root)
    assert outcome["status"] == "error"
    assert outcome["error"]["code"] == "REPORT_MISMATCH"


@pytest.mark.parametrize("path", ["\0", "\udcff"], ids=["embedded-nul", "surrogate"])
def test_invalid_saved_report_path_is_structured_error(path):
    outcome = shared_notes.verify_shared_notes_report_file(path)
    assert outcome["status"] == "error" and outcome["document_ids"] == []
    assert outcome["error"]["code"] == "REPORT_UNAVAILABLE"
    json.dumps(outcome, ensure_ascii=False).encode("utf-8")


def test_saved_report_file_control_and_loop_refusal(tmp_path):
    report = shared_notes.search_shared_notes_report("PCA training")
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report))
    assert shared_notes.verify_shared_notes_report_file(path)["status"] == "verified"
    loop = tmp_path / "loop.json"
    loop.symlink_to(loop.name)
    outcome = shared_notes.verify_shared_notes_report_file(loop)
    assert outcome["error"]["code"] == "REPORT_UNAVAILABLE"
