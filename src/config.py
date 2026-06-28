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


@dataclass
class AppConfig:
    youtube_api_key: str
    max_age_hours: int
    scoring: ScoringConfig
    channels: list[dict[str, str]]
    keyword_queries: list[str]
    sheets_enabled: bool
    sheets_id: str
    service_account_json: Path | None
    output_channel_id: str


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
