"""Pytest config: redirect OUTPUT_DIR to a temp dir per test so the suite
never touches the real `output/` state files."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _isolated_output_dir(tmp_path, monkeypatch):
    """Point every module's OUTPUT_DIR / *_PATH constant at tmp_path."""
    import src.config as config_mod

    monkeypatch.setattr(config_mod, "OUTPUT_DIR", tmp_path, raising=True)

    # Reload modules that capture OUTPUT_DIR at import time.
    for name in (
        "src.storage.daily_counts",
        "src.storage.dedupe_ledger",
        "src.storage.pruner",
        "src.storage.queue",
        "src.safety.content_filter",
        "src.vizard.pipeline",
    ):
        if name in sys.modules:
            importlib.reload(sys.modules[name])

    yield tmp_path

    # Restore module state after the test so subsequent imports are clean.
    for name in (
        "src.storage.daily_counts",
        "src.storage.dedupe_ledger",
        "src.storage.pruner",
        "src.safety.content_filter",
        "src.vizard.pipeline",
    ):
        if name in sys.modules:
            importlib.reload(sys.modules[name])
