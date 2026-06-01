from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace


def test_app_runs_startup_cache_prebuild_before_gpu_and_live_execution() -> None:
    source = Path("gear_optimizer/app.py").read_text(encoding="utf-8")

    cache_idx = source.index("run_startup_cpu_work(")
    gpu_idx = source.index("self._configure_execution_and_prewarm(cfg)")
    execute_idx = source.index("self._execute_tasks(")

    assert cache_idx < gpu_idx < execute_idx


def test_cpu_work_manager_runs_timeline_and_fg_cache_phases(monkeypatch) -> None:
    from gear_optimizer.solver import cpu_work_manager
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import FgResponseFrontierCachePrebuildSummary
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import TimelineFrontierCachePrebuildSummary

    calls: list[str] = []

    def _timeline(**_kwargs):
        calls.append("timeline")
        return TimelineFrontierCachePrebuildSummary(total=1, completed=1, disk=1)

    def _fg(**_kwargs):
        calls.append("fg")
        return FgResponseFrontierCachePrebuildSummary(total=1, completed=1, built=1)

    monkeypatch.setattr(cpu_work_manager, "run_timeline_frontier_cache_prebuild", _timeline)
    monkeypatch.setattr(cpu_work_manager, "run_fg_response_frontier_cache_prebuild", _fg)

    cpu_work_manager.run_startup_cpu_work(
        cfg=object(),
        song_queue=[("Data/Easy/Fake.txt",)],
        ref_arrays={},
        data_root="Data",
    )

    assert set(calls) == {"timeline", "fg"}


def test_cpu_work_manager_suppresses_startup_cache_banner_when_all_cache_hits(monkeypatch) -> None:
    from gear_optimizer.solver import cpu_work_manager
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import FgResponseFrontierCachePrebuildSummary
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import TimelineFrontierCachePrebuildSummary

    monkeypatch.setattr(
        cpu_work_manager,
        "run_timeline_frontier_cache_prebuild",
        lambda **_kwargs: TimelineFrontierCachePrebuildSummary(total=1, completed=1, built=0, disk=1, memory=0),
    )
    monkeypatch.setattr(
        cpu_work_manager,
        "run_fg_response_frontier_cache_prebuild",
        lambda **_kwargs: FgResponseFrontierCachePrebuildSummary(total=1, completed=1, built=0, disk=1, memory=0),
    )

    stream = io.StringIO()
    cpu_work_manager.run_startup_cpu_work(
        cfg=object(),
        song_queue=[("Data/Easy/Fake.txt",)],
        ref_arrays={},
        data_root="Data",
        announce_stream=stream,
    )

    assert "[Startup][Cache]" not in stream.getvalue()


def test_cpu_work_manager_announces_startup_cache_banner_when_builds_run(monkeypatch) -> None:
    from gear_optimizer.solver import cpu_work_manager
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import FgResponseFrontierCachePrebuildSummary
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import TimelineFrontierCachePrebuildSummary

    monkeypatch.setattr(
        cpu_work_manager,
        "run_timeline_frontier_cache_prebuild",
        lambda **_kwargs: TimelineFrontierCachePrebuildSummary(total=1, completed=1, built=1, disk=0, memory=0),
    )
    monkeypatch.setattr(
        cpu_work_manager,
        "run_fg_response_frontier_cache_prebuild",
        lambda **_kwargs: FgResponseFrontierCachePrebuildSummary(total=1, completed=1, built=0, disk=1, memory=0),
    )

    stream = io.StringIO()
    cpu_work_manager.run_startup_cpu_work(
        cfg=object(),
        song_queue=[("Data/Easy/Fake.txt",)],
        ref_arrays={},
        data_root="Data",
        announce_stream=stream,
    )

    assert stream.getvalue().count("[Startup][Cache]") == 1


