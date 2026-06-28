from __future__ import annotations

import logging
import time
from typing import Any

import requests

from src.config import VizardConfig

BASE_URL = "https://elb-api.vizard.ai/hvizard-server-front/open-api/v1"

LOG = logging.getLogger(__name__)

# Vizard response codes (from vizard-api-skills/SKILL.md)
CODE_OK = 2000
CODE_PROCESSING = 1000
CODE_INVALID_KEY = 4001
CODE_RATE_LIMIT = 4003
CODE_NO_CREDITS = 4007
CODE_DOWNLOAD_FAILED = 4008

RETRY_CODES = {CODE_RATE_LIMIT}
FATAL_CODES = {CODE_INVALID_KEY, CODE_NO_CREDITS}
SKIP_CODES = {CODE_DOWNLOAD_FAILED}


class VizardError(RuntimeError):
    """Generic Vizard API failure."""


class VizardSkipSource(VizardError):
    """Source should be skipped (e.g. 4008 download failed) but pipeline continues."""


class VizardFatal(VizardError):
    """Unrecoverable error (e.g. 4001 invalid key, 4007 out of credits)."""


class VizardClient:
    MAX_RETRIES = 4
    INITIAL_BACKOFF_SECONDS = 5

    def __init__(self, config: VizardConfig) -> None:
        self.config = config
        self._headers = {
            "Content-Type": "application/json",
            "VIZARDAI_API_KEY": config.api_key,
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{BASE_URL}{path}"
        backoff = self.INITIAL_BACKOFF_SECONDS
        last_data: dict[str, Any] = {}

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = requests.request(
                    method,
                    url,
                    headers=self._headers,
                    json=payload,
                    timeout=60,
                )
            except requests.RequestException as error:
                if attempt == self.MAX_RETRIES:
                    raise VizardError(f"Vizard network error on {path}: {error}") from error
                LOG.warning("Vizard network error (attempt %d/%d): %s",
                            attempt, self.MAX_RETRIES, error)
                time.sleep(backoff)
                backoff *= 2
                continue

            # Retry transient HTTP 5xx (server-side hiccups).
            if 500 <= response.status_code < 600:
                if attempt == self.MAX_RETRIES:
                    raise VizardError(f"Vizard {response.status_code} on {path} after retries")
                LOG.warning("Vizard HTTP %s (attempt %d/%d), backing off %ds",
                            response.status_code, attempt, self.MAX_RETRIES, backoff)
                time.sleep(backoff)
                backoff *= 2
                continue

            try:
                data = response.json()
            except ValueError as error:
                raise VizardError(
                    f"Vizard non-JSON response on {path}: {response.text[:200]}"
                ) from error
            last_data = data
            code = data.get("code")

            if code in FATAL_CODES:
                raise VizardFatal(f"Vizard FATAL on {path}: {data}")
            if code in SKIP_CODES:
                raise VizardSkipSource(f"Vizard skip-source on {path}: {data}")
            if code in RETRY_CODES:
                if attempt == self.MAX_RETRIES:
                    raise VizardError(f"Vizard rate limited on {path} after {attempt} attempts")
                LOG.warning("Vizard rate limited (attempt %d/%d), backing off %ds",
                            attempt, self.MAX_RETRIES, backoff)
                time.sleep(backoff)
                backoff *= 2
                continue
            return data

        raise VizardError(f"Vizard exhausted retries on {path}: {last_data}")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._request("POST", path, payload=payload)
        if data.get("code") != CODE_OK:
            raise VizardError(f"Vizard API error on {path}: {data}")
        return data

    def _get(self, path: str) -> dict[str, Any]:
        # Note: returns raw response (caller inspects `code`) — used by
        # wait_for_clips which polls for 1000 (still processing).
        return self._request("GET", path)

    def create_project(self, video_url: str, project_name: str) -> int:
        payload: dict[str, Any] = {
            "videoUrl": video_url,
            "videoType": self.config.video_type,
            "lang": self.config.lang,
            "preferLength": self.config.prefer_length,
            "getClips": 1,
            "ratioOfClip": self.config.ratio_of_clip,
            "subtitleSwitch": self.config.subtitle_switch,
            "headlineSwitch": self.config.headline_switch,
            "emojiSwitch": self.config.emoji_switch,
            "highlightSwitch": self.config.highlight_switch,
            "removeSilenceSwitch": self.config.remove_silence_switch,
            "autoBrollSwitch": self.config.auto_broll_switch,
            "maxClipNumber": self.config.max_clip_number,
            "projectName": project_name,
        }
        if self.config.template_id:
            payload["templateId"] = self.config.template_id

        data = self._post("/project/create", payload)
        return int(data["projectId"])

    def wait_for_clips(self, project_id: int) -> list[dict[str, Any]]:
        deadline = time.time() + self.config.poll_timeout_seconds
        while time.time() < deadline:
            data = self._get(f"/project/query/{project_id}")
            code = data.get("code")
            if code == 2000 and data.get("videos"):
                return data["videos"]
            if code not in (1000, 2000):
                raise VizardError(f"Processing failed for project {project_id}: {data}")

            elapsed = int(self.config.poll_timeout_seconds - (deadline - time.time()))
            print(f"  Vizard processing... ({elapsed}s elapsed)")
            time.sleep(self.config.poll_interval_seconds)

        raise VizardError(f"Timed out waiting for project {project_id}")

    def list_social_accounts(self) -> list[dict[str, Any]]:
        data = self._get("/project/social-accounts")
        accounts = data.get("publishAccounts") or data.get("accounts") or []
        return [account for account in accounts if account.get("status") == "active"]

    # Vizard /project/ai-social platform enum (from SKILL.md)
    AI_SOCIAL_PLATFORM = {
        "general": 1,
        "tiktok": 2,
        "instagram": 3,
        "youtube": 4,
        "facebook": 5,
        "linkedin": 6,
        "twitter": 7,
        "x": 7,
    }
    AI_SOCIAL_TONE_CATCHY = 2

    def ai_caption(
        self,
        *,
        final_video_id: int,
        platform: str,
        tone: int = AI_SOCIAL_TONE_CATCHY,
    ) -> str:
        """Generate a platform-native caption + hashtags via Vizard AI.

        Returns empty string on any non-fatal error so the caller can fall
        back to Vizard's default auto-caption (`post=""`).
        """
        platform_id = self.AI_SOCIAL_PLATFORM.get(platform.lower())
        if not platform_id:
            return ""
        payload = {
            "finalVideoId": final_video_id,
            "aiSocialPlatform": platform_id,
            "tone": tone,
            "voice": 0,
        }
        try:
            data = self._post("/project/ai-social", payload)
        except (VizardError, VizardSkipSource):
            return ""
        return str(data.get("aiSocialContent") or "")

    def publish_clip(
        self,
        *,
        final_video_id: int,
        social_account_id: str,
        publish_time_ms: int | None = None,
        title: str = "",
        post: str = "",
    ) -> None:
        payload: dict[str, Any] = {
            "finalVideoId": final_video_id,
            "socialAccountId": social_account_id,
            "post": post,
        }
        if title:
            payload["title"] = title
        if publish_time_ms is not None:
            payload["publishTime"] = publish_time_ms

        self._post("/project/publish-video", payload)
