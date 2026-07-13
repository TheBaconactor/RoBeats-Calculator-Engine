from __future__ import annotations

from pathlib import Path

import pytest

from gear_optimizer.core.constants import PathConfig


def test_frontier_cache_prebuild_uses_queue_scope_when_queue_is_present(tmp_path: Path) -> None:
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import ordered_frontier_cache_song_paths

    queued = tmp_path / "queued.txt"
    queued.write_text("Song Name\tQueued\n", encoding="utf-8")
    data_song = tmp_path / "Data" / "Hard" / "global.txt"
    data_song.parent.mkdir(parents=True)
    data_song.write_text("Song Name\tGlobal\n", encoding="utf-8")

    paths = ordered_frontier_cache_song_paths(queue_paths=(str(queued),), data_root=tmp_path / "Data")

    assert paths == [str(queued)]


def test_frontier_cache_prebuild_scans_data_when_queue_is_empty(tmp_path: Path) -> None:
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import ordered_frontier_cache_song_paths

    data_song = tmp_path / "Data" / "Hard" / "global.txt"
    data_song.parent.mkdir(parents=True)
    data_song.write_text("Song Name\tGlobal\n", encoding="utf-8")

    paths = ordered_frontier_cache_song_paths(queue_paths=(), data_root=tmp_path / "Data")

    assert paths == [str(data_song)]


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
    monkeypatch.setattr(
        module,
        "PATHS",
        PathConfig(script_dir=str(tmp_path / "source"), bin_dir=str(runtime_bin), data_dir=str(tmp_path / "data")),
    )

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
    monkeypatch.setattr(
        module,
        "PATHS",
        PathConfig(
            script_dir=str(tmp_path / "source"),
            bin_dir=str(tmp_path / "instance-bin"),
            data_dir=str(tmp_path / "data"),
        ),
    )

    assert getattr(module, resolver_name)() == explicit_cache
