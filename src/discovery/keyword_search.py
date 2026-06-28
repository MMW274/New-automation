from __future__ import annotations

from datetime import datetime, timedelta, timezone

from googleapiclient.errors import HttpError

from src.config import AppConfig
from src.discovery.youtube_client import YouTubeClient


def search_by_keywords(client: YouTubeClient, config: AppConfig) -> dict[str, str]:
    """Return video_id -> search query label for keyword matches."""
    published_after = datetime.now(timezone.utc) - timedelta(hours=config.max_age_hours)
    discovered: dict[str, str] = {}

    for query in config.keyword_queries:
        try:
            video_ids = client.search_videos(query, published_after)
        except HttpError as error:
            if error.resp.status in (403, 429):
                print(f"  Warning: YouTube search quota hit — skipping remaining keyword searches.")
                break
            raise
        for video_id in video_ids:
            discovered[video_id] = f"search:{query}"

    return discovered
