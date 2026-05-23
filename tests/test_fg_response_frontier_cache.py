from __future__ import annotations

import configparser
from pathlib import Path

import numpy as np


def _calc_song() -> dict:
    return {
        "metadata": {
            "Song Name": "FG Cache Unit",
            "Difficulty": "Easy",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Last Note Time": 0.4,
            "Long Notes": 0,
        },
        "song_data": {
            "timestamps": np.asarray([0.0, 0.2, 0.4], dtype=np.float32),
            "note_types": np.asarray([1, 1, 1], dtype=np.int16),
        },
    }


def _ref_arrays() -> dict[str, np.ndarray]:
    return {
        "Fever Time": np.ones((161,), dtype=np.float32),
        "Fever Fill Rate": np.ones((161,), dtype=np.float32),
    }


def _write_song(path: Path) -> None:
    path.write_text(
        "\n".join(
            (
                "Song Name\tFG Cache Unit",
                "Difficulty\tEasy",
                "Primary Color\tRush",
                "Secondary Color\tFlow",
                "Last Note Time\t0.4",
                "Long Notes\t0",
                "Song Data",
                "0.000 0 0 1",
                "0.200 0 0 1",
                "0.400 0 0 1",
            )
        ),
        encoding="utf-8",
    )


def test_fg_response_frontier_payload_roundtrips_disk_cache(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        reset_fg_response_frontier_payload_cache,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_DISK_CACHE", "1")
    reset_fg_response_frontier_payload_cache()

    first = build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=((0, 0),))
    assert first.cache_source == "built"
    assert first.disk_path.exists()
    assert len(first.payload.frontiers) == 1
    assert first.payload.frontier_for_stats(ft_stat=0, ff_stat=0).first_frontier

    reset_fg_response_frontier_payload_cache()
    second = build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=((0, 0),))
    assert second.cache_source == "disk"
    assert len(second.payload.frontiers) == 1
    assert second.payload.frontier_for_stats(ft_stat=0, ff_stat=0).first_frontier == (
        first.payload.frontier_for_stats(ft_stat=0, ff_stat=0).first_frontier
    )


def test_fg_response_frontier_sparse_bundle_is_single_disk_artifact(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_DISK_CACHE", "1")
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"
    assert first.disk_path.exists()
    assert len(list(tmp_path.glob("*.npz"))) == 1

    def _raise_build(*_args, **_kwargs):
        raise AssertionError("warm sparse bundle should load without rebuilding frontiers")

    response_cache.reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(response_cache, "build_force_greats_response_frontiers_gpu_batch", _raise_build)
    second = response_cache.build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=keys)
    assert second.cache_source == "disk"
    assert set(second.payload.frontier_by_key) == set(keys)


def test_fg_response_frontier_payload_memory_cache_precedes_disk(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_DISK_CACHE", "1")
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"

    def _raise_disk_load(_cache_key):
        raise AssertionError("resident response-frontier payload should not hit disk")

    monkeypatch.setattr(response_cache, "_load_payload", _raise_disk_load)
    info = response_cache.fg_response_frontier_payload_cache_info(_calc_song(), _ref_arrays(), stat_keys=keys)
    assert info.cache_source == "memory"

    second = response_cache.build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=keys)
    assert second.cache_source == "memory"
    assert second.payload is first.payload


def test_fg_response_frontier_prebuild_uses_runtime_cache_key(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import build_fg_response_frontier_cache_for_path
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        fg_response_frontier_payload_cache_info,
        reset_fg_response_frontier_payload_cache,
    )
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_DISK_CACHE", "1")
    reset_fg_response_frontier_payload_cache()
    song_path = tmp_path / "unit_song.txt"
    _write_song(song_path)

    build_result = build_fg_response_frontier_cache_for_path(
        str(song_path),
        _ref_arrays(),
        stat_keys=((0, 0),),
        skip_cached=False,
    )
    assert build_result.source in {"built", "disk", "memory"}

    reset_fg_response_frontier_payload_cache()
    calc_song = get_base_calc_song(str(song_path), {})
    apply_timing_envelope(calc_song)
    cache_info = fg_response_frontier_payload_cache_info(calc_song, _ref_arrays(), stat_keys=((0, 0),))
    assert cache_info.cache_source == "disk"


