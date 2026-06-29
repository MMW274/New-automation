"""Content safety gate.

TikTok and YouTube Shorts both demonetize / takedown news clips containing
graphic violence, casualty counts, slurs, or extremist references. Even
auto-clipped news content can trip these filters when the original story
covers war / mass-casualty events.

This module classifies a clip title (and optionally transcript) as either
`safe` or `risky`. Risky clips are NOT published; they are written to
`output/review_queue.json` for manual review.

Default term list is conservative and tuned for news content. Override by
adding `blocked_terms` to `config/vizard.yaml`.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from src.config import OUTPUT_DIR

REVIEW_QUEUE_PATH = OUTPUT_DIR / "review_queue.json"

DEFAULT_BLOCKED_TERMS: tuple[str, ...] = (
    # Graphic violence — explicit casualty / killing descriptors
    "beheaded", "beheading", "decapitated",
    "execution", "executed",
    "mutilated", "dismembered", "disembowel",
    "massacre", "genocide", "ethnic cleansing",
    "mass shooting", "school shooting",
    "child abuse", "child porn", "csam", "pedophile",
    "suicide", "self-harm", "self harm",
    "rape", "raped", "rapist",
    # Hate speech triggers — common slurs (kept short for hygiene)
    "nigger", "faggot", "kike", "tranny",
    # Misinformation tripwires
    "vaccine kills", "vaccine death", "qanon",
    # Platform-banned topics for news monetization
    "weapon tutorial", "how to make a bomb",
)

WHITESPACE = re.compile(r"\s+")


class SafetyVerdict:
    __slots__ = ("safe", "matched_terms", "reason")

    def __init__(self, safe: bool, matched_terms: list[str], reason: str = "") -> None:
        self.safe = safe
        self.matched_terms = matched_terms
        self.reason = reason

    def __bool__(self) -> bool:
        return self.safe


def _normalize(text: str) -> str:
    return WHITESPACE.sub(" ", text.lower())


def classify(
    text: str,
    *,
    blocked_terms: tuple[str, ...] | list[str] = DEFAULT_BLOCKED_TERMS,
) -> SafetyVerdict:
    if not text:
        return SafetyVerdict(safe=True, matched_terms=[])
    haystack = _normalize(text)
    hits = sorted({term for term in blocked_terms if term and term in haystack})
    if hits:
        return SafetyVerdict(
            safe=False,
            matched_terms=hits,
            reason=f"matched: {', '.join(hits)}",
        )
    return SafetyVerdict(safe=True, matched_terms=[])


def hold_for_review(record: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if REVIEW_QUEUE_PATH.exists():
        try:
            queue = json.loads(REVIEW_QUEUE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            queue = []
    else:
        queue = []
    record = {
        **record,
        "held_at": datetime.now(timezone.utc).isoformat(),
    }
    queue.append(record)
    REVIEW_QUEUE_PATH.write_text(json.dumps(queue, indent=2), encoding="utf-8")
