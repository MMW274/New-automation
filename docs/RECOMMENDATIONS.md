# Pipeline Recommendations

Prioritized improvements for the News Channel Automation pipeline.

---

## High priority

### 1. Spread clip publishing over time (not all at once)

**Issue:** 10 clips × 3 platforms = 30 posts in ~2 minutes. TikTok and YouTube may flag burst posting.

**Fix:** Add `publish_stagger_minutes: 30` — space each clip 30–60 min apart while still using immediate publish (different `publishTime` values).

### 2. Enforce per-platform daily caps in code

**Issue:** `platform_daily_limits` in config is reference-only today.

**Fix:** Track posts per platform per day in `output/daily_counts.json` (cached on GitHub Actions). Stop publishing to TikTok after 4 clips/day, YouTube after 3, etc.

### 3. YouTube API quota — channel-first mode

**Issue:** 8 keyword searches = 800 quota units. Local testing exhausted daily limit.

**Fix:** Add `keyword_search_enabled: false` in config for cloud runs. Channel scans (~11 units) are enough with 11 subscriptions. Request quota increase in Google Cloud if needed.

### 4. Source diversity filter

**Issue:** Cloud run picked 3 Fox News videos on the same Iran story.

**Fix:** Max 1 video per channel per run; prefer different channels/topics in top picks.

---

## Medium priority

### 5. Bouncy template ID

Set `template_id` in `config/vizard.yaml` from Vizard workspace to match your manual UI styling.

### 6. Run failure notifications

Add GitHub Actions step to send email/Discord/Telegram on workflow failure. Success optional.

### 7. Reduce cloud frequency

4 runs/day × 15 credits = ~60 Vizard credits/day. Consider **2 runs/day** (8am + 8pm Berlin) until you confirm ROI.

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
