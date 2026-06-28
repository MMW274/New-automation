# Workflow Analysis & Phase 2 Design

Based on your manual Vizard workflow (June 2026 screenshots).

## Your Manual Steps (mapped to automation)

| Step | What you do in UI | Automation |
|------|-------------------|------------|
| 1 | Paste YouTube URL | Phase 1 discovery picks top URL |
| 2 | English, Get AI clips ON | `config/vizard.yaml` → `lang: en`, clipping mode |
| 3 | 9:16 ratio, Any length | `ratio_of_clip: 1`, `prefer_length: [0]` |
| 4 | Bouncy template | `template_id` (set from Vizard workspace) |
| 5 | Emoji, highlight, silence, B-roll ON | All switches = 1 in config |
| 6 | Auto schedule ON | `auto_schedule: true` + publish API |
| 7 | Viral score ≥ 9.0 | `min_viral_score: 9.0` |
| 8 | 8 clips/day, 4am–7pm Berlin | `clips_per_day`, hours, `timezone` |
| 9 | Until all clips posted | Scheduler spreads all qualified clips |
| 10 | TikTok + Fill Viz YouTube | `social_accounts` username matching |

## Improvements made

### Phase 1
- Fixed wrong YouTube channel IDs (Fox, CNN, etc.)
- Trusted news channel boost (1.5×) — reduces MeidasTouch-style re-uploads
- Skip deleted/live videos without duration
- Dedupe: won't re-submit same source within 48h

### Phase 2
- `python -m src.scheduler.run_pipeline` — full discover → Vizard → schedule
- Matches your UI settings in `config/vizard.yaml`
- Filters clips by viral score before scheduling
- Publishes to both TikTok and YouTube with staggered times

## What still needs your input

1. **VIZARDAI_API_KEY** in `.env` (Vizard workspace → API settings)
2. **Bouncy template ID** — optional; find in Vizard and set `template_id` in config
3. Run `python -m src.vizard.list_accounts` to verify Fill Viz + today_news98 match

## Commands

```bash
# Discovery only (Phase 1)
python -m src.scheduler.run

# Full pipeline (Phase 2) — uses ~5 Vizard credits per source video
python -m src.scheduler.run_pipeline

# Preview without API calls to Vizard publish
python -m src.scheduler.run_pipeline --dry-run

# List connected social accounts
python -m src.vizard.list_accounts
```

## Credit usage

Your UI shows **5 credits per upload**. One pipeline run = 1 source video = ~5 credits, regardless of how many clips are generated.
