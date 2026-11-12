from __future__ import annotations

import io
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from gear_optimizer.frontier.cache import FrontierCacheBuildResult, PrebuildTally, build_frontier_cache_for_chart
from tests.curves_support import synthetic_curves

CURVES = synthetic_curves({"Fever Time": [0.0] * 161, "Fever Fill Rate": [0.0] * 161})


def _fake_prebuilds(monkeypatch, *, timeline, fg) -> None:
    """startup_prebuild's two prebuilds, faked per cache."""
    from gear_optimizer.frontier import startup_prebuild

    monkeypatch.setattr(
        startup_prebuild,
        "prebuild_frontier_cache",
        lambda prebuild, **kwargs: {"timeline": timeline, "fg_response": fg}[prebuild.cache.name](**kwargs),
    )


def test_cpu_work_manager_runs_timeline_and_fg_cache_phases(monkeypatch) -> None:
    from gear_optimizer.frontier import startup_prebuild
    from gear_optimizer.frontier.cache import FrontierCachePrebuildSummary

    calls: list[str] = []

    def _timeline(**_kwargs):
        calls.append("timeline_start")
        time.sleep(0.02)
        calls.append("timeline_end")
        return FrontierCachePrebuildSummary(total=1)

    def _fg(**_kwargs):
        calls.append("fg_start")
        calls.append("fg_end")
        return FrontierCachePrebuildSummary(total=1, built=1)

    _fake_prebuilds(monkeypatch, timeline=_timeline, fg=_fg)

    startup_prebuild.run_startup_cpu_work(charts_by_mode={"precise": ["Data/Easy/Fake.txt"]}, curves={})

    assert calls == ["timeline_start", "timeline_end", "fg_start", "fg_end"]


def test_cpu_work_manager_reports_each_cache_and_fails_loud(monkeypatch) -> None:
    from gear_optimizer.frontier import startup_prebuild
    from gear_optimizer.frontier.cache import FrontierCachePrebuildSummary

    _fake_prebuilds(
        monkeypatch,
        timeline=lambda **_kwargs: FrontierCachePrebuildSummary(total=2, built=1),
        fg=lambda **_kwargs: FrontierCachePrebuildSummary(total=2, failures=1),
    )

    stream = io.StringIO()
    with pytest.raises(RuntimeError, match="FG response-frontier cache': 1"):
        startup_prebuild.run_startup_cpu_work(
            charts_by_mode={"precise": ["a.txt"], "non-precise": ["A.TXT"]}, curves={}, announce_stream=stream
        )

    output = stream.getvalue()
    assert "caches for 1 queued song(s)" in output
    assert "Timeline frontier cache ready: total=2 built=1" in output
    assert "FG response-frontier cache ready: total=2 built=0 failures=1" in output


class _InstantPool:
    """Stands for the worker pool: a submitted build is done at once. A chart named broken.txt breaks its worker."""

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.submitted: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def submit(self, _task, chart_path, *args):
        import concurrent.futures
        from concurrent.futures.process import BrokenProcessPool

        self.submitted.append((Path(chart_path).name, *args))
        future = concurrent.futures.Future()
        if Path(chart_path).name == "broken.txt":
            future.set_exception(BrokenProcessPool("native worker exited"))
        else:
            future.set_result(
                FrontierCacheBuildResult(path=chart_path, source="built", build_ms=1.0, cache_file=f"{chart_path}.npz")
            )
        return future


def _pool(monkeypatch, prebuild_module) -> _InstantPool:
    pools: list[_InstantPool] = []
    monkeypatch.setattr(
        prebuild_module, "BoundedRecyclingProcessPool", lambda **kwargs: pools.append(_InstantPool(**kwargs)) or pools[0]
    )
    return SimpleNamespace(of=lambda: pools[0])


def _timeline_pool_build(monkeypatch, chart_paths: list[str]) -> tuple[PrebuildTally, _InstantPool]:
    from gear_optimizer.frontier import timeline_prebuild as prebuild

    pool = _pool(monkeypatch, prebuild)
    monkeypatch.setattr(prebuild, "timeline_prebuild_worker_count", lambda: 2)
    monkeypatch.setattr(prebuild, "frontier_prebuild_intra_worker_threads", lambda _workers: 1)
    tally = PrebuildTally(prebuild.TIMELINE_FRONTIER_CACHE, len(chart_paths))
    prebuild.TIMELINE_FRONTIER_PREBUILD.build_in_pool(chart_paths, CURVES, "precise", tally)
    return tally, pool.of()


def test_timeline_pool_build_recycles_worker_allocator_high_water(monkeypatch) -> None:
    """Persistent workers exhausted commit after ~2,216 builds: the pool replaces its workers every 64 tasks each."""
    tally, pool = _timeline_pool_build(monkeypatch, ["a.txt", "b.txt"])

    assert len(tally.results) == 2
    assert pool.kwargs["max_tasks_per_worker"] == 64


