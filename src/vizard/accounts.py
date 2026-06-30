from __future__ import annotations

from dataclasses import dataclass

from src.config import VizardConfig
from src.vizard.client import VizardClient


@dataclass
class PublishTarget:
    platform: str
    account_id: str
    username: str
    page: str


def _platform_key(platform: str) -> str:
    key = platform.lower()
    if key in ("x",):
        return "twitter"
    return key


def _is_excluded(username: str, page: str, excluded: list[str]) -> bool:
    if not excluded:
        return False
    label = f"{username} {page}".lower()
    uname = username.lower()
    for name in excluded:
        needle = name.lower()
        if needle in label or needle == uname:
            return True
    return False


def resolve_publish_targets(
    client: VizardClient, config: VizardConfig
) -> list[PublishTarget]:
    accounts = client.list_social_accounts()
    targets: list[PublishTarget] = []
    excluded = [name.lower() for name in getattr(config, "excluded_accounts", [])]

    for account in accounts:
        platform = str(account.get("platform", ""))
        username = str(account.get("username", ""))
        page = str(account.get("page") or "")
        account_id = str(account["id"])
        label = f"{username} {page}".lower()

        if _is_excluded(username, page, excluded):
            continue

        if config.publish_all_connected:
            targets.append(
                PublishTarget(
                    platform=platform,
                    account_id=account_id,
                    username=username,
                    page=page,
                )
            )
            continue

        hint = config.social_accounts.get(_platform_key(platform), "").lower()
        if hint and hint in label:
            targets.append(
                PublishTarget(
                    platform=platform,
                    account_id=account_id,
                    username=username,
                    page=page,
                )
            )

    return targets


def filter_clips_by_score(clips: list[dict], min_score: float) -> list[dict]:
    filtered: list[dict] = []
    for clip in clips:
        try:
            score = float(clip.get("viralScore", 0))
        except (TypeError, ValueError):
            continue
        if score >= min_score:
            filtered.append(clip)
    filtered.sort(key=lambda clip: float(clip.get("viralScore", 0)), reverse=True)
    return filtered
