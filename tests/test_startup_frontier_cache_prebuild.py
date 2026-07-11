from __future__ import annotations

import io
import json
import os
import time
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
        calls.append("timeline_start")
        time.sleep(0.02)
        calls.append("timeline_end")
        return TimelineFrontierCachePrebuildSummary(total=1, completed=1, disk=1)

    def _fg(**_kwargs):
        calls.append("fg_start")
        calls.append("fg_end")
        return FgResponseFrontierCachePrebuildSummary(total=1, completed=1, built=1)

    monkeypatch.setattr(cpu_work_manager, "run_timeline_frontier_cache_prebuild", _timeline)
    monkeypatch.setattr(cpu_work_manager, "run_fg_response_frontier_cache_prebuild", _fg)

    cpu_work_manager.run_startup_cpu_work(
        cfg=object(),
        song_queue=[("Data/Easy/Fake.txt",)],
        ref_arrays={},
        data_root="Data",
    )

    assert calls == ["timeline_start", "timeline_end", "fg_start", "fg_end"]


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

    output = stream.getvalue()
    assert "Verifying exact timeline + FG response frontier caches" in output
    assert "Building and caching exact timeline + FG response frontiers" not in output


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

    output = stream.getvalue()
    assert "Verifying exact timeline + FG response frontier caches" in output
    assert "Building and caching exact timeline + FG response frontiers" in output


def test_cpu_work_manager_reports_individual_phase_elapsed(monkeypatch) -> None:
    from gear_optimizer.solver import cpu_work_manager
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import FgResponseFrontierCachePrebuildSummary
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import TimelineFrontierCachePrebuildSummary

    events: list[tuple[str, dict]] = []
    perf_values = iter((100.0, 100.25, 200.0, 200.75))

    monkeypatch.setattr(cpu_work_manager.time, "perf_counter", lambda: next(perf_values))
    monkeypatch.setattr(
        cpu_work_manager,
        "emit_profile_event",
        lambda *, component, event, metrics: events.append((event, dict(metrics))),
    )
    monkeypatch.setattr(
        cpu_work_manager,
        "run_timeline_frontier_cache_prebuild",
        lambda **_kwargs: TimelineFrontierCachePrebuildSummary(total=1, completed=1, built=1),
    )
    monkeypatch.setattr(
        cpu_work_manager,
        "run_fg_response_frontier_cache_prebuild",
        lambda **_kwargs: FgResponseFrontierCachePrebuildSummary(total=1, completed=1, built=1),
    )

    cpu_work_manager.run_startup_cpu_work(
        cfg=object(),
        song_queue=[("Data/Easy/Fake.txt",)],
        ref_arrays={},
        data_root="Data",
    )

    done_metrics = [metrics for event, metrics in events if event == "startup_cpu_work_done"]
    elapsed_by_phase = {str(metrics["phase"]): float(metrics["elapsed_ms"]) for metrics in done_metrics}
    assert elapsed_by_phase == {
        "timeline_frontier_cache": 250.0,
        "fg_response_frontier_cache": 750.0,
    }


def test_timeline_single_missing_prebuild_runs_in_process(monkeypatch, tmp_path: Path) -> None:
    from gear_optimizer.solver import timeline_frontier_cache_prebuild as prebuild

    song_path = tmp_path / "Song.txt"
    song_path.write_text("fake", encoding="utf-8")
    built: list[str] = []

    class _UnexpectedExecutor:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("single missing path must not spawn a process pool")

    monkeypatch.setattr(prebuild.concurrent.futures, "ProcessPoolExecutor", _UnexpectedExecutor)
    monkeypatch.setattr(
        prebuild,
        "build_timeline_frontier_cache_for_path",
        lambda path, _ref_arrays: built.append(str(path))
        or prebuild.TimelineFrontierCacheBuildResult(
            path=str(path),
            source="disk",
            build_ms=0.0,
            cache_file="cache.npz",
        ),
    )

    summary, results = prebuild._run_missing_timeline_prebuild([str(song_path)], {})

    assert built == [str(song_path)]
    assert summary.completed == 1
    assert summary.disk == 1
    assert results[0].path == str(song_path)


