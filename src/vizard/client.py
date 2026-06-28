from __future__ import annotations

import time
from typing import Any

import requests

from src.config import VizardConfig

BASE_URL = "https://elb-api.vizard.ai/hvizard-server-front/open-api/v1"


class VizardError(RuntimeError):
    pass


class VizardClient:
    def __init__(self, config: VizardConfig) -> None:
        self.config = config
        self._headers = {
            "Content-Type": "application/json",
            "VIZARDAI_API_KEY": config.api_key,
        }

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            f"{BASE_URL}{path}",
            headers=self._headers,
            json=payload,
            timeout=60,
        )
        data = response.json()
        if data.get("code") != 2000:
            raise VizardError(f"Vizard API error on {path}: {data}")
        return data

    def _get(self, path: str) -> dict[str, Any]:
        response = requests.get(
            f"{BASE_URL}{path}",
            headers=self._headers,
            timeout=60,
        )
        return response.json()

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
