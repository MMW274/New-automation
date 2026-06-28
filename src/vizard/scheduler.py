from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def build_publish_schedule(
    clip_count: int,
    *,
    clips_per_day: int,
    start_hour: int,
    end_hour: int,
    timezone: str,
    start_offset_days: int = 1,
) -> list[datetime]:
    """Spread clips evenly between start_hour and end_hour, N clips per day."""
    if clip_count <= 0:
        return []

    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    current_day = date.today() + timedelta(days=start_offset_days)
    window_minutes = max((end_hour - start_hour) * 60, 60)
    slot_minutes = window_minutes / clips_per_day

    schedule: list[datetime] = []
    day_index = 0
    slot_index = 0

    while len(schedule) < clip_count:
        day = current_day + timedelta(days=day_index)
        minute_offset = slot_minutes * slot_index + slot_minutes / 2
        hour = start_hour + int(minute_offset // 60)
        minute = int(minute_offset % 60)

        candidate = datetime(
            day.year,
            day.month,
            day.day,
            hour,
            minute,
            tzinfo=tz,
        )
        if candidate > now:
            schedule.append(candidate)

        slot_index += 1
        if slot_index >= clips_per_day:
            slot_index = 0
            day_index += 1

    return schedule[:clip_count]
