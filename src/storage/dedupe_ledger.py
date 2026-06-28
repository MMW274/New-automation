"""Forever-growing dedupe ledger, decoupled from `submitted.json`.

`submitted.json` carries the full publish record per source and is rotated
yearly by `pruner.py`. To keep the permanent-dedupe guarantee intact across
rotations we maintain a separate, append-only ledger that holds nothing but
the IDs we must never reuse:

  output/dedupe_ids.json
  {
    "video_ids": ["abc...", ...],   # YouTube source IDs ever submitted
    "clip_ids": [12345, ...]        # Vizard finalVideoIds ever published
  }

The pipeline writes to this file at submission time AND reads it as the
authoritative source of dedupe truth at pick-candidate time.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.config import OUTPUT_DIR

LEDGER_PATH = OUTPUT_DIR / "dedupe_ids.json"


def _empty() -> dict[str, list]:
    return {"video_ids": [], "clip_ids": []}


def load_ledger() -> dict[str, list]:
    if not LEDGER_PATH.exists():
        return _empty()
    try:
        data = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty()
    return {
        "video_ids": list(data.get("video_ids", [])),
        "clip_ids": list(data.get("clip_ids", [])),
    }


def _save(data: dict[str, list]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def video_ids() -> set[str]:
    return {str(v) for v in load_ledger()["video_ids"]}


def clip_ids() -> set[int]:
    out: set[int] = set()
    for raw in load_ledger()["clip_ids"]:
        try:
            out.add(int(raw))
        except (TypeError, ValueError):
            continue
    return out


def remember_video(video_id: str) -> None:
    if not video_id:
        return
    data = load_ledger()
    if video_id in data["video_ids"]:
        return
    data["video_ids"].append(video_id)
    _save(data)


def remember_clip(clip_video_id: int) -> None:
    data = load_ledger()
    try:
        clip_int = int(clip_video_id)
    except (TypeError, ValueError):
        return
    if clip_int in {int(c) for c in data["clip_ids"]}:
        return
    data["clip_ids"].append(clip_int)
    _save(data)


def seed_from_submitted(submitted_path: Path) -> None:
    """One-shot import: backfill the ledger from existing submitted.json
    so dedupe survives the cutover even if submitted.json gets pruned."""
    if not submitted_path.exists():
        return
    records = json.loads(submitted_path.read_text(encoding="utf-8"))
    data = load_ledger()
    known_videos = set(data["video_ids"])
    known_clips = {int(c) for c in data["clip_ids"]}
    for entry in records:
        vid = entry.get("video_id")
        if vid and vid not in known_videos:
            data["video_ids"].append(vid)
            known_videos.add(vid)
        for pub in entry.get("published", []) or []:
            cid = pub.get("clip_video_id")
            if cid is None:
                continue
            try:
                cid_int = int(cid)
            except (TypeError, ValueError):
                continue
            if cid_int not in known_clips:
                data["clip_ids"].append(cid_int)
                known_clips.add(cid_int)
    _save(data)
