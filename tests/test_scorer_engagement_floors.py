"""Engagement-quality floors: a source video must clear min_views,
min_views_per_hour, and min_engagement_rate before it can be clipped."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.config import ScoringConfig
from src.discovery.scorer import score_videos


def _scoring(
    *,
    min_views: int = 0,
    min_views_per_hour: float = 0.0,
    min_engagement_rate: float = 0.0,
) -> ScoringConfig:
    return ScoringConfig(
        max_age_hours=48,
        min_views=min_views,
        min_duration_seconds=10,
        max_duration_seconds=10_000,
        relevance_terms=["trump"],
        blocked_topics=[],
        top_n=50,
        weights={"views_per_hour": 1.0, "engagement_rate": 10.0, "like_ratio": 5.0},
        trusted_channels=[],
        channel_boost=1.0,
        min_views_per_hour=min_views_per_hour,
        min_engagement_rate=min_engagement_rate,
    )


def _video(
    video_id: str,
    *,
    views: int,
    likes: int,
    comments: int,
    hours_old: float,
) -> dict:
    published = datetime.now(timezone.utc) - timedelta(hours=hours_old)
    return {
        "id": video_id,
        "snippet": {
            "title": "Trump press conference",
            "description": "",
            "channelTitle": "Fox News",
            "publishedAt": published.isoformat().replace("+00:00", "Z"),
        },
        "contentDetails": {"duration": "PT5M"},
        "statistics": {
            "viewCount": str(views),
            "likeCount": str(likes),
            "commentCount": str(comments),
        },
    }


def test_min_views_400k_drops_low_view_video():
    videos = [
        _video("a", views=300_000, likes=10_000, comments=2_000, hours_old=10),
        _video("b", views=500_000, likes=15_000, comments=2_500, hours_old=10),
    ]
    scored = score_videos(videos, sources={"a": "x", "b": "x"}, scoring=_scoring(min_views=400_000))
    assert [s.video_id for s in scored] == ["b"]


def test_min_views_per_hour_drops_cold_video():
    # 500k views but 100 hours old -> 5,000 views/hr exactly. Floor 6,000 drops it.
    cold = _video("a", views=500_000, likes=10_000, comments=2_000, hours_old=100)
    hot = _video("b", views=500_000, likes=10_000, comments=2_000, hours_old=5)
    scored = score_videos(
        [cold, hot], sources={"a": "x", "b": "x"}, scoring=_scoring(min_views_per_hour=6000)
    )
    assert [s.video_id for s in scored] == ["b"]


def test_min_engagement_rate_drops_passive_views():
    # video a: 1M views, only 100 likes, 0 comments -> rate ~0.0001
    # video b: 1M views, 6000 likes, 1000 comments -> rate ~0.009
    bot_views = _video("a", views=1_000_000, likes=100, comments=0, hours_old=10)
    real = _video("b", views=1_000_000, likes=6_000, comments=1_000, hours_old=10)
    scored = score_videos(
        [bot_views, real],
        sources={"a": "x", "b": "x"},
        scoring=_scoring(min_engagement_rate=0.005),
    )
    assert [s.video_id for s in scored] == ["b"]


def test_all_floors_off_keeps_everything():
    videos = [_video("a", views=1000, likes=10, comments=1, hours_old=10)]
    scored = score_videos(videos, sources={"a": "x"}, scoring=_scoring())
    assert [s.video_id for s in scored] == ["a"]
