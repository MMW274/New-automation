"""Weekly performance snapshot.

For every source video we have ever submitted, fetch the source video's
current YouTube statistics (views, likes, comments) so we can see whether
our virality scoring is actually picking winners.

Output: `output/performance.json` (a single rolling snapshot, overwritten
each run; the workflow uploads it as an artifact for historical record).

Quota cost: ceil(N / 50) units where N is the number of distinct source
video IDs we've ever submitted. At ~3 sources/run × 3 runs/day, even after
a full year that's ~3300 sources = 66 units. Cheap.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import OUTPUT_DIR, load_config
from src.discovery.youtube_client import YouTubeClient
from src.storage import dedupe_ledger

PERFORMANCE_PATH = OUTPUT_DIR / "performance.json"
SUBMITTED_PATH = OUTPUT_DIR / "submitted.json"
HISTORY_DIR = OUTPUT_DIR / "history"


def _load_all_submitted() -> list[dict]:
    """Recent submitted.json + every archived history file."""
    records: list[dict] = []
    if SUBMITTED_PATH.exists():
        records.extend(json.loads(SUBMITTED_PATH.read_text(encoding="utf-8")))
    if HISTORY_DIR.exists():
        for path in sorted(HISTORY_DIR.glob("submitted-*.json")):
            try:
                records.extend(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
    return records


def collect_performance(limit: int | None = None) -> dict:
    config = load_config()
    client = YouTubeClient(config.youtube_api_key)

    submitted = _load_all_submitted()
    by_video: dict[str, dict] = {}
    for entry in submitted:
        vid = entry.get("video_id")
        if not vid:
            continue
        # Keep the most recent record per source video (we're permanent-dedupe
        # so there is normally exactly one; but be defensive).
        prev = by_video.get(vid)
        if prev is None or entry.get("submitted_at", "") > prev.get("submitted_at", ""):
            by_video[vid] = entry

    video_ids = list(by_video.keys())
    if limit:
        video_ids = video_ids[-limit:]
    print(f"Fetching stats for {len(video_ids)} source video(s)...")

    details = client.get_video_details(video_ids)
    stats_by_id = {item["id"]: item for item in details}

    rows: list[dict] = []
    for vid in video_ids:
        record = by_video[vid]
        api = stats_by_id.get(vid, {})
        stats = api.get("statistics", {})
        snippet = api.get("snippet", {})
        rows.append(
            {
                "video_id": vid,
                "url": record.get("url"),
                "title": record.get("title"),
                "channel_title": record.get("channel_title"),
                "submitted_at": record.get("submitted_at"),
                "clips_published": record.get("clips_published", 0),
                "platforms": sorted(
                    {p.get("platform") for p in record.get("published", []) if p.get("platform")}
                ),
                "now_views": int(stats.get("viewCount", 0)),
                "now_likes": int(stats.get("likeCount", 0)),
                "now_comments": int(stats.get("commentCount", 0)),
                "still_available": bool(snippet),
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(rows),
        "ledger_video_count": len(dedupe_ledger.video_ids()),
        "ledger_clip_count": len(dedupe_ledger.clip_ids()),
        "rows": sorted(rows, key=lambda r: r["now_views"], reverse=True),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PERFORMANCE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Snapshot performance of published sources.")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    result = collect_performance(limit=args.limit)
    print(
        f"Wrote {PERFORMANCE_PATH} — {result['source_count']} sources, "
        f"top now-views: {result['rows'][0]['now_views'] if result['rows'] else 0}"
    )


if __name__ == "__main__":
    main()