def test_fg_single_missing_prebuild_runs_in_process(monkeypatch, tmp_path: Path) -> None:
    from gear_optimizer.solver import fg_response_frontier_cache_prebuild as prebuild

    song_path = tmp_path / "Song.txt"
    song_path.write_text("fake", encoding="utf-8")
    built: list[str] = []

    class _UnexpectedExecutor:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("single missing path must not spawn a process pool")

    monkeypatch.setattr(
        prebuild,
        "_dedupe_paths_by_response_bundle_key",
        lambda paths, _ref_arrays: (
            [
                prebuild.FgPrebuildChart(
                    path=str(path),
                    digest=str(path),
                    note_count=0,
                    long_notes=0,
                    duration_sec=0.0,
                )
                for path in paths
            ],
            {},
        ),
    )
    monkeypatch.setattr(prebuild.concurrent.futures, "ProcessPoolExecutor", lambda **_kwargs: _UnexpectedExecutor())
    monkeypatch.setattr(
        prebuild,
        "build_fg_response_frontier_cache_for_path",
        lambda path, _ref_arrays, *, stat_keys: built.append(str(path))
        or prebuild.FgResponseFrontierCacheBuildResult(
            path=str(path),
            source="disk",
            build_ms=0.0,
            cache_file="cache.npz",
        ),
    )

    summary, results = prebuild._run_missing_fg_prebuild([str(song_path)], {}, ((0, 0),))

    assert built == [str(song_path)]
    assert summary.completed == 1
    assert summary.disk == 1
    assert results[0].path == str(song_path)


def test_fg_prebuild_weighted_admission_bounds_inflight_weight_and_completes_all(monkeypatch) -> None:
    """The admission scheduler must (a) never let the sum of in-flight memory weights exceed the
    RAM budget -- the invariant whose absence crashed the machine on 2026-07-09 -- while (b) still
    completing every song (progress guarantee: one build is always admitted)."""
    from gear_optimizer.solver import fg_response_frontier_cache_prebuild as prebuild

    # 26 GB available -> budget 20 GB: one ~12 GB giant at a time, light charts backfill.
    monkeypatch.setattr(prebuild, "_fg_prebuild_available_ram_gb", lambda: 26.0)
    monkeypatch.setattr(prebuild, "frontier_prebuild_worker_count", lambda: 8)
    monkeypatch.setattr(prebuild, "frontier_prebuild_cpu_count", lambda: 31)
    # Hermetic closed-loop inputs: no real pool workers exist under the fake executor, and the
    # RAM guard thread has nothing real to guard.
    monkeypatch.setattr(prebuild, "_fg_prebuild_live_worker_commit_gb", lambda: 0.0)
    monkeypatch.setattr(prebuild, "_start_fg_prebuild_ram_guard", lambda: None)
    items = [
        prebuild.FgPrebuildChart(path=f"giant{i}.txt", digest=f"g{i}", note_count=7000, long_notes=0, duration_sec=1.0)
        for i in range(3)
    ] + [
        prebuild.FgPrebuildChart(path=f"light{i}.txt", digest=f"l{i}", note_count=500, long_notes=0, duration_sec=1.0)
        for i in range(4)
    ]
    monkeypatch.setattr(
        prebuild, "_dedupe_paths_by_response_bundle_key", lambda _paths, _ref_arrays: (list(items), {})
    )

    budget_gb = 26.0 - prebuild._FG_PREBUILD_SYSTEM_RESERVE_GB
    ledger_peaks: list[float] = []

    class _FakeFuture:
        def __init__(self, path: str):
            self._result = prebuild.FgResponseFrontierCacheBuildResult(
                path=path, source="built", build_ms=1.0, cache_file=f"{path}.npz"
            )

        def result(self):
            return self._result

    class _FakeExecutor:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def submit(self, _fn, path, reducer_threads):
            assert int(reducer_threads) >= 1
            return _FakeFuture(str(path))

    def _fake_wait(futures, timeout=None, return_when=None):
        del timeout, return_when
        # Record the in-flight weight peak at each drain point, then complete exactly one build.
        ordered = list(futures)
        ledger_peaks.append(sum(futures[future][1] for future in ordered))
        return {ordered[0]}, set(ordered[1:])

    monkeypatch.setattr(prebuild.concurrent.futures, "ProcessPoolExecutor", _FakeExecutor)
    monkeypatch.setattr(prebuild.concurrent.futures, "wait", _fake_wait)

    summary, results = prebuild._run_missing_fg_prebuild(
        [item.path for item in items], {}, ((0, 0),)
    )

    assert summary.completed == len(items)
    assert summary.failures == 0
    assert sorted(result.path for result in results) == sorted(item.path for item in items)
    assert ledger_peaks, "admission loop never drained"
    assert max(ledger_peaks) <= budget_gb + 1e-9


