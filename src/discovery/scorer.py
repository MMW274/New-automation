from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from src.config import ScoringConfig
from src.discovery.youtube_client import YouTubeClient


@dataclass
class ScoredVideo:
    video_id: str
    title: str
    channel_title: str
    published_at: str
    url: str
    view_count: int
    like_count: int
    comment_count: int
    duration_seconds: int
    hours_since_publish: float
    views_per_hour: float
    engagement_rate: float
    score: float
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _matches_relevance(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _matches_blocked_topic(text: str, blocked: list[str]) -> str | None:
    """Return the first blocked topic phrase that appears in `text`, else None.

    Used as a HARD filter — any hit drops the video before it can be scored,
    even if it would otherwise pass the relevance gate. Keeps sports / weather
    / celebrity / world-only-news out of the candidate pool.
    """
    if not blocked:
        return None
    lowered = text.lower()
    for term in blocked:
        if term and term in lowered:
            return term
    return None


def score_videos(
    videos: list[dict[str, Any]],
    sources: dict[str, str],
    scoring: ScoringConfig,
) -> list[ScoredVideo]:
    now = datetime.now(timezone.utc)
    weights = scoring.weights
    scored: list[ScoredVideo] = []

    for video in videos:
        video_id = video.get("id")
        snippet = video.get("snippet")
        content_details = video.get("contentDetails") or {}
        duration = content_details.get("duration")

        if not video_id or not snippet or not duration:
            continue

        stats = video.get("statistics", {})
        duration_seconds = YouTubeClient.parse_duration_seconds(duration)

        view_count = int(stats.get("viewCount", 0))
        like_count = int(stats.get("likeCount", 0))
        comment_count = int(stats.get("commentCount", 0))

        published_dt = datetime.fromisoformat(
            snippet["publishedAt"].replace("Z", "+00:00")
        )
        hours_since_publish = max(
            (now - published_dt).total_seconds() / 3600,
            1 / 60,
        )

        title = snippet.get("title", "")
        description = snippet.get("description", "")
        relevance_text = f"{title} {description}"

        if view_count < scoring.min_views:
            continue
        if duration_seconds < scoring.min_duration_seconds:
            continue
        if duration_seconds > scoring.max_duration_seconds:
            continue
        if scoring.relevance_terms and not _matches_relevance(
            relevance_text, scoring.relevance_terms
        ):
            continue
        if _matches_blocked_topic(relevance_text, scoring.blocked_topics):
            continue

        views_per_hour = view_count / hours_since_publish
        engagement_rate = (like_count + comment_count * 3) / max(view_count, 1)
        like_ratio = like_count / max(view_count, 1)

        score = (
            views_per_hour * float(weights.get("views_per_hour", 1.0))
            + engagement_rate * float(weights.get("engagement_rate", 10.0)) * 1000
            + like_ratio * float(weights.get("like_ratio", 5.0)) * 10000
        )

        channel_title = snippet.get("channelTitle", "")
        if scoring.trusted_channels and scoring.channel_boost > 1:
            trusted = {name.lower() for name in scoring.trusted_channels}
            if any(name in channel_title.lower() for name in trusted):
                score *= scoring.channel_boost

        scored.append(
            ScoredVideo(
                video_id=video_id,
                title=title,
                channel_title=channel_title,
                published_at=snippet["publishedAt"],
                url=YouTubeClient.video_url(video_id),
                view_count=view_count,
                like_count=like_count,
                comment_count=comment_count,
                duration_seconds=duration_seconds,
                hours_since_publish=round(hours_since_publish, 2),
                views_per_hour=round(views_per_hour, 2),
                engagement_rate=round(engagement_rate, 6),
                score=round(score, 2),
                source=sources.get(video_id, "unknown"),
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[: scoring.top_n]