def test_timeline_pool_build_counts_a_broken_worker_per_chart(monkeypatch) -> None:
    tally, _pool_used = _timeline_pool_build(monkeypatch, ["broken.txt", "ready.txt"])

    assert tally.total == 2
    assert tally.failures == 1
    assert [result.path for result in tally.results] == ["ready.txt"]


def _fg_pool_build(monkeypatch, tmp_path: Path, note_counts: dict[str, int], *, available_gb: float, workers: int):
    """The FG pool build of charts with the given note counts (every chart its own notes), on a faked machine: free RAM,
    worker count, 31 frontier CPUs, no live workers. Returns (tally, the pool, the in-flight (chart, weight GB) sets
    seen at each wait)."""
    from gear_optimizer.frontier import fg_prebuild as prebuild

    paths = []
    for index, (name, notes) in enumerate(note_counts.items()):
        path = tmp_path / name
        path.write_text(_chart_text(name, [round(0.05 * note + 0.001 * index, 3) for note in range(notes)]), encoding="utf-8")
        paths.append(str(path))
    pool = _pool(monkeypatch, prebuild)
    monkeypatch.setattr(prebuild.psutil, "virtual_memory", lambda: SimpleNamespace(available=available_gb * 1e9))
    monkeypatch.setattr(prebuild.psutil, "Process", lambda: SimpleNamespace(children=lambda recursive: []))
    monkeypatch.setattr(prebuild, "frontier_prebuild_worker_count", lambda: workers)
    monkeypatch.setattr(prebuild, "frontier_prebuild_cpu_count", lambda: 31)
    in_flight_seen: list[list[tuple[str, float]]] = []

    def wait_for_one(futures, **_kwargs):
        ordered = list(futures)
        in_flight_seen.append([(Path(futures[f][0]).name, futures[f][1]) for f in ordered])
        return {ordered[0]}, set(ordered[1:])

    monkeypatch.setattr(prebuild.concurrent.futures, "wait", wait_for_one)
    tally = PrebuildTally(prebuild.FG_RESPONSE_FRONTIER_CACHE, len(paths))
    prebuild.FG_RESPONSE_FRONTIER_PREBUILD.build_in_pool(paths, CURVES, "precise", tally)
    return tally, pool.of(), in_flight_seen


def test_fg_prebuild_weighted_admission_bounds_inflight_weight_and_completes_all(monkeypatch, tmp_path: Path) -> None:
    """The admission scheduler must (a) never let the sum of in-flight memory weights exceed the
    RAM budget -- the invariant whose absence crashed the machine on 2026-07-09 -- while (b) still
    completing every song (progress guarantee: one build is always admitted)."""
    # 26 GB available, 6 GB reserved -> budget 20 GB: two 7 GB giants at a time, light charts backfill.
    note_counts = {f"giant{i}.txt": 7000 for i in range(3)} | {f"light{i}.txt": 500 for i in range(4)}

    tally, pool, in_flight_seen = _fg_pool_build(monkeypatch, tmp_path, note_counts, available_gb=26.0, workers=8)

    assert tally.failures == 0
    assert sorted(Path(result.path).name for result in tally.results) == sorted(note_counts)
    assert all(threads >= 1 for _name, threads, _mode in pool.submitted)
    peaks = [sum(weight for _name, weight in in_flight) for in_flight in in_flight_seen]
    assert peaks and max(peaks) <= 20.0 + 1e-9
    assert max(len(in_flight) for in_flight in in_flight_seen) > 1  # and it does run several at once
    assert pool.kwargs["max_tasks_per_worker"] == 16


def test_fg_prebuild_tail_admission_counts_the_song_being_submitted(monkeypatch, tmp_path: Path) -> None:
    """After the first one-worker task drains, the final popped song is still one workload unit: each of the two
    builds owns the idle CPUs, capped at the measured useful width of 11 threads."""
    tally, pool, _seen = _fg_pool_build(
        monkeypatch, tmp_path, {"first.txt": 100, "last.txt": 101}, available_gb=64.0, workers=1
    )

    assert [Path(result.path).name for result in tally.results] == ["last.txt", "first.txt"]  # heaviest first
    assert [threads for _name, threads, _mode in pool.submitted] == [11, 11]


def test_fg_prebuild_admission_weight_is_anchored_to_measured_peaks(monkeypatch, tmp_path: Path) -> None:
    """Weight model invariants: floored baseline for tiny charts, the measured ~7k-note giant maps
    to the peak anchor, extrapolation above the anchor never clamps down (a bigger future chart
    must weigh more -- clamping would re-create the 2026-07-09 over-commit crash)."""
    note_counts = {f"{notes}.txt": notes for notes in (1, 1000, 3500, 7000, 10000, 14000)}

    _tally, _pool_used, in_flight_seen = _fg_pool_build(monkeypatch, tmp_path, note_counts, available_gb=26.0, workers=1)

    weight = {int(Path(name).stem): gb for in_flight in in_flight_seen for name, gb in in_flight}
    assert set(weight) == set(note_counts.values())
    assert 2.0 < weight[1] < 2.001  # the floor
    assert abs(weight[7000] - 7.0) < 1e-9  # the anchor
    assert weight[14000] > 7.0
    assert [weight[notes] for notes in sorted(weight)] == sorted(weight.values())  # monotone in the note count


