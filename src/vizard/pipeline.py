from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from src.config import OUTPUT_DIR, VizardConfig
from src.discovery.scorer import ScoredVideo
from src.scheduler.optimal_slots import next_optimal_slot
from src.safety.content_filter import (
    DEFAULT_BLOCKED_TERMS,
    classify as safety_classify,
    hold_for_review,
)
from src.vizard.accounts import PublishTarget, filter_clips_by_score, resolve_publish_targets
from src.vizard.client import VizardClient, VizardError, VizardFatal, VizardSkipSource
from src.storage import dedupe_ledger
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


def _all_submitted_video_ids() -> set[str]:
    """Every YouTube source video ever submitted — permanent dedupe key.

    Reads BOTH the long-lived dedupe ledger AND the current submitted.json
    (which may have been pruned to the recent window). Once a source has
    reached either list it MUST NEVER be re-submitted, even years later.
    """
    from_log = {entry["video_id"] for entry in _load_submitted() if entry.get("video_id")}
    return dedupe_ledger.video_ids() | from_log


def _all_published_clip_ids() -> set[int]:
    """Defensive second layer: every Vizard finalVideoId we've ever published.

    Reads BOTH the ledger and the current submitted.json.
    """
    ids: set[int] = set(dedupe_ledger.clip_ids())
    for entry in _load_submitted():
        for pub in entry.get("published", []) or []:
            cid = pub.get("clip_video_id")
            if cid is not None:
                try:
                    ids.add(int(cid))
                except (TypeError, ValueError):
                    continue
    return ids


def pick_fresh_candidates(
    candidates: list[ScoredVideo],
    *,
    dedupe_hours: int = 0,  # kept for backward-compat; ignored (permanent dedupe)
    limit: int,
    one_per_channel: bool = True,
) -> list[ScoredVideo]:
    ever_submitted = _all_submitted_video_ids()
    seen_channels: set[str] = set()
    fresh: list[ScoredVideo] = []
    for candidate in candidates:
        if candidate.video_id in ever_submitted:
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


