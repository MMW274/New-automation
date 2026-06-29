from src.storage import dedupe_ledger


def test_ledger_persists_across_reads():
    dedupe_ledger.remember_video("abc123")
    dedupe_ledger.remember_clip(42)
    assert "abc123" in dedupe_ledger.video_ids()
    assert 42 in dedupe_ledger.clip_ids()


def test_ledger_deduplicates_inserts():
    for _ in range(5):
        dedupe_ledger.remember_video("xyz789")
        dedupe_ledger.remember_clip(7)
    assert list(dedupe_ledger.load_ledger()["video_ids"]).count("xyz789") == 1
    assert list(dedupe_ledger.load_ledger()["clip_ids"]).count(7) == 1


def test_pick_fresh_candidates_excludes_ledgered():
    from src.discovery.scorer import ScoredVideo
    from src.vizard.pipeline import pick_fresh_candidates

    dedupe_ledger.remember_video("banned1")

    def _make(vid: str, channel: str = "ChA") -> ScoredVideo:
        return ScoredVideo(
            video_id=vid,
            title="t",
            channel_title=channel,
            published_at="2026-06-28T00:00:00Z",
            url=f"https://youtube.com/watch?v={vid}",
            view_count=100000,
            like_count=1000,
            comment_count=100,
            duration_seconds=300,
            hours_since_publish=2.0,
            views_per_hour=50000,
            engagement_rate=0.05,
            score=100000.0,
            source="ChA",
        )

    candidates = [_make("banned1"), _make("fresh1"), _make("fresh2", "ChB")]
    picked = pick_fresh_candidates(candidates, limit=5, one_per_channel=True)
    assert [c.video_id for c in picked] == ["fresh1", "fresh2"]


def test_seed_from_submitted_backfills(tmp_path):
    import json

    submitted = tmp_path / "submitted.json"
    submitted.write_text(
        json.dumps(
            [
                {
                    "video_id": "seedA",
                    "project_id": 1,
                    "published": [{"clip_video_id": 100}, {"clip_video_id": 101}],
                },
                {"video_id": "seedB", "project_id": 2, "published": []},
            ]
        )
    )
    dedupe_ledger.seed_from_submitted(submitted)
    assert {"seedA", "seedB"} <= dedupe_ledger.video_ids()
    assert {100, 101} <= dedupe_ledger.clip_ids()
