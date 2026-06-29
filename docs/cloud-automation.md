# Cloud automation (no laptop required)

Runs on **GitHub Actions** — works 24/7 even when your Mac is closed.

## Setup (one time, ~5 min)

### 1. Push code to GitHub

Repo: https://github.com/MMW274/New-automation

### 2. Add secrets

GitHub → **Settings** → **Secrets and variables** → **Actions**

Create an **Environment** named `YOUTUBE_API_KEY` (legacy name — holds both secrets; rename to `production` later and update `.github/workflows/automation.yml`), then add these **environment secrets**:

| Secret | Value |
|--------|--------|
| `YOUTUBE_API_KEY` | Your `AIzaSy...` key |
| `VIZARDAI_API_KEY` | From Vizard workspace → API |

### 3. Enable Actions

GitHub → **Actions** tab → enable workflows if prompted.

### 4. Stop local Mac job (optional)

```bash
./scripts/uninstall-local-automation.sh
```

## Schedule

Discovery runs **3× daily** (UTC):

| UTC | Berlin | US ET | Purpose |
|-----|--------|-------|---------|
| 11:00 | 13:00 | 07:00 | Morning X / breaking news catch |
| 17:00 | 19:00 | 13:00 | Midday refresh |
| 22:00 | 00:00 | 18:00 | TikTok + YT Shorts prime |

Per-clip **publish times** are then chosen by `src/scheduler/optimal_slots.py` to land in platform-optimal US ET windows by day of week:

- **TikTok** — 6 pm–10 pm daily; Thu 6 am extra; Sat 5 pm; Sun 9 am
- **YouTube Shorts** — 6 pm–8 pm daily; Fri 6–7 pm peak; Sat 1 pm
- **X (Twitter)** — Tue/Wed 10 am preferred; weekdays 10 am / 2 pm

Manual trigger: GitHub → Actions → **News Automation Pipeline** → **Run workflow**

## Multi-platform

Connect accounts in **Vizard workspace** (not in our code):

1. vizard.ai → connect **X**, **Facebook Page**, etc.
2. Run `python -m src.vizard.list_accounts` locally to verify
3. Next cloud run publishes to **every active account** automatically

## Per-run limits (safe for platforms)

| Setting | Value | Why |
|---------|-------|-----|
| Source videos | 3 | Different stories, ~15 Vizard credits |
| Max clips | 4 (`max_clips_per_run`) | Stays well under TikTok/YouTube daily caps |
| Min score | 8.5 | Quality filter |
| Platforms | All connected | Max visibility |

Daily caps enforced in `config/vizard.yaml > platform_daily_limits`:
- YouTube Shorts: 3
- TikTok: 4
- X: 10
- Facebook: 5

## Failure handling

On any workflow failure, the job **auto-opens a GitHub Issue** labeled `pipeline-failure, automation` with the run URL and a triage checklist. No extra secrets required (uses the built-in `GITHUB_TOKEN`).

## Logs

Each run uploads `output/submitted.json`, `output/daily_counts.json`, `output/candidates.json` as a 30-day GitHub artifact.

Dedupe state is cached across runs (`pipeline-state-v3-<run_id>`) so the same source video isn't re-used within 48h.
