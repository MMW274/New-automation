# Project Log — News Channel Automation

**Workspace:** News channel Automationa  
**Repo:** https://github.com/MMW274/New-automation  
**Output channel:** [Fill Viz](https://www.youtube.com/channel/UClUZaCTA-gBR2iB8LKAAhNw)  
**Last updated:** 2026-06-28

---

## Pipeline overview

```
YouTube Discovery (11 channels, keyword search disabled to save quota)
    → Score by views/hour + engagement (trusted-channel boost ×1.5)
    → Pick up to 3 fresh source videos (48h dedupe, max 1 per channel)
    → Vizard AI clipping (viral score ≥ 8.5)
    → Smart slot publish: each clip scheduled into the next platform-optimal
      US ET window per day of week (src/scheduler/optimal_slots.py)
    → GitHub Actions cloud, 3× daily discovery (11/17/22 UTC)
    → Workflow failure auto-opens a GitHub issue
```

---

## Phase history

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | Done | YouTube discovery, virality scoring, JSON/CSV export |
| 2 | Done | Vizard API submit, clip filter, multi-platform publish |
| 3 | Done | Cloud automation via GitHub Actions (3× daily) |
| 4 | Done | Smart slot publishing + failure-issue notifications |
| 5 | Done | RSS-first discovery (~0 quota); per-platform AI captions; Vizard retry/backoff; **permanent source + clip dedupe** |
| 6 | Planned | Analytics feedback loop (YT + TikTok actuals → re-weight scorer); dynamic relevance terms (Google Trends); state pruning |

---

## Connected platforms (Vizard)

| Platform | Account | Status |
|----------|---------|--------|
| YouTube | Fill Viz | Active |
| TikTok | today_news98 | Active |
| X / Twitter | Fill Viz | Active |
| Facebook | — | Skipped (verification friction) |

---

## Monitored YouTube channels (11)

Fox News, The Economic Times, CBC News, CNN, BBC News, Times Of India, CBS News, NBC News, The Sun, ABC News, The White House

---

## Run history

### Local runs (2026-06-28)

| Run | Source | Clips | Platforms | Notes |
|-----|--------|-------|-----------|-------|
| 1 | QN7eFcaO2QA (Fox) | 1 | YT + TikTok | Scheduled (legacy mode) |
| 2 | bOy1B1gjGrg (Fox) | 6 | YT + TikTok | Immediate publish |
| 3 | Multi (3 sources) | 10 | YT + TikTok + X | Before cloud migration |

### Cloud run — first success

- **URL:** https://github.com/MMW274/New-automation/actions/runs/28333330535
- **Date:** 2026-06-28 ~19:25–19:38 UTC
- **Duration:** 12m 47s
- **Source videos:** 3 (Fox News Trump/Iran coverage)
- **Clips published:** 10 (viral score ≥ 8.5)
- **Platforms:** TikTok + YouTube + X (30 posts total)
- **YouTube quota:** Keyword search skipped (daily limit hit); channel scans used instead

### Cloud run — first attempt (failed)

- **URL:** https://github.com/MMW274/New-automation/actions/runs/28333306739
- **Cause:** Workflow missing `environment: YOUTUBE_API_KEY` (secrets in env, not repo)
- **Fix:** Commit `07430ea`

---

## Configuration snapshot

| File | Key settings |
|------|----------------|
| `config/vizard.yaml` | 3 sources/run, 4 clips max/run, 2/source, score ≥ 8.5, `smart_publish_slots: true`, all platforms |
| `config/scoring.yaml` | 24h window, trusted channel boost 1.5× |
| `config/channels.yaml` | 11 subscribed news channels |
| `config/keywords.yaml` | `keyword_search_enabled: false` (cloud quota guard) |
| `.github/workflows/automation.yml` | Cron 3× daily UTC (11/17/22), env `YOUTUBE_API_KEY`, auto-issue on failure |
| `src/scheduler/optimal_slots.py` | Day-of-week × platform US ET peak-window picker |

---

## Secrets (never in git)

| Secret | Location |
|--------|----------|
| `YOUTUBE_API_KEY` | `.env` local + GitHub Environment `YOUTUBE_API_KEY` (legacy env name — both secrets live here) |
| `VIZARDAI_API_KEY` | `.env` local + GitHub Environment `YOUTUBE_API_KEY` (same env) |

> The Environment is named `YOUTUBE_API_KEY` for historical reasons; rename it to `production` and update `.github/workflows/automation.yml > environment:` when convenient.

---

## Credit usage estimate

~5 Vizard credits per source video × 3 sources = **~15 credits per cloud run**  
× 3 runs/day = **~45 credits/day** (platform daily caps throttle the actual unique-clip total to ≤17/day)

---

## Commands reference

```bash
# Local manual run
./scripts/run_pipeline.sh

# List Vizard accounts
./scripts/list_accounts.sh

# Stop local Mac automation (use cloud instead)
./scripts/uninstall-local-automation.sh

# Trigger cloud run manually
gh workflow run automation.yml --repo MMW274/New-automation
```
