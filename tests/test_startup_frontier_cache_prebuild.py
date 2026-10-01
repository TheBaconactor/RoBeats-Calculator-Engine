from __future__ import annotations

import io
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

from gear_optimizer.solver.frontier_cache import FrontierCacheBuildResult, build_frontier_cache_for_chart
from tests.curves_support import synthetic_curves


def test_app_runs_startup_cache_prebuild_before_gpu_and_live_execution() -> None:
    source = Path("gear_optimizer/app.py").read_text(encoding="utf-8")

    cache_idx = source.index("run_startup_cpu_work(")
    gpu_idx = source.index("self._configure_execution_and_prewarm(run.multi_start)")
    execute_idx = source.index("self._execute_tasks(")

    assert cache_idx < gpu_idx < execute_idx


def test_standalone_and_service_share_the_startup_cache_owner() -> None:
    app_source = Path("gear_optimizer/app.py").read_text(encoding="utf-8")
    service_source = Path("gear_optimizer/robeatsmeta_service.py").read_text(encoding="utf-8")

    assert "run_startup_cpu_work(" in app_source
    assert "run_startup_cpu_work(" in service_source
    assert "prebuild_frontier_cache(" not in service_source
    assert 'str(REPO_ROOT / "main.py"), "run"' in service_source


def _fake_prebuilds(monkeypatch, *, timeline, fg) -> None:
    """cpu_work_manager's two prebuilds, faked per cache."""
    from gear_optimizer.solver import cpu_work_manager

    monkeypatch.setattr(
        cpu_work_manager,
        "prebuild_frontier_cache",
        lambda prebuild, **kwargs: {"timeline": timeline, "fg_response": fg}[prebuild.cache.name](**kwargs),
    )


def test_cpu_work_manager_runs_timeline_and_fg_cache_phases(monkeypatch) -> None:
    from gear_optimizer.solver import cpu_work_manager
    from gear_optimizer.solver.frontier_cache import FrontierCachePrebuildSummary

    calls: list[str] = []

    def _timeline(**_kwargs):
        calls.append("timeline_start")
        time.sleep(0.02)
        calls.append("timeline_end")
        return FrontierCachePrebuildSummary(total=1, completed=1, disk=1)

    def _fg(**_kwargs):
        calls.append("fg_start")
        calls.append("fg_end")
        return FrontierCachePrebuildSummary(total=1, completed=1, built=1)

    _fake_prebuilds(monkeypatch, timeline=_timeline, fg=_fg)

    cpu_work_manager.run_startup_cpu_work(
        song_queue=[("Data/Easy/Fake.txt",)],
        curves={},
        data_root="Data",
    )

    assert calls == ["timeline_start", "timeline_end", "fg_start", "fg_end"]


def test_cpu_work_manager_suppresses_startup_cache_banner_when_all_cache_hits(monkeypatch) -> None:
    from gear_optimizer.solver import cpu_work_manager
    from gear_optimizer.solver.frontier_cache import FrontierCachePrebuildSummary

    _fake_prebuilds(
        monkeypatch,
        timeline=lambda **_kwargs: FrontierCachePrebuildSummary(total=1, completed=1, built=0, disk=1, memory=0),
        fg=lambda **_kwargs: FrontierCachePrebuildSummary(total=1, completed=1, built=0, disk=1, memory=0),
    )

    stream = io.StringIO()
    cpu_work_manager.run_startup_cpu_work(
        song_queue=[("Data/Easy/Fake.txt",)],
        curves={},
        data_root="Data",
        announce_stream=stream,
    )

    output = stream.getvalue()
    assert "Verifying exact timeline + FG response frontier caches" in output
    assert "Building and caching exact timeline + FG response frontiers" not in output


def test_cpu_work_manager_announces_startup_cache_banner_when_builds_run(monkeypatch) -> None:
    from gear_optimizer.solver import cpu_work_manager
    from gear_optimizer.solver.frontier_cache import FrontierCachePrebuildSummary

    _fake_prebuilds(
        monkeypatch,
        timeline=lambda **_kwargs: FrontierCachePrebuildSummary(total=1, completed=1, built=1, disk=0, memory=0),
        fg=lambda **_kwargs: FrontierCachePrebuildSummary(total=1, completed=1, built=0, disk=1, memory=0),
    )

    stream = io.StringIO()
    cpu_work_manager.run_startup_cpu_work(
        song_queue=[("Data/Easy/Fake.txt",)],
        curves={},
        data_root="Data",
        announce_stream=stream,
    )

    output = stream.getvalue()
    assert "Verifying exact timeline + FG response frontier caches" in output
    assert "Building and caching exact timeline + FG response frontiers" in output


