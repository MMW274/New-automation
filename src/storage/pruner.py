"""Periodic state housekeeping.

- `submitted.json`: archives entries older than N days (default 180) to
  `output/history/submitted-<YYYY>.json`, keeps recent in-place. The
  permanent dedupe guarantee is preserved by `dedupe_ledger.py` so pruned
  entries never become re-submittable.
- `daily_counts.json`: keeps only the last `keep_days` UTC days.
- Always backfills the dedupe ledger from `submitted.json` BEFORE pruning.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config import OUTPUT_DIR
from src.storage import dedupe_ledger

SUBMITTED_PATH = OUTPUT_DIR / "submitted.json"
DAILY_COUNTS_PATH = OUTPUT_DIR / "daily_counts.json"
HISTORY_DIR = OUTPUT_DIR / "history"

DEFAULT_KEEP_DAYS = 180
DEFAULT_COUNTS_KEEP = 60


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError):
        return None


def prune_submitted(*, keep_days: int = DEFAULT_KEEP_DAYS) -> dict[str, int]:
    """Archive entries older than `keep_days` into per-year history files."""
    if not SUBMITTED_PATH.exists():
        return {"kept": 0, "archived": 0}

    # Safety net: make absolutely sure the dedupe ledger has everything before
    # we move anything out of submitted.json.
    dedupe_ledger.seed_from_submitted(SUBMITTED_PATH)

    records = json.loads(SUBMITTED_PATH.read_text(encoding="utf-8"))
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)

    keep: list[dict] = []
    by_year: dict[int, list[dict]] = defaultdict(list)
    for entry in records:
        when = _parse_dt(entry.get("submitted_at", ""))
        if when is None or when >= cutoff:
            keep.append(entry)
        else:
            by_year[when.year].append(entry)

    if not by_year:
        return {"kept": len(keep), "archived": 0}

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    archived = 0
    for year, entries in by_year.items():
        path = HISTORY_DIR / f"submitted-{year}.json"
        existing: list[dict] = []
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
        seen = {(e.get("video_id"), e.get("project_id")) for e in existing}
        for entry in entries:
            key = (entry.get("video_id"), entry.get("project_id"))
            if key not in seen:
                existing.append(entry)
                seen.add(key)
                archived += 1
        path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    SUBMITTED_PATH.write_text(json.dumps(keep, indent=2), encoding="utf-8")
    return {"kept": len(keep), "archived": archived}


def prune_daily_counts(*, keep_days: int = DEFAULT_COUNTS_KEEP) -> int:
    if not DAILY_COUNTS_PATH.exists():
        return 0
    data: dict[str, dict[str, int]] = json.loads(
        DAILY_COUNTS_PATH.read_text(encoding="utf-8")
    )
    cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).date()
    kept: dict[str, dict[str, int]] = {}
    for day_str, counts in data.items():
        try:
            day = datetime.strptime(day_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if day >= cutoff:
            kept[day_str] = counts
    DAILY_COUNTS_PATH.write_text(json.dumps(kept, indent=2), encoding="utf-8")
    return len(data) - len(kept)


def run_prune(
    *,
    submitted_keep_days: int = DEFAULT_KEEP_DAYS,
    counts_keep_days: int = DEFAULT_COUNTS_KEEP,
) -> dict[str, int]:
    s_result = prune_submitted(keep_days=submitted_keep_days)
    c_pruned = prune_daily_counts(keep_days=counts_keep_days)
    return {**s_result, "daily_counts_pruned": c_pruned}


def main() -> None:
    result = run_prune()
    print(f"Pruner: {result}")


if __name__ == "__main__":
    main()
