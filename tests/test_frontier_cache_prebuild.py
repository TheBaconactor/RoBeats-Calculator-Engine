"""The startup prebuild driver both frontier caches share (frontier_cache.prebuild_frontier_cache).

CPU-only: a unit FrontierCache over tmp_path whose "complete" files hold b"complete", and a recording build step.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import numpy as np

from gear_optimizer.solver import frontier_cache
from gear_optimizer.solver.frontier_cache import (
    FrontierCache,
    FrontierCacheBuildResult,
    FrontierCachePrebuild,
    PrebuildTally,
    content_addressed_path,
    prebuild_frontier_cache,
)
from tests.curves_support import synthetic_curves

CURVES = synthetic_curves({"Fever Time": np.ones(161, np.float32), "Fever Fill Rate": np.ones(161, np.float32)})


class _Run:
    """A unit cache and a prebuild whose steps record what ran, in order."""

    def __init__(self, tmp_path: Path, monkeypatch) -> None:
        directory = tmp_path / "cache"
        self.calls: list[str] = []
        self.cache = FrontierCache(
            name="unit",
            log_label="[UnitCache]",
            directory=lambda: directory,
            file_path=lambda key: content_addressed_path(directory, key),
            version=lambda: "v1",
            predecessors={},
            is_complete=lambda path: Path(path).read_bytes() == b"complete",
            song_key=lambda song, _curves: ("v1", song.chart.name, song.mode),
            manifest_name="manifest_v1.json",
            manifest_version_field="frontier_version",
        )
        self.prebuild = FrontierCachePrebuild(
            cache=self.cache,
            build_songs=self._build_songs,
            maintain=lambda _plan, build_missing, rotate: self.calls.append(f"maintain:{build_missing}:{rotate}"),
        )

        @contextmanager
        def lock(*_args, **_kwargs):
            self.calls.append("lock")
            yield

        monkeypatch.setattr(frontier_cache, "FrontierBuildLock", lock)

    def _build_songs(self, song_paths: list[str], curves, timing_mode: str) -> PrebuildTally:
        self.calls.append(f"build:{len(song_paths)}")
        tally = PrebuildTally(self.cache, len(song_paths), progress_every=10)
        for song_path in song_paths:
            tally.add(
                FrontierCacheBuildResult(
                    path=song_path, source="built", build_ms=1.0, cache_file=str(self.write(song_path, timing_mode))
                )
            )
        return tally

    def write(self, chart: str, timing_mode: str = "non-precise", content: bytes = b"complete") -> Path:
        path = self.cache.chart_file(str(chart), CURVES, timing_mode)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def run(self, charts: list[Path], **kwargs):
        kwargs.setdefault("timing_modes", ("non-precise",))
        return prebuild_frontier_cache(
            self.prebuild, song_queue=[(str(chart),) for chart in charts], curves=CURVES, data_root=None, **kwargs
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
    assert (summary.total, summary.completed, summary.disk, summary.built) == (1, 1, 1, 0)


def test_unrecorded_complete_files_are_recorded_under_the_lock_without_a_build(tmp_path: Path, monkeypatch) -> None:
    run = _Run(tmp_path, monkeypatch)
    recorded = _chart(tmp_path / "charts" / "A.txt", "A")
    unrecorded = _chart(tmp_path / "charts" / "B.txt", "B")
    run.write(recorded)
    run.cache.manifest_plan([str(recorded)], CURVES, timing_mode="non-precise")
    run.write(unrecorded)

    summary = run.run([recorded, unrecorded])

    assert run.calls == ["lock", "maintain:True:False"]
    assert (summary.completed, summary.disk, summary.built) == (2, 2, 0)
    assert run.cache.manifest_plan([str(unrecorded)], CURVES, timing_mode="non-precise").validated_entry_count == 0


def test_without_a_current_manifest_the_locked_plan_records_the_hits(tmp_path: Path, monkeypatch) -> None:
    run = _Run(tmp_path, monkeypatch)
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    run.write(chart)

    summary = run.run([chart])

    assert run.calls == ["lock", "maintain:True:False"]
    assert (summary.completed, summary.disk) == (1, 1)
    assert run.cache.manifest_records_current_version()


def test_missing_charts_are_built_and_recorded(tmp_path: Path, monkeypatch) -> None:
    run = _Run(tmp_path, monkeypatch)
    hit = _chart(tmp_path / "charts" / "A.txt", "A")
    missing = _chart(tmp_path / "charts" / "B.txt", "B")
    run.write(hit)

    summary = run.run([hit, missing])

    assert run.calls == ["lock", "maintain:True:False", "build:1"]
    assert (summary.total, summary.completed, summary.disk, summary.built, summary.failures) == (2, 2, 1, 1, 0)
    assert (
        run.cache.manifest_plan([str(missing)], CURVES, timing_mode="non-precise").validated_entry_count == 0
    )  # recorded by the build


def test_without_build_missing_a_missing_chart_is_a_failure(tmp_path: Path, monkeypatch) -> None:
    run = _Run(tmp_path, monkeypatch)
    chart = _chart(tmp_path / "charts" / "A.txt", "A")

    summary = run.run([chart], build_missing=False)

    assert run.calls == ["lock", "maintain:False:False"]
    assert (summary.total, summary.completed, summary.failures) == (1, 0, 1)


def test_an_authorized_rotation_goes_through_the_lock_and_maintenance(tmp_path: Path, monkeypatch) -> None:
    run = _Run(tmp_path, monkeypatch)
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    run.write(chart)
    run.cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")

    summary = run.run([chart], authorize_destructive_rotation=True)

    assert run.calls == ["lock", "maintain:True:True"]
    assert (summary.completed, summary.disk) == (1, 1)


def test_every_timing_mode_is_verified_and_summed(tmp_path: Path, monkeypatch) -> None:
    run = _Run(tmp_path, monkeypatch)
    charts = [_chart(tmp_path / "charts" / f"{name}.txt", name) for name in ("A", "B")]

    summary = run.run(charts, timing_modes=("precise", "non-precise"))

    assert run.calls.count("build:2") == 2
    assert (summary.total, summary.built) == (4, 4)


def test_an_empty_queue_verifies_every_chart_under_the_data_root(tmp_path: Path, monkeypatch) -> None:
    run = _Run(tmp_path, monkeypatch)
    data = tmp_path / "Data"
    _chart(data / "Hard" / "b.txt", "B")
    _chart(data / "Easy" / "a.txt", "A")
    (data / "Other").mkdir()
    _chart(data / "Other" / "ignored.txt", "C")

    summary = prebuild_frontier_cache(
        run.prebuild, song_queue=[], curves=CURVES, data_root=data, timing_modes=("precise",)
    )

    assert summary.built == 2