def test_startup_frontier_cache_prebuild_has_no_scope_or_disable_flags() -> None:
    forbidden = (
        "TimelineFrontierCachePrebuildScope",
        "TimelineFrontierCachePrebuildMaxSongs",
        "TimelineFrontierCachePrebuildExecutor",
        "TIMELINE_FRONTIER_CACHE_PREBUILD_SCOPE",
        "TIMELINE_FRONTIER_CACHE_PREBUILD_MAX_SONGS",
        "TIMELINE_FRONTIER_CACHE_PREBUILD_EXECUTOR",
        "FRONTIER_CACHE_PREBUILD",
        "skip_cached",
        "CpuWorkManager",
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


def test_fg_response_prebuild_skips_valid_cache_hit(monkeypatch, tmp_path: Path) -> None:
    from gear_optimizer.solver import fg_response_frontier_cache_prebuild as prebuild
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import FgResponseFrontierCacheInfo

    song_path = tmp_path / "Song.txt"
    song_path.write_text("fake", encoding="utf-8")
    cache_path = tmp_path / "cache.npz"
    cache_path.write_text("cache", encoding="utf-8")

    calc_song = {"metadata": {"Song Name": "Cached Song"}, "song_data": {"timestamps": [1.0, 2.0]}}

    monkeypatch.setattr("gear_optimizer.data.song_io.get_base_calc_song", lambda *_args, **_kwargs: calc_song)
    monkeypatch.setattr("gear_optimizer.solver.timing_envelope.apply_timing_envelope", lambda _song: None)

    def _cache_info(_calc_song, _ref_arrays, *, stat_keys):
        return FgResponseFrontierCacheInfo(
            cache_key=("cache",),
            disk_path=cache_path,
            cache_source="disk",
            total_notes=2,
            long_notes=0,
            frontier_count=len(tuple(stat_keys)),
        )

    def _unexpected_build(*_args, **_kwargs):
        raise AssertionError("valid startup cache hit must not rebuild")

    monkeypatch.setattr(
        "gear_optimizer.solver.taichi_gem.force_greats.response_cache.fg_response_frontier_payload_cache_info",
        _cache_info,
    )
    monkeypatch.setattr(
        "gear_optimizer.solver.taichi_gem.force_greats.response_cache.build_or_load_response_frontier_payload",
        _unexpected_build,
    )

    result = prebuild.build_fg_response_frontier_cache_for_path(
        str(song_path),
        {"Fever Time": [0.0], "Fever Fill Rate": [0.0]},
        stat_keys=((0, 0),),
    )

    assert result.source == "disk"
    assert result.build_ms == 0.0
    assert result.cache_file == str(cache_path)


def test_fg_response_prebuild_builds_cache_miss(monkeypatch, tmp_path: Path) -> None:
    from gear_optimizer.solver import fg_response_frontier_cache_prebuild as prebuild
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import FgResponseFrontierCacheInfo

    song_path = tmp_path / "Song.txt"
    song_path.write_text("fake", encoding="utf-8")
    cache_path = tmp_path / "cache.npz"
    calc_song = {"metadata": {"Song Name": "Missing Song"}, "song_data": {"timestamps": [1.0, 2.0, 3.0]}}

    monkeypatch.setattr("gear_optimizer.data.song_io.get_base_calc_song", lambda *_args, **_kwargs: calc_song)
    monkeypatch.setattr("gear_optimizer.solver.timing_envelope.apply_timing_envelope", lambda _song: None)
    monkeypatch.setattr(
        "gear_optimizer.solver.taichi_gem.force_greats.response_cache.fg_response_frontier_payload_cache_info",
        lambda *_args, **_kwargs: FgResponseFrontierCacheInfo(
            cache_key=("missing",),
            disk_path=cache_path,
            cache_source="missing",
            total_notes=3,
            long_notes=0,
            frontier_count=0,
        ),
    )
    monkeypatch.setattr(
        "gear_optimizer.solver.taichi_gem.force_greats.response_cache.build_or_load_response_frontier_payload",
        lambda *_args, **_kwargs: SimpleNamespace(
            cache_source="built",
            elapsed_ms=12.5,
            total_notes=3,
            long_notes=0,
            frontier_count=1,
            disk_path=cache_path,
        ),
    )

    result = prebuild.build_fg_response_frontier_cache_for_path(
        str(song_path),
        {"Fever Time": [0.0], "Fever Fill Rate": [0.0]},
        stat_keys=((0, 0),),
    )

    assert result.source == "built"
    assert result.build_ms == 12.5
