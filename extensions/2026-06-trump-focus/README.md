# 2026-06-trump-focus

**Created:** 2026-06-29
**Author:** Pipeline operator
**Goal:** Only ship clips from genuinely viral Trump / US-politics stories.

## What this overlay changes (vs base config)

### `scoring.overlay.yaml`

- **`min_views: 400_000`** — raised from 5,000. A YouTube upload must
  already have 400k+ views in its first 24h before we'll even consider
  clipping it. This is the "is it really blowing up?" gate.
- **`min_views_per_hour: 5_000`** — must be currently *hot*, not a slow
  burner. 5K/hr ≈ 120K/day pace.
- **`min_engagement_rate: 0.005`** — at least 0.5% of viewers must like
  or comment. Filters out passive views (bots, autoplay).
- **`relevance_terms_add`** — extends base list with: Epstein, Kash
  Patel, Pete Hegseth, Stephen Miller, Susie Wiles, Mike Johnson, Tulsi
  Gabbard, RFK Jr, DOGE / Elon-Musk-DOGE, and Trump-led global combos
  (Trump+Putin, Trump+Xi, Trump+NATO, Trump+Netanyahu, Trump+Zelensky,
  Trump tariffs, Trump pardon, Trump indictment, Trump rally).
- **`blocked_topics_add`** — adds Iran/Gaza-only stories that don't
  mention Trump (we still pick those up if "Trump" is in the title).

### `vizard.overlay.yaml`

No Vizard changes yet — the publish cadence (TikTok 2/day etc.) and
viral score floor (9.0) from the base config still apply.

## Why this approach

We learned the hard way that editing `config/scoring.yaml` and
`config/vizard.yaml` directly on every iteration causes regressions
(channels removed, knobs forgotten). This overlay folder is the new
home for every iteration going forward. The base config is now a
"set once, leave alone" thing.

## Roll back

Comment out the `2026-06-trump-focus` line in `extensions/active.yaml`.
The folder stays on disk as audit history.
