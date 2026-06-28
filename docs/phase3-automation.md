# Phase 3 — Hands-off automation

> **Current default is cloud (GitHub Actions, 3× daily UTC).** See [`cloud-automation.md`](cloud-automation.md). The local-launchd flow below is kept for offline / backup use only.

## What runs automatically (cloud)

3× daily discovery at 11/17/22 UTC:

1. Scan 11 trusted news channels (keyword search disabled to conserve quota)
2. Pick up to 3 fresh source videos (48h dedupe, max 1 per channel)
3. Submit each to Vizard → generate clips
4. Filter clips with viral score **≥ 8.5**
5. **Smart-slot publish** — each clip is scheduled into the next platform-optimal US ET window (see `src/scheduler/optimal_slots.py`):
   - YouTube Shorts **Fill Viz**
   - TikTok **today_news98**
   - X **Fill Viz**

On failure, a GitHub issue is auto-opened with the run URL and a triage checklist.

## Local fallback install (one time, optional)

```bash
cd "/Users/mehulwadhavekar/Desktop/Cursor Projects/News channel Automationa"
chmod +x scripts/install-automation.sh
./scripts/install-automation.sh
```

Requires Mac to be awake (or wake on schedule). Check log:

```bash
tail -f output/automation.log
```

## Stop / restart

```bash
# Stop
launchctl bootout gui/$(id -u)/com.fillviz.news-automation

# Restart
./scripts/install-automation.sh
```

## Config

| File | Setting |
|------|---------|
| `config/vizard.yaml` | `min_viral_score: 8.5`, `publish_immediately: true` |
| `config/scoring.yaml` | Discovery filters |
| `config/channels.yaml` | Your subscribed channels |

## Manual run

```bash
./scripts/run_pipeline.sh
```
