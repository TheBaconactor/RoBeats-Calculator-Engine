"""The startup prebuild driver both frontier caches share (frontier_cache.prebuild_frontier_cache).

CPU-only: a unit FrontierCache over tmp_path whose "complete" files hold b"complete", and recording build steps.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import numpy as np

from gear_optimizer.frontier import cache as frontier_cache
from gear_optimizer.frontier.cache import (
    FrontierCache,
    FrontierCacheBuildResult,
    FrontierCachePrebuild,
    PrebuildTally,
    build_frontier_cache_for_chart,
    prebuild_frontier_cache,
)
from tests.curves_support import synthetic_curves

CURVES = synthetic_curves({"Fever Time": np.ones(161, np.float32) * 0.15, "Fever Fill Rate": np.ones(161, np.float32) * 0.333})


class _Run:
    """A unit cache and a prebuild whose steps record what ran, in order. A chart named "Broken" fails to build."""

    def __init__(self, tmp_path: Path, monkeypatch) -> None:
        directory = tmp_path / "cache"
        self.calls: list[str] = []
        self.cache = FrontierCache(
            name="unit",
            log_label="[UnitCache]",
            directory=lambda: directory,
            version=lambda: "v1",
            predecessors={},
            is_complete=lambda path: Path(path).read_bytes() == b"complete",
            song_key=lambda song, _curves: ("v1", song.chart.name, song.mode),
            manifest_name="manifest_v1.json",
            manifest_version_field="frontier_version",
        )
        self.prebuild = FrontierCachePrebuild(
            cache=self.cache,
            ensure=self._ensure,
            build_in_pool=self._build_in_pool,
            maintain=lambda _plan, rotate: self.calls.append(f"maintain:{rotate}"),
        )

        @contextmanager
        def lock(*_args, **_kwargs):
            self.calls.append("lock")
            yield

        monkeypatch.setattr(frontier_cache, "exclusive_file_lock", lock)

    def _ensure(self, song, curves) -> tuple[str, float, Path]:
        if song.chart.name == "Broken":
            raise ValueError("this chart does not build")
        path = self.cache.file_path(self.cache.song_key(song, curves))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"complete")
        return "built", 1.0, path

    def _build_in_pool(self, chart_paths: list[str], curves, timing_mode: str, tally: PrebuildTally) -> None:
        self.calls.append(f"pool:{len(chart_paths)}")
        for chart_path in chart_paths:
            tally.collect(chart_path, lambda: build_frontier_cache_for_chart(chart_path, curves, timing_mode, self._ensure))

    def write(self, chart: str, timing_mode: str = "non-precise", content: bytes = b"complete") -> Path:
        path = self.cache.chart_file(str(chart), CURVES, timing_mode)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def run(self, charts: list[Path], *, timing_modes=("non-precise",), **kwargs):
        return prebuild_frontier_cache(
            self.prebuild, charts_by_mode={mode: [str(chart) for chart in charts] for mode in timing_modes},
            curves=CURVES, **kwargs
        )


def _chart(path: Path, name: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"Song Name\t{name}\nDifficulty\tEasy\nPrimary Color\tRush\nSecondary Color\tFlow\nLast Note Time\t0.4\n"
        "Long Notes\t0\nSong Data\n0.000 0 0 1\n0.400 1 1 1\n",
        encoding="utf-8",
    )
    return path


def test_recorded_hits_return_without_the_build_lock(tmp_path: Path, monkeypatch) -> None:
    run = _Run(tmp_path, monkeypatch)
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    run.write(chart)
    run.cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")

    summary = run.run([chart])

    assert run.calls == []
    assert (summary.total, summary.built) == (1, 0)


def test_unrecorded_complete_files_are_recorded_under_the_lock_without_a_build(tmp_path: Path, monkeypatch) -> None:
    run = _Run(tmp_path, monkeypatch)
    recorded = _chart(tmp_path / "charts" / "A.txt", "A")
    unrecorded = _chart(tmp_path / "charts" / "B.txt", "B")
    run.write(recorded)
    run.cache.manifest_plan([str(recorded)], CURVES, timing_mode="non-precise")
    run.write(unrecorded)

    summary = run.run([recorded, unrecorded])

    assert run.calls == ["lock", "maintain:False"]
    assert (summary.total, summary.built) == (2, 0)
    assert run.cache.manifest_plan([str(unrecorded)], CURVES, timing_mode="non-precise").newly_recorded == 0


def test_without_a_current_manifest_the_locked_plan_records_the_hits(tmp_path: Path, monkeypatch) -> None:
    run = _Run(tmp_path, monkeypatch)
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    run.write(chart)

    summary = run.run([chart])

    assert run.calls == ["lock", "maintain:False"]
    assert summary.total == 1
    assert run.cache.manifest_entries()


def test_one_missing_chart_is_built_in_this_process_and_recorded(tmp_path: Path, monkeypatch) -> None:
    """One missing chart (an upload's start) never goes to the worker pool."""
    run = _Run(tmp_path, monkeypatch)
    hit = _chart(tmp_path / "charts" / "A.txt", "A")
    missing = _chart(tmp_path / "charts" / "B.txt", "B")
    run.write(hit)

    summary = run.run([hit, missing])

    assert run.calls == ["lock", "maintain:False"]  # no pool
    assert (summary.total, summary.built, summary.failures) == (2, 1, 0)
    assert (
        run.cache.manifest_plan([str(missing)], CURVES, timing_mode="non-precise").newly_recorded == 0
    )  # recorded by the build


def test_an_authorized_rotation_goes_through_the_lock_and_maintenance(tmp_path: Path, monkeypatch) -> None:
    run = _Run(tmp_path, monkeypatch)
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    run.write(chart)
    run.cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")

    summary = run.run([chart], authorize_destructive_rotation=True)

    assert run.calls == ["lock", "maintain:True"]
    assert summary.total == 1


def test_every_timing_mode_is_verified_and_summed(tmp_path: Path, monkeypatch) -> None:
    run = _Run(tmp_path, monkeypatch)
    charts = [_chart(tmp_path / "charts" / f"{name}.txt", name) for name in ("A", "B")]

    summary = run.run(charts, timing_modes=("precise", "non-precise"))

    assert run.calls.count("pool:2") == 2
    assert (summary.total, summary.built) == (4, 4)


def test_each_mode_verifies_its_own_charts_once(tmp_path: Path, monkeypatch) -> None:
    run = _Run(tmp_path, monkeypatch)
    a, b = (_chart(tmp_path / "charts" / f"{name}.txt", name) for name in ("A", "B"))

    summary = prebuild_frontier_cache(
        run.prebuild, charts_by_mode={"precise": [str(a), str(a).upper(), str(b)], "non-precise": [str(b)]},
        curves=CURVES,
    )

    assert [call for call in run.calls if call.startswith("pool")] == ["pool:2"]  # non-precise builds its one chart here
    assert (summary.total, summary.built) == (3, 3)


def test_a_failed_build_is_counted_and_not_recorded(tmp_path: Path, monkeypatch) -> None:
    run = _Run(tmp_path, monkeypatch)
    charts = [_chart(tmp_path / "charts" / f"{name}.txt", name) for name in ("A", "Broken", "C")]

    summary = run.run(charts)

    assert (summary.total, summary.built, summary.failures) == (3, 2, 1)
    plan = run.cache.manifest_plan([str(chart) for chart in charts], CURVES, timing_mode="non-precise")
    assert plan.missing_paths == (str(charts[1]),) and plan.newly_recorded == 0


def test_a_build_also_serves_the_charts_it_stands_for(tmp_path: Path, monkeypatch) -> None:
    """Charts whose songs one file serves are built once: the others are results of that build, or fail with it."""
    run = _Run(tmp_path, monkeypatch)
    a, twin, broken, broken_twin = (
        _chart(tmp_path / "charts" / f"{name}.txt", name) for name in ("A", "A twin", "Broken", "Broken twin")
    )
    tally = PrebuildTally(run.cache, 4)

    tally.collect(str(a), lambda: build_frontier_cache_for_chart(str(a), CURVES, "non-precise", run._ensure), (str(twin),))
    tally.collect(
        str(broken), lambda: build_frontier_cache_for_chart(str(broken), CURVES, "non-precise", run._ensure),
        (str(broken_twin),),
    )

    assert [(result.path, result.source) for result in tally.results] == [(str(a), "built"), (str(twin), "disk")]
    assert tally.results[0].cache_file == tally.results[1].cache_file
    assert tally.failures == 2
