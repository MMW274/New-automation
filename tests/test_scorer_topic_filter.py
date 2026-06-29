"""Hard topic filter: off-topic stories (sports / weather / world news) must
be dropped from candidates before scoring, even if a relevance term sneaks
in via description text."""

from __future__ import annotations

from src.config import ScoringConfig
from src.discovery.scorer import score_videos


def _scoring(*, blocked_topics=None) -> ScoringConfig:
    return ScoringConfig(
        max_age_hours=48,
        min_views=100,
        min_duration_seconds=10,
        max_duration_seconds=10_000,
        relevance_terms=["trump", "white house", "congress"],
        blocked_topics=blocked_topics or [],
        top_n=50,
        weights={"views_per_hour": 1.0, "engagement_rate": 10.0, "like_ratio": 5.0},
        trusted_channels=[],
        channel_boost=1.0,
    )


def _video(video_id: str, title: str, description: str = "") -> dict:
    return {
        "id": video_id,
        "snippet": {
            "title": title,
            "description": description,
            "channelTitle": "Test Channel",
            "publishedAt": "2026-06-29T10:00:00Z",
        },
        "contentDetails": {"duration": "PT5M"},
        "statistics": {"viewCount": "10000", "likeCount": "200", "commentCount": "50"},
    }


def test_blocked_topic_drops_wnba_even_with_relevance_match():
    videos = [
        _video("a", "Caitlin Clark WNBA foul — Trump reacts"),
        _video("b", "Trump signs executive order on tariffs"),
    ]
    scored = score_videos(
        videos, sources={"a": "x", "b": "x"}, scoring=_scoring(blocked_topics=["wnba"])
    )
    ids = [s.video_id for s in scored]
    assert "a" not in ids, "WNBA story slipped past blocked_topics filter"
    assert "b" in ids


def test_blocked_topic_drops_flood_story():
    videos = [
        _video("a", "Texas flood kills 20 — Trump tours damage"),
        _video("b", "Trump speaks at White House press conference"),
    ]
    scored = score_videos(
        videos,
        sources={"a": "x", "b": "x"},
        scoring=_scoring(blocked_topics=["flood", "flooding"]),
    )
    ids = [s.video_id for s in scored]
    assert "a" not in ids
    assert "b" in ids


def test_blocked_topic_empty_list_does_not_drop_anything():
    videos = [_video("a", "Trump press conference at the White House")]
    scored = score_videos(videos, sources={"a": "x"}, scoring=_scoring(blocked_topics=[]))
    assert [s.video_id for s in scored] == ["a"]