def test_fg_prebuild_submits_longest_compatible_completed_duration_first(
    monkeypatch, tmp_path: Path
) -> None:
    from gear_optimizer.solver import fg_response_frontier_cache_prebuild as prebuild
    from gear_optimizer.solver.fg_response_frontier_timing_history import (
        FgPrebuildTimingContext,
        update_fg_prebuild_timing_history,
    )

    monkeypatch.setattr(prebuild, "_fg_prebuild_available_ram_gb", lambda: 26.0)
    monkeypatch.setattr(prebuild, "frontier_prebuild_worker_count", lambda: 2)
    monkeypatch.setattr(prebuild, "frontier_prebuild_cpu_count", lambda: 8)
    monkeypatch.setattr(prebuild, "_fg_prebuild_live_worker_commit_gb", lambda: 0.0)
    monkeypatch.setattr(prebuild, "_start_fg_prebuild_ram_guard", lambda: None)
    monkeypatch.setattr(prebuild, "_cache_version", lambda: "version")
    monkeypatch.setattr(prebuild, "_ref_axes_signature", lambda _arrays: "ref")
    monkeypatch.setattr(prebuild, "_stat_keys_signature", lambda _keys: "stats")
    monkeypatch.setattr(prebuild, "fg_prebuild_cpu_identity", lambda: "cpu")
    charts = [
        prebuild.FgPrebuildChart("large-notes.txt", "large", 2000, 0, 200.0),
        prebuild.FgPrebuildChart("long-history.txt", "long", 1000, 0, 100.0),
        prebuild.FgPrebuildChart("short-history.txt", "short", 900, 0, 90.0),
    ]
    monkeypatch.setattr(
        prebuild,
        "_dedupe_paths_by_response_bundle_key",
        lambda _paths, _ref_arrays: (list(charts), {}),
    )
    history_path = tmp_path / "timing.json"
    context = FgPrebuildTimingContext("version", "cpu", 4, "ref", "stats", 8, 2)
    records = update_fg_prebuild_timing_history(
        history_path,
        [],
        chart=charts[1],
        context=context,
        duration_ms=9000.0,
    )
    update_fg_prebuild_timing_history(
        history_path,
        records,
        chart=charts[2],
        context=context,
        duration_ms=1000.0,
    )
    submitted: list[str] = []

    class _FakeFuture:
        def __init__(self, path: str):
            self.path = path

        def result(self):
            return prebuild.FgResponseFrontierCacheBuildResult(
                path=self.path,
                source="built",
                build_ms=500.0,
                cache_file=f"{self.path}.npz",
            )

    class _FakeExecutor:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def submit(self, _fn, path, _reducer_threads):
            submitted.append(str(path))
            return _FakeFuture(str(path))

    def _fake_wait(futures, timeout=None, return_when=None):
        del timeout, return_when
        ordered = list(futures)
        return {ordered[0]}, set(ordered[1:])

    monkeypatch.setattr(prebuild.concurrent.futures, "ProcessPoolExecutor", _FakeExecutor)
    monkeypatch.setattr(prebuild.concurrent.futures, "wait", _fake_wait)

    summary, _results = prebuild._run_missing_fg_prebuild(
        [chart.path for chart in charts],
        {},
        ((0, 0),),
        timing_history_path=history_path,
    )

    assert summary.completed == 3
    assert submitted[0] == "long-history.txt"


def test_fg_response_prebuild_does_not_parse_priority_for_manifest_hits(monkeypatch, tmp_path: Path) -> None:
    from gear_optimizer.solver import fg_response_frontier_cache_prebuild as prebuild

    song_a = tmp_path / "SongA.txt"
    song_b = tmp_path / "SongB.txt"
    song_a.write_text("fake", encoding="utf-8")
    song_b.write_text("fake", encoding="utf-8")

    class _Plan:
        total_paths = 2
        hit_paths = (str(song_a), str(song_b))
        missing_paths = ()
        key_by_norm_path = {}

        @property
        def hit_count(self) -> int:
            return 2

    monkeypatch.setattr(prebuild, "all_response_stat_keys", lambda: ((0, 0),))
    monkeypatch.setattr(prebuild, "_build_manifest_plan", lambda *_args, **_kwargs: _Plan())
    monkeypatch.setattr(prebuild, "_apply_manifest_results", lambda **_kwargs: 0)
    monkeypatch.setattr(
        "gear_optimizer.solver.taichi_gem.force_greats.response_cache.cleanup_fg_response_frontier_cache_temp_files",
        lambda: 0,
    )
    compression_calls = 0

    def _compress() -> None:
        nonlocal compression_calls
        compression_calls += 1

    monkeypatch.setattr(
        "gear_optimizer.solver.taichi_gem.force_greats.response_cache.compress_cache_dir_sidecars",
        _compress,
    )

    def _unexpected_parse(_paths, _ref_arrays):
        raise AssertionError("manifest hits must not reach the dedupe/weight parse pass")

    monkeypatch.setattr(prebuild, "_dedupe_paths_by_response_bundle_key", _unexpected_parse)

    summary = prebuild.run_fg_response_frontier_cache_prebuild(
        cfg=object(),
        song_queue=[(str(song_a),), (str(song_b),)],
        ref_arrays={"Fever Time": [0.0], "Fever Fill Rate": [0.0]},
        data_root=tmp_path,
    )

    assert summary.total == 2
    assert summary.completed == 2
    assert summary.disk == 2
    assert compression_calls == 1


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