def _slot_for_target(
    target: PublishTarget,
    *,
    stagger_index: int,
    config: VizardConfig,
    used_slots_by_platform: dict[str, set[datetime]],
) -> datetime:
    """Pick the next platform-optimal publish time for this target.

    Falls back to legacy `_stagger_time` when slot-aware publishing is disabled.
    """
    if not getattr(config, "smart_publish_slots", True):
        return _stagger_time(stagger_index, config)

    platform_key = target.platform.lower()
    if platform_key in ("x",):
        platform_key = "twitter"

    used = used_slots_by_platform.setdefault(platform_key, set())
    after = datetime.now(timezone.utc) + timedelta(
        minutes=max(config.publish_stagger_minutes // 6, 5)
    )
    slot = next_optimal_slot(
        platform_key,
        after=after,
        used_slots=used,
        fallback_interval_minutes=config.publish_stagger_minutes,
    )
    used.add(slot)
    return slot


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
    used_slots_by_platform: dict[str, set[datetime]] | None = None,
) -> tuple[dict[str, Any], int]:
    client = VizardClient(config)
    cap = clips_remaining if clips_remaining is not None else config.max_clips_per_source
    cap = min(cap, config.max_clips_per_source)
    if used_slots_by_platform is None:
        used_slots_by_platform = {}

    print(f"\n--- Vizard: {candidate.title[:70]} ---")
    print(f"Source: {candidate.url} ({candidate.channel_title})")

    if dry_run:
        print(f"  Would process up to {cap} clips across {len(targets)} platforms")
        return {"dry_run": True, "url": candidate.url, "clips_published": 0}, stagger_index

    project_id = client.create_project(candidate.url, candidate.title[:100])
    print(f"  projectId={project_id}")

    # Lock this source in the permanent ledger IMMEDIATELY so a mid-run crash,
    # a pruned submitted.json, or a bad cache restore can never free it.
    dedupe_ledger.remember_video(candidate.video_id)

    # Record submission so a mid-run crash still locks this source out.
    pre_record = {
        "video_id": candidate.video_id,
        "url": candidate.url,
        "title": candidate.title,
        "channel_title": candidate.channel_title,
        "project_id": project_id,
        "clips_published": 0,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "published": [],
        "status": "in_progress",
    }
    submitted_log = _load_submitted()
    submitted_log.append(pre_record)
    _save_submitted(submitted_log)

    clips = client.wait_for_clips(project_id)
    qualified = filter_clips_by_score(clips, config.min_viral_score)[:cap]
    print(f"  {len(clips)} clips generated, {len(qualified)} qualify (>= {config.min_viral_score})")

    already_published_clip_ids = _all_published_clip_ids()
    published: list[dict[str, Any]] = []
    clips_published = 0
    status = "complete"

    try:
        for clip in qualified:
            video_id = int(clip["videoId"])
            if video_id in already_published_clip_ids:
                print(f"  Skip clip {video_id} — already published in a prior run.")
                continue
            already_published_clip_ids.add(video_id)
            dedupe_ledger.remember_clip(video_id)
            title = str(clip.get("title", ""))
            score = clip.get("viralScore")

            if getattr(config, "safety_filter_enabled", True):
                blocked = (
                    tuple(config.blocked_terms)
                    if getattr(config, "blocked_terms", None)
                    else DEFAULT_BLOCKED_TERMS
                )
                transcript = str(clip.get("transcript", "") or "")
                verdict = safety_classify(f"{title} {transcript}", blocked_terms=blocked)
                if not verdict.safe:
                    print(f"  Held for review (safety: {verdict.reason}) — {title[:60]}")
                    hold_for_review(
                        {
                            "video_id": video_id,
                            "project_id": project_id,
                            "title": title,
                            "viral_score": score,
                            "source": candidate.url,
                            "matched_terms": verdict.matched_terms,
                        }
                    )
                    continue

            eligible_targets = [
                t
                for t in targets
                if can_publish(t.platform, _platform_daily_limit(config, t.platform))
            ]
            if not eligible_targets:
                print("  Daily platform limits reached — stopping clip publish.")
                break

            print(f"  Clip {stagger_index + 1} | score={score} | {title[:60]}")

            for target in eligible_targets:
                publish_at = _slot_for_target(
                    target,
                    stagger_index=stagger_index,
                    config=config,
                    used_slots_by_platform=used_slots_by_platform,
                )
                publish_ms = int(publish_at.timestamp() * 1000)
                caption = ""
                if getattr(config, "per_platform_captions", True):
                    caption = client.ai_caption(
                        final_video_id=video_id,
                        platform=target.platform,
                    )
                client.publish_clip(
                    final_video_id=video_id,
                    social_account_id=target.account_id,
                    publish_time_ms=publish_ms,
                    title=title if _platform_needs_title(target.platform) else "",
                    post=caption,
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
                print(
                    f"    → {target.platform} ({target.username or target.page}) "
                    f"@ {publish_at.astimezone(timezone.utc).strftime('%a %H:%MZ')}"
                )

            clips_published += 1
            stagger_index += 1
            time.sleep(config.publish_gap_seconds)
    except Exception as error:
        status = f"partial:{type(error).__name__}"
        print(f"  Publish loop aborted ({error}); keeping dedupe record intact.")
        raise
    finally:
        # Always persist progress — even on raise — so the source can never be
        # picked up again. Update the pre_record in-place.
        submitted_log = _load_submitted()
        for entry in submitted_log:
            if entry.get("project_id") == project_id:
                entry["clips_published"] = clips_published
                entry["published"] = published
                entry["status"] = status
                break
        _save_submitted(submitted_log)

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
    used_slots_by_platform: dict[str, set[datetime]] = {}
    results: list[dict[str, Any]] = []
    for pick in picks:
        remaining = clip_budget - total_clips
        if remaining <= 0:
            break
        try:
            result, stagger_index = run_vizard_pipeline(
                pick,
                config,
                targets,
                clips_remaining=min(remaining, config.max_clips_per_source),
                stagger_index=stagger_index,
                used_slots_by_platform=used_slots_by_platform,
            )
        except VizardFatal:
            # Invalid key / out of credits — no point continuing this run.
            raise
        except VizardSkipSource as error:
            print(f"  Skipping source ({error}); continuing with next pick.")
            continue
        except VizardError as error:
            print(f"  Source failed ({error}); continuing with next pick.")
            continue
        clips = result.get("clips_published", 0)
        total_clips += clips
        results.append(result)
        if total_clips >= clip_budget:
            break

    print(f"\nDone. {total_clips} clips scheduled across {len(targets)} platform(s).")
    print(f"Log: {SUBMITTED_PATH}")
    return {"sources_processed": len(results), "total_clips": total_clips, "results": results}
