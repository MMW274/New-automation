from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import load_config
from src.discovery.channel_scanner import scan_channels
from src.discovery.keyword_search import search_by_keywords
from src.discovery.scorer import score_videos
from src.discovery.youtube_client import YouTubeClient
from src.storage.queue import save_candidates
from src.storage.sheets import sync_to_google_sheets


def run_discovery(*, hours: int | None = None, dry_run: bool = False) -> int:
    config = load_config()
    if hours is not None:
        config.max_age_hours = hours
        config.scoring.max_age_hours = hours

    client = YouTubeClient(config.youtube_api_key)

    print(f"Scanning last {config.max_age_hours} hours...")
    channel_sources = scan_channels(client, config)
    print(f"  Channel uploads found: {len(channel_sources)}")

    keyword_sources = search_by_keywords(client, config)
    print(f"  Keyword search matches: {len(keyword_sources)}")

    sources = {**keyword_sources, **channel_sources}
    unique_ids = list(sources.keys())
    print(f"  Unique videos to score: {len(unique_ids)}")

    if not unique_ids:
        print("No videos found in the selected time window.")
        return 0

    video_details = client.get_video_details(unique_ids)
    candidates = score_videos(video_details, sources, config.scoring)

    print(f"\nTop {len(candidates)} candidates:\n")
    for index, candidate in enumerate(candidates, start=1):
        print(
            f"{index:>2}. [{candidate.score:,.0f}] {candidate.views_per_hour:,.0f} views/hr"
        )
        print(f"    {candidate.title[:90]}")
        print(f"    {candidate.url}")
        print(f"    Source: {candidate.source} | Channel: {candidate.channel_title}\n")

    if dry_run:
        print("Dry run — results not saved.")
        return len(candidates)

    paths = save_candidates(
        candidates,
        max_age_hours=config.max_age_hours,
        output_channel_id=config.output_channel_id,
    )
    print(f"Saved JSON: {paths['json']}")
    print(f"Saved CSV:  {paths['csv']}")

    if config.sheets_enabled:
        sync_to_google_sheets(candidates, config)
        print(f"Synced to Google Sheet: {config.sheets_id}")

    if candidates:
        print(f"\nTop pick for Vizard: {candidates[0].url}")

    return len(candidates)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover high-velocity Trump / US news videos for Vizard clipping."
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=None,
        help="Override max age window (default from config/scoring.yaml).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results without writing output files.",
    )
    args = parser.parse_args()
    run_discovery(hours=args.hours, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
