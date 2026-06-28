"""Zero-quota YouTube channel scanner using public Atom/RSS feeds.

YouTube publishes a public Atom feed per channel at
`https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}`. It contains
the most recent ~15 uploads with publishedAt, title, videoId, channel info.
No API key required, no quota cost.

We still need `videos.list` (1 unit per 50 ids) for view/like/comment counts,
but eliminate `channels.list` + `playlistItems.list` (~22 units/run) entirely.

If the RSS fetch fails (404, 5xx, parse error), the caller can fall back to
`channel_scanner.scan_channels` which uses the official Data API.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests

from src.config import AppConfig

LOG = logging.getLogger(__name__)

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}
TIMEOUT_SECONDS = 12


def _fetch_channel_feed(channel_id: str) -> list[dict[str, str]]:
    """Return list of {video_id, published_at, title} for one channel."""
    url = RSS_URL.format(channel_id=channel_id)
    response = requests.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    entries: list[dict[str, str]] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        video_id_el = entry.find("yt:videoId", ATOM_NS)
        published_el = entry.find("atom:published", ATOM_NS)
        title_el = entry.find("atom:title", ATOM_NS)
        if video_id_el is None or published_el is None:
            continue
        entries.append(
            {
                "video_id": video_id_el.text or "",
                "published_at": published_el.text or "",
                "title": (title_el.text or "") if title_el is not None else "",
            }
        )
    return entries


def scan_channels_rss(
    config: AppConfig,
) -> tuple[dict[str, str], list[str]]:
    """Discover recent uploads via RSS for every configured channel.

    Returns:
        (discovered, failed_channel_ids) where `discovered` is
        {video_id: source_channel_name} and `failed_channel_ids` is the list
        of channels whose RSS feed could not be parsed (caller should fall
        back to the API scanner for those).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.max_age_hours)
    discovered: dict[str, str] = {}
    failed: list[str] = []

    for channel in config.channels:
        channel_id = channel["id"]
        channel_name = channel.get("name", channel_id)
        try:
            entries = _fetch_channel_feed(channel_id)
        except Exception as error:  # noqa: BLE001 — RSS is best-effort
            LOG.warning("RSS fetch failed for %s (%s): %s", channel_name, channel_id, error)
            failed.append(channel_id)
            continue

        for entry in entries:
            try:
                published_dt = datetime.fromisoformat(
                    entry["published_at"].replace("Z", "+00:00")
                )
            except ValueError:
                continue
            if published_dt < cutoff:
                continue
            if entry["video_id"]:
                discovered[entry["video_id"]] = channel_name

    return discovered, failed
