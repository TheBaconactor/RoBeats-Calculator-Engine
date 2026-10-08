"""The frontier-cache manifest: which charts a prebuild may skip without reading their cache files.

CPU-only: a unit FrontierCache over tmp_path (its "complete" files hold b"complete"), plus the two real caches'
completeness checks.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from gear_optimizer.solver.frontier_cache import FrontierCache, FrontierCacheBuildResult, content_addressed_path
from tests.curves_support import synthetic_curves

CURVES = synthetic_curves({"Fever Time": np.ones(161, np.float32), "Fever Fill Rate": np.ones(161, np.float32)})


def _cache(directory: Path, *, file_path=None, is_complete=None, version: str = "v1") -> FrontierCache:
    return FrontierCache(
        name="unit",
        log_label="[UnitCache]",
        directory=lambda: directory,
        file_path=file_path or (lambda key: content_addressed_path(directory, key)),
        version=lambda: version,
        predecessors={},
        is_complete=is_complete or (lambda path: Path(path).read_bytes() == b"complete"),
        song_key=lambda song, _curves: ("v1", song.chart.name),
        manifest_name="manifest_v1.json",
        manifest_version_field="frontier_version",
    )


def _chart(path: Path, name: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"Song Name\t{name}\nDifficulty\tEasy\nPrimary Color\tRush\nSecondary Color\tFlow\nLast Note Time\t0.4\n"
        "Long Notes\t0\nSong Data\n0.000 0 0 1\n0.400 1 1 1\n",
        encoding="utf-8",
    )
    return path


def _entries(cache: FrontierCache) -> dict[str, dict]:
    return json.loads(cache.manifest_path().read_text(encoding="utf-8"))["entries"]


def _built_file(cache: FrontierCache, chart: Path) -> Path:
    path = cache.chart_file(str(chart), CURVES, "non-precise")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"complete")
    return path


def test_a_complete_derived_file_hits_and_is_recorded(tmp_path: Path) -> None:
    cache = _cache(tmp_path / "cache")
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    _built_file(cache, chart)

    plan = cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")

    assert plan.hit_paths == (str(chart),) and plan.missing_paths == ()
    assert plan.validated_entry_count == 1
    assert [entry["song_path"] for entry in _entries(cache).values()] == [str(chart)]


def test_a_probe_without_persistence_writes_no_manifest(tmp_path: Path) -> None:
    cache = _cache(tmp_path / "cache")
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    _built_file(cache, chart)

    plan = cache.manifest_plan([str(chart)], CURVES, persist_validated_entries=False, timing_mode="non-precise")

    assert plan.hit_paths == (str(chart),) and plan.validated_entry_count == 1
    assert not cache.manifest_path().exists()


def test_manifest_keys_separate_timing_modes(tmp_path: Path) -> None:
    cache = _cache(tmp_path / "cache")
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    path_key = os.path.abspath(chart).casefold()

    perfect = cache.manifest_plan([str(chart)], CURVES, timing_mode="precise").key_by_norm_path[path_key]
    zero = cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise").key_by_norm_path[path_key]

    assert perfect != zero


def test_a_recorded_hit_survives_an_mtime_touch_without_revalidation(tmp_path: Path) -> None:
    """The fast path compares the file's size, never its mtime: external copies move mtimes without changing bytes
    (an mtime check re-validated every FG bundle on every startup)."""
    validated: list[str] = []
    cache = _cache(tmp_path / "cache", is_complete=lambda path: validated.append(path) or True)
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    cache_file = _built_file(cache, chart)
    cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")
    validated.clear()

    future = cache_file.stat().st_mtime + 10_000.0
    os.utime(cache_file, (future, future))
    plan = cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")

    assert plan.hit_paths == (str(chart),) and plan.validated_entry_count == 0
    assert validated == []


def test_a_recorded_hit_whose_file_changed_size_is_revalidated(tmp_path: Path) -> None:
    validated: list[str] = []
    cache = _cache(tmp_path / "cache", is_complete=lambda path: validated.append(path) or True)
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    cache_file = _built_file(cache, chart)
    cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")
    validated.clear()

    cache_file.write_bytes(b"complete, rebuilt larger")
    plan = cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")

    assert plan.hit_paths == (str(chart),)
    assert validated == [str(cache_file)]


def test_an_incomplete_file_is_a_miss(tmp_path: Path) -> None:
    cache = _cache(tmp_path / "cache")
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    _built_file(cache, chart).write_bytes(b"partial")

    plan = cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")

    assert plan.hit_paths == () and plan.missing_paths == (str(chart),)
    assert not cache.manifest_path().exists()


def test_a_key_derivation_change_without_a_version_change_drops_every_hit(tmp_path: Path) -> None:
    """The 2026-07-02 incident: the derived key moved but the version did not, so the manifest kept reporting stale
    files as ready. A sample of hits is re-derived; a mismatch makes every chart a miss."""
    directory = tmp_path / "cache"
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    recorded = _built_file(_cache(directory), chart)
    _cache(directory).manifest_plan([str(chart)], CURVES, timing_mode="non-precise")
    moved = _cache(directory, file_path=lambda key: directory / "elsewhere.npz")

    plan = moved.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")

    assert recorded.exists()
    assert plan.hit_paths == () and plan.missing_paths == (str(chart),)


def test_a_hit_whose_chart_does_not_parse_is_not_a_drift_signal(tmp_path: Path) -> None:
    """Re-deriving a hit's file parses its chart; a chart that fails to parse is the per-file path's problem."""
    cache = _cache(tmp_path / "cache")
    chart = tmp_path / "charts" / "broken.txt"
    chart.parent.mkdir()
    chart.write_text("not a chart", encoding="utf-8")
    cache_file = tmp_path / "cache" / "built.npz"
    cache_file.parent.mkdir()
    cache_file.write_bytes(b"complete")
    plan = cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")
    assert plan.missing_paths == (str(chart),)
    cache.record_manifest(
        plan, [FrontierCacheBuildResult(path=str(chart), source="built", build_ms=0.0, cache_file=str(cache_file))]
    )

    assert cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise").hit_paths == (str(chart),)


def test_a_chart_published_under_a_new_directory_hits_without_validation(tmp_path: Path) -> None:
    """Entries are keyed by chart content: every deploy publishes the charts under a new directory."""
    validated: list[str] = []
    cache = _cache(tmp_path / "cache", is_complete=lambda path: validated.append(path) or True)
    chart = _chart(tmp_path / "revision-1" / "A.txt", "A")
    _built_file(cache, chart)
    cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")
    validated.clear()
    moved = tmp_path / "revision-2" / "A.txt"
    moved.parent.mkdir()
    moved.write_bytes(chart.read_bytes())
    chart.unlink()

    plan = cache.manifest_plan([str(moved)], CURVES, timing_mode="non-precise")

    assert plan.hit_paths == (str(moved),) and validated == []


def test_entries_whose_file_is_gone_are_dropped_when_the_manifest_is_saved(tmp_path: Path) -> None:
    cache = _cache(tmp_path / "cache")
    chart_a = _chart(tmp_path / "charts" / "A.txt", "A")
    chart_b = _chart(tmp_path / "charts" / "B.txt", "B")
    _built_file(cache, chart_a)
    file_b = _built_file(cache, chart_b)
    cache.manifest_plan([str(chart_a), str(chart_b)], CURVES, timing_mode="non-precise")
    assert len(_entries(cache)) == 2

    file_b.unlink()
    chart_c = _chart(tmp_path / "charts" / "C.txt", "C")
    _built_file(cache, chart_c)
    cache.manifest_plan([str(chart_c)], CURVES, timing_mode="non-precise")

    assert sorted(Path(entry["song_path"]).name for entry in _entries(cache).values()) == ["A.txt", "C.txt"]


def test_recorded_build_results_hit_on_the_next_plan(tmp_path: Path) -> None:
    cache = _cache(tmp_path / "cache")
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    plan = cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")
    assert plan.missing_paths == (str(chart),)
    cache_file = _built_file(cache, chart)

    recorded = cache.record_manifest(
        plan, [FrontierCacheBuildResult(path=str(chart), source="built", build_ms=1.0, cache_file=str(cache_file))]
    )

    assert recorded == 1
    assert [entry["song_path"] for entry in _entries(cache).values()] == [os.path.abspath(chart)]
    assert cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise").hit_paths == (str(chart),)


def test_a_manifest_of_another_version_is_ignored(tmp_path: Path) -> None:
    directory = tmp_path / "cache"
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    _built_file(_cache(directory), chart)
    _cache(directory).manifest_plan([str(chart)], CURVES, timing_mode="non-precise")
    assert _cache(directory).manifest_records_current_version()

    rotated = _cache(directory, version="v2")

    assert not rotated.manifest_records_current_version()
    plan = rotated.manifest_plan([str(chart)], CURVES, persist_validated_entries=False, timing_mode="non-precise")
    assert plan.validated_entry_count == 1  # the complete file is validated again, not trusted from v1's entry


def test_both_caches_record_an_incomplete_file_as_a_miss(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.api.timeline import TIMELINE_FRONTIER_CACHE
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import FG_RESPONSE_FRONTIER_CACHE

    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path / "timeline"))
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg"))
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    broken = tmp_path / "broken.npz"
    broken.write_text("not a complete npz", encoding="utf-8")
    for cache in (TIMELINE_FRONTIER_CACHE, FG_RESPONSE_FRONTIER_CACHE):
        plan = cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")
        cache.record_manifest(
            plan, [FrontierCacheBuildResult(path=str(chart), source="disk", build_ms=0.0, cache_file=str(broken))]
        )

        assert cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise").missing_paths == (str(chart),)
