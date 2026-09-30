"""Frontier-cache manifests key entries by chart content and drop entries whose cache file is gone.

A chart published under a new directory (every engine deploy publishes the charts under a new
frontier_server_sources/<revision>) still hits its entry, so a restart re-validates nothing.

CPU-only: exercises the shared manifest helpers directly on tmp_path.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

from gear_optimizer.solver.frontier_cache_manifest import apply_manifest_results, build_manifest_plan

_VERSION_FIELD = "frontier_version"
_CACHE_VERSION = "v1"


def _chart_and_cache(root: Path, name: str) -> tuple[Path, Path]:
    chart = root / "charts" / f"{name}.txt"
    cache = root / "cache" / f"{name}.npz"
    chart.parent.mkdir(exist_ok=True)
    cache.parent.mkdir(exist_ok=True)
    chart.write_text(f"chart {name}", encoding="utf-8")
    cache.write_bytes(name.encode("utf-8") * 64)
    return chart, cache


def _plan(song_paths: list[Path], manifest_path: Path, validator=None):
    return build_manifest_plan(
        [str(path) for path in song_paths],
        manifest_path=manifest_path,
        cache_version=_CACHE_VERSION,
        version_field=_VERSION_FIELD,
        ref_sig_hex="ref",
        cache_file_validator=validator,
        derived_cache_file_fn=lambda song: str(manifest_path.parent / f"{Path(song).stem}.npz"),
    )


def _saved_entries(manifest_path: Path) -> dict[str, dict]:
    return json.loads(manifest_path.read_text(encoding="utf-8"))["entries"]


def test_a_chart_published_under_a_new_directory_still_hits_without_validation(tmp_path: Path) -> None:
    manifest_path = tmp_path / "cache" / "manifest_v1.json"
    song_a, _cache_a = _chart_and_cache(tmp_path, "A")
    validated: list[str] = []

    def validator(cache_file: str) -> bool:
        validated.append(Path(cache_file).name)
        return True

    assert _plan([song_a], manifest_path, validator).hit_paths == (str(song_a),)
    assert validated == ["A.npz"]

    moved = tmp_path / "revision-2" / "A.txt"
    moved.parent.mkdir()
    moved.write_bytes(song_a.read_bytes())
    song_a.unlink()
    validated.clear()
    plan = _plan([moved], manifest_path, validator)
    assert plan.hit_paths == (str(moved),) and plan.missing_paths == ()
    assert validated == []  # same content: the recorded entry, no re-validation


def test_a_changed_chart_misses_and_save_drops_entries_whose_cache_file_is_gone(tmp_path: Path) -> None:
    manifest_path = tmp_path / "cache" / "manifest_v1.json"
    song_a, cache_a = _chart_and_cache(tmp_path, "A")
    song_b, cache_b = _chart_and_cache(tmp_path, "B")
    _plan([song_a, song_b], manifest_path, lambda _cache_file: True)
    assert len(_saved_entries(manifest_path)) == 2

    song_a.write_text("chart A, edited", encoding="utf-8")
    assert _plan([song_a], manifest_path, lambda _cache_file: False).missing_paths == (str(song_a),)

    cache_b.unlink()
    song_c, _cache_c = _chart_and_cache(tmp_path, "C")
    _plan([song_c], manifest_path, lambda _cache_file: True)
    kept = sorted(Path(entry["cache_file"]).name for entry in _saved_entries(manifest_path).values())
    assert kept == ["A.npz", "C.npz"]  # B's cache file is gone

def test_recorded_build_results_carry_their_chart_path(tmp_path: Path) -> None:
    manifest_path = tmp_path / "cache" / "manifest_v1.json"
    song, cache = _chart_and_cache(tmp_path, "Built")
    plan = _plan([song], manifest_path)
    assert plan.missing_paths == (str(song),)

    updated = apply_manifest_results(
        plan=plan,
        manifest_path=manifest_path,
        cache_version=_CACHE_VERSION,
        version_field=_VERSION_FIELD,
        results=[SimpleNamespace(path=str(song), cache_file=str(cache), source="built")],
    )

    assert updated == 1
    assert [entry["song_path"] for entry in _saved_entries(manifest_path).values()] == [os.path.abspath(song)]
    assert _plan([song], manifest_path).hit_paths == (str(song),)


def test_an_entry_without_a_chart_path_hits_and_survives_while_its_cache_file_exists(tmp_path: Path) -> None:
    manifest_path = tmp_path / "cache" / "manifest_v1.json"
    song, cache = _chart_and_cache(tmp_path, "Legacy")
    other, _other_cache = _chart_and_cache(tmp_path, "Other")
    key = _plan([song], manifest_path).key_by_norm_path[os.path.abspath(song).casefold()]
    manifest_path.write_text(
        json.dumps(
            {
                "schema": 2,
                _VERSION_FIELD: _CACHE_VERSION,
                "entries": {
                    key: {
                        "cache_file": str(cache),
                        "cache_mtime_ns": int(cache.stat().st_mtime_ns),
                        "cache_size": int(cache.stat().st_size),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    validated: list[str] = []

    def validator(cache_file: str) -> bool:
        validated.append(Path(cache_file).name)
        return True

    legacy = _plan([song], manifest_path, validator)
    assert legacy.hit_paths == (str(song),)
    assert validated == []
    assert key in _saved_entries(manifest_path)  # a pure hit writes nothing

    _plan([other], manifest_path, validator)

    saved = _saved_entries(manifest_path)
    assert key in saved and len(saved) == 2  # pruning follows the cache files, not the chart paths
