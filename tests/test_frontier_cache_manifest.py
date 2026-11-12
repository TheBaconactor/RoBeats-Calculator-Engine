"""The frontier-cache manifest: which charts a prebuild may skip without reading their cache files.

CPU-only: a unit FrontierCache over tmp_path (its "complete" files hold b"complete"), plus the two real caches'
completeness checks.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from gear_optimizer.frontier.cache import FrontierCache, FrontierCacheBuildResult, content_addressed_path
from tests.curves_support import synthetic_curves

CURVES = synthetic_curves({"Fever Time": np.ones(161, np.float32) * 0.15, "Fever Fill Rate": np.ones(161, np.float32) * 0.333})


def _cache(directory: Path, *, version: str = "v1", predecessors: tuple[str, ...] = (), is_complete=None,
           song_key=None) -> FrontierCache:
    return FrontierCache(
        name="unit",
        log_label="[UnitCache]",
        directory=lambda: directory,
        file_path=lambda key: content_addressed_path(directory, key),
        version=lambda: version,
        predecessors={version: predecessors},
        is_complete=is_complete or (lambda path: Path(path).read_bytes() == b"complete"),
        song_key=song_key or (lambda song, _curves: (version, song.chart.name, song.mode)),
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


def _built_file(cache: FrontierCache, chart: Path, timing_mode: str = "non-precise") -> Path:
    path = cache.chart_file(str(chart), CURVES, timing_mode)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"complete")
    return path


def test_a_complete_derived_file_hits_and_is_recorded(tmp_path: Path) -> None:
    cache = _cache(tmp_path / "cache")
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    cache_file = _built_file(cache, chart)

    plan = cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")

    assert plan.hit_paths == (str(chart),) and plan.missing_paths == ()
    assert plan.newly_recorded == 1
    assert [entry["cache_file"] for entry in _entries(cache).values()] == [str(cache_file)]


def test_a_probe_without_persistence_writes_no_manifest(tmp_path: Path) -> None:
    cache = _cache(tmp_path / "cache")
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    _built_file(cache, chart)

    plan = cache.manifest_plan([str(chart)], CURVES, persist=False, timing_mode="non-precise")

    assert plan.hit_paths == (str(chart),) and plan.newly_recorded == 1
    assert not cache.manifest_path().exists()


def test_manifest_keys_separate_timing_modes(tmp_path: Path) -> None:
    cache = _cache(tmp_path / "cache")
    chart = _chart(tmp_path / "charts" / "A.txt", "A")

    perfect = cache.manifest_plan([str(chart)], CURVES, timing_mode="precise").key_by_path[str(chart)]
    zero = cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise").key_by_path[str(chart)]

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

    assert plan.hit_paths == (str(chart),) and plan.newly_recorded == 0
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
    moved = _cache(directory, song_key=lambda song, _curves: ("v1", song.chart.name, song.mode, "a new key input"))

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
    file_a = _built_file(cache, chart_a)
    file_b = _built_file(cache, chart_b)
    cache.manifest_plan([str(chart_a), str(chart_b)], CURVES, timing_mode="non-precise")
    assert len(_entries(cache)) == 2

    file_b.unlink()
    chart_c = _chart(tmp_path / "charts" / "C.txt", "C")
    file_c = _built_file(cache, chart_c)
    cache.manifest_plan([str(chart_c)], CURVES, timing_mode="non-precise")

    assert sorted(entry["cache_file"] for entry in _entries(cache).values()) == sorted([str(file_a), str(file_c)])


def test_recorded_build_results_hit_on_the_next_plan(tmp_path: Path) -> None:
    cache = _cache(tmp_path / "cache")
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    plan = cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise")
    assert plan.missing_paths == (str(chart),)
    cache_file = _built_file(cache, chart)

    cache.record_manifest(
        plan, [FrontierCacheBuildResult(path=str(chart), source="built", build_ms=1.0, cache_file=str(cache_file))]
    )

    assert [entry["cache_file"] for entry in _entries(cache).values()] == [str(cache_file)]
    assert cache.manifest_plan([str(chart)], CURVES, timing_mode="non-precise").hit_paths == (str(chart),)


def test_a_manifest_of_an_unrelated_version_is_ignored(tmp_path: Path) -> None:
    directory = tmp_path / "cache"
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    one_key = lambda song, _curves: ("any version", song.chart.name)  # noqa: E731 - both versions derive one file
    _built_file(_cache(directory, song_key=one_key), chart)
    _cache(directory, song_key=one_key).manifest_plan([str(chart)], CURVES, timing_mode="non-precise")
    assert _cache(directory, song_key=one_key).manifest_entries()

    rotated = _cache(directory, version="v2", song_key=one_key)

    assert not rotated.manifest_entries()
    plan = rotated.manifest_plan([str(chart)], CURVES, persist=False, timing_mode="non-precise")
    assert plan.newly_recorded == 1  # the complete file is validated again, not trusted from v1's entry


def _opened(log: list[str]):
    """A completeness check that records the files it is asked to open."""
    return lambda path: log.append(path) or Path(path).read_bytes() == b"complete"


def test_a_ratified_predecessors_entries_stand_without_opening_a_file(tmp_path: Path) -> None:
    """A start after a ratified version change: the predecessor verified these very files and they are byte-identical to
    the new version's, so every chart hits in both timing modes without one cache file being opened."""
    directory = tmp_path / "cache"
    charts = [_chart(tmp_path / "charts" / f"{name}.txt", name) for name in ("A", "B")]
    paths = [str(chart) for chart in charts]
    modes = ("precise", "non-precise")
    for mode in modes:
        for chart in charts:
            _built_file(_cache(directory), chart, mode)
        _cache(directory).manifest_plan(paths, CURVES, timing_mode=mode)
    opened: list[str] = []
    successor = _cache(directory, version="v2", predecessors=("v1",), is_complete=_opened(opened))

    plans = [successor.manifest_plan(paths, CURVES, timing_mode=mode) for mode in modes]

    assert [(plan.hit_paths, plan.missing_paths, plan.newly_recorded) for plan in plans] == [(tuple(paths), (), 2)] * 2
    assert opened == []
    manifest = json.loads(successor.manifest_path().read_text(encoding="utf-8"))
    assert manifest["frontier_version"] == "v2" and len(manifest["entries"]) == 4  # the predecessor's are spent
    # The next start is a plain restart: recorded hits, nothing derived again.
    restart = [successor.manifest_plan(paths, CURVES, timing_mode=mode) for mode in modes]
    assert [plan.newly_recorded for plan in restart] == [0, 0] and opened == []