def test_fg_response_frontier_prebuild_skips_warm_disk_cache(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import build_fg_response_frontier_cache_for_path
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_DISK_CACHE", "1")
    response_cache.reset_fg_response_frontier_payload_cache()
    song_path = tmp_path / "unit_song.txt"
    _write_song(song_path)

    first = build_fg_response_frontier_cache_for_path(
        str(song_path),
        _ref_arrays(),
        stat_keys=((0, 0),),
        skip_cached=False,
    )
    assert first.source == "built"

    def _raise_build(*_args, **_kwargs):
        raise AssertionError("warm disk cache should skip response-frontier construction")

    response_cache.reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(response_cache, "build_or_load_response_frontier_payload", _raise_build)
    second = build_fg_response_frontier_cache_for_path(
        str(song_path),
        _ref_arrays(),
        stat_keys=((0, 0),),
        skip_cached=True,
    )
    assert second.source == "disk"
    assert second.skipped is True


def test_run_fg_response_frontier_prebuild_uses_pool_scope(tmp_path: Path, monkeypatch) -> None:
    import concurrent.futures

    from gear_optimizer.solver import fg_response_frontier_cache_prebuild
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        reset_fg_response_frontier_payload_cache,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_DISK_CACHE", "1")
    monkeypatch.setattr(fg_response_frontier_cache_prebuild, "_full_budget_ftff_stat_keys", lambda: ((0, 0),))
    seen_scope: list[str] = []

    def _fake_paths(*, queue_paths, data_root, scope):
        seen_scope.append(str(scope))
        return list(queue_paths)

    def _thread_executor(*, worker_count, ref_arrays, stat_keys):
        return concurrent.futures.ThreadPoolExecutor(max_workers=1)

    monkeypatch.setattr(fg_response_frontier_cache_prebuild, "ordered_timeline_frontier_cache_paths", _fake_paths)
    monkeypatch.setattr(fg_response_frontier_cache_prebuild, "_build_prebuild_executor", _thread_executor)
    reset_fg_response_frontier_payload_cache()
    song_path = tmp_path / "unit_song.txt"
    _write_song(song_path)

    cfg = configparser.ConfigParser()
    cfg.add_section("IterationEngine")

    summary = fg_response_frontier_cache_prebuild.run_fg_response_frontier_cache_prebuild(
        cfg=cfg,
        song_queue=[(str(song_path), "FG Cache Unit", "Easy")],
        ref_arrays=_ref_arrays(),
        data_root=tmp_path,
    )
    assert summary.total == 1
    assert summary.completed == 1
    assert summary.failures == 0
    assert summary.built == 1
    assert seen_scope == ["pool"]


def test_fg_response_frontier_prebuild_defaults_to_full_budget_keys() -> None:
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import (
        read_fg_response_frontier_cache_prebuild_settings,
    )

    settings = read_fg_response_frontier_cache_prebuild_settings(None)

    assert len(settings.stat_keys) > 1000


def test_fg_response_frontier_prebuild_ignores_stat_key_flags(monkeypatch) -> None:
    from gear_optimizer.solver import fg_response_frontier_cache_prebuild
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import (
        read_fg_response_frontier_cache_prebuild_settings,
    )

    cfg = configparser.ConfigParser()
    cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "FGResponseFrontierCachePrebuildStatKeys", "0:0")
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_PREBUILD_STAT_KEYS", "0:0")
    monkeypatch.setattr(fg_response_frontier_cache_prebuild, "_full_budget_ftff_stat_keys", lambda: ((7, 8),))

    settings = read_fg_response_frontier_cache_prebuild_settings(cfg)

    assert settings.stat_keys == ((7, 8),)


def test_fg_response_frontier_prebuild_has_no_public_flags() -> None:
    forbidden = (
        "FGResponseFrontierCachePrebuildScope",
        "FGResponseFrontierCachePrebuildWorkers",
        "FGResponseFrontierCachePrebuildMaxSongs",
        "FGResponseFrontierCachePrebuildExecutor",
        "FGResponseFrontierCachePrebuildStatKeys",
        "FG_RESPONSE_FRONTIER_CACHE_PREBUILD",
    )
    paths = list(Path("gear_optimizer").rglob("*.py")) + [Path("config.ini"), Path("config.profile.ini")]
    offenders: list[tuple[str, str]] = []
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            if token in text:
                offenders.append((str(path), token))
    assert offenders == []


def test_frontier_cache_prebuild_passes_same_queue_to_timeline_and_fg(monkeypatch) -> None:
    from gear_optimizer.solver import frontier_cache_prebuild
    from gear_optimizer.solver.frontier_cache_prebuild import run_frontier_cache_prebuilds
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import FgResponseFrontierCachePrebuildSummary
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import TimelineFrontierCachePrebuildSummary

    seen: list[tuple[str, list[tuple[str, str, str]]]] = []

    def _fake_timeline(*, cfg, song_queue, ref_arrays, data_root):
        seen.append(("timeline", list(song_queue)))
        return TimelineFrontierCachePrebuildSummary(total=1, completed=1)

    def _fake_fg(*, cfg, song_queue, ref_arrays, data_root):
        seen.append(("fg", list(song_queue)))
        return FgResponseFrontierCachePrebuildSummary(total=1, completed=1)

    monkeypatch.setattr(frontier_cache_prebuild, "run_timeline_frontier_cache_prebuild", _fake_timeline)
    monkeypatch.setattr(frontier_cache_prebuild, "run_fg_response_frontier_cache_prebuild", _fake_fg)

    queue = ((str(idx), "Song", "Easy") for idx in range(1))
    run_frontier_cache_prebuilds(cfg=None, song_queue=queue, ref_arrays={}, data_root=None)

    assert sorted(seen) == [
        ("fg", [("0", "Song", "Easy")]),
        ("timeline", [("0", "Song", "Easy")]),
    ]


def test_cpu_work_manager_delegates_frontier_prebuild(monkeypatch) -> None:
    from gear_optimizer.solver import cpu_work_manager
    from gear_optimizer.solver.cpu_work_manager import CpuWorkManager
    from gear_optimizer.solver.frontier_cache_prebuild import FrontierCachePrebuildSummary
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import FgResponseFrontierCachePrebuildSummary
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import TimelineFrontierCachePrebuildSummary

    seen: list[list[tuple[str, str, str]]] = []

    def _fake_frontiers(*, cfg, song_queue, ref_arrays, data_root):
        seen.append(list(song_queue))
        return FrontierCachePrebuildSummary(
            timeline=TimelineFrontierCachePrebuildSummary(total=1, completed=1),
            fg_response=FgResponseFrontierCachePrebuildSummary(total=1, completed=1),
            elapsed_ms=1.0,
        )

    monkeypatch.setattr(cpu_work_manager, "run_frontier_cache_prebuilds", _fake_frontiers)

    queue = ((str(idx), "Song", "Easy") for idx in range(1))
    CpuWorkManager().run_startup(cfg=None, song_queue=queue, ref_arrays={}, data_root=None)

    assert seen == [[("0", "Song", "Easy")]]
