# Pipeline Recommendations

Prioritized improvements for the News Channel Automation pipeline.

---

## High priority

### 1. ~~Spread clip publishing over time~~ ✅ Done

`publish_stagger_minutes: 45` — clips scheduled 45 min apart via Vizard `publishTime`.

### 2. ~~Enforce per-platform daily caps~~ ✅ Done

`output/daily_counts.json` tracks posts per platform. Stops when YouTube (3), TikTok (4), etc. hit daily limits.

### 3. ~~YouTube API quota — channel-first mode~~ ✅ Done

`keyword_search_enabled: false` in `config/keywords.yaml`. Channel scans only (~11 quota units).

### 4. ~~Source diversity filter~~ ✅ Done

`max_one_video_per_channel: true` — max 1 source video per news channel per run.

---

## Medium priority

### 5. Bouncy template ID

Set `template_id` in `config/vizard.yaml` from Vizard workspace → Templates → copy ID from URL to match your manual UI styling. Until set, Vizard uses its default template.

### 6. ~~Run failure notifications~~ ✅ Done

Workflow auto-opens a labeled GitHub issue on failure (`actions/github-script` step in `automation.yml`). No extra secrets required.

### 7. ~~Smart cron + per-platform publish slotting~~ ✅ Done

Cron now fires 3× daily UTC (11/17/22 — covers US morning X / midday / evening TikTok+YT prime). Per-clip `publishTime` is chosen by `src/scheduler/optimal_slots.py` per day-of-week × platform peak (TikTok 6-9pm + Thu 6am + Sun 9am; YT Shorts Fri-Sat 6-9pm; X Tue-Wed 10am).

### 8. Google Sheets sync

Enable `GOOGLE_SHEETS_ENABLED` for a live dashboard of candidates and run status on your phone.

### 9. ~~RSS discovery (~0 quota)~~ ✅ Done

`src/discovery/rss_scanner.py` fetches `https://www.youtube.com/feeds/videos.xml?channel_id={id}` per channel (0 quota). `src/scheduler/run_pipeline.py` calls RSS first and only falls back to `playlistItems.list` for channels whose RSS feed failed.

### 10. ~~Vizard retry/backoff~~ ✅ Done

`VizardClient._request` now exponential-backoffs `4003` (rate limit) + HTTP 5xx, raises `VizardFatal` for `4001`/`4007`, raises `VizardSkipSource` for `4008`. Pipeline catches Skip and continues with the next source.

### 11. ~~Per-platform AI captions~~ ✅ Done

`VizardClient.ai_caption(final_video_id, platform)` calls `/project/ai-social` with `aiSocialPlatform` 2/4/7 and `tone=2` (Catchy). Result is passed as the `post` field per platform. Disabled via `per_platform_captions: false`.

### 11a. PERMANENT source dedupe ✅ Done (safety)

`pick_fresh_candidates` ignores `dedupe_hours` and uses `_all_submitted_video_ids()` — once a source YouTube video has been submitted (recorded immediately on `create_project`), it can NEVER be re-submitted. Clip-level dedupe via `_all_published_clip_ids()` adds a second layer. Submission state is written in a `try/finally` so partial failures still hold the lock.

---

## Low priority / future

### 12. Facebook Page

Connect when Meta verification allows. Pipeline auto-includes it via `publish_all_connected: true`.

### 13. Instagram Reels

Connect in Vizard if you create a news Instagram account.

### 14. Content review gate

Optional `--approve` mode: save clips to a review queue before publishing (Telegram bot with approve/reject).

### 15. Analytics loop

Track which clip titles/scores get most views (YT Data API + TikTok Display API). Re-fit `config/scoring.yaml > weights` monthly. Validates Vizard `viralScore` against real performance.

### 16. Dynamic relevance terms

Pull Google Trends US daily top-20 (`pytrends`) and merge into `config/scoring.yaml > relevance_terms` so non-Trump breaking stories aren't filtered out.

### 17. State pruning

`output/submitted.json` and `output/daily_counts.json` grow forever. Keep last 14 / 30 days; archive the rest under `output/history/`.

---

## Platform posting limits (reference)

| Platform | Safe daily | Current per run |
|----------|-----------|-----------------|
| YouTube Shorts | 1–3 | up to 10 |
| TikTok | 1–4 | up to 10 |
| X | ~10 | up to 10 |
| Facebook | 1–5 | 0 (not connected) |

**Recommendation:** Cap at **3–4 unique clips per run** once platforms are stable, or stagger posts across the day.
