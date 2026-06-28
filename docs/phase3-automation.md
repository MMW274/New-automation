# Phase 3 — Hands-off automation

## What runs automatically

Every **6 hours** (and once on install):

1. Scan YouTube for hot Trump/US news (your 11 channels + keywords)
2. Pick top video not submitted in last 48h
3. Submit to Vizard → generate clips
4. **Publish immediately** every clip with viral score **≥ 8.5** to:
   - YouTube **Fill Viz**
   - TikTok **today_news98**

No calendar scheduling — posts go live as soon as Vizard finishes.

## Install (one time)

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
