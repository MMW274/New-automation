# Extensions — overlay-based adjustments

The `config/` folder and `src/` modules are the **stable main frame** of
this pipeline. Once the system is running well, we do **NOT** edit them
on every tweak — that's how regressions sneak in.

Instead, every adjustment, A/B test, or seasonal focus shift lives in its
own dated folder inside `extensions/`. The pipeline loads them at startup
and **layers them on top of the base config** (deep merge). The base files
stay untouched.

## How an overlay works

1. Create a new folder: `extensions/YYYY-MM-<short-name>/`
2. Drop one or both of these files inside it:
   - `scoring.overlay.yaml` — merged onto `config/scoring.yaml`
   - `vizard.overlay.yaml` — merged onto `config/vizard.yaml`
3. Add the folder name to `extensions/active.yaml` under `active:` (order
   matters — later overlays win on scalar conflicts).
4. (Optional but encouraged) add a `README.md` inside the overlay folder
   explaining **what** changed and **why**, with the date.

That's it. The cron / `python -m src.scheduler.run_pipeline` automatically
picks the overlay up. Nothing in `src/` needs editing.

## Merge rules

| YAML key in overlay | Effect on base config |
|---|---|
| Scalar (`min_views: 400000`) | **Overrides** the base scalar |
| Dict (`weights: {…}`) | **Deep-merged** into the base dict |
| List (`relevance_terms: […]`) | **Replaces** the base list entirely |
| Suffix `_add` on a list key (`relevance_terms_add: […]`) | **Extends** the base list (deduped) |
| Suffix `_remove` on a list key (`blocked_topics_remove: […]`) | **Removes** entries from the base list |

This lets you add ten relevance terms in an overlay without copy-pasting
the whole base list, and pull a single blocked topic out without
forking everything.

## Layering

Multiple overlays can be active simultaneously. They are applied in the
order listed in `active.yaml`, so the **last** overlay wins on scalar
conflicts. Use this for stacked tweaks:

```yaml
# extensions/active.yaml
active:
  - 2026-06-trump-focus      # baseline focus tightening
  - 2026-07-epstein-surge    # later: temporarily favour Epstein coverage
```

## When to actually edit the core

Touch `config/*.yaml` or `src/**` only when:

- A new **schema field** is needed (e.g. a brand new platform).
- A **bug** in the main frame must be fixed.
- An overlay capability is missing (extend the loader, then move the
  one-time plumbing into core — never the values themselves).

Everything else goes in an overlay.

## Disabling an overlay

Remove its name from `active.yaml` (or comment the line out). The folder
stays on disk as an audit trail of what was once active.
