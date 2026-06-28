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

Set `template_id` in `config/vizard.yaml` from Vizard workspace to match your manual UI styling.

### 6. Run failure notifications

Add GitHub Actions step to send email/Discord/Telegram on workflow failure. Success optional.

### 7. ~~Reduce cloud frequency~~ ✅ Done

Reduced to **2 runs/day** (8am + 8pm Berlin) in GitHub Actions workflow.

### 8. Google Sheets sync

Enable `GOOGLE_SHEETS_ENABLED` for a live dashboard of candidates and run status on your phone.

---

## Low priority / future

### 9. Facebook Page

Connect when Meta verification allows. Pipeline auto-includes it via `publish_all_connected: true`.

### 10. Instagram Reels

Connect in Vizard if you create a news Instagram account.

### 11. Content review gate

Optional `--approve` mode: save clips to a review queue before publishing (Telegram bot with approve/reject).

### 12. Analytics loop

Track which clip titles/scores get most views; feed back into scoring weights over time.

---

## Platform posting limits (reference)

| Platform | Safe daily | Current per run |
|----------|-----------|-----------------|
| YouTube Shorts | 1–3 | up to 10 |
| TikTok | 1–4 | up to 10 |
| X | ~10 | up to 10 |
| Facebook | 1–5 | 0 (not connected) |

**Recommendation:** Cap at **3–4 unique clips per run** once platforms are stable, or stagger posts across the day.
