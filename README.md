# News Channel Automation

Fully automated Trump / US news clip pipeline: discover on YouTube → clip with [Vizard.ai](https://vizard.ai) → publish to **TikTok, YouTube, and X**.

**Output:** [Fill Viz](https://www.youtube.com/channel/UClUZaCTA-gBR2iB8LKAAhNw) · **Repo:** [github.com/MMW274/New-automation](https://github.com/MMW274/New-automation)

## Status (2026-06-28)

| Component | Status |
|-----------|--------|
| YouTube discovery | Live — 11 channels |
| Vizard clipping | Live — score ≥ 8.5 |
| Multi-platform publish | TikTok + YouTube + X |
| Cloud automation | GitHub Actions, 3× daily (11/17/22 UTC) |
| Smart publish timing | Day-of-week × platform US ET peaks (`src/scheduler/optimal_slots.py`) |
| Per-platform AI captions | Vizard `/project/ai-social` per target (TikTok/YT/X) |
| Discovery quota | RSS-first (`src/discovery/rss_scanner.py`) — ~0 YouTube quota |
| Source dedupe | **Permanent** — a source video can never be republished |
| Failure alerts | Auto-opens GitHub issue on workflow failure |
| Retry safety | Exponential backoff on Vizard 4003 + HTTP 5xx; skip on 4008; fatal on 4001/4007 |
| Facebook | Not connected (optional later) |

## Cloud automation (no laptop needed)

Runs on GitHub Actions — see [`docs/cloud-automation.md`](docs/cloud-automation.md).

Secrets in GitHub Environment **`YOUTUBE_API_KEY`**: `YOUTUBE_API_KEY`, `VIZARDAI_API_KEY`.

```bash
# Manual cloud trigger
gh workflow run automation.yml --repo MMW274/New-automation
```

## Local manual run

```bash
cp .env.example .env   # add API keys
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./scripts/run_pipeline.sh
```

## Configuration

| File | Purpose |
|------|---------|
| `config/channels.yaml` | 11 news channels you subscribe to |
| `config/keywords.yaml` | YouTube search queries |
| `config/scoring.yaml` | Virality scoring, trusted channel boost |
| `config/vizard.yaml` | Clipping settings, 3 sources, 10 clips, all platforms |

## Documentation

| Doc | Contents |
|-----|----------|
| [`docs/PROJECT-LOG.md`](docs/PROJECT-LOG.md) | Full run history, config snapshot, commands |
| [`docs/RECOMMENDATIONS.md`](docs/RECOMMENDATIONS.md) | Pipeline improvements (prioritized) |
| [`docs/cloud-automation.md`](docs/cloud-automation.md) | GitHub Actions setup |
| [`docs/phase2-workflow.md`](docs/phase2-workflow.md) | Vizard UI → API mapping |

## Security

API keys live in `.env` (local) and GitHub Environment secrets — never committed. Pre-commit hook blocks accidental `.env` commits:

```bash
./scripts/enable-git-hooks.sh
```