def test_fg_response_manifest_treats_incomplete_cache_file_as_miss(monkeypatch, tmp_path: Path) -> None:
    from gear_optimizer.solver import fg_response_frontier_cache_prebuild as prebuild

    cache_dir = tmp_path / "cache"
    song_path = tmp_path / "Song.txt"
    cache_path = tmp_path / "broken.npz"
    song_path.write_text("fake", encoding="utf-8")
    cache_path.write_text("not a complete npz", encoding="utf-8")
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(cache_dir))
    ref_arrays = {"Fever Time": [1.0] * 161, "Fever Fill Rate": [1.0] * 161}
    stat_keys = ((0, 0),)

    plan = prebuild._build_manifest_plan([str(song_path)], ref_arrays, stat_keys=stat_keys)
    prebuild._apply_manifest_results(
        plan=plan,
        results=[SimpleNamespace(path=str(song_path), source="disk", cache_file=str(cache_path))],
        stat_keys=stat_keys,
    )

    second_plan = prebuild._build_manifest_plan([str(song_path)], ref_arrays, stat_keys=stat_keys)

    assert second_plan.hit_paths == ()
    assert second_plan.missing_paths == (str(song_path),)


def test_timeline_manifest_treats_incomplete_cache_file_as_miss(monkeypatch, tmp_path: Path) -> None:
    from gear_optimizer.solver import timeline_frontier_cache_prebuild as prebuild

    cache_dir = tmp_path / "cache"
    song_path = tmp_path / "Song.txt"
    cache_path = tmp_path / "broken.npz"
    song_path.write_text("fake", encoding="utf-8")
    cache_path.write_text("not a complete npz", encoding="utf-8")
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(cache_dir))
    ref_arrays = {"Fever Time": [1.0] * 161, "Fever Fill Rate": [1.0] * 161}

    plan = prebuild._build_manifest_plan([str(song_path)], ref_arrays)
    prebuild._apply_manifest_results(
        plan=plan,
        results=[SimpleNamespace(path=str(song_path), source="disk", cache_file=str(cache_path))],
    )

    second_plan = prebuild._build_manifest_plan([str(song_path)], ref_arrays)

    assert second_plan.hit_paths == ()
    assert second_plan.missing_paths == (str(song_path),)


def test_manifest_identity_hit_does_not_validate_payload(tmp_path: Path) -> None:
    from gear_optimizer.solver.frontier_cache_manifest import build_manifest_plan

    song_path = tmp_path / "Song.txt"
    cache_path = tmp_path / "cache.npz"
    manifest_path = tmp_path / "manifest.json"
    song_path.write_text("fake", encoding="utf-8")
    cache_path.write_text("cache", encoding="utf-8")
    st = os.stat(cache_path)

    first_plan = build_manifest_plan(
        [str(song_path)],
        manifest_path=manifest_path,
        cache_version="v1",
        version_field="version",
        ref_sig_hex="ref",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "schema": 1,
                "version": "v1",
                "entries": {
                    first_plan.key_by_norm_path[os.path.abspath(song_path).casefold()]: {
                        "cache_file": str(cache_path),
                        "cache_mtime_ns": int(st.st_mtime_ns),
                        "cache_size": int(st.st_size),
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    second_plan = build_manifest_plan(
        [str(song_path)],
        manifest_path=manifest_path,
        cache_version="v1",
        version_field="version",
        ref_sig_hex="ref",
        cache_file_validator=lambda _path: (_ for _ in ()).throw(
            AssertionError("identity hit must not validate payload")
        ),
    )

    assert second_plan.hit_paths == (str(song_path),)
    assert second_plan.missing_paths == ()
