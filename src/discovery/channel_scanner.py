from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.config import AppConfig
from src.discovery.youtube_client import YouTubeClient


def scan_channels(client: YouTubeClient, config: AppConfig) -> dict[str, str]:
    """Return video_id -> source channel name for recent uploads."""
    published_after = datetime.now(timezone.utc) - timedelta(hours=config.max_age_hours)
    discovered: dict[str, str] = {}

    for channel in config.channels:
        channel_id = channel["id"]
        channel_name = channel.get("name", channel_id)

        uploads_playlist = client.get_uploads_playlist_id(channel_id)
        if not uploads_playlist:
            continue

        video_ids = client.list_playlist_videos(uploads_playlist, published_after)
        for video_id in video_ids:
            discovered[video_id] = channel_name

    return discovered
