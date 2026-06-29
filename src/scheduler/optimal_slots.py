"""Day-of-week + platform aware publish-time slotting.

Peak windows derived from 2026 short-form video research:
- TikTok: Hootsuite (Thu 6-9am ET best), Buffer 7.1M-post study, Apaya 2026
- YouTube Shorts: Buffer (Fri 4-7pm ET peak), Metricool 2026
- X (Twitter): Buffer / Metricool consensus (Tue/Wed 9-11am ET)

Returned times are timezone-aware UTC datetimes ready for Vizard `publishTime`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# day_of_week (Mon=0 .. Sun=6) -> ordered list of preferred ET hours
PLATFORM_PEAKS: dict[str, dict[int, list[int]]] = {
    "tiktok": {
        0: [18, 20, 13],
        1: [18, 6, 20],
        2: [18, 22, 13],
        3: [6, 13, 18],
        4: [18, 19, 20],
        5: [17, 12, 20],
        6: [9, 13, 18],
    },
    "youtube": {
        0: [18, 20],
        1: [18, 20],
        2: [18, 20],
        3: [18, 19],
        4: [18, 19, 16],
        5: [18, 13],
        6: [13, 18],
    },
    "twitter": {
        0: [10, 14],
        1: [10, 14],
        2: [10, 14],
        3: [10, 14],
        4: [10],
        5: [11],
        6: [11],
    },
}

DEFAULT_PEAKS_BY_PLATFORM: dict[str, list[int]] = {
    "tiktok": [18, 20, 13, 9],
    "youtube": [18, 20, 13],
    "twitter": [10, 14],
}


def _normalize_platform(platform: str) -> str:
    name = platform.lower()
    if name in ("x", "twitter"):
        return "twitter"
    if name in ("yt", "youtube", "youtubeshorts", "youtube shorts"):
        return "youtube"
    if name in ("tt", "tiktok"):
        return "tiktok"
    return name


def next_optimal_slot(
    platform: str,
    *,
    after: datetime,
    used_slots: set[datetime] | None = None,
    lookahead_hours: int = 48,
    min_lead_minutes: int = 6,
    fallback_interval_minutes: int = 45,
) -> datetime:
    """Return next platform-optimal publish time strictly after `after`.

    - `after` and the returned value are timezone-aware UTC datetimes.
    - `used_slots` lets the caller deduplicate slots already claimed this run.
    - Falls back to `after + fallback_interval_minutes` when no preferred slot
      remains in the lookahead window (rare, only when many clips compete).
    """
    used_slots = used_slots or set()
    norm = _normalize_platform(platform)
    earliest = after.astimezone(timezone.utc) + timedelta(minutes=min_lead_minutes)
    deadline = earliest + timedelta(hours=lookahead_hours)

    peaks_by_dow = PLATFORM_PEAKS.get(norm)
    default_peaks = DEFAULT_PEAKS_BY_PLATFORM.get(norm, [18])

    candidate = earliest.astimezone(ET)
    day = candidate.date()
    while True:
        hours = (
            peaks_by_dow.get(candidate.weekday(), default_peaks)
            if peaks_by_dow
            else default_peaks
        )
        for hour in hours:
            slot_et = datetime(day.year, day.month, day.day, hour, 0, tzinfo=ET)
            slot_utc = slot_et.astimezone(timezone.utc)
            if slot_utc <= earliest:
                continue
            if slot_utc > deadline:
                break
            if slot_utc in used_slots:
                continue
            return slot_utc
        day = day + timedelta(days=1)
        candidate = datetime(day.year, day.month, day.day, 0, 0, tzinfo=ET)
        if candidate.astimezone(timezone.utc) > deadline:
            break

    fallback = earliest + timedelta(minutes=fallback_interval_minutes)
    while fallback in used_slots:
        fallback = fallback + timedelta(minutes=fallback_interval_minutes)
    return fallback
