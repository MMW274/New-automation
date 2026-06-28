# Project Log — News Channel Automation

**Workspace:** News channel Automationa  
**Repo:** https://github.com/MMW274/New-automation  
**Output channel:** [Fill Viz](https://www.youtube.com/channel/UClUZaCTA-gBR2iB8LKAAhNw)  
**Last updated:** 2026-06-28

---

## Pipeline overview

```
YouTube Discovery (11 channels + keywords)
    → Score by views/hour + engagement
    → Pick up to 3 fresh source videos (48h dedupe)
    → Vizard AI clipping (score ≥ 8.5)
    → Publish immediately to ALL connected Vizard accounts
    → GitHub Actions (cloud, 4× daily — no laptop required)
```

---

## Phase history

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | Done | YouTube discovery, virality scoring, JSON/CSV export |
| 2 | Done | Vizard API submit, clip filter, multi-platform publish |
| 3 | Done | Cloud automation via GitHub Actions |
| 4 | Planned | Notifications, quota optimization, platform rate limits |

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
| `config/vizard.yaml` | 3 sources/run, 10 clips max, score ≥ 8.5, immediate publish, all platforms |
| `config/scoring.yaml` | 24h window, trusted channel boost 1.5× |
| `config/channels.yaml` | 11 subscribed news channels |
| `config/keywords.yaml` | 4 keyword queries (100 units each) |
| `.github/workflows/automation.yml` | Cron 4× daily Berlin, env `YOUTUBE_API_KEY` |

---

## Secrets (never in git)

| Secret | Location |
|--------|----------|
| `YOUTUBE_API_KEY` | `.env` local + GitHub Environment `YOUTUBE_API_KEY` |
| `VIZARDAI_API_KEY` | `.env` local + GitHub Environment `YOUTUBE_API_KEY` |

---

## Credit usage estimate

~5 Vizard credits per source video × 3 sources = **~15 credits per cloud run**  
× 4 runs/day = **~60 credits/day**

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
