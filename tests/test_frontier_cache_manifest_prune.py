"""Frontier-cache manifests drop entries whose chart path is gone.

Manifest keys hash the chart's absolute path, so entries for pruned publication snapshots and
finished job workspaces can never be looked up again; every save used to carry them forward.

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


def test_save_drops_entries_whose_chart_is_gone(tmp_path: Path) -> None:
    manifest_path = tmp_path / "cache" / "manifest_v1.json"
    song_a, _cache_a = _chart_and_cache(tmp_path, "A")
    song_b, _cache_b = _chart_and_cache(tmp_path, "B")
    song_c, _cache_c = _chart_and_cache(tmp_path, "C")
    validated: list[str] = []

    def validator(cache_file: str) -> bool:
        validated.append(Path(cache_file).name)
        return True

    first = _plan([song_a, song_b], manifest_path, validator)
    assert first.hit_paths == (str(song_a), str(song_b))
    assert sorted(entry["song_path"] for entry in _saved_entries(manifest_path).values()) == [
        os.path.abspath(song_a),
        os.path.abspath(song_b),
    ]

    song_b.unlink()
    added = _plan([song_c], manifest_path, validator)
    assert added.hit_paths == (str(song_c),)
    assert sorted(entry["song_path"] for entry in _saved_entries(manifest_path).values()) == [
        os.path.abspath(song_a),
        os.path.abspath(song_c),
    ]

    validated.clear()
    again = _plan([song_a, song_c], manifest_path, validator)
    assert again.hit_paths == (str(song_a), str(song_c))
    assert again.missing_paths == ()
    assert validated == []  # surviving entries still take the identity fast path


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


def test_legacy_entry_still_hits_until_the_next_save_drops_it(tmp_path: Path) -> None:
    manifest_path = tmp_path / "cache" / "manifest_v1.json"
    song, cache = _chart_and_cache(tmp_path, "Legacy")
    other, _other_cache = _chart_and_cache(tmp_path, "Other")
    key = _plan([song], manifest_path).key_by_norm_path[os.path.abspath(song).casefold()]
    manifest_path.write_text(
        json.dumps(
            {
                "schema": 1,
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
    assert key not in saved
    assert [entry["song_path"] for entry in saved.values()] == [os.path.abspath(other)]