def test_fg_prebuild_reducer_threads_size_to_memory_weight_class(monkeypatch, tmp_path: Path) -> None:
    """Giants (few admitted concurrently by weight) get the freed cores as reducer threads, capped
    at the measured-safe width; light charts that run wide get one thread. No flat worker cap."""
    # 48 GB available -> 42 GB budget, 31 frontier CPUs, up to 24 workers (the 2026-07-09 box shape).
    note_counts = {"giant.txt": 8400} | {f"light{i:02d}.txt": 1 + i for i in range(24)}

    _tally, pool, _seen = _fg_pool_build(monkeypatch, tmp_path, note_counts, available_gb=48.0, workers=24)

    threads = {name: width for name, width, _mode in pool.submitted}
    assert threads["giant.txt"] == 6  # 8 GB: 42 / 8 -> 5 at a time -> 31 // 5
    assert threads["light23.txt"] == 1  # ~2 GB: 42 / 2 -> 20 at a time -> 31 // 20


def test_fg_prebuild_builds_duplicate_bundle_keys_once(monkeypatch, tmp_path: Path) -> None:
    """Charts with the same notes share one bundle: one is built, the other is a result of that build."""
    from gear_optimizer.frontier import fg_prebuild as prebuild

    for name in ("first.txt", "second.txt", "other.txt"):
        notes = [1.0, 2.0, 3.0] if name == "other.txt" else [1.0, 2.0]
        (tmp_path / name).write_text(_chart_text("Same Song", notes), encoding="utf-8")
    pool = _pool(monkeypatch, prebuild)
    monkeypatch.setattr(prebuild.psutil, "virtual_memory", lambda: SimpleNamespace(available=64e9))
    monkeypatch.setattr(prebuild.psutil, "Process", lambda: SimpleNamespace(children=lambda recursive: []))
    tally = PrebuildTally(prebuild.FG_RESPONSE_FRONTIER_CACHE, 3)

    prebuild.FG_RESPONSE_FRONTIER_PREBUILD.build_in_pool(
        [str(tmp_path / name) for name in ("second.txt", "other.txt", "first.txt")], CURVES, "precise", tally
    )

    assert sorted(name for name, _threads, _mode in pool.of().submitted) == ["first.txt", "other.txt"]
    by_name = {Path(result.path).name: result for result in tally.results}
    assert (by_name["first.txt"].source, by_name["second.txt"].source) == ("built", "disk")
    assert by_name["second.txt"].cache_file == by_name["first.txt"].cache_file


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
    from gear_optimizer.frontier.fg_cache import ensure_response_frontier_cache_for_song

    song_path = tmp_path / "Song.txt"
    song_path.write_text(_chart_text("Cached Song", [1.0, 2.0]), encoding="utf-8")
    def _unexpected_build(*_args, **_kwargs):
        raise AssertionError("valid startup cache hit must not rebuild")

    monkeypatch.setattr("gear_optimizer.frontier.fg_cache._payload_file_is_complete", lambda *_args: True)
    monkeypatch.setattr("gear_optimizer.frontier.fg_cache._build_response_frontier_cache_payload", _unexpected_build)

    result = build_frontier_cache_for_chart(str(song_path), CURVES, "precise", ensure_response_frontier_cache_for_song)

    assert result.source == "disk"
    assert result.build_ms == 0.0


def test_fg_response_prebuild_builds_cache_miss(monkeypatch, tmp_path: Path) -> None:
    from gear_optimizer.frontier.fg_cache import ensure_response_frontier_cache_for_song

    song_path = tmp_path / "Song.txt"
    song_path.write_text(_chart_text("Missing Song", [1.0, 2.0, 3.0]), encoding="utf-8")
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg"))
    monkeypatch.setattr("gear_optimizer.frontier.fg_cache._payload_file_is_complete", lambda *_args: False)
    monkeypatch.setattr("gear_optimizer.frontier.fg_cache._load_payload", lambda _key: None)
    monkeypatch.setattr("gear_optimizer.frontier.fg_cache._build_response_frontier_cache_payload", lambda *_args: object())
    monkeypatch.setattr("gear_optimizer.frontier.fg_cache._save_payload", lambda *_args: None)

    result = build_frontier_cache_for_chart(str(song_path), CURVES, "precise", ensure_response_frontier_cache_for_song)

    assert result.source == "built"
    assert result.build_ms > 0.0


def test_ram_guard_force_resumes_stalled_worker_below_resume_floor(monkeypatch):
    """Deadlock breaker: on a RAM-starved host where free RAM never reaches the resume
    floor, a suspended worker must still be force-resumed so the build cannot hang forever
    holding the single-builder lock (the 2026-07-11 optimizer lock-up)."""
    import time

    from gear_optimizer.frontier import fg_prebuild as pb

    monkeypatch.setattr(pb, "_GUARD_POLL_SECONDS", 0.005)
    monkeypatch.setattr(pb, "_RESUME_STALL_POLLS", 2)
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
