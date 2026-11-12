from __future__ import annotations

from pathlib import Path

import pytest

from gear_optimizer.frontier.fg_cache_store import FG_RESPONSE_FRONTIER_CACHE
from gear_optimizer.frontier.timeline_cache import TIMELINE_FRONTIER_CACHE

CACHES = (
    (TIMELINE_FRONTIER_CACHE, "TIMELINE_FRONTIER_CACHE_DIR", "timeline_frontier_cache"),
    (FG_RESPONSE_FRONTIER_CACHE, "FG_RESPONSE_FRONTIER_CACHE_DIR", "fg_response_frontier_cache"),
)


@pytest.mark.parametrize(("cache", "override_name", "cache_leaf"), CACHES)
def test_frontier_cache_default_follows_runtime_bin_dir(monkeypatch, tmp_path: Path, cache, override_name, cache_leaf) -> None:
    runtime_bin = tmp_path / "instance-bin"
    monkeypatch.delenv(override_name, raising=False)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_BIN_DIR", str(runtime_bin))

    assert cache.directory() == runtime_bin / cache_leaf


@pytest.mark.parametrize(("cache", "override_name", "_cache_leaf"), CACHES)
def test_frontier_cache_explicit_override_wins_over_runtime_bin_dir(
    monkeypatch, tmp_path: Path, cache, override_name, _cache_leaf
) -> None:
    explicit_cache = tmp_path / "explicit-cache"
    monkeypatch.setenv(override_name, str(explicit_cache))
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_BIN_DIR", str(tmp_path / "instance-bin"))

    assert cache.directory() == explicit_cache
