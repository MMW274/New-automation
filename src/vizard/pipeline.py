from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from src.config import OUTPUT_DIR, VizardConfig
from src.discovery.scorer import ScoredVideo
from src.vizard.accounts import PublishTarget, filter_clips_by_score, resolve_publish_targets
from src.vizard.client import VizardClient, VizardError
from src.storage.daily_counts import (
    can_publish,
    platform_slots_remaining,
    record_publish,
)

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
    one_per_channel: bool = True,
) -> list[ScoredVideo]:
    submitted = _load_submitted()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=dedupe_hours)
    recent_ids = {
        entry["video_id"]
        for entry in submitted
        if datetime.fromisoformat(entry["submitted_at"]) > cutoff
    }

    seen_channels: set[str] = set()
    fresh: list[ScoredVideo] = []
    for candidate in candidates:
        if candidate.video_id in recent_ids:
            continue
        channel_key = candidate.channel_title.lower().strip()
        if one_per_channel and channel_key in seen_channels:
            continue
        if one_per_channel:
            seen_channels.add(channel_key)
        fresh.append(candidate)
        if len(fresh) >= limit:
            break
    return fresh


def _platform_needs_title(platform: str) -> bool:
    return platform.lower() == "youtube"


def _platform_daily_limit(config: VizardConfig, platform: str) -> int:
    key = platform.lower()
    if key in ("twitter", "x"):
        key = "twitter"
    return int(config.platform_daily_limits.get(key, 999))


def _stagger_time(stagger_index: int, config: VizardConfig) -> datetime:
    base = datetime.now(timezone.utc) + timedelta(minutes=2)
    return base + timedelta(minutes=stagger_index * config.publish_stagger_minutes)


def _effective_clip_cap(config: VizardConfig, targets: list[PublishTarget]) -> int:
    """Most restrictive platform slot count caps total unique clips this run."""
    caps = [config.max_clips_per_run]
    for target in targets:
        limit = _platform_daily_limit(config, target.platform)
        caps.append(platform_slots_remaining(target.platform, limit))
    return max(min(caps), 0)


def run_vizard_pipeline(
    candidate: ScoredVideo,
    config: VizardConfig,
    targets: list[PublishTarget],
    *,
    dry_run: bool = False,
    clips_remaining: int | None = None,
    stagger_index: int = 0,
) -> tuple[dict[str, Any], int]:
    client = VizardClient(config)
    cap = clips_remaining if clips_remaining is not None else config.max_clips_per_source
    cap = min(cap, config.max_clips_per_source)

    print(f"\n--- Vizard: {candidate.title[:70]} ---")
    print(f"Source: {candidate.url} ({candidate.channel_title})")

    if dry_run:
        print(f"  Would process up to {cap} clips across {len(targets)} platforms")
        return {"dry_run": True, "url": candidate.url, "clips_published": 0}, stagger_index

    project_id = client.create_project(candidate.url, candidate.title[:100])
    print(f"  projectId={project_id}")

    clips = client.wait_for_clips(project_id)
    qualified = filter_clips_by_score(clips, config.min_viral_score)[:cap]
    print(f"  {len(clips)} clips generated, {len(qualified)} qualify (>= {config.min_viral_score})")

    if not qualified:
        return {"project_id": project_id, "clips_published": 0, "published": []}, stagger_index

    published: list[dict[str, Any]] = []
    clips_published = 0

    for clip in qualified:
        video_id = int(clip["videoId"])
        title = str(clip.get("title", ""))
        score = clip.get("viralScore")
        publish_at = _stagger_time(stagger_index, config)
        publish_ms = int(publish_at.timestamp() * 1000)

        eligible_targets = [
            t
            for t in targets
            if can_publish(t.platform, _platform_daily_limit(config, t.platform))
        ]
        if not eligible_targets:
            print("  Daily platform limits reached — stopping clip publish.")
            break

        print(
            f"  Clip {stagger_index + 1} | score={score} | "
            f"schedule={publish_at.isoformat()} | {title[:50]}"
        )

        for target in eligible_targets:
            client.publish_clip(
                final_video_id=video_id,
                social_account_id=target.account_id,
                publish_time_ms=publish_ms,
                title=title if _platform_needs_title(target.platform) else "",
                post="",
            )
            record_publish(target.platform)
            published.append(
                {
                    "platform": target.platform,
                    "username": target.username,
                    "clip_video_id": video_id,
                    "social_account_id": target.account_id,
                    "title": title,
                    "viral_score": score,
                    "publish_at": publish_at.isoformat(),
                }
            )
            print(f"    → {target.platform} ({target.username or target.page})")

        clips_published += 1
        stagger_index += 1
        time.sleep(config.publish_gap_seconds)

    record = {
        "video_id": candidate.video_id,
        "url": candidate.url,
        "title": candidate.title,
        "channel_title": candidate.channel_title,
        "project_id": project_id,
        "clips_published": clips_published,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "published": published,
    }
    submitted = _load_submitted()
    submitted.append(record)
    _save_submitted(submitted)

    return {
        "project_id": project_id,
        "clips_published": clips_published,
        "published": published,
    }, stagger_index