def test_timeline_single_missing_prebuild_runs_in_process(monkeypatch, tmp_path: Path) -> None:
    from gear_optimizer.solver import timeline_frontier_cache_prebuild as prebuild

    song_path = tmp_path / "Song.txt"
    song_path.write_text("fake", encoding="utf-8")
    built: list[str] = []

    class _UnexpectedExecutor:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("single missing path must not spawn a process pool")

    monkeypatch.setattr(prebuild, "BoundedRecyclingProcessPool", _UnexpectedExecutor)
    monkeypatch.setattr(
        prebuild,
        "build_frontier_cache_for_chart",
        lambda path, _curves, _mode, _ensure: built.append(str(path))
        or FrontierCacheBuildResult(path=str(path), source="disk", build_ms=0.0, cache_file="cache.npz"),
    )

    tally = prebuild._build_timeline_songs([str(song_path)], {}, "perfect_window")

    assert built == [str(song_path)]
    assert len(tally.results) == 1 and tally.sources["disk"] == 1
    assert tally.results[0].path == str(song_path)


def test_timeline_multi_prebuild_recycles_worker_allocator_high_water(monkeypatch) -> None:
    from gear_optimizer.solver import timeline_frontier_cache_prebuild as prebuild

    captured_kwargs = {}

    class _FakeExecutor:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def submit(self, _fn, path, _timing_mode):
            future = prebuild.concurrent.futures.Future()
            future.set_result(
                FrontierCacheBuildResult(path=str(path), source="disk", build_ms=0.0, cache_file=f"{path}.npz")
            )
            return future

    monkeypatch.setattr(prebuild, "timeline_prebuild_worker_count", lambda: 2)
    monkeypatch.setattr(prebuild, "frontier_prebuild_intra_worker_threads", lambda _workers: 1)
    monkeypatch.setattr(prebuild, "BoundedRecyclingProcessPool", _FakeExecutor)

    tally = prebuild._build_timeline_songs(["a.txt", "b.txt"], {}, "perfect_window")

    assert len(tally.results) == 2
    assert captured_kwargs["max_tasks_per_worker"] == prebuild._TIMELINE_PREBUILD_MAX_TASKS_PER_WORKER