def test_a_predecessors_entry_stands_only_for_the_file_at_the_size_it_recorded(tmp_path: Path) -> None:
    directory = tmp_path / "cache"
    resized, renamed = (_chart(tmp_path / "charts" / f"{name}.txt", name) for name in ("A", "B"))
    resized_file = _built_file(_cache(directory), resized)
    _built_file(_cache(directory), renamed)
    _cache(directory).manifest_plan([str(resized), str(renamed)], CURVES, timing_mode="non-precise")
    resized_file.write_bytes(b"complete, but not the bytes the predecessor verified")
    opened: list[str] = []
    # The successor derives another file for B than the predecessor recorded (its key changed with the version).
    successor = _cache(
        directory, version="v2", predecessors=("v1",), is_complete=_opened(opened),
        song_key=lambda song, _curves: ("v2", song.chart.name, song.mode, *(("moved",) if song.chart.name == "B" else ())),
    )

    plan = successor.manifest_plan([str(resized), str(renamed)], CURVES, timing_mode="non-precise")

    assert opened == [str(resized_file)]  # opened and found incomplete; B's derived file does not exist
    assert plan.hit_paths == () and plan.missing_paths == (str(resized), str(renamed))


def test_manifest_entries_are_not_inherited_through_two_versions(tmp_path: Path) -> None:
    """Compatibility is not transitive: v2 read v1's file and recorded it, but v3 ratified v2 only, so v3 never derives
    v1's file and the chart is a miss (it is built), whatever v2's manifest says."""
    directory = tmp_path / "cache"
    chart = _chart(tmp_path / "charts" / "A.txt", "A")
    file_v1 = _built_file(_cache(directory), chart)
    v2 = _cache(directory, version="v2", predecessors=("v1",))
    assert v2.manifest_plan([str(chart)], CURVES, timing_mode="non-precise").hit_paths == (str(chart),)
    assert [entry["cache_file"] for entry in _entries(v2).values()] == [str(file_v1)]
    opened: list[str] = []

    plan = _cache(directory, version="v3", predecessors=("v2",), is_complete=_opened(opened)).manifest_plan(
        [str(chart)], CURVES, timing_mode="non-precise"
    )

    assert plan.missing_paths == (str(chart),) and opened == []


def test_both_caches_record_an_incomplete_file_as_a_miss(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.frontier.timeline_cache import TIMELINE_FRONTIER_CACHE
    from gear_optimizer.frontier.fg_cache_store import FG_RESPONSE_FRONTIER_CACHE

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