def run_multi_video_pipeline(
    candidates: list[ScoredVideo],
    config: VizardConfig,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    client = VizardClient(config)
    targets = resolve_publish_targets(client, config)

    print("\n=== Vizard multi-video pipeline ===")
    print(f"Sources per run: {config.source_videos_per_run} (max 1 per channel)")
    print(f"Max clips per run: {config.max_clips_per_run}")
    print(f"Stagger: {config.publish_stagger_minutes} min between clips")
    print(f"Min viral score: {config.min_viral_score}")

    if not targets:
        raise VizardError(
            "No active social accounts in Vizard. Connect platforms in Vizard workspace."
        )

    print(f"\nPublishing to {len(targets)} connected account(s):")
    for target in targets:
        limit = _platform_daily_limit(config, target.platform)
        used = limit - platform_slots_remaining(target.platform, limit)
        print(f"  • {target.platform}: {used}/{limit} used today")

    clip_budget = _effective_clip_cap(config, targets)
    print(f"\nClip budget this run: {clip_budget}")

    if clip_budget <= 0:
        print("All platform daily limits reached. Skipping run.")
        return {"sources_processed": 0, "total_clips": 0}

    picks = pick_fresh_candidates(
        candidates,
        dedupe_hours=config.dedupe_hours,
        limit=config.source_videos_per_run,
        one_per_channel=config.max_one_video_per_channel,
    )
    if not picks:
        print("\nNo fresh source videos (all recently processed or same channel).")
        return {"sources_processed": 0, "total_clips": 0}

    print(f"\nSelected {len(picks)} source video(s):")
    for index, pick in enumerate(picks, start=1):
        print(f"  {index}. [{pick.channel_title}] {pick.title[:55]}")
        print(f"     {pick.url}")

    if dry_run:
        for pick in picks:
            run_vizard_pipeline(pick, config, targets, dry_run=True)
        return {"dry_run": True, "sources": len(picks)}

    total_clips = 0
    stagger_index = 0
    results: list[dict[str, Any]] = []
    for pick in picks:
        remaining = clip_budget - total_clips
        if remaining <= 0:
            break
        result, stagger_index = run_vizard_pipeline(
            pick,
            config,
            targets,
            clips_remaining=min(remaining, config.max_clips_per_source),
            stagger_index=stagger_index,
        )
        clips = result.get("clips_published", 0)
        total_clips += clips
        results.append(result)
        if total_clips >= clip_budget:
            break

    print(f"\nDone. {total_clips} clips scheduled across {len(targets)} platform(s).")
    print(f"Log: {SUBMITTED_PATH}")
    return {"sources_processed": len(results), "total_clips": total_clips, "results": results}
