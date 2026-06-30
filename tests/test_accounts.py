from __future__ import annotations

from dataclasses import replace

from src.config import VizardConfig
from src.vizard.accounts import resolve_publish_targets


def _config(**overrides) -> VizardConfig:
    base = VizardConfig(
        api_key="test",
        lang="en",
        video_type=2,
        ratio_of_clip=1,
        prefer_length=[0],
        subtitle_switch=1,
        headline_switch=1,
        emoji_switch=1,
        highlight_switch=1,
        remove_silence_switch=1,
        auto_broll_switch=1,
        template_id=None,
        max_clip_number=20,
        auto_schedule=False,
        publish_immediately=False,
        publish_stagger_minutes=20,
        publish_gap_seconds=10,
        min_viral_score=8.5,
        clips_per_day=8,
        post_start_hour=4,
        post_end_hour=19,
        timezone="UTC",
        start_offset_days=1,
        social_accounts={
            "youtube": "Fill Viz",
            "tiktok": "today_news98",
            "twitter": "Fill Viz",
        },
        poll_interval_seconds=30,
        poll_timeout_seconds=1800,
        dedupe_hours=48,
        source_videos_per_run=5,
        max_clips_per_run=5,
        max_clips_per_source=2,
        max_one_video_per_channel=True,
        publish_all_connected=False,
        excluded_accounts=["Shamy", "Amy Sheldon"],
        platform_daily_limits={"youtube": 3, "tiktok": 5, "twitter": 4},
        smart_publish_slots=False,
        per_platform_captions=True,
        safety_filter_enabled=True,
        blocked_terms=[],
    )
    return replace(base, **overrides)


class _FakeClient:
    def list_social_accounts(self) -> list[dict]:
        return [
            {"id": "1", "platform": "TikTok", "username": "today_news98", "page": "", "status": "active"},
            {"id": "2", "platform": "YouTube", "username": "Fill Viz", "page": "", "status": "active"},
            {"id": "3", "platform": "Twitter", "username": "Fill Viz", "page": "", "status": "active"},
            {"id": "4", "platform": "Twitter", "username": "Shamy", "page": "", "status": "active"},
            {"id": "5", "platform": "Instagram", "username": "Amy Sheldon", "page": "", "status": "active"},
        ]


def test_resolve_publish_targets_news_accounts_only() -> None:
    targets = resolve_publish_targets(_FakeClient(), _config())
    usernames = {t.username for t in targets}
    assert usernames == {"today_news98", "Fill Viz"}
    assert len(targets) == 3
    assert "Shamy" not in usernames
    assert "Amy Sheldon" not in usernames


def test_excluded_accounts_block_even_when_publish_all_connected() -> None:
    targets = resolve_publish_targets(_FakeClient(), _config(publish_all_connected=True))
    usernames = {t.username for t in targets}
    assert "Shamy" not in usernames
    assert "Amy Sheldon" not in usernames
    assert len(targets) == 3