def test_timeline_multi_prebuild_counts_broken_worker_future_per_path(monkeypatch) -> None:
    from concurrent.futures.process import BrokenProcessPool

    from gear_optimizer.solver import timeline_frontier_cache_prebuild as prebuild

    class _FakeExecutor:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def submit(self, _fn, path, _timing_mode):
            future = prebuild.concurrent.futures.Future()
            if path == "broken.txt":
                future.set_exception(BrokenProcessPool("native worker exited"))
            else:
                future.set_result(
                    FrontierCacheBuildResult(path=str(path), source="disk", build_ms=0.0, cache_file=f"{path}.npz")
                )
            return future

    monkeypatch.setattr(prebuild, "timeline_prebuild_worker_count", lambda: 2)
    monkeypatch.setattr(prebuild, "frontier_prebuild_intra_worker_threads", lambda _workers: 1)
    monkeypatch.setattr(prebuild, "BoundedRecyclingProcessPool", _FakeExecutor)

    tally = prebuild._build_timeline_songs(["broken.txt", "ready.txt"], {}, "perfect_window")

    assert tally.total == 2
    assert tally.failures == 1
    assert [result.path for result in tally.results] == ["ready.txt"]


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
        lambda paths, _curves, _mode: ([(str(path), 0) for path in paths], {}),
    )
    monkeypatch.setattr(prebuild, "BoundedRecyclingProcessPool", lambda **_kwargs: _UnexpectedExecutor())
    monkeypatch.setattr(
        prebuild,
        "build_frontier_cache_for_chart",
        lambda path, _curves, _mode, _ensure: built.append(str(path))
        or FrontierCacheBuildResult(path=str(path), source="disk", build_ms=0.0, cache_file="cache.npz"),
    )

    tally = prebuild._build_fg_songs([str(song_path)], {}, "perfect_window")

    assert built == [str(song_path)]
    assert len(tally.results) == 1 and tally.sources["disk"] == 1
    assert tally.results[0].path == str(song_path)


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
    monkeypatch.setattr(prebuild, "_start_fg_prebuild_ram_guard", lambda: SimpleNamespace(stop=lambda: None))
    items = [(f"giant{i}.txt", 7000) for i in range(3)] + [(f"light{i}.txt", 500) for i in range(4)]
    monkeypatch.setattr(
        prebuild, "_dedupe_paths_by_response_bundle_key", lambda _paths, _curves, _mode: (list(items), {})
    )

    budget_gb = 26.0 - prebuild._FG_PREBUILD_SYSTEM_RESERVE_GB
    ledger_peaks: list[float] = []

    class _FakeFuture:
        def __init__(self, path: str):
            self._result = FrontierCacheBuildResult(path=path, source="built", build_ms=1.0, cache_file=f"{path}.npz")

        def result(self):
            return self._result

    captured_kwargs = {}

    class _FakeExecutor:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def submit(self, _fn, path, reducer_threads, _timing_mode):
            assert int(reducer_threads) >= 1
            return _FakeFuture(str(path))

    def _fake_wait(futures, timeout=None, return_when=None):
        del timeout, return_when
        # Record the in-flight weight peak at each drain point, then complete exactly one build.
        ordered = list(futures)
        ledger_peaks.append(sum(weight for _path, weight in (futures[f] for f in ordered)))
        return {ordered[0]}, set(ordered[1:])

    monkeypatch.setattr(prebuild, "BoundedRecyclingProcessPool", _FakeExecutor)
    monkeypatch.setattr(prebuild.concurrent.futures, "wait", _fake_wait)

    tally = prebuild._build_fg_songs([path for path, _notes in items], {}, "perfect_window")

    assert len(tally.results) == len(items)
    assert tally.failures == 0
    assert sorted(result.path for result in tally.results) == sorted(path for path, _notes in items)
    assert ledger_peaks, "admission loop never drained"
    assert max(ledger_peaks) <= budget_gb + 1e-9
    assert captured_kwargs["max_tasks_per_worker"] == prebuild._FG_PREBUILD_MAX_TASKS_PER_WORKER


def test_fg_prebuild_tail_admission_counts_the_song_being_submitted(monkeypatch) -> None:
    """After the first one-worker task drains, the final popped song is still one workload unit."""
    from gear_optimizer.solver import fg_response_frontier_cache_prebuild as prebuild

    items = [("first.txt", 100), ("last.txt", 100)]
    monkeypatch.setattr(prebuild, "_fg_prebuild_available_ram_gb", lambda: 64.0)
    monkeypatch.setattr(prebuild, "frontier_prebuild_worker_count", lambda: 1)
    monkeypatch.setattr(prebuild, "frontier_prebuild_cpu_count", lambda: 31)
    monkeypatch.setattr(prebuild, "_fg_prebuild_live_worker_commit_gb", lambda: 0.0)
    monkeypatch.setattr(prebuild, "_start_fg_prebuild_ram_guard", lambda: SimpleNamespace(stop=lambda: None))
    monkeypatch.setattr(
        prebuild, "_dedupe_paths_by_response_bundle_key", lambda _paths, _refs, _mode: (list(items), {})
    )
    submitted_widths: list[int] = []

    class _FakeFuture:
        def __init__(self, path: str):
            self._result = FrontierCacheBuildResult(path=path, source="built", build_ms=1.0, cache_file=f"{path}.npz")

        def result(self):
            return self._result

    class _FakeExecutor:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def submit(self, _fn, path, reducer_threads, _timing_mode):
            submitted_widths.append(int(reducer_threads))
            return _FakeFuture(str(path))

    monkeypatch.setattr(prebuild, "BoundedRecyclingProcessPool", _FakeExecutor)
    monkeypatch.setattr(
        prebuild.concurrent.futures,
        "wait",
        lambda futures, **_kwargs: ({next(iter(futures))}, set()),
    )

    tally = prebuild._build_fg_songs([path for path, _notes in items], {}, "perfect_window")

    assert [result.path for result in tally.results] == ["first.txt", "last.txt"]
    assert submitted_widths == [11, 11]


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
    paths = list(Path("gear_optimizer").rglob("*.py")) + [Path("config.ini")]
    offenders: list[tuple[str, str]] = []
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            if token in text:
                offenders.append((str(path), token))

    assert offenders == []


