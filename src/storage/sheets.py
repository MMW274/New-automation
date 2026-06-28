from __future__ import annotations

from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials

from src.config import AppConfig
from src.discovery.scorer import ScoredVideo

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "Rank",
    "URL",
    "Title",
    "Channel",
    "Views",
    "Views/Hour",
    "Score",
    "Age (hrs)",
    "Source",
    "Published At",
    "Updated At",
]


def sync_to_google_sheets(candidates: list[ScoredVideo], config: AppConfig) -> None:
    if not config.sheets_enabled:
        return
    if not config.service_account_json or not config.service_account_json.exists():
        raise ValueError(
            "GOOGLE_SHEETS_ENABLED=true but service account JSON is missing at "
            f"{config.service_account_json}"
        )

    credentials = Credentials.from_service_account_file(
        str(config.service_account_json),
        scopes=SCOPES,
    )
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(config.sheets_id)
    worksheet = spreadsheet.sheet1

    updated_at = datetime.now(timezone.utc).isoformat()
    rows = [HEADERS]
    for index, candidate in enumerate(candidates, start=1):
        rows.append(
            [
                index,
                candidate.url,
                candidate.title,
                candidate.channel_title,
                candidate.view_count,
                candidate.views_per_hour,
                candidate.score,
                candidate.hours_since_publish,
                candidate.source,
                candidate.published_at,
                updated_at,
            ]
        )

    worksheet.clear()
    worksheet.update(rows, value_input_option="USER_ENTERED")
