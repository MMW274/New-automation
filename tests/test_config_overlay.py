"""Overlay loader — verifies the additive layering pattern used by
`extensions/` so that future iterations never have to touch the base
configs in `config/`."""

from __future__ import annotations

from pathlib import Path

import yaml

from src.config_overlay import (
    _deep_merge,
    apply_overlay,
    list_active_overlays,
    load_overlay_yaml,
)


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_scalar_overlay_replaces_base():
    base = {"min_views": 5000, "top_n": 15}
    overlay = {"min_views": 400000}
    merged = _deep_merge(base, overlay)
    assert merged == {"min_views": 400000, "top_n": 15}


def test_list_replace_default_behaviour():
    base = {"relevance_terms": ["trump", "white house"]}
    overlay = {"relevance_terms": ["epstein"]}
    merged = _deep_merge(base, overlay)
    assert merged == {"relevance_terms": ["epstein"]}


def test_list_add_extends_dedup_case_insensitive():
    base = {"relevance_terms": ["trump", "white house"]}
    overlay = {"relevance_terms_add": ["EPSTEIN", "trump", "kash patel"]}
    merged = _deep_merge(base, overlay)
    assert merged["relevance_terms"] == [
        "trump",
        "white house",
        "EPSTEIN",
        "kash patel",
    ]


def test_list_remove_strips_entries():
    base = {"blocked_topics": ["wnba", "flood", "nba"]}
    overlay = {"blocked_topics_remove": ["WNBA", "flood"]}
    merged = _deep_merge(base, overlay)
    assert merged == {"blocked_topics": ["nba"]}


def test_deep_merge_nested_dict():
    base = {"weights": {"views_per_hour": 1.0, "engagement_rate": 10.0}}
    overlay = {"weights": {"engagement_rate": 15.0}}
    merged = _deep_merge(base, overlay)
    assert merged == {
        "weights": {"views_per_hour": 1.0, "engagement_rate": 15.0}
    }


def test_base_dict_is_not_mutated():
    base = {"relevance_terms": ["trump"], "weights": {"a": 1}}
    overlay = {"relevance_terms_add": ["epstein"], "weights": {"a": 2}}
    snapshot = {"relevance_terms": ["trump"], "weights": {"a": 1}}
    _deep_merge(base, overlay)
    assert base == snapshot


def test_no_active_overlays_returns_empty(tmp_path):
    # No extensions dir at all -> empty list, empty merged dict, base intact.
    assert list_active_overlays(tmp_path) == []
    assert load_overlay_yaml(tmp_path, "scoring.overlay.yaml") == {}
    base = {"min_views": 100}
    assert apply_overlay(base, tmp_path, "scoring.overlay.yaml") == base


def test_active_yaml_orders_overlays(tmp_path):
    _write(tmp_path / "extensions" / "active.yaml", {"active": ["a-bundle", "b-bundle"]})
    _write(
        tmp_path / "extensions" / "a-bundle" / "scoring.overlay.yaml",
        {"min_views": 100, "relevance_terms_add": ["trump"]},
    )
    _write(
        tmp_path / "extensions" / "b-bundle" / "scoring.overlay.yaml",
        {"min_views": 999, "relevance_terms_add": ["epstein"]},
    )
    # load_overlay_yaml returns the *unresolved* overlay layer — _add keys
    # are accumulated across overlays and only resolved against base when
    # apply_overlay is called.
    merged = load_overlay_yaml(tmp_path, "scoring.overlay.yaml")
    assert merged["min_views"] == 999
    assert merged["relevance_terms_add"] == ["trump", "epstein"]

    # When applied to an empty base, the _add is resolved into the real list.
    applied = apply_overlay({}, tmp_path, "scoring.overlay.yaml")
    assert applied["relevance_terms"] == ["trump", "epstein"]

    # When applied to a real base with existing terms, both stack.
    applied = apply_overlay(
        {"relevance_terms": ["biden"]}, tmp_path, "scoring.overlay.yaml"
    )
    assert applied["relevance_terms"] == ["biden", "trump", "epstein"]


def test_apply_overlay_layers_onto_base(tmp_path):
    _write(tmp_path / "extensions" / "active.yaml", {"active": ["focus"]})
    _write(
        tmp_path / "extensions" / "focus" / "scoring.overlay.yaml",
        {
            "min_views": 400000,
            "min_views_per_hour": 5000,
            "relevance_terms_add": ["kash patel", "epstein"],
            "blocked_topics_remove": ["flood"],
        },
    )
    base = {
        "min_views": 5000,
        "relevance_terms": ["trump", "white house"],
        "blocked_topics": ["wnba", "flood"],
    }
    merged = apply_overlay(base, tmp_path, "scoring.overlay.yaml")
    assert merged["min_views"] == 400000
    assert merged["min_views_per_hour"] == 5000
    assert merged["relevance_terms"] == [
        "trump",
        "white house",
        "kash patel",
        "epstein",
    ]
    assert merged["blocked_topics"] == ["wnba"]


def test_missing_overlay_file_is_skipped(tmp_path):
    _write(tmp_path / "extensions" / "active.yaml", {"active": ["focus"]})
    # No overlay file inside the focus folder — should be silently ignored.
    (tmp_path / "extensions" / "focus").mkdir(parents=True, exist_ok=True)
    base = {"min_views": 5000}
    merged = apply_overlay(base, tmp_path, "scoring.overlay.yaml")
    assert merged == base
