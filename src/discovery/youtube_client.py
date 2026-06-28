from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class YouTubeClient:
    """Thin wrapper around YouTube Data API v3."""

    def __init__(self, api_key: str) -> None:
        self._service = build("youtube", "v3", developerKey=api_key, cache_discovery=False)

    def get_uploads_playlist_id(self, channel_id: str) -> str | None:
        response = (
            self._service.channels()
            .list(part="contentDetails", id=channel_id, maxResults=1)
            .execute()
        )
        items = response.get("items", [])
        if not items:
            return None
        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    def list_playlist_videos(
        self, playlist_id: str, published_after: datetime, max_results: int = 50
    ) -> list[str]:
        video_ids: list[str] = []
        request = self._service.playlistItems().list(
            part="contentDetails,snippet",
            playlistId=playlist_id,
            maxResults=min(max_results, 50),
        )

        while request is not None:
            response = request.execute()
            for item in response.get("items", []):
                published_at = item["snippet"]["publishedAt"]
                published_dt = datetime.fromisoformat(
                    published_at.replace("Z", "+00:00")
                )
                if published_dt < published_after:
                    return video_ids
                video_ids.append(item["contentDetails"]["videoId"])

            request = self._service.playlistItems().list_next(request, response)
            if request is None:
                break

        return video_ids

    def search_videos(
        self,
        query: str,
        published_after: datetime,
        max_results: int = 25,
    ) -> list[str]:
        published_after_iso = published_after.astimezone(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        response = (
            self._service.search()
            .list(
                part="id",
                q=query,
                type="video",
                order="viewCount",
                publishedAfter=published_after_iso,
                maxResults=min(max_results, 50),
                relevanceLanguage="en",
                regionCode="US",
            )
            .execute()
        )
        return [
            item["id"]["videoId"]
            for item in response.get("items", [])
            if item["id"].get("videoId")
        ]

    def get_video_details(self, video_ids: list[str]) -> list[dict[str, Any]]:
        if not video_ids:
            return []

        details: list[dict[str, Any]] = []
        for index in range(0, len(video_ids), 50):
            chunk = video_ids[index : index + 50]
            response = (
                self._service.videos()
                .list(part="snippet,statistics,contentDetails", id=",".join(chunk))
                .execute()
            )
            details.extend(response.get("items", []))
        return details

    @staticmethod
    def parse_duration_seconds(iso_duration: str) -> int:
        """Parse ISO 8601 duration (PT#H#M#S) into total seconds."""
        hours = minutes = seconds = 0
        value = iso_duration.replace("PT", "")
        number = ""
        for char in value:
            if char.isdigit():
                number += char
            elif char == "H":
                hours = int(number or 0)
                number = ""
            elif char == "M":
                minutes = int(number or 0)
                number = ""
            elif char == "S":
                seconds = int(number or 0)
                number = ""
        return hours * 3600 + minutes * 60 + seconds

    @staticmethod
    def video_url(video_id: str) -> str:
        return f"https://www.youtube.com/watch?v={video_id}"

    def safe_execute(self, label: str, func) -> Any:
        try:
            return func()
        except HttpError as error:
            raise RuntimeError(f"YouTube API error during {label}: {error}") from error
