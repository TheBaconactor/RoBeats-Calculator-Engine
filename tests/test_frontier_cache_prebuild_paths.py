from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("module_name", "resolver_name", "override_name", "cache_leaf"),
    (
        (
            "gear_optimizer.solver.taichi_gem.api.timeline",
            "_frontier_disk_cache_dir",
            "TIMELINE_FRONTIER_CACHE_DIR",
            "timeline_frontier_cache",
        ),
        (
            "gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys",
            "_fg_response_disk_cache_dir",
            "FG_RESPONSE_FRONTIER_CACHE_DIR",
            "fg_response_frontier_cache",
        ),
    ),
)
def test_frontier_cache_default_follows_runtime_bin_dir(
    monkeypatch,
    tmp_path: Path,
    module_name: str,
    resolver_name: str,
    override_name: str,
    cache_leaf: str,
) -> None:
    import importlib

    module = importlib.import_module(module_name)
    runtime_bin = tmp_path / "instance-bin"
    monkeypatch.delenv(override_name, raising=False)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_BIN_DIR", str(runtime_bin))

    assert getattr(module, resolver_name)() == runtime_bin / cache_leaf


@pytest.mark.parametrize(
    ("module_name", "resolver_name", "override_name"),
    (
        (
            "gear_optimizer.solver.taichi_gem.api.timeline",
            "_frontier_disk_cache_dir",
            "TIMELINE_FRONTIER_CACHE_DIR",
        ),
        (
            "gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys",
            "_fg_response_disk_cache_dir",
            "FG_RESPONSE_FRONTIER_CACHE_DIR",
        ),
    ),
)
def test_frontier_cache_explicit_override_wins_over_runtime_bin_dir(
    monkeypatch,
    tmp_path: Path,
    module_name: str,
    resolver_name: str,
    override_name: str,
) -> None:
    import importlib

    module = importlib.import_module(module_name)
    explicit_cache = tmp_path / "explicit-cache"
    monkeypatch.setenv(override_name, str(explicit_cache))
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_BIN_DIR", str(tmp_path / "instance-bin"))

    assert getattr(module, resolver_name)() == explicit_cache
