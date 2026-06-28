from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import OUTPUT_DIR
from src.discovery.scorer import ScoredVideo


def _ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def save_candidates(
    candidates: list[ScoredVideo],
    *,
    max_age_hours: int,
    output_channel_id: str,
) -> dict[str, Path]:
    output_dir = _ensure_output_dir()
    generated_at = datetime.now(timezone.utc).isoformat()

    payload: dict[str, Any] = {
        "generated_at": generated_at,
        "max_age_hours": max_age_hours,
        "output_channel_id": output_channel_id,
        "count": len(candidates),
        "candidates": [candidate.to_dict() for candidate in candidates],
    }

    json_path = output_dir / "candidates.json"
    csv_path = output_dir / "candidates.csv"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    fieldnames = [
        "rank",
        "url",
        "title",
        "channel_title",
        "view_count",
        "views_per_hour",
        "score",
        "hours_since_publish",
        "source",
        "published_at",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, candidate in enumerate(candidates, start=1):
            writer.writerow(
                {
                    "rank": index,
                    "url": candidate.url,
                    "title": candidate.title,
                    "channel_title": candidate.channel_title,
                    "view_count": candidate.view_count,
                    "views_per_hour": candidate.views_per_hour,
                    "score": candidate.score,
                    "hours_since_publish": candidate.hours_since_publish,
                    "source": candidate.source,
                    "published_at": candidate.published_at,
                }
            )

    history_dir = output_dir / "history"
    history_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    history_path = history_dir / f"candidates-{stamp}.json"
    history_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {"json": json_path, "csv": csv_path, "history": history_path}
