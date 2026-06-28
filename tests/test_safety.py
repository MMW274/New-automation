import importlib
import json


def _mod():
    """Re-resolve the module so we see the OUTPUT_DIR patched by conftest."""
    return importlib.import_module("src.safety.content_filter")


def test_safe_title_passes():
    verdict = _mod().classify("Trump signs new executive order on trade")
    assert verdict.safe
    assert verdict.matched_terms == []


def test_graphic_term_blocks():
    verdict = _mod().classify("Reports of mass shooting at school in Texas")
    assert not verdict.safe
    assert "mass shooting" in verdict.matched_terms


def test_blocklist_case_insensitive():
    verdict = _mod().classify("EXECUTION caught on camera")
    assert not verdict.safe
    assert "execution" in verdict.matched_terms


def test_custom_blocklist_overrides_default():
    verdict = _mod().classify("Trump press conference today", blocked_terms=("trump",))
    assert not verdict.safe
    assert "trump" in verdict.matched_terms


def test_hold_for_review_appends_to_queue():
    mod = _mod()
    mod.hold_for_review({"video_id": "vid1", "title": "risky"})
    mod.hold_for_review({"video_id": "vid2", "title": "risky2"})
    queue = json.loads(mod.REVIEW_QUEUE_PATH.read_text(encoding="utf-8"))
    assert len(queue) == 2
    assert queue[0]["video_id"] == "vid1"
    assert "held_at" in queue[0]


def test_default_blocklist_is_non_trivial():
    assert len(_mod().DEFAULT_BLOCKED_TERMS) >= 10
