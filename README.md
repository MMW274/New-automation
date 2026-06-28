# News Channel Automation — Phase 1

Automated discovery of high-velocity Trump / US government news videos on YouTube. Ranks candidates by views-per-hour and saves ready-to-paste links for [Vizard.ai](https://vizard.ai) clipping.

**Output channel:** [Fill Viz](https://www.youtube.com/channel/UClUZaCTA-gBR2iB8LKAAhNw)

## What Phase 1 does

1. Scans major US news YouTube channels for recent uploads
2. Runs keyword searches (`Trump`, `White House`, `Congress`, etc.)
3. Scores videos by virality (views/hour + engagement)
4. Saves top candidates to `output/candidates.json` and `output/candidates.csv`
5. Optionally syncs results to your [Google Sheet](https://docs.google.com/spreadsheets/d/1B24KcqCYUWT3nJG6SF30LBKbkVBg1CUWaqUrjrkLsVc/edit)

## Quick start

### 1. Get a YouTube API key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → enable **YouTube Data API v3**
3. Create an API key under **Credentials**

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set YOUTUBE_API_KEY=your_key_here
```

### 3. Install and run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Full run — saves to output/
python -m src.scheduler.run

# Preview without saving
python -m src.scheduler.run --dry-run

# Shorter window (last 10 hours)
python -m src.scheduler.run --hours 10
```

Or use the helper script:

```bash
chmod +x scripts/run_discovery.sh
./scripts/run_discovery.sh
```

### 4. Use the results

Open `output/candidates.json` or `output/candidates.csv`. Copy the top URL and paste it into Vizard — same workflow as before, but the hunting is automated.

## Configuration

| File | Purpose |
|------|---------|
| `config/channels.yaml` | News channels to monitor |
| `config/keywords.yaml` | YouTube search queries |
| `config/scoring.yaml` | Age window, min views, relevance filters, top N |

### Scoring formula

```
views_per_hour = view_count / hours_since_publish
engagement_rate = (likes + comments×3) / views
score = views_per_hour + engagement_rate×1000 + like_ratio×10000
```

Videos must match at least one term in `relevance_terms` and exceed `min_views`.

## Google Sheets sync (optional)

1. Create a Google Cloud service account and download JSON credentials
2. Save to `credentials/google-service-account.json`
3. Share your spreadsheet with the service account email (Editor access)
4. In `.env`:

```
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEETS_ID=1B24KcqCYUWT3nJG6SF30LBKbkVBg1CUWaqUrjrkLsVc
GOOGLE_SERVICE_ACCOUNT_JSON=credentials/google-service-account.json
```

## Schedule it (every 4 hours)

```bash
crontab -e
```

Add:

```
0 */4 * * * cd "/Users/mehulwadhavekar/Desktop/Cursor Projects/News channel Automationa" && ./scripts/run_discovery.sh >> output/cron.log 2>&1
```

## API quota

Default YouTube quota: **10,000 units/day**.

| Operation | Cost |
|-----------|------|
| Channel playlist scan | 1 unit/page |
| Keyword search | 100 units/query |
| Video stats batch | 1 unit/50 videos |

With 10 channels + 8 keyword queries, one run ≈ **850 units**. Safe to run every 4 hours.

## Project layout

```
config/          # Channels, keywords, scoring rules
src/discovery/   # YouTube client, scanner, scorer
src/storage/     # JSON/CSV export + Google Sheets
src/scheduler/   # CLI entry point
output/          # Latest candidates + history
vizard-api-skills/  # Vizard API docs (Phase 2)
scripts/         # Cron-friendly runner
```

## Phase 2 (next)

- Auto-submit top URL to Vizard API
- Poll until clips are ready
- Notify you via Telegram/email

See `vizard-api-skills/SKILL.md` for Vizard API workflow.

## Repo

```bash
git remote add origin git@github.com:MMW274/New-automation.git
git push -u origin main
```
