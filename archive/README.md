# Archive

Dead code that is **not** referenced by the live pipeline, kept here for
reference rather than deleted. Anything in `archive/` is excluded from
imports, tests, and the CI lint check.

Audit each `.py.bak` file before reviving it — the live equivalent has
usually moved on.

## Contents

| File | Replaced by | Removed on |
|---|---|---|
| `src_vizard_scheduler.py.bak` | `src/scheduler/optimal_slots.py` + `src/vizard/pipeline.py` (smart per-platform slotting) | 2026-06-29 |

## What is *not* archived (deliberately)

These look unused but are feature-flagged and stay in `src/` because
toggling them back on is a one-line YAML / env change:

- `src/discovery/keyword_search.py` — gated by `keyword_search_enabled` in
  `config/keywords.yaml` (currently `false`; costs 100 YouTube quota
  units per query, so expensive to leave on).
- `src/storage/sheets.py` — gated by `GOOGLE_SHEETS_ENABLED=true` env
  var (currently off).
- `src/scheduler/run.py` — discovery-only entrypoint used by
  `scripts/run_discovery.sh` for local dry-runs. Skips Vizard publish.
- `src/vizard/list_accounts.py` — used by `scripts/list_accounts.sh` to
  print connected social accounts. Helpful debugging CLI.
