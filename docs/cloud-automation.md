# Cloud automation (no laptop required)

Runs on **GitHub Actions** — works 24/7 even when your Mac is closed.

## Setup (one time, ~5 min)

### 1. Push code to GitHub

Repo: https://github.com/MMW274/New-automation

### 2. Add secrets

GitHub → **Settings** → **Secrets and variables** → **Actions**

Create an **Environment** named `YOUTUBE_API_KEY`, then add these **environment secrets**:

| Secret | Value |
|--------|--------|
| `YOUTUBE_API_KEY` | Your `AIzaSy...` key |
| `VIZARDAI_API_KEY` | From Vizard workspace → API |

> If you already added them under Environment `YOUTUBE_API_KEY`, you're set — the workflow uses that environment automatically.

### 3. Enable Actions

GitHub → **Actions** tab → enable workflows if prompted.

### 4. Stop local Mac job (optional)

```bash
./scripts/uninstall-local-automation.sh
```

## Schedule

Runs **4× daily** at 6am, 12pm, 6pm, 10pm Berlin time:

```
Discover 2-3 source videos → Vizard clips → publish up to 10 clips
→ ALL connected Vizard accounts (YouTube, TikTok, Facebook, X, …)
```

Manual trigger: GitHub → Actions → **News Automation Pipeline** → **Run workflow**

## Multi-platform

Connect accounts in **Vizard workspace** (not in our code):

1. vizard.ai → connect **X**, **Facebook Page**, etc.
2. Run `python -m src.vizard.list_accounts` locally to verify
3. Next cloud run publishes to **every active account** automatically

## Limits per run (safe for platforms)

| Setting | Value | Why |
|---------|-------|-----|
| Source videos | 3 | Different stories, ~15 Vizard credits |
| Max clips | 10 | Under TikTok/YouTube daily sweet spots |
| Min score | 8.5 | Quality filter |
| Platforms | All connected | Max visibility |

Platform daily safe limits (reference in `config/vizard.yaml`):
- YouTube Shorts: ~3/day
- TikTok: ~4/day  
- Facebook: ~5/day
- X: ~10/day

We publish up to **10 unique clips** × **N platforms** per run.

## Logs

Each run saves artifacts in GitHub Actions → workflow run → **Artifacts**.

Dedupe state (`output/submitted.json`) cached between runs so the same source isn't re-used within 48h.
