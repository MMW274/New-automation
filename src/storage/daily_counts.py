from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.config import OUTPUT_DIR

DAILY_COUNTS_PATH = OUTPUT_DIR / "daily_counts.json"


def _normalize_platform(platform: str) -> str:
    name = platform.lower()
    if name in ("twitter", "x"):
        return "twitter"
    return name


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_daily_counts() -> dict[str, dict[str, int]]:
    if not DAILY_COUNTS_PATH.exists():
        return {}
    return json.loads(DAILY_COUNTS_PATH.read_text(encoding="utf-8"))


def save_daily_counts(data: dict[str, dict[str, int]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DAILY_COUNTS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_platform_count(platform: str) -> int:
    data = load_daily_counts()
    return data.get(_today_key(), {}).get(_normalize_platform(platform), 0)


def can_publish(platform: str, daily_limit: int) -> bool:
    if daily_limit <= 0:
        return True
    return get_platform_count(platform) < daily_limit


def record_publish(platform: str) -> None:
    data = load_daily_counts()
    today = _today_key()
    day = data.setdefault(today, {})
    key = _normalize_platform(platform)
    day[key] = day.get(key, 0) + 1
    save_daily_counts(data)


def platform_slots_remaining(platform: str, daily_limit: int) -> int:
    if daily_limit <= 0:
        return 999
    return max(daily_limit - get_platform_count(platform), 0)
