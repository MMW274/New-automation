from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT_DIR / "config"
OUTPUT_DIR = ROOT_DIR / "output"


@dataclass
class ScoringConfig:
    max_age_hours: int
    min_views: int
    min_duration_seconds: int
    max_duration_seconds: int
    relevance_terms: list[str]
    top_n: int
    weights: dict[str, float]
    trusted_channels: list[str]
    channel_boost: float


@dataclass
class AppConfig:
    youtube_api_key: str
    max_age_hours: int
    scoring: ScoringConfig
    channels: list[dict[str, str]]
    keyword_queries: list[str]
    keyword_search_enabled: bool
    sheets_enabled: bool
    sheets_id: str
    service_account_json: Path | None
    output_channel_id: str


@dataclass
class VizardConfig:
    api_key: str
    lang: str
    video_type: int
    ratio_of_clip: int
    prefer_length: list[int]
    subtitle_switch: int
    headline_switch: int
    emoji_switch: int
    highlight_switch: int
    remove_silence_switch: int
    auto_broll_switch: int
    template_id: int | None
    max_clip_number: int
    auto_schedule: bool
    publish_immediately: bool
    publish_stagger_minutes: int
    publish_gap_seconds: int
    min_viral_score: float
    clips_per_day: int
    post_start_hour: int
    post_end_hour: int
    timezone: str
    start_offset_days: int
    social_accounts: dict[str, str]
    poll_interval_seconds: int
    poll_timeout_seconds: int
    dedupe_hours: int
    source_videos_per_run: int
    max_clips_per_run: int
    max_clips_per_source: int
    max_one_video_per_channel: bool
    publish_all_connected: bool
    platform_daily_limits: dict[str, int]
    smart_publish_slots: bool
    per_platform_captions: bool


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_config() -> AppConfig:
    load_dotenv(ROOT_DIR / ".env")

    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "YOUTUBE_API_KEY is missing. Copy .env.example to .env and add your key."
        )

    scoring_raw = _load_yaml(CONFIG_DIR / "scoring.yaml")
    channels_raw = _load_yaml(CONFIG_DIR / "channels.yaml")
    keywords_raw = _load_yaml(CONFIG_DIR / "keywords.yaml")

    scoring = ScoringConfig(
        max_age_hours=int(scoring_raw.get("max_age_hours", 24)),
        min_views=int(scoring_raw.get("min_views", 5000)),
        min_duration_seconds=int(scoring_raw.get("min_duration_seconds", 120)),
        max_duration_seconds=int(scoring_raw.get("max_duration_seconds", 7200)),
        relevance_terms=[t.lower() for t in scoring_raw.get("relevance_terms", [])],
        top_n=int(scoring_raw.get("top_n", 15)),
        weights=scoring_raw.get("weights", {}),
        trusted_channels=scoring_raw.get("trusted_channels", []),
        channel_boost=float(scoring_raw.get("channel_boost", 1.0)),
    )

    service_account = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    service_account_path = (
        Path(service_account) if service_account else None
    )
    if service_account_path and not service_account_path.is_absolute():
        service_account_path = ROOT_DIR / service_account_path

    return AppConfig(
        youtube_api_key=api_key,
        max_age_hours=scoring.max_age_hours,
        scoring=scoring,
        channels=channels_raw.get("channels", []),
        keyword_queries=keywords_raw.get("queries", []),
        keyword_search_enabled=bool(keywords_raw.get("keyword_search_enabled", False)),
        sheets_enabled=os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true",
        sheets_id=os.getenv(
            "GOOGLE_SHEETS_ID",
            "1B24KcqCYUWT3nJG6SF30LBKbkVBg1CUWaqUrjrkLsVc",
        ),
        service_account_json=service_account_path,
        output_channel_id=os.getenv(
            "OUTPUT_YOUTUBE_CHANNEL_ID", "UClUZaCTA-gBR2iB8LKAAhNw"
        ),
    )


def load_vizard_config() -> VizardConfig:
    load_dotenv(ROOT_DIR / ".env")
    api_key = os.getenv("VIZARDAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "VIZARDAI_API_KEY is missing. Add it to .env from Vizard workspace → API."
        )

    raw = _load_yaml(CONFIG_DIR / "vizard.yaml")
    template_id = raw.get("template_id")
    return VizardConfig(
        api_key=api_key,
        lang=str(raw.get("lang", "en")),
        video_type=int(raw.get("video_type", 2)),
        ratio_of_clip=int(raw.get("ratio_of_clip", 1)),
        prefer_length=list(raw.get("prefer_length", [0])),
        subtitle_switch=int(raw.get("subtitle_switch", 1)),
        headline_switch=int(raw.get("headline_switch", 1)),
        emoji_switch=int(raw.get("emoji_switch", 1)),
        highlight_switch=int(raw.get("highlight_switch", 1)),
        remove_silence_switch=int(raw.get("remove_silence_switch", 1)),
        auto_broll_switch=int(raw.get("auto_broll_switch", 1)),
        template_id=int(template_id) if template_id else None,
        max_clip_number=int(raw.get("max_clip_number", 20)),
        auto_schedule=bool(raw.get("auto_schedule", False)),
        publish_immediately=bool(raw.get("publish_immediately", False)),
        publish_stagger_minutes=int(raw.get("publish_stagger_minutes", 45)),
        publish_gap_seconds=int(raw.get("publish_gap_seconds", 10)),
        min_viral_score=float(raw.get("min_viral_score", 9.0)),
        clips_per_day=int(raw.get("clips_per_day", 8)),
        post_start_hour=int(raw.get("post_start_hour", 4)),
        post_end_hour=int(raw.get("post_end_hour", 19)),
        timezone=str(raw.get("timezone", "Europe/Berlin")),
        start_offset_days=int(raw.get("start_offset_days", 1)),
        social_accounts=dict(raw.get("social_accounts", {})),
        poll_interval_seconds=int(raw.get("poll_interval_seconds", 30)),
        poll_timeout_seconds=int(raw.get("poll_timeout_seconds", 1800)),
        dedupe_hours=int(raw.get("dedupe_hours", 48)),
        source_videos_per_run=int(raw.get("source_videos_per_run", 3)),
        max_clips_per_run=int(raw.get("max_clips_per_run", 10)),
        max_clips_per_source=int(raw.get("max_clips_per_source", 2)),
        max_one_video_per_channel=bool(raw.get("max_one_video_per_channel", True)),
        publish_all_connected=bool(raw.get("publish_all_connected", True)),
        platform_daily_limits=dict(raw.get("platform_daily_limits", {})),
        smart_publish_slots=bool(raw.get("smart_publish_slots", True)),
        per_platform_captions=bool(raw.get("per_platform_captions", True)),
    )
