"""Overlay loader — additive config layering.

The base configs in `config/*.yaml` are the stable main frame and are
NOT meant to be edited on every iteration. Instead, each adjustment
lives in its own dated folder inside `extensions/`. This module merges
those overlays on top of the base config at runtime.

See `extensions/README.md` for the user-facing description of the
overlay pattern. This file is the only one-time plumbing change in
`src/` — every future adjustment is YAML-only.

Merge rules
-----------
- Scalar key in overlay        -> overrides base.
- Dict key in overlay          -> deep-merged into base dict.
- List key in overlay          -> REPLACES base list.
- `<key>_add`  in overlay      -> EXTENDS base list (dedup, order preserved).
- `<key>_remove` in overlay    -> REMOVES entries from the base list.

`_add` and `_remove` are accumulated when multiple overlays stack
together, and only resolved against the base list at the final apply
step.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

EXTENSIONS_DIR_NAME = "extensions"
ACTIVE_MANIFEST = "active.yaml"
_ADD_SUFFIX = "_add"
_REMOVE_SUFFIX = "_remove"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def _canon(value: Any) -> Any:
    """Canonical form used for list-dedup comparisons."""
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _dedup_extend(base: list[Any], extra: list[Any]) -> list[Any]:
    seen = {_canon(item) for item in base}
    result = list(base)
    for item in extra or []:
        if _canon(item) not in seen:
            result.append(item)
            seen.add(_canon(item))
    return result


def _merge_overlays(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Combine two overlay layers without consulting any base config.

    The `_add` and `_remove` keys are preserved (concatenated + deduped)
    so the final base merge can apply them in one shot. Plain scalars
    in `b` override `a`, dicts recurse, lists in `b` replace lists in `a`.
    """
    result = deepcopy(a)
    for key, b_value in b.items():
        if key.endswith(_ADD_SUFFIX) or key.endswith(_REMOVE_SUFFIX):
            existing = list(result.get(key, []) or [])
            result[key] = _dedup_extend(existing, list(b_value or []))
            continue

        a_value = result.get(key)
        if isinstance(a_value, dict) and isinstance(b_value, dict):
            result[key] = _merge_overlays(a_value, b_value)
        else:
            result[key] = deepcopy(b_value)
    return result


def _apply_to_base(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Apply an already-collapsed overlay dict onto the base config.

    Resolves `_add` / `_remove` keys against the actual lists in `base`.
    Plain keys in `overlay` win; nested dicts recurse.
    """
    result = deepcopy(base)
    for key, overlay_value in overlay.items():
        if key.endswith(_ADD_SUFFIX):
            target = key[: -len(_ADD_SUFFIX)]
            base_list = list(result.get(target, []) or [])
            result[target] = _dedup_extend(base_list, list(overlay_value or []))
            continue

        if key.endswith(_REMOVE_SUFFIX):
            target = key[: -len(_REMOVE_SUFFIX)]
            base_list = list(result.get(target, []) or [])
            blocked = {_canon(item) for item in (overlay_value or [])}
            result[target] = [item for item in base_list if _canon(item) not in blocked]
            continue

        base_value = result.get(key)
        if isinstance(base_value, dict) and isinstance(overlay_value, dict):
            result[key] = _apply_to_base(base_value, overlay_value)
        else:
            result[key] = deepcopy(overlay_value)
    return result


# Backward-compat alias used by tests; behaves as overlay-onto-base.
def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    return _apply_to_base(base, overlay)


def list_active_overlays(root_dir: Path) -> list[str]:
    """Return ordered overlay folder names declared in extensions/active.yaml.

    Empty list if the extensions folder or manifest is missing — pipeline
    works exactly like before.
    """
    manifest = root_dir / EXTENSIONS_DIR_NAME / ACTIVE_MANIFEST
    data = _load_yaml(manifest)
    active = data.get("active", []) or []
    return [str(name).strip() for name in active if name]


def load_overlay_yaml(
    root_dir: Path,
    base_filename: str,
) -> dict[str, Any]:
    """Combine every active overlay's `<base_filename>` into one dict,
    in the order declared by `active.yaml`. Returns an empty dict when
    no overlays apply. `_add` / `_remove` keys are accumulated, NOT
    resolved here — that happens in `apply_overlay`.
    """
    overlays_dir = root_dir / EXTENSIONS_DIR_NAME
    merged: dict[str, Any] = {}
    for overlay_name in list_active_overlays(root_dir):
        overlay_path = overlays_dir / overlay_name / base_filename
        if not overlay_path.exists():
            continue
        overlay_data = _load_yaml(overlay_path)
        if not isinstance(overlay_data, dict):
            continue
        merged = _merge_overlays(merged, overlay_data)
    return merged


def apply_overlay(
    base: dict[str, Any],
    root_dir: Path,
    overlay_filename: str,
) -> dict[str, Any]:
    """Load active overlays for `overlay_filename` and apply them onto
    `base`. Returns a new dict; `base` is not mutated."""
    overlay = load_overlay_yaml(root_dir, overlay_filename)
    if not overlay:
        return deepcopy(base)
    return _apply_to_base(base, overlay)