def _chart_text(name: str, timestamps: list[float]) -> str:
    notes = "".join(f"{time} {index} {index % 4} 1\n" for index, time in enumerate(timestamps, 1))
    return (
        f"Song Name\t{name}\nDifficulty\tHard\nPrimary Color\tRush\nSecondary Color\tFlow\n"
        f"Last Note Time\t{timestamps[-1]}\nLong Notes\t0\nSong Data\n{notes}"
    )


def test_fg_response_prebuild_skips_valid_cache_hit(monkeypatch, tmp_path: Path) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import ensure_response_frontier_cache_for_song
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import FgResponseFrontierCacheInfo

    song_path = tmp_path / "Song.txt"
    song_path.write_text(_chart_text("Cached Song", [1.0, 2.0]), encoding="utf-8")
    cache_path = tmp_path / "cache.npz"
    cache_path.write_text("cache", encoding="utf-8")

    def _cache_info(_song, _curves, *, stat_keys):
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

    result = build_frontier_cache_for_chart(
        str(song_path),
        synthetic_curves({"Fever Time": [0.0] * 161, "Fever Fill Rate": [0.0] * 161}),
        "perfect_window",
        ensure_response_frontier_cache_for_song,
    )

    assert result.source == "disk"
    assert result.build_ms == 0.0
    assert result.cache_file == str(cache_path)


def test_fg_response_prebuild_builds_cache_miss(monkeypatch, tmp_path: Path) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import ensure_response_frontier_cache_for_song
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import FgResponseFrontierCacheInfo

    song_path = tmp_path / "Song.txt"
    song_path.write_text(_chart_text("Missing Song", [1.0, 2.0, 3.0]), encoding="utf-8")
    cache_path = tmp_path / "cache.npz"
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

    result = build_frontier_cache_for_chart(
        str(song_path),
        synthetic_curves({"Fever Time": [0.0] * 161, "Fever Fill Rate": [0.0] * 161}),
        "perfect_window",
        ensure_response_frontier_cache_for_song,
    )

    assert result.source == "built"
    assert result.build_ms == 12.5


def test_ram_guard_force_resumes_stalled_worker_below_resume_floor(monkeypatch):
    """Deadlock breaker: on a RAM-starved host where free RAM never reaches the resume
    floor, a suspended worker must still be force-resumed so the build cannot hang forever
    holding the single-builder lock (the 2026-07-11 optimizer lock-up)."""
    import time

    from gear_optimizer.solver import fg_response_frontier_cache_prebuild as pb

    monkeypatch.setattr(pb, "_FG_PREBUILD_GUARD_POLL_SECONDS", 0.005)
    monkeypatch.setattr(pb, "_FG_PREBUILD_RESUME_STALL_POLLS", 2)
    # Free RAM permanently below both the suspend (5) and resume (12) floors.
    monkeypatch.setattr(pb, "_fg_prebuild_available_ram_gb", lambda: 0.3)

    class _FakeProc:
        def __init__(self, pid, t):
            self.pid = pid
            self._t = t
            self.suspend_calls = 0
            self.resume_calls = 0

        def suspend(self):
            self.suspend_calls += 1

        def resume(self):
            self.resume_calls += 1

        def is_running(self):
            return True

        def create_time(self):
            return self._t

    younger = _FakeProc(102, 2.0)
    older = _FakeProc(101, 1.0)
    monkeypatch.setattr(pb, "_fg_prebuild_pool_worker_processes", lambda: [older, younger])

    guard = pb._FgPrebuildRamGuard()
    # Simulate the deadlock precondition: a worker was already suspended and, with free RAM
    # stuck below the resume floor, the old code would never resume it.
    guard._suspended = [younger]
    guard.start()
    try:
        deadline = time.time() + 2.0
        while time.time() < deadline and younger.resume_calls == 0:
            time.sleep(0.02)
    finally:
        guard.stop()

    assert younger.resume_calls >= 1, "stalled worker was never force-resumed -> deadlock"
