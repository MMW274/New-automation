import json
from datetime import datetime, timedelta, timezone

from src.storage import dedupe_ledger, pruner


def _write_submitted(path, entries):
    path.write_text(json.dumps(entries, indent=2))


def test_pruner_archives_old_entries_keeps_recent(tmp_path):
    submitted = pruner.SUBMITTED_PATH
    now = datetime.now(timezone.utc)
    recent_ts = (now - timedelta(days=10)).isoformat()
    old_ts = (now - timedelta(days=400)).isoformat()
    _write_submitted(
        submitted,
        [
            {"video_id": "recent", "project_id": 1, "submitted_at": recent_ts, "published": []},
            {
                "video_id": "old",
                "project_id": 2,
                "submitted_at": old_ts,
                "published": [{"clip_video_id": 999}],
            },
        ],
    )

    result = pruner.prune_submitted(keep_days=180)
    kept = json.loads(submitted.read_text())

    assert result["kept"] == 1
    assert result["archived"] == 1
    assert [e["video_id"] for e in kept] == ["recent"]

    # Ledger must contain BOTH so dedupe still works after the prune.
    vids = dedupe_ledger.video_ids()
    assert "recent" in vids and "old" in vids
    assert 999 in dedupe_ledger.clip_ids()

    # Old entry should now live in history/submitted-<year>.json
    history_files = list(pruner.HISTORY_DIR.glob("submitted-*.json"))
    assert history_files, "expected an archived history file"


def test_prune_daily_counts_drops_old_days(tmp_path):
    now = datetime.now(timezone.utc).date()
    data = {
        (now - timedelta(days=1)).strftime("%Y-%m-%d"): {"youtube": 1},
        (now - timedelta(days=100)).strftime("%Y-%m-%d"): {"tiktok": 2},
    }
    pruner.DAILY_COUNTS_PATH.write_text(json.dumps(data))
    pruner.prune_daily_counts(keep_days=60)
    after = json.loads(pruner.DAILY_COUNTS_PATH.read_text())
    assert len(after) == 1
