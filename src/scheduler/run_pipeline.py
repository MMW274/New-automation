from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import load_config, load_vizard_config
from src.discovery.channel_scanner import scan_channels
from src.discovery.keyword_search import search_by_keywords
from src.discovery.scorer import score_videos
from src.discovery.youtube_client import YouTubeClient
from src.storage.queue import save_candidates
from src.storage.sheets import sync_to_google_sheets
from src.vizard.pipeline import run_multi_video_pipeline


def run_full_pipeline(*, hours: int | None = None, dry_run: bool = False) -> None:
    app_config = load_config()
    if hours is not None:
        app_config.max_age_hours = hours
        app_config.scoring.max_age_hours = hours

    client = YouTubeClient(app_config.youtube_api_key)

    print(f"Scanning last {app_config.max_age_hours} hours...")
    channel_sources = scan_channels(client, app_config)
    keyword_sources = search_by_keywords(client, app_config)
    sources = {**keyword_sources, **channel_sources}
    unique_ids = list(sources.keys())

    if not unique_ids:
        print("No videos found.")
        return

    video_details = client.get_video_details(unique_ids)
    candidates = score_videos(video_details, sources, app_config.scoring)

    print(f"\nTop {min(8, len(candidates))} candidates:")
    for index, candidate in enumerate(candidates[:8], start=1):
        print(f"  {index}. [{candidate.score:,.0f}] {candidate.title[:70]}")
        print(f"     {candidate.url}")

    if not dry_run:
        save_candidates(
            candidates,
            max_age_hours=app_config.max_age_hours,
            output_channel_id=app_config.output_channel_id,
        )
        if app_config.sheets_enabled:
            sync_to_google_sheets(candidates, app_config)

    vizard_config = load_vizard_config()
    run_multi_video_pipeline(candidates, vizard_config, dry_run=dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover news videos and publish clips to all Vizard-connected platforms."
    )
    parser.add_argument("--hours", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_full_pipeline(hours=args.hours, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
