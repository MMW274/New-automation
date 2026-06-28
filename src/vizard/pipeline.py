from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.config import OUTPUT_DIR, VizardConfig
from src.discovery.scorer import ScoredVideo
from src.vizard.accounts import PublishTarget, filter_clips_by_score, resolve_publish_targets
from src.vizard.client import VizardClient, VizardError
from src.vizard.scheduler import build_publish_schedule

SUBMITTED_PATH = OUTPUT_DIR / "submitted.json"


def _load_submitted() -> list[dict[str, Any]]:
    if not SUBMITTED_PATH.exists():
        return []
    return json.loads(SUBMITTED_PATH.read_text(encoding="utf-8"))


def _save_submitted(records: list[dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SUBMITTED_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")


def pick_fresh_candidates(
    candidates: list[ScoredVideo],
    *,
    dedupe_hours: int,
    limit: int,
) -> list[ScoredVideo]:
    submitted = _load_submitted()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=dedupe_hours)
    recent_ids = {
        entry["video_id"]
        for entry in submitted
        if datetime.fromisoformat(entry["submitted_at"]) > cutoff
    }

    fresh: list[ScoredVideo] = []
    for candidate in candidates:
        if candidate.video_id in recent_ids:
            continue
        fresh.append(candidate)
        if len(fresh) >= limit:
            break
    return fresh


def _platform_needs_title(platform: str) -> bool:
    return platform.lower() == "youtube"


def run_vizard_pipeline(
    candidate: ScoredVideo,
    config: VizardConfig,
    targets: list[PublishTarget],
    *,
    dry_run: bool = False,
    clips_remaining: int | None = None,
) -> dict[str, Any]:
    client = VizardClient(config)
    cap = clips_remaining if clips_remaining is not None else config.max_clips_per_source
    cap = min(cap, config.max_clips_per_source)

    print(f"\n--- Vizard: {candidate.title[:70]} ---")
    print(f"Source: {candidate.url}")

    if dry_run:
        print(f"  Would process up to {cap} clips across {len(targets)} platforms")
        return {"dry_run": True, "url": candidate.url, "clips_published": 0}

    project_id = client.create_project(candidate.url, candidate.title[:100])
    print(f"  projectId={project_id}")

    clips = client.wait_for_clips(project_id)
    qualified = filter_clips_by_score(clips, config.min_viral_score)[:cap]
    print(f"  {len(clips)} clips generated, {len(qualified)} qualify (>= {config.min_viral_score})")

    if not qualified:
        return {"project_id": project_id, "clips_published": 0, "published": []}

    published: list[dict[str, Any]] = []
    for index, clip in enumerate(qualified, start=1):
        video_id = int(clip["videoId"])
        title = str(clip.get("title", ""))
        score = clip.get("viralScore")
        print(f"  Clip {index} | score={score} | {title[:60]}")

        for target in targets:
            client.publish_clip(
                final_video_id=video_id,
                social_account_id=target.account_id,
                publish_time_ms=None if config.publish_immediately else None,
                title=title if _platform_needs_title(target.platform) else "",
                post="",
            )
            published.append(
                {
                    "platform": target.platform,
                    "username": target.username,
                    "clip_video_id": video_id,
                    "social_account_id": target.account_id,
                    "title": title,
                    "viral_score": score,
                }
            )
            print(f"    → {target.platform} ({target.username or target.page})")

        if index < len(qualified):
            time.sleep(config.publish_gap_seconds)

    record = {
        "video_id": candidate.video_id,
        "url": candidate.url,
        "title": candidate.title,
        "project_id": project_id,
        "clips_published": len(qualified),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "published": published,
    }
    submitted = _load_submitted()
    submitted.append(record)
    _save_submitted(submitted)

    return {
        "project_id": project_id,
        "clips_published": len(qualified),
        "published": published,
    }


def run_multi_video_pipeline(
    candidates: list[ScoredVideo],
    config: VizardConfig,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    client = VizardClient(config)
    targets = resolve_publish_targets(client, config)

    print("\n=== Vizard multi-video pipeline ===")
    print(f"Sources per run: {config.source_videos_per_run}")
    print(f"Max clips total: {config.max_clips_per_run}")
    print(f"Min viral score: {config.min_viral_score}")
    print(f"Publish mode: {'immediate' if config.publish_immediately else 'scheduled'}")

    if not targets:
        raise VizardError(
            "No active social accounts in Vizard. Connect YouTube, TikTok, Facebook, X "
            "in Vizard workspace, then run: python -m src.vizard.list_accounts"
        )

    print(f"\nPublishing to {len(targets)} connected account(s):")
    for target in targets:
        limit = config.platform_daily_limits.get(target.platform.lower(), "—")
        print(f"  • {target.platform}: {target.username or target.page} (daily safe ~{limit})")

    picks = pick_fresh_candidates(
        candidates,
        dedupe_hours=config.dedupe_hours,
        limit=config.source_videos_per_run,
    )
    if not picks:
        print("\nNo fresh source videos (all recently processed).")
        return {"sources_processed": 0, "total_clips": 0}

    print(f"\nSelected {len(picks)} source video(s):")
    for index, pick in enumerate(picks, start=1):
        print(f"  {index}. {pick.title[:65]}")
        print(f"     {pick.url}")

    if dry_run:
        for pick in picks:
            run_vizard_pipeline(pick, config, targets, dry_run=True)
        return {"dry_run": True, "sources": len(picks)}

    total_clips = 0
    results: list[dict[str, Any]] = []
    for pick in picks:
        remaining = config.max_clips_per_run - total_clips
        if remaining <= 0:
            break
        result = run_vizard_pipeline(
            pick,
            config,
            targets,
            clips_remaining=remaining,
        )
        clips = result.get("clips_published", 0)
        total_clips += clips
        results.append(result)
        if total_clips >= config.max_clips_per_run:
            break

    print(f"\nDone. {total_clips} clips published across {len(targets)} platform(s).")
    print(f"Log: {SUBMITTED_PATH}")
    return {"sources_processed": len(results), "total_clips": total_clips, "results": results}
