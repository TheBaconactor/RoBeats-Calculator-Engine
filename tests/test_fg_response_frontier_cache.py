from __future__ import annotations

import concurrent.futures
import os
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


def _calc_song() -> dict:
    return {
        "metadata": {
            "Song Name": "FG Cache Unit",
            "Difficulty": "Easy",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Last Note Time": 0.4,
            "Long Notes": 0,
        },
        "song_data": {
            "timestamps": np.asarray([0.0, 0.2, 0.4], dtype=np.float32),
            "note_types": np.asarray([1, 1, 1], dtype=np.int16),
        },
    }


def _calc_song_named(name: str) -> dict:
    calc_song = _calc_song()
    calc_song["metadata"] = dict(calc_song["metadata"])
    calc_song["metadata"]["Song Name"] = str(name)
    return calc_song


def _ref_arrays() -> dict[str, np.ndarray]:
    return {
        "Fever Time": np.ones((161,), dtype=np.float32),
        "Fever Fill Rate": np.ones((161,), dtype=np.float32),
    }


def _varying_ref_arrays() -> dict[str, np.ndarray]:
    return {
        "Fever Time": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, 161, dtype=np.float32),
    }


def _write_song(path: Path, *, extra_tail: str = "") -> None:
    lines = [
        "Song Name\tFG Cache Unit",
        "Difficulty\tEasy",
        "Primary Color\tRush",
        "Secondary Color\tFlow",
        "Last Note Time\t0.4",
        "Long Notes\t0",
        "Song Data",
        "0.000 0 0 1",
        "0.200 0 0 1",
        "0.400 0 0 1",
    ]
    if extra_tail:
        lines.append(str(extra_tail))
    path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def _remove_npz_array(path: Path, array_name: str) -> None:
    import zipfile

    tmp = path.with_name(f"{path.stem}.rewrite.npz")
    drop_name = f"{array_name}.npy"
    with zipfile.ZipFile(path, mode="r") as source:
        with zipfile.ZipFile(tmp, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as target:
            for member in source.infolist():
                if member.filename == drop_name:
                    continue
                target.writestr(member, source.read(member.filename))
    tmp.replace(path)


def _add_npz_array(path: Path, array_name: str, array: np.ndarray) -> None:
    import io
    import zipfile

    tmp = path.with_name(f"{path.stem}.rewrite.npz")
    buffer = io.BytesIO()
    np.save(buffer, np.asarray(array), allow_pickle=False)
    with zipfile.ZipFile(path, mode="r") as source:
        with zipfile.ZipFile(tmp, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as target:
            for member in source.infolist():
                target.writestr(member, source.read(member.filename))
            target.writestr(f"{array_name}.npy", buffer.getvalue())
    tmp.replace(path)


def test_fg_response_frontier_payload_roundtrips_disk_cache(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        reset_fg_response_frontier_payload_cache,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    reset_fg_response_frontier_payload_cache()

    first = build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=((0, 0),))
    assert first.cache_source == "built"
    assert first.disk_path.exists()
    assert len(first.payload.frontiers) == 1
    assert first.payload.frontier_for_stats(ft_stat=0, ff_stat=0).first_frontier

    reset_fg_response_frontier_payload_cache()
    second = build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=((0, 0),))
    assert second.cache_source == "disk"
    assert len(second.payload.frontiers) == 1
    assert second.payload.frontier_for_stats(ft_stat=0, ff_stat=0).first_frontier == (
        first.payload.frontier_for_stats(ft_stat=0, ff_stat=0).first_frontier
    )


def test_fg_response_frontier_payload_reuses_old_disk_cache_without_ttl(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        reset_fg_response_frontier_payload_cache,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import _surface_sidecar_paths

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ROBEATSMETA_LIVE_CACHE_IDLE_TTL_SECONDS", "1800")
    reset_fg_response_frontier_payload_cache()

    first = build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=((0, 0),))
    assert first.cache_source == "built"
    pool_sidecar, coeff_sidecar = _surface_sidecar_paths(first.disk_path)
    stale_ts = time.time() - 3700.0
    for path in (first.disk_path, pool_sidecar, coeff_sidecar):
        os.utime(path, (stale_ts, stale_ts))

    reset_fg_response_frontier_payload_cache()
    second = build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=((0, 0),))
    assert second.cache_source == "disk"
    assert second.disk_path.exists()
    assert second.disk_path.stat().st_mtime == stale_ts
    assert pool_sidecar.stat().st_mtime == stale_ts
    assert coeff_sidecar.stat().st_mtime == stale_ts


def test_fg_response_frontier_sparse_bundle_is_single_disk_artifact(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"
    assert first.disk_path.exists()
    assert len(list(tmp_path.glob("*.npz"))) == 1
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import _surface_sidecar_paths

    row_sidecar, pattern_sidecar = _surface_sidecar_paths(first.disk_path)
    assert row_sidecar.exists()
    assert pattern_sidecar.exists()
    with np.load(first.disk_path, allow_pickle=False) as data:
        assert data["stat_keys"].dtype == np.dtype("uint8")
        assert data["stat_keys"].flags.f_contiguous
        assert data["frontier_meta"].flags.f_contiguous
        # Surfaces live in the uncompressed sidecars, not the slim .npz.
        assert "first_surface_pool" not in data.files
        assert "first_surface_chunk_offsets" not in data.files
        assert "first_surface_pool_chunk_00000" not in data.files
        assert "first_surface_head_coeffs_chunk_00000" not in data.files
        surface_row_count = int(data["first_surface_row_count"])
        surface_pattern_count = int(data["first_surface_pattern_count"])
        assert surface_row_count > 0
        assert surface_pattern_count > 0
        assert not {
            "state_offsets",
            "state_counts",
            "state_keys",
            "state_surface_offsets",
            "state_surface_counts",
            "state_surface_pool",
        }.intersection(data.files)
    row_refs = np.load(row_sidecar, mmap_mode="r", allow_pickle=False)
    assert row_refs.dtype == np.dtype("uint32")
    assert row_refs.shape == (surface_row_count, 4)
    assert row_refs.flags.c_contiguous
    patterns = np.load(pattern_sidecar, mmap_mode="r", allow_pickle=False)
    assert patterns.dtype == np.dtype("uint32")
    assert patterns.shape == (surface_pattern_count, 10)

    def _raise_build(*_args, **_kwargs):
        raise AssertionError("warm sparse bundle should load without rebuilding frontiers")

    response_cache.reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(response_cache, "build_force_greats_response_first_frontiers_gpu_batch", _raise_build)
    second = response_cache.build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=keys)
    assert second.cache_source == "disk"
    assert set(second.payload.frontier_by_key) == set(keys)


def test_fg_response_frontier_bundle_interns_equal_surface_segments(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_surfaces import SurfaceRowsFirstFrontier
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import (
        _fg_response_disk_cache_path,
        _load_bundle_array_members,
        _load_payload,
        _save_payload,
        _surface_sidecar_paths,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import FgResponseFrontierCachePayload
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseFrontierResult

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    rows = np.asarray(
        [
            [1, 0, 0, 0, 0, 0, 0],
            [3, 0, 1, 0, 5, 2, 1],
        ],
        dtype=np.uint64,
    )
    first = FgResponseFrontierResult(SurfaceRowsFirstFrontier(rows.copy()), {}, 1, 2, 3, 4, 5, 6, 7, 0.0)
    second = FgResponseFrontierResult(SurfaceRowsFirstFrontier(rows.copy()), {}, 8, 9, 10, 11, 12, 13, 14, 0.0)
    payload = FgResponseFrontierCachePayload(
        frontier_by_key={(0, 0): first, (1, 0): second},
        raw_fill_by_ff=np.zeros((TOTAL_ROWS + 1,), dtype=np.float64),
        non_fever_base_by_ff=np.zeros((TOTAL_ROWS + 1,), dtype=np.int32),
        real_time_by_ft=np.zeros((TOTAL_ROWS + 1,), dtype=np.float64),
        total_notes=120,
        long_notes=0,
        use_forced_great_timing=True,
    )
    cache_key = ("unit", "equal-frontier-segments")

    _save_payload(cache_key, payload)

    arrays = _load_bundle_array_members(
        cache_key,
        names=(
            "frontier_ids",
            "frontier_meta",
            "first_offsets",
            "first_counts",
            "first_surface_row_count",
            "first_surface_pattern_count",
        ),
    )
    assert arrays["frontier_ids"].tolist() == [0, 1]
    assert arrays["frontier_meta"].shape[0] == 2
    assert arrays["first_offsets"].tolist() == [0, 0]
    assert arrays["first_counts"].tolist() == [2, 2]
    assert int(arrays["first_surface_row_count"]) == 2

    row_sidecar, pattern_sidecar = _surface_sidecar_paths(_fg_response_disk_cache_path(cache_key))
    row_refs = np.load(row_sidecar, mmap_mode="r", allow_pickle=False)
    patterns = np.load(pattern_sidecar, mmap_mode="r", allow_pickle=False)
    assert row_refs.shape == (2, 4)
    assert row_refs.dtype == np.dtype("uint32")
    assert patterns.shape[1] == 10
    assert patterns.dtype == np.dtype("uint32")

    loaded = _load_payload(cache_key)
    assert loaded is not None
    assert loaded.frontier_by_key[(0, 0)] is not loaded.frontier_by_key[(1, 0)]
    assert loaded.frontier_by_key[(0, 0)].first_frontier == loaded.frontier_by_key[(1, 0)].first_frontier
    assert loaded.frontier_by_key[(1, 0)].non_fever_base == 14


def test_fg_response_frontier_surface_chunk_loader_reads_requested_ranges(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import (
        _save_payload,
        load_first_surface_scoring_rows,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import FgResponseFrontierCachePayload
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseFrontierResult, FgResponseSurface

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    surfaces = (
        FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 10, 0, 0),
        FgResponseSurface(2, 0, 0, 0, 0, 0, 0, 0, 20, 1, 0),
        FgResponseSurface(3, 0, 0, 0, 0, 0, 0, 0, 30, 2, 1),
    )
    frontier = FgResponseFrontierResult(surfaces, {}, 1, 2, 3, 4, 5, 6, 7, 0.0)
    payload = FgResponseFrontierCachePayload(
        frontier_by_key={(0, 0): frontier},
        raw_fill_by_ff=np.zeros((TOTAL_ROWS + 1,), dtype=np.float64),
        non_fever_base_by_ff=np.zeros((TOTAL_ROWS + 1,), dtype=np.int32),
        real_time_by_ft=np.zeros((TOTAL_ROWS + 1,), dtype=np.float64),
        total_notes=3,
        long_notes=0,
        use_forced_great_timing=True,
    )
    cache_key = ("unit", "surface-chunks")

    _save_payload(cache_key, payload)
    rows, coeffs = load_first_surface_scoring_rows(cache_key, ((1, 2),))

    assert rows[:, 0].tolist() == [2, 3]
    assert rows[:, 8:11].tolist() == [[20, 1, 0], [30, 2, 1]]
    assert coeffs.shape == (2, 4)
    assert coeffs.dtype == np.dtype("int32")


@pytest.mark.parametrize("cache_mutation", ("missing_core_array", "missing_surface_sidecar", "extra_stale_array"))
def test_fg_response_frontier_disk_info_rejects_non_exact_bundle(
    tmp_path: Path,
    monkeypatch,
    cache_mutation: str,
) -> None:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import (
        _fg_response_disk_cache_path,
        _payload_disk_info_if_complete,
        _save_payload,
        _surface_sidecar_paths,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import FgResponseFrontierCachePayload
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseFrontierResult, FgResponseSurface

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    surfaces = (
        FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 10, 0, 0),
        FgResponseSurface(2, 0, 0, 0, 0, 0, 0, 0, 20, 1, 0),
        FgResponseSurface(3, 0, 0, 0, 0, 0, 0, 0, 30, 2, 1),
    )
    payload = FgResponseFrontierCachePayload(
        frontier_by_key={(0, 0): FgResponseFrontierResult(surfaces, {}, 1, 2, 3, 4, 5, 6, 7, 0.0)},
        raw_fill_by_ff=np.zeros((TOTAL_ROWS + 1,), dtype=np.float64),
        non_fever_base_by_ff=np.zeros((TOTAL_ROWS + 1,), dtype=np.int32),
        real_time_by_ft=np.zeros((TOTAL_ROWS + 1,), dtype=np.float64),
        total_notes=3,
        long_notes=0,
        use_forced_great_timing=True,
    )
    cache_key = ("unit", "non-exact-bundle", cache_mutation)

    _save_payload(cache_key, payload)
    cache_path = _fg_response_disk_cache_path(cache_key)
    if cache_mutation == "missing_core_array":
        _remove_npz_array(cache_path, "raw_fill_by_ff")
    elif cache_mutation == "missing_surface_sidecar":
        pool_sidecar, _coeff_sidecar = _surface_sidecar_paths(cache_path)
        pool_sidecar.unlink()
    elif cache_mutation == "extra_stale_array":
        _add_npz_array(cache_path, "obsolete_array", np.asarray([1], dtype=np.int32))
    else:
        raise AssertionError(f"Unhandled cache mutation: {cache_mutation}")

    assert _payload_disk_info_if_complete(cache_key, ((0, 0),)) is None


def test_fg_response_frontier_scoring_bundle_does_not_unpack_payload_on_disk_hit(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_calc_song(), _varying_ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"
    response_cache.reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(
        response_cache,
        "_load_payload",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("full payload unpack should not run")),
    )

    bundle = response_cache.load_response_frontier_scoring_bundle(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )

    assert set(bundle.frontier_idx_by_key) == set(keys)
    assert bundle.surface_pattern_ids.shape == (0,)
    assert bundle.surface_pattern_words.shape == (0, 8)
    assert int(bundle.surface_row_count) > 0


def test_fg_response_frontier_scoring_bundle_reuses_persisted_head_coeffs(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner_host

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_calc_song(), _varying_ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import _surface_sidecar_paths

    _row_sidecar, pattern_sidecar = _surface_sidecar_paths(first.disk_path)
    with np.load(first.disk_path, allow_pickle=False) as data:
        assert "first_surface_head_len" in data.files
        assert "first_surface_head_coeffs" not in data.files
        assert "first_surface_head_coeffs_chunk_00000" not in data.files
        assert data["first_surface_head_len"].dtype == np.dtype("uint8")
    # Head coeffs persist losslessly as two packed uint32 columns in each exact pattern row.
    persisted_patterns = np.load(pattern_sidecar, mmap_mode="r", allow_pickle=False)
    assert persisted_patterns.dtype == np.dtype("uint32")
    assert persisted_patterns.shape[1] == 10

    response_cache.reset_fg_response_frontier_payload_cache()

    def _raise_recompute(*_args, **_kwargs):
        raise AssertionError("persisted song-only head coeffs should be reused")

    monkeypatch.setattr(response_inner_host, "_precompute_surface_head_coeffs", _raise_recompute)
    bundle = response_cache.load_response_frontier_scoring_bundle(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )

    assert set(bundle.frontier_idx_by_key) == set(keys)
    frontier_idx = bundle.frontier_idx_by_key[(0, 0)]
    start = int(bundle.frontier_offsets[int(frontier_idx)])
    count = int(bundle.frontier_lengths[int(frontier_idx)])
    _rows, coeffs = response_cache.load_first_surface_scoring_rows(bundle.cache_key, ((start, count),))
    assert coeffs.shape == (count, 4)
    assert coeffs.dtype == np.dtype("int32")


def test_fg_response_frontier_scoring_bundle_disk_hit_skips_redundant_disk_info_probe(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_calc_song(), _varying_ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"
    response_cache.reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(
        response_cache,
        "_payload_disk_info_if_complete",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("disk info probe should be skipped")),
    )

    bundle = response_cache.load_response_frontier_scoring_bundle(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )

    assert set(bundle.frontier_idx_by_key) == set(keys)
    assert bundle.surface_pattern_ids.shape == (0,)
    assert bundle.surface_pattern_words.shape == (0, 8)
    assert int(bundle.surface_row_count) > 0


def test_fg_response_frontier_scoring_bundle_requires_startup_cache(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()

    with pytest.raises(ValueError, match="Startup cache prebuild must build"):
        response_cache.load_response_frontier_scoring_bundle(
            _calc_song(),
            _varying_ref_arrays(),
            stat_keys=((0, 0),),
        )
    assert not list(tmp_path.glob("*.npz"))


def test_fg_response_frontier_scoring_bundle_rejects_partial_runtime_cache(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()

    response_cache.build_or_load_response_frontier_payload(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=((0, 0),),
    )
    response_cache.reset_fg_response_frontier_payload_cache()

    with pytest.raises(ValueError, match="all-FT/FF bundle"):
        response_cache.load_response_frontier_scoring_bundle(
            _calc_song(),
            _varying_ref_arrays(),
            stat_keys=((3, 3),),
        )


def test_fg_response_frontier_payload_load_is_not_a_production_api() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    assert not hasattr(response_cache, "load_response_frontier_payload")


def test_response_frontier_job_prep_has_no_scoring_cache_prebuild_route() -> None:
    from gear_optimizer.helpers.song_helpers import force_greats

    assert not hasattr(force_greats, "prebuild_response_frontier_job_caches")
    assert not hasattr(force_greats, "prebuild_force_greats_response_frontier_candidate_cache")


def test_fg_response_prebuild_dedupes_duplicate_bundle_keys(tmp_path: Path) -> None:
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import _dedupe_paths_by_response_bundle_key

    first_path = tmp_path / "first.txt"
    second_path = tmp_path / "second.txt"
    _write_song(first_path)
    _write_song(second_path)

    representatives, duplicates = _dedupe_paths_by_response_bundle_key(
        (str(first_path), str(second_path)),
        _ref_arrays(),
    )

    # Representatives carry the note count from the same parse pass (admission weight input).
    assert [path for path, _notes in representatives] == [str(first_path)]
    assert all(isinstance(notes, int) and notes > 0 for _path, notes in representatives)
    assert duplicates == {str(first_path): (str(second_path),)}


def test_fg_response_frontier_selected_result_loads_exact_first_frontier_from_bundle(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (1, 0))
    response_cache.build_or_load_response_frontier_payload(_calc_song(), _varying_ref_arrays(), stat_keys=keys)
    response_cache.reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(
        response_cache,
        "_load_payload",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("full payload unpack should not run")),
    )

    scoring_bundle = response_cache.load_response_frontier_scoring_bundle(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )
    result = response_cache.frontier_result_from_scoring_bundle_for_stats(
        _calc_song(),
        _varying_ref_arrays(),
        scoring_bundle,
        ft_stat=1,
        ff_stat=0,
    )

    assert result.first_frontier
    assert repr(result.state_frontiers) == "{}"


def test_fg_response_frontier_bundle_version_change_invalidates_legacy_disk_bundle(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (1, 0))

    monkeypatch.setattr(response_cache, "_FG_RESPONSE_CACHE_VERSION", "fg-response-frontier-legacy-v1")
    legacy = response_cache.build_or_load_response_frontier_payload(_calc_song(), _varying_ref_arrays(), stat_keys=keys)
    assert legacy.cache_source == "built"

    response_cache.reset_fg_response_frontier_payload_cache()
    build_calls: list[int] = []
    real_build = response_cache.build_force_greats_response_first_frontiers_gpu_batch

    def _record_build(*args, **kwargs):
        build_calls.append(len(tuple(kwargs.get("geometries") or ())))
        return real_build(*args, **kwargs)

    monkeypatch.setattr(response_cache, "build_force_greats_response_first_frontiers_gpu_batch", _record_build)
    monkeypatch.setattr(response_cache, "_FG_RESPONSE_CACHE_VERSION", "fg-response-frontier-sparse-bundle-v2-test")
    current = response_cache.build_or_load_response_frontier_payload(_calc_song(), _varying_ref_arrays(), stat_keys=keys)

    assert current.cache_source == "built"
    assert build_calls == [2]
    assert len(list(tmp_path.glob("*.npz"))) == 2


@pytest.mark.parametrize("predecessor_index", (1, 2, 3))
def test_ratified_compatible_version_reuses_complete_bundle_without_build(
    tmp_path: Path,
    monkeypatch,
    predecessor_index: int,
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache, response_cache_store

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (1, 0))
    # Exercise the explicitly ratified V30 lineage independently of the current semantic
    # version. Issue #149 deliberately starts V31 with no compatible predecessor because V30
    # bundles do not contain the exact cross-lane activation schedule witness.
    current_version = "fg-response-frontier-visible-first-v30+logic-6126c01d035d"
    monkeypatch.setattr(response_cache, "_FG_RESPONSE_CACHE_VERSION", current_version)
    compatible_versions = response_cache_store.fg_response_compatible_cache_versions()
    assert compatible_versions[0] == current_version
    assert compatible_versions[1:] == (
        "fg-response-frontier-visible-first-v30+logic-87b79fd8a257",
        "fg-response-frontier-visible-first-v30+logic-584d8e8c6077",
        "fg-response-frontier-visible-first-v30+logic-a6d09c0280bd",
    )
    predecessor = compatible_versions[int(predecessor_index)]

    monkeypatch.setattr(response_cache, "_FG_RESPONSE_CACHE_VERSION", predecessor)
    legacy = response_cache.build_or_load_response_frontier_payload(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )
    assert legacy.cache_source == "built"
    legacy_path = Path(legacy.disk_path)
    assert legacy_path.exists()

    response_cache.reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(response_cache, "_FG_RESPONSE_CACHE_VERSION", current_version)

    def _build_must_not_run(*_args, **_kwargs):
        raise AssertionError("ratified compatible cache hit must not rebuild")

    monkeypatch.setattr(
        response_cache,
        "build_force_greats_response_first_frontiers_gpu_batch",
        _build_must_not_run,
    )
    reused = response_cache.build_or_load_response_frontier_payload(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )
    scoring = response_cache.load_response_frontier_scoring_bundle(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )

    assert reused.cache_source == "disk"
    assert Path(reused.disk_path) == legacy_path
    assert response_cache_store.resolve_fg_response_bundle_path(scoring.cache_key) == legacy_path
    assert response_cache_store.purge_stale_version_cache_files() == 0
    assert legacy_path.exists()


def test_issue149_v31_accepts_only_ratified_predecessors() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache, response_cache_store

    current_version = response_cache._FG_RESPONSE_CACHE_VERSION
    assert current_version == "fg-response-frontier-visible-first-v31+logic-2042ea22ebba"
    assert response_cache_store.fg_response_compatible_cache_versions() == (
        current_version,
        "fg-response-frontier-visible-first-v31+logic-52861c6156f1",
        "fg-response-frontier-visible-first-v31+logic-8953b1ce23bf",
        "fg-response-frontier-visible-first-v31+logic-f6b8a98a3729",
        "fg-response-frontier-visible-first-v31+logic-76140458b749",
        "fg-response-frontier-visible-first-v31+logic-822b279e81da",
        "fg-response-frontier-visible-first-v31+logic-eed4d4700100",
        "fg-response-frontier-visible-first-v31+logic-f67224918652",
        "fg-response-frontier-visible-first-v31+logic-11055cda9f1e",
        "fg-response-frontier-visible-first-v31+logic-60b24504b797",
        "fg-response-frontier-visible-first-v31+logic-9e160ae9539c",
        "fg-response-frontier-visible-first-v31+logic-d1bb9475bd29",
        "fg-response-frontier-visible-first-v31+logic-cbd1843e029f",
        "fg-response-frontier-visible-first-v31+logic-da4da67d45fd",
        "fg-response-frontier-visible-first-v31+logic-76d9f97718b6",
        "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf",
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    )


def test_issue149_reconstruction_predecessor_reuses_bundle_without_build(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache, response_cache_store

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (1, 0))
    current_version = response_cache._FG_RESPONSE_CACHE_VERSION
    predecessor = response_cache_store.fg_response_compatible_cache_versions()[1]

    monkeypatch.setattr(response_cache, "_FG_RESPONSE_CACHE_VERSION", predecessor)
    legacy = response_cache.build_or_load_response_frontier_payload(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )
    legacy_path = Path(legacy.disk_path)

    response_cache.reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(response_cache, "_FG_RESPONSE_CACHE_VERSION", current_version)

    def _build_must_not_run(*_args, **_kwargs):
        raise AssertionError("ratified V31 reconstruction predecessor must not rebuild")

    monkeypatch.setattr(
        response_cache,
        "build_force_greats_response_first_frontiers_gpu_batch",
        _build_must_not_run,
    )
    reused = response_cache.build_or_load_response_frontier_payload(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )
    scoring = response_cache.load_response_frontier_scoring_bundle(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )

    assert reused.cache_source == "disk"
    assert Path(reused.disk_path) == legacy_path
    assert response_cache_store.resolve_fg_response_bundle_path(scoring.cache_key) == legacy_path
    assert response_cache_store.purge_stale_version_cache_files() == 0
    assert legacy_path.exists()


def test_purge_stale_version_cache_files_removes_only_superseded(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store as store
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_patterns import (
        SURFACE_PATTERN_COLUMNS,
        SURFACE_ROW_COLUMNS,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import (
        _FG_RESPONSE_CACHE_VERSION,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))

    def _plant(
        digest: str,
        version: str | None,
        *,
        sidecars: bool = True,
        obsolete_sidecars: bool = False,
    ) -> None:
        members = {"payload": np.arange(3)}
        if version is not None:
            members["version"] = np.array(version)
        np.savez(str(tmp_path / f"{digest}.npz"), **members)
        if sidecars:
            if obsolete_sidecars:
                np.save(str(tmp_path / f"{digest}.surf_pool.npy"), np.zeros((2, 11), np.uint32))
                np.save(str(tmp_path / f"{digest}.surf_coeffs.npy"), np.zeros((2, 4), np.uint16))
            else:
                np.save(
                    str(tmp_path / f"{digest}{store._SURFACE_ROW_SIDECAR_SUFFIX}"),
                    np.zeros((2, SURFACE_ROW_COLUMNS), np.uint32),
                )
                np.save(
                    str(tmp_path / f"{digest}{store._SURFACE_PATTERN_SIDECAR_SUFFIX}"),
                    np.zeros((2, SURFACE_PATTERN_COLUMNS), np.uint32),
                )

    _plant("stale_a", "fg-response-frontier-visible-first-v29", obsolete_sidecars=True)
    _plant("stale_b", "fg-response-frontier-legacy-v2")
    _plant("stale_c", "fg-response-frontier-legacy-v1", sidecars=False)  # sidecars already evicted
    _plant("current", _FG_RESPONSE_CACHE_VERSION)
    compatible_predecessors = store.fg_response_compatible_cache_versions()[1:]
    for index, compatible_predecessor in enumerate(compatible_predecessors):
        _plant(f"compatible_{index}", compatible_predecessor)
    _plant("noversion", None)  # missing version field: must be kept, never guessed stale

    with pytest.raises(RuntimeError, match="destructive cache rotation was not explicitly authorized"):
        store.purge_stale_version_cache_files()
    assert (tmp_path / "stale_a.npz").exists()

    removed = store.purge_stale_version_cache_files(authorize_rotation=True)

    # stale_a + stale_b delete 3 files each; stale_c deletes only its .npz. Its already-absent
    # sidecars are not failures, so the marker is still written below (purge_complete-flag guard).
    assert removed == 7
    # The current entry AND the version-less entry survive (never guess-delete), plus the marker.
    expected_names = {
        "current.npz",
        f"current{store._SURFACE_ROW_SIDECAR_SUFFIX}",
        f"current{store._SURFACE_PATTERN_SIDECAR_SUFFIX}",
        "noversion.npz",
        f"noversion{store._SURFACE_ROW_SIDECAR_SUFFIX}",
        f"noversion{store._SURFACE_PATTERN_SIDECAR_SUFFIX}",
        store._PURGED_VERSION_MARKER,
    }
    for index in range(len(compatible_predecessors)):
        expected_names.update(
            {
                f"compatible_{index}.npz",
                f"compatible_{index}{store._SURFACE_ROW_SIDECAR_SUFFIX}",
                f"compatible_{index}{store._SURFACE_PATTERN_SIDECAR_SUFFIX}",
            }
        )
    assert {p.name for p in tmp_path.iterdir()} == expected_names
    assert (
        (tmp_path / store._PURGED_VERSION_MARKER).read_text(encoding="utf-8").strip()
        == store._purged_version_marker_value()
    )
    # The marker gates the rescan: a second call short-circuits without re-reading bundles.
    assert store.purge_stale_version_cache_files() == 0


@pytest.mark.skipif(sys.platform != "win32", reason="NTFS WOF compression is Windows-only")
def test_compress_cache_dir_sidecars_preserves_memmap_bytes(tmp_path: Path, monkeypatch) -> None:
    import ctypes
    from ctypes import wintypes

    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store as store

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    arr = np.zeros((50000, 4), dtype=np.uint32)
    arr[:, 0] = np.arange(50000) % 33
    arr[:, 1] = 452 + (np.arange(50000) % 600)
    sidecar = tmp_path / f"deadbeefdeadbeef{store._SURFACE_ROW_SIDECAR_SUFFIX}"
    store._save_surface_sidecar_atomic(sidecar, arr)
    logical = sidecar.stat().st_size

    store.compress_cache_dir_sidecars()

    # The whole point: NTFS compression must never alter the bytes the scorer memmaps.
    mm = np.load(sidecar, mmap_mode="r")
    try:
        same = bool(np.array_equal(np.asarray(mm), arr))
    finally:
        mm._mmap.close()  # release the file handle before tmp_path teardown (Windows WinError 32)
        del mm
    assert same, "NTFS compression altered the memmapped bytes"
    # On NTFS the on-disk footprint shrinks; on a non-NTFS volume compact no-ops (size unchanged).
    get_compressed = ctypes.windll.kernel32.GetCompressedFileSizeW
    get_compressed.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    get_compressed.restype = wintypes.DWORD
    high = wintypes.DWORD(0)
    low = get_compressed(str(sidecar), ctypes.byref(high))
    on_disk = (high.value << 32) | low
    assert on_disk <= logical


def test_macos_sidecar_compression_copies_in_bounded_batches_and_preserves_bytes(
    tmp_path: Path, monkeypatch
) -> None:
    import shutil

    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store as store

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(store.sys, "platform", "darwin")
    monkeypatch.setattr(store, "_sidecar_needs_filesystem_compression", lambda _path: True)
    row_sidecar = tmp_path / f"deadbeef{store._SURFACE_ROW_SIDECAR_SUFFIX}"
    pattern_sidecar = tmp_path / f"deadbeef{store._SURFACE_PATTERN_SIDECAR_SUFFIX}"
    rows = np.arange(20000, dtype=np.uint32).reshape(5000, 4)
    patterns = np.arange(1000, dtype=np.uint32).reshape(100, 10)
    store._save_surface_sidecar_atomic(row_sidecar, rows)
    store._save_surface_sidecar_atomic(pattern_sidecar, patterns)
    expected = {path.name: path.read_bytes() for path in (row_sidecar, pattern_sidecar)}
    calls: list[list[str]] = []

    def _fake_ditto(args, **_kwargs):
        command = [str(value) for value in args]
        assert command[:3] == ["/usr/bin/ditto", "--hfsCompression", "--nocache"]
        staging = Path(command[-1])
        for source_text in command[3:-1]:
            source = Path(source_text)
            shutil.copy2(source, staging / source.name)
        calls.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(store.subprocess, "run", _fake_ditto)

    store.compress_cache_dir_sidecars()

    assert len(calls) == 1
    assert row_sidecar.read_bytes() == expected[row_sidecar.name]
    assert pattern_sidecar.read_bytes() == expected[pattern_sidecar.name]
    assert not (tmp_path / store._MACOS_COMPRESSION_STAGING_DIR).exists()


def test_macos_sidecar_compression_failure_keeps_original_bytes(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store as store

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(store.sys, "platform", "darwin")
    monkeypatch.setattr(store, "_sidecar_needs_filesystem_compression", lambda _path: True)
    sidecar = tmp_path / f"deadbeef{store._SURFACE_ROW_SIDECAR_SUFFIX}"
    store._save_surface_sidecar_atomic(sidecar, np.arange(20000, dtype=np.uint32))
    expected = sidecar.read_bytes()
    monkeypatch.setattr(
        store.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1),
    )

    store.compress_cache_dir_sidecars()

    assert sidecar.read_bytes() == expected
    assert not (tmp_path / store._MACOS_COMPRESSION_STAGING_DIR).exists()


@pytest.mark.parametrize("destination_platform", ["darwin", "win32"])
def test_plain_cross_platform_export_is_detected_for_destination_compression(
    tmp_path: Path, monkeypatch, destination_platform: str
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store as store

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(store.sys, "platform", destination_platform)
    sidecar = tmp_path / f"exported{store._SURFACE_ROW_SIDECAR_SUFFIX}"
    store._save_surface_sidecar_atomic(sidecar, np.arange(20000, dtype=np.uint32))
    expected = sidecar.read_bytes()
    monkeypatch.setattr(store, "_file_allocated_bytes", lambda path: int(path.stat().st_size))

    assert store.cache_dir_sidecars_need_compression()
    assert sidecar.read_bytes() == expected


def test_fg_response_frontier_uint8_persistence_bounds_fail_loud() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import _as_uint8_exact

    with pytest.raises(ValueError, match="exceeds persisted uint8 bounds"):
        _as_uint8_exact("unit", np.asarray([0, 256], dtype=np.int32))


def test_fg_response_frontier_disk_bundle_reuses_overlapping_stat_keys(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    calls: list[tuple[tuple[float, int, float], ...]] = []

    def _fake_build(*, geometries, **_kwargs):
        rows = tuple((float(row[0]), int(row[1]), float(row[2])) for row in geometries)
        calls.append(rows)
        return tuple(
            FgResponseFrontierResult(
                first_frontier=(FgResponseSurface(idx, 0, 0, 0, 0, 0, 0, 0, 0, 0),),
                state_frontiers={3: (FgResponseSurface(idx, 0, 0, 0, 0, 0, 0, 0, 0, 0),)},
                states_evaluated=1,
                actions=1,
                transitions_evaluated=1,
                generated_surfaces=1,
                retained_surfaces_total=1,
                max_state_frontier=1,
                non_fever_base=0,
                seconds=0.0,
            )
            for idx, _row in enumerate(rows, start=1)
        )

    monkeypatch.setattr(response_cache, "build_force_greats_response_first_frontiers_gpu_batch", _fake_build)
    ref_arrays = _varying_ref_arrays()

    first = response_cache.build_or_load_response_frontier_payload(
        _calc_song(),
        ref_arrays,
        stat_keys=((0, 0), (1, 0)),
    )
    assert first.cache_source == "built"
    assert [len(call) for call in calls] == [2]

    response_cache.reset_fg_response_frontier_payload_cache()
    second = response_cache.build_or_load_response_frontier_payload(
        _calc_song(),
        ref_arrays,
        stat_keys=((1, 0), (2, 0)),
    )

    assert second.cache_source == "built"
    assert set(second.payload.frontier_by_key) == {(1, 0), (2, 0)}
    assert [len(call) for call in calls] == [2, 1]
    assert len(list(tmp_path.glob("*.npz"))) == 1


def test_fg_response_frontier_bundle_builds_are_single_owner(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    active = 0
    max_active = 0
    lock = threading.Lock()

    def _fake_build(*, geometries, **_kwargs):
        nonlocal active, max_active
        rows = tuple(geometries or ())
        with lock:
            active += 1
            max_active = max(int(max_active), int(active))
        try:
            time.sleep(0.05)
            return tuple(
                FgResponseFrontierResult(
                    first_frontier=(FgResponseSurface(idx, 0, 0, 0, 0, 0, 0, 0, 0, 0),),
                    state_frontiers={},
                    states_evaluated=1,
                    actions=1,
                    transitions_evaluated=1,
                    generated_surfaces=1,
                    retained_surfaces_total=1,
                    max_state_frontier=1,
                    non_fever_base=0,
                    seconds=0.0,
                )
                for idx, _row in enumerate(rows, start=1)
            )
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(response_cache, "build_force_greats_response_first_frontiers_gpu_batch", _fake_build)
    ref_arrays = _varying_ref_arrays()

    def _build(name: str) -> None:
        response_cache.build_or_load_response_frontier_payload(
            _calc_song_named(name),
            ref_arrays,
            stat_keys=((0, 0), (1, 0), (2, 0)),
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(_build, "FG Cache Unit A"), executor.submit(_build, "FG Cache Unit B")]
        for future in futures:
            future.result()

    assert max_active == 1


def test_fg_response_frontier_bundle_build_does_not_populate_geometry_lru(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()

    def _fake_build(*, geometries, **_kwargs):
        return tuple(
            FgResponseFrontierResult(
                first_frontier=(FgResponseSurface(idx, 0, 0, 0, 0, 0, 0, 0, 0, 0),),
                state_frontiers={},
                states_evaluated=1,
                actions=1,
                transitions_evaluated=1,
                generated_surfaces=1,
                retained_surfaces_total=1,
                max_state_frontier=1,
                non_fever_base=0,
                seconds=0.0,
            )
            for idx, _row in enumerate(tuple(geometries), start=1)
        )

    def _forbid_geometry_lru(*_args, **_kwargs):
        raise AssertionError("response bundle build must not populate the obsolete per-stat geometry LRU")

    monkeypatch.setattr(response_cache, "build_force_greats_response_first_frontiers_gpu_batch", _fake_build)
    monkeypatch.setattr(response_cache, "_memory_put", _forbid_geometry_lru)

    result = response_cache.build_or_load_response_frontier_payload(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=((0, 0), (1, 0), (2, 0)),
    )

    assert result.cache_source == "built"
    assert set(result.payload.frontier_by_key) == {(0, 0), (1, 0), (2, 0)}


def test_fg_response_frontier_payload_loads_slim_scoring_frontiers(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    ref_arrays = _varying_ref_arrays()
    keys = ((0, 0), (1, 0))

    full = response_cache.build_or_load_response_frontier_payload(_calc_song(), ref_arrays, stat_keys=keys)
    assert all(frontier.first_frontier for frontier in full.payload.frontiers)
    assert all(not frontier.state_frontiers for frontier in full.payload.frontiers)

    response_cache.reset_fg_response_frontier_payload_cache()
    warm = response_cache.build_or_load_response_frontier_payload(_calc_song(), ref_arrays, stat_keys=keys)
    assert warm.cache_source == "disk"
    assert all(frontier.first_frontier for frontier in warm.payload.frontiers)
    assert all(not frontier.state_frontiers for frontier in warm.payload.frontiers)

    restored = response_cache.build_or_load_response_frontier_payload(_calc_song(), ref_arrays, stat_keys=((1, 0),))
    restored_frontier = restored.payload.frontier_for_stats(ft_stat=1, ff_stat=0)
    assert restored_frontier.first_frontier
    assert not restored_frontier.state_frontiers
    assert restored_frontier.first_frontier == full.payload.frontier_for_stats(ft_stat=1, ff_stat=0).first_frontier


def test_fg_response_frontier_cache_rejects_incomplete_frontiers(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    calls: list[int] = []

    def _fake_build(*, geometries, **_kwargs):
        rows = tuple(geometries)
        calls.append(len(rows))
        out = []
        for idx, _geometry in enumerate(rows, start=1):
            surface = FgResponseSurface(idx, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            out.append(
                FgResponseFrontierResult(
                    first_frontier=(),
                    state_frontiers={},
                    states_evaluated=1,
                    actions=1,
                    transitions_evaluated=1,
                    generated_surfaces=1,
                    retained_surfaces_total=1,
                    max_state_frontier=1,
                    non_fever_base=0,
                    seconds=0.0,
                )
            )
        return tuple(out)

    monkeypatch.setattr(response_cache, "build_force_greats_response_first_frontiers_gpu_batch", _fake_build)
    keys = ((0, 0), (1, 0))
    ref_arrays = _varying_ref_arrays()

    with pytest.raises(ValueError, match="requires first-frontier surfaces"):
        response_cache.build_or_load_response_frontier_payload(_calc_song(), ref_arrays, stat_keys=keys)
    assert calls == [2]


def test_fg_response_frontier_payload_memory_cache_precedes_disk(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"

    def _raise_disk_load(_cache_key):
        raise AssertionError("resident response-frontier payload should not hit disk")

    monkeypatch.setattr(response_cache, "_load_payload", _raise_disk_load)
    info = response_cache.fg_response_frontier_payload_cache_info(_calc_song(), _ref_arrays(), stat_keys=keys)
    assert info.cache_source == "memory"

    second = response_cache.build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=keys)
    assert second.cache_source == "memory"
    assert second.payload is first.payload


def test_fg_response_frontier_cache_info_ignores_obsolete_geometry_lru(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    response_cache.reset_fg_response_frontier_payload_cache()
    surface = FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    complete_frontier = FgResponseFrontierResult(
        first_frontier=(surface,),
        state_frontiers={0: (surface,)},
        states_evaluated=1,
        actions=1,
        transitions_evaluated=1,
        generated_surfaces=1,
        retained_surfaces_total=1,
        max_state_frontier=1,
        non_fever_base=0,
        seconds=0.0,
    )
    keys = ((0, 0), (1, 0))
    first_key = response_cache.fg_response_frontier_geometry_cache_key(
        _calc_song(),
        _ref_arrays(),
        ft_stat=0,
        ff_stat=0,
    )
    response_cache._memory_put(first_key, complete_frontier)

    info = response_cache.fg_response_frontier_payload_cache_info(
        _calc_song(),
        _ref_arrays(),
        stat_keys=keys,
    )

    assert info.cache_source == "missing"
    assert info.frontier_count == 0


def test_fg_response_frontier_prebuild_has_no_public_flags() -> None:
    forbidden = (
        "FGResponseFrontierCachePrebuildScope",
        "FGResponseFrontierCachePrebuildWorkers",
        "FGResponseFrontierCachePrebuildMaxSongs",
        "FGResponseFrontierCachePrebuildExecutor",
        "FGResponseFrontierCachePrebuildStatKeys",
        "FG_RESPONSE_FRONTIER_CACHE_PREBUILD",
        "FG_RESPONSE_FRONTIER_DISK_CACHE",
        "include_state_frontiers",
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


def test_fg_response_frontier_cache_build_has_single_production_owner() -> None:
    allowed = {
        Path("gear_optimizer/solver/taichi_gem/force_greats/response_cache.py"),
        Path("gear_optimizer/solver/fg_response_frontier_cache_prebuild.py"),
    }
    offenders: list[str] = []
    for path in Path("gear_optimizer").rglob("*.py"):
        if path in allowed:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "build_or_load_response_frontier_payload" in text:
            offenders.append(str(path))

    assert offenders == []


def test_fg_prebuild_admission_weight_is_anchored_to_measured_peaks() -> None:
    """Weight model invariants: floored baseline for tiny charts, the measured ~7k-note giant maps
    to the peak anchor, extrapolation above the anchor never clamps down (a bigger future chart
    must weigh more -- clamping would re-create the 2026-07-09 over-commit crash)."""
    from gear_optimizer.solver import fg_response_frontier_cache_prebuild as prebuild

    assert prebuild._fg_prebuild_song_weight_gb(0) == prebuild._FG_PREBUILD_FLOOR_COMMIT_GB
    anchor = prebuild._fg_prebuild_song_weight_gb(int(prebuild._FG_PREBUILD_PEAK_COMMIT_NOTES))
    assert abs(anchor - prebuild._FG_PREBUILD_PEAK_COMMIT_GB) < 1e-9
    assert prebuild._fg_prebuild_song_weight_gb(14000) > prebuild._FG_PREBUILD_PEAK_COMMIT_GB
    # Monotone in note count.
    weights = [prebuild._fg_prebuild_song_weight_gb(n) for n in (0, 1000, 3500, 7000, 10000)]
    assert weights == sorted(weights)


def test_fg_prebuild_reducer_threads_size_to_memory_weight_class(monkeypatch) -> None:
    """Giants (few admitted concurrently by weight) get the freed cores as reducer threads, capped
    at the measured-safe width; light charts that run wide get one thread. No flat worker cap."""
    from gear_optimizer.solver import fg_response_frontier_cache_prebuild as prebuild

    # 42 GB budget, 31 frontier CPUs, up to 24 workers (the 2026-07-09 box shape).
    giant = prebuild._fg_prebuild_reducer_threads(8.0, budget_gb=42.0, max_workers=24, frontier_cpus=31)
    light = prebuild._fg_prebuild_reducer_threads(2.0, budget_gb=42.0, max_workers=24, frontier_cpus=31)
    # 42/8 -> 5 concurrent -> 31//5=6, below the measured-safe saturation cap of 9.
    assert giant == 6
    assert prebuild._FG_PREBUILD_MAX_REDUCER_THREADS == 11
    assert light == 1  # 42/2 -> 21 concurrent -> 31//21=1
    # A one-song queue owns otherwise-idle CPUs, capped at the measured saturation width.
    assert prebuild._fg_prebuild_reducer_threads(
        8.0,
        budget_gb=42.0,
        max_workers=24,
        frontier_cpus=31,
        workload_count=1,
    ) == 11
    with pytest.raises(ValueError, match="workload count must be positive"):
        prebuild._fg_prebuild_reducer_threads(
            8.0,
            budget_gb=42.0,
            max_workers=24,
            frontier_cpus=31,
            workload_count=0,
        )
    # No psutil (budget unknown): fall back to the core-derived worker cap, still capped.
    assert prebuild._fg_prebuild_reducer_threads(8.0, budget_gb=None, max_workers=8, frontier_cpus=31) == 3  # min(cap, 31//8)
    assert prebuild._fg_prebuild_reducer_threads(8.0, budget_gb=None, max_workers=31, frontier_cpus=31) == 1


def test_native_static_fg_prep_attaches_canonical_response_bundle(monkeypatch) -> None:
    from gear_optimizer.solver import native_inflight_pipeline as pipeline
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store

    calc_song = {"song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)}}
    ref_arrays = {"Fever Time": np.asarray([0.0]), "Fever Fill Rate": np.asarray([0.0])}
    canonical_keys = ((0, 0), (1, 1))
    # surface_row_count=0 -> the session-box prune early-returns the bundle unchanged, keeping
    # this a pure wiring test (the prune itself is covered by test_fg_session_box_prune).
    bundle = SimpleNamespace(cache_key=("bundle-key",), surface_row_count=0)
    seen: dict[str, object] = {}
    # The session-box prune replaced the sidecar page-cache warm in the prep path (it reads and
    # materializes the surviving rows itself); the wiring must route the loaded bundle through it.
    real_prune = response_cache.session_prune_scoring_bundle

    def _prune(bundle_arg, ref_arrays_arg):
        seen["session_prune"] = 1
        return real_prune(bundle_arg, ref_arrays_arg)

    monkeypatch.setattr(response_cache, "session_prune_scoring_bundle", _prune)
    monkeypatch.setattr(pipeline, "resolve_active_fg_calc_song", lambda _song: calc_song)
    monkeypatch.setattr(response_cache, "all_response_stat_keys", lambda: canonical_keys)

    def _load_bundle(calc_song_arg, ref_arrays_arg, *, stat_keys):
        seen["calc_song"] = calc_song_arg
        seen["ref_arrays"] = ref_arrays_arg
        seen["stat_keys"] = tuple(stat_keys)
        return bundle

    monkeypatch.setattr(response_cache, "load_response_frontier_scoring_bundle", _load_bundle)

    song = SimpleNamespace(
        gpu_inputs=SimpleNamespace(ref_arrays=ref_arrays),
        runtime=SimpleNamespace(fg=SimpleNamespace()),
    )

    pipeline.prepare_fg_static_sync(song)

    assert song.runtime.fg.fg_response_scoring_bundle is bundle
    assert song.runtime.fg.fg_static_prep_done is True
    assert seen == {
        "calc_song": calc_song,
        "ref_arrays": ref_arrays,
        "stat_keys": canonical_keys,
        "session_prune": 1,
    }


def test_packed_scoring_does_not_require_state_frontiers(monkeypatch) -> None:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    frontier_idx_by_stat = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    frontier_idx_by_stat[0, 0] = 0
    bundle = SimpleNamespace(
        frontier_idx_by_stat=frontier_idx_by_stat,
        frontier_offsets=np.asarray([0], dtype=np.int32),
        frontier_lengths=np.asarray([1], dtype=np.int32),
        surface_pattern_ids=np.zeros((1,), dtype=np.int32),
        surface_pattern_words=np.zeros((1, 8), dtype=np.uint32),
        surface_counts=np.zeros((1, 3), dtype=np.int32),
        surface_pattern_head_coeffs=np.zeros((1, 4), dtype=np.int32),
        raw_fill_by_ff=np.zeros((TOTAL_ROWS + 1,), dtype=np.float64),
        real_time_by_ft=np.ones((TOTAL_ROWS + 1,), dtype=np.float64),
    )
    batch = response_frontier.FgResponseFrontierPackedScoringBatch(
        started=0.0,
        stats_inputs=({"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Rush": 0, "Flow": 0},),
        calc_song={"song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)}},
        song_inputs=SimpleNamespace(
            timestamps=np.asarray([0.0], dtype=np.float32),
            perfect_candidates=np.asarray([0.0], dtype=np.float32),
            great_candidates=np.asarray([0.0], dtype=np.float32),
            perfect_floor=np.asarray([0.0], dtype=np.float32),
            great_floor=np.asarray([0.0], dtype=np.float32),
            lanes=np.asarray([0], dtype=np.int32),
            use_forced_great_timing=True,
        ),
        ref_arrays={},
        selected_color="Rush",
        primary_color="Rush",
        secondary_color="Flow",
        scoring_bundle=bundle,
        scoring_bundle_ms=0.0,
        base_components=np.zeros((1, 7), dtype=np.int32),
        ft_values=np.asarray([0], dtype=np.int32),
        ff_values=np.asarray([0], dtype=np.int32),
        residual_values=np.asarray([0], dtype=np.int32),
        frontier_idx_by_stat=frontier_idx_by_stat,
        primary_ftff_delta_values=np.zeros(1, dtype=np.int32),
        secondary_ftff_delta_values=np.zeros(1, dtype=np.int32),
        score_elements_constant=True,
        head_len=1,
        body_total=0,
        kept_stat_keys=((0, 0),),
        group_meta=np.asarray([[0, 0, 0, 0, 0, 0, 1, 0]], dtype=np.int32),
        group_ft=np.asarray([0], dtype=np.int32),
        group_ff=np.asarray([0], dtype=np.int32),
        group_ft_stat=np.asarray([0], dtype=np.int32),
        group_ff_stat=np.asarray([0], dtype=np.int32),
        candidate_slices=((0, 1),),
        scoring_surface_pattern_ids=np.zeros((1,), dtype=np.int32),
        scoring_surface_pattern_words=np.zeros((1, 8), dtype=np.uint32),
        scoring_surface_counts=np.zeros((1, 3), dtype=np.int32),
        scoring_surface_pattern_head_coeffs=np.zeros((1, 4), dtype=np.int32),
        scoring_group_offsets=np.asarray([0], dtype=np.int32),
        scoring_group_lengths=np.asarray([1], dtype=np.int32),
        scoring_unique_frontiers=1,
        scoring_surface_compact_ms=0.0,
        scoring_surface_head_coeff_ms=0.0,
    )

    def _score_must_not_load_bundle(*_args, **_kwargs):
        raise AssertionError("prepared response-frontier scoring must not build or load cache on the GPU owner")

    monkeypatch.setattr(response_frontier, "load_response_frontier_scoring_bundle", _score_must_not_load_bundle)

    def _score_must_receive_prepared_surfaces(**kwargs):
        assert kwargs["group_offsets"].tolist() == [0]
        assert kwargs["group_lengths"].tolist() == [1]
        assert "logical_owners" not in kwargs
        assert "logical_surfaces" not in kwargs
        assert "logical_work_cumsum" not in kwargs
        assert kwargs["surface_pattern_ids"].shape == (1,)
        assert kwargs["surface_pattern_words"].shape == (1, 8)
        assert kwargs["surface_counts"].shape == (1, 3)
        assert kwargs["surface_pattern_head_coeffs"].shape == (1, 4)
        return np.asarray([[123, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], dtype=np.int32), 1

    monkeypatch.setattr(
        response_frontier,
        "_score_response_group_meta_gpu",
        _score_must_receive_prepared_surfaces,
    )
    monkeypatch.setattr(
        response_frontier,
        "frontier_result_from_scoring_bundle_for_stats",
        lambda *_a, **_k: FgResponseFrontierResult((surface,), {}, 1, 1, 0, 1, 1, 1, 0, 0.0),
    )

    result = response_frontier.score_prepared_force_greats_response_frontier_batch_sync(
        batch,
        include_forced_counts=False,
    )

    assert result[0].best_score == 123
    assert result[0].forced_counts == ()

    result_with_counts = response_frontier.score_prepared_force_greats_response_frontier_batch_sync(
        batch,
        include_forced_counts=True,
    )

    assert result_with_counts[0].best_score == 123
    assert result_with_counts[0].forced_counts == ()


def test_packed_scoring_batch_loads_canonical_bundle_during_prepare(monkeypatch) -> None:
    from gear_optimizer.core.constants import GEM_SCALE_FEVER, TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    song_inputs = SimpleNamespace(
        total_notes=1,
        long_notes=0,
        last_note_time=1.0,
        use_forced_great_timing=True,
        primary_color="Rush",
        secondary_color="Flow",
        timestamps=np.asarray([0.0], dtype=np.float32),
        perfect_candidates=np.asarray([0.0], dtype=np.float32),
        great_candidates=np.asarray([0.0], dtype=np.float32),
        perfect_floor=np.asarray([0.0], dtype=np.float32),
        great_floor=np.asarray([0.0], dtype=np.float32),
    )
    seen: dict[str, object] = {}
    canonical_keys = (
        (0, 0),
        (0, GEM_SCALE_FEVER),
        (GEM_SCALE_FEVER, 0),
        (TOTAL_ROWS, TOTAL_ROWS),
    )

    monkeypatch.setattr(response_frontier, "extract_fg_song_inputs", lambda _song: song_inputs)
    monkeypatch.setattr(response_frontier, "all_response_stat_keys", lambda: canonical_keys)

    def _fake_build_bundle(calc_song, ref_arrays, *, stat_keys):
        keys = tuple(stat_keys)
        seen["calc_song"] = calc_song
        seen["ref_arrays"] = ref_arrays
        seen["stat_keys"] = keys
        frontier_idx_by_stat = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
        for ft_stat, ff_stat in keys:
            frontier_idx_by_stat[int(ft_stat), int(ff_stat)] = 0
        surface_words = np.zeros((1, 8), dtype=np.uint32)
        bundle = SimpleNamespace(
            frontier_idx_by_key={key: 0 for key in keys},
            frontier_idx_by_stat=frontier_idx_by_stat,
            frontier_offsets=np.asarray([0], dtype=np.int32),
            frontier_lengths=np.asarray([1], dtype=np.int32),
            surface_pattern_ids=np.zeros((1,), dtype=np.int32),
            surface_pattern_words=surface_words,
            surface_counts=np.zeros((1, 3), dtype=np.int32),
            surface_pattern_head_coeffs=np.zeros((1, 4), dtype=np.int32),
            total_notes=1,
        )
        seen["bundle"] = bundle
        return bundle

    monkeypatch.setattr(response_frontier, "load_response_frontier_scoring_bundle", _fake_build_bundle)

    batch = response_frontier.prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=({"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0},),
        calc_song={"song_data": {}},
        ref_arrays={"ref": object()},
        selected_color="Rush",
        total_budget=1,
    )

    assert batch.scoring_bundle is seen["bundle"]
    assert seen["calc_song"] == {"song_data": {}}
    assert seen["ref_arrays"] == {"ref": batch.ref_arrays["ref"]}
    assert seen["stat_keys"] == canonical_keys
    assert batch.kept_stat_keys == ()
    assert batch.scoring_bundle_ms >= 0.0
    assert batch.group_meta is None
    assert batch.scoring_surface_pattern_ids is None
    assert batch.scoring_surface_pattern_words is None
    assert batch.scoring_surface_counts is None
    assert batch.scoring_surface_pattern_head_coeffs is None
    assert batch.scoring_group_offsets is None
    assert batch.scoring_group_lengths is None


def test_packed_scoring_batch_uses_supplied_prewarmed_bundle(monkeypatch) -> None:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    song_inputs = SimpleNamespace(
        total_notes=1,
        long_notes=0,
        last_note_time=1.0,
        use_forced_great_timing=True,
        primary_color="Rush",
        secondary_color="Flow",
        timestamps=np.asarray([0.0], dtype=np.float32),
        perfect_candidates=np.asarray([0.0], dtype=np.float32),
        great_candidates=np.asarray([0.0], dtype=np.float32),
        perfect_floor=np.asarray([0.0], dtype=np.float32),
        great_floor=np.asarray([0.0], dtype=np.float32),
    )
    frontier_idx_by_stat = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    frontier_idx_by_stat[0, 0] = 0
    prewarmed_bundle = SimpleNamespace(
        frontier_idx_by_key={(0, 0): 0},
        frontier_idx_by_stat=frontier_idx_by_stat,
        frontier_offsets=np.asarray([0], dtype=np.int32),
        frontier_lengths=np.asarray([1], dtype=np.int32),
        surface_pattern_ids=np.zeros((1,), dtype=np.int32),
        surface_pattern_words=np.zeros((1, 8), dtype=np.uint32),
        surface_counts=np.zeros((1, 3), dtype=np.int32),
        surface_pattern_head_coeffs=np.zeros((1, 4), dtype=np.int32),
        total_notes=1,
    )

    monkeypatch.setattr(response_frontier, "extract_fg_song_inputs", lambda _song: song_inputs)
    monkeypatch.setattr(
        response_frontier,
        "load_response_frontier_scoring_bundle",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must use prewarmed bundle")),
    )

    batch = response_frontier.prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=({"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0},),
        calc_song={"song_data": {}},
        ref_arrays={"ref": object()},
        selected_color="Rush",
        total_budget=0,
        scoring_bundle=prewarmed_bundle,
    )

    assert batch.scoring_bundle is prewarmed_bundle
    assert batch.kept_stat_keys == ()
    assert batch.group_meta is None
    assert batch.scoring_surface_pattern_head_coeffs is None


def test_packed_scoring_batch_compacts_selected_frontier_surfaces(monkeypatch) -> None:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    song_inputs = SimpleNamespace(
        total_notes=3,
        long_notes=0,
        last_note_time=1.0,
        use_forced_great_timing=True,
        primary_color="Rush",
        secondary_color="Flow",
        timestamps=np.asarray([0.0, 0.1, 0.2], dtype=np.float32),
        perfect_candidates=np.asarray([0.0, 0.1, 0.2], dtype=np.float32),
        great_candidates=np.asarray([0.0, 0.1, 0.2], dtype=np.float32),
        perfect_floor=np.asarray([0.0, 0.1, 0.2], dtype=np.float32),
        great_floor=np.asarray([0.0, 0.1, 0.2], dtype=np.float32),
    )
    frontier_idx_by_stat = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    frontier_idx_by_stat[0, 0] = 1
    surface_words = np.arange(24, dtype=np.uint32).reshape(3, 8)
    surface_counts = np.arange(9, dtype=np.int32).reshape(3, 3)
    surface_head_coeffs = np.full((3, 4), 3, dtype=np.int32)
    prewarmed_bundle = SimpleNamespace(
        frontier_idx_by_key={(0, 0): 1},
        frontier_idx_by_stat=frontier_idx_by_stat,
        frontier_offsets=np.asarray([0, 2], dtype=np.int32),
        frontier_lengths=np.asarray([2, 1], dtype=np.int32),
        surface_pattern_ids=np.arange(3, dtype=np.int32),
        surface_pattern_words=surface_words,
        surface_counts=surface_counts,
        surface_pattern_head_coeffs=surface_head_coeffs,
        total_notes=3,
    )

    monkeypatch.setattr(response_frontier, "extract_fg_song_inputs", lambda _song: song_inputs)

    from dataclasses import replace

    monkeypatch.setattr(
        response_frontier,
        "build_prepared_force_greats_response_frontier_group_arrays_on_owner",
        lambda batch: replace(
            batch,
            group_meta=np.asarray([[0, 0, 0, 0, 0, 0, 1, 0]], dtype=np.int32),
            group_ft=np.asarray([0], dtype=np.int32),
            group_ff=np.asarray([0], dtype=np.int32),
            group_ft_stat=np.asarray([0], dtype=np.int32),
            group_ff_stat=np.asarray([0], dtype=np.int32),
            candidate_slices=((0, 1),),
            kept_stat_keys=((0, 0),),
            scoring_surface_pattern_ids=np.zeros((1,), dtype=np.int32),
            scoring_surface_pattern_words=surface_words[2:3],
            scoring_surface_counts=surface_counts[2:3],
            scoring_surface_pattern_head_coeffs=surface_head_coeffs[2:3],
            scoring_group_offsets=np.asarray([0], dtype=np.int32),
            scoring_group_lengths=np.asarray([1], dtype=np.int32),
            scoring_unique_frontiers=1,
        ),
    )

    batch = response_frontier.prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=({"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0},),
        calc_song={"song_data": {}},
        ref_arrays={"ref": object()},
        selected_color="Rush",
        total_budget=0,
        scoring_bundle=prewarmed_bundle,
    )
    assert batch.scoring_surface_pattern_ids is None

    built = response_frontier.build_prepared_force_greats_response_frontier_group_arrays_on_owner(batch)

    np.testing.assert_array_equal(built.scoring_surface_pattern_ids, np.zeros((1,), dtype=np.int32))
    np.testing.assert_array_equal(built.scoring_surface_pattern_words, surface_words[2:3])
    np.testing.assert_array_equal(built.scoring_surface_counts, surface_counts[2:3])
    assert built.scoring_group_offsets.tolist() == [0]
    assert built.scoring_group_lengths.tolist() == [1]
    np.testing.assert_array_equal(built.scoring_surface_pattern_head_coeffs, surface_head_coeffs[2:3])
    assert not hasattr(built, "scoring_logical_owners")
    assert not hasattr(built, "scoring_logical_surfaces")
    assert not hasattr(built, "scoring_logical_work_cumsum")


def test_packed_scoring_batch_dedupes_and_coalesces_selected_segments() -> None:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    frontier_idx_by_stat = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    frontier_idx_by_stat[0, 0] = 0
    frontier_idx_by_stat[1, 0] = 1
    frontier_idx_by_stat[2, 0] = 2
    surface_words = np.arange(24, dtype=np.uint32).reshape(3, 8)
    surface_counts = np.arange(9, dtype=np.int32).reshape(3, 3)
    surface_head_coeffs = np.arange(12, dtype=np.int32).reshape(3, 4)
    bundle = SimpleNamespace(
        frontier_idx_by_stat=frontier_idx_by_stat,
        frontier_offsets=np.asarray([0, 0, 2], dtype=np.int32),
        frontier_lengths=np.asarray([2, 2, 1], dtype=np.int32),
        surface_pattern_ids=np.arange(3, dtype=np.int32),
        surface_pattern_words=surface_words,
        surface_counts=surface_counts,
        surface_pattern_head_coeffs=surface_head_coeffs,
        cache_key=("unit", "unused"),
    )

    (
        packed_pattern_ids,
        packed_words,
        packed_counts,
        packed_coeffs,
        group_offsets,
        group_lengths,
        unique_frontiers,
        _compact_ms,
        _head_coeff_ms,
    ) = response_frontier._pack_scoring_surfaces_for_batch(
        scoring_bundle=bundle,
        group_meta=np.asarray([[0, 0, 0, 0, 0, 0, 3, 0]] * 3, dtype=np.int32),
        group_ft_stat=np.asarray([0, 1, 2], dtype=np.int32),
        group_ff_stat=np.asarray([0, 0, 0], dtype=np.int32),
    )

    assert unique_frontiers == 3
    np.testing.assert_array_equal(packed_pattern_ids, np.arange(3, dtype=np.int32))
    np.testing.assert_array_equal(packed_words, surface_words)
    np.testing.assert_array_equal(packed_counts, surface_counts)
    np.testing.assert_array_equal(packed_coeffs, surface_head_coeffs)
    assert group_offsets.tolist() == [0, 0, 2]
    assert group_lengths.tolist() == [2, 2, 1]


def test_release_fg_response_song_memory_evicts_only_target_song():
    """`release_fg_response_song_memory` must drop every memory tier for the target song's
    surfaces (scoring bundle, slim metadata, frontier, payload) while leaving other songs'
    entries resident. This is the per-song release that keeps a standalone optimizer run from
    accumulating one ~0.5-1.5 GB surface pool per scored song until the memory guard restarts it."""
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store as store
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import (
        fg_response_frontier_bundle_cache_key,
        fg_response_frontier_geometry_cache_key,
        fg_response_frontier_payload_cache_key,
    )

    song = _calc_song()
    ref_a = _ref_arrays()
    ref_b = _varying_ref_arrays()  # distinct ref axes -> distinct per-song key prefix

    a_bundle = fg_response_frontier_bundle_cache_key(song, ref_a)
    a_geo = fg_response_frontier_geometry_cache_key(song, ref_a, ft_stat=3, ff_stat=5)
    a_payload = fg_response_frontier_payload_cache_key(song, ref_a, [(3, 5)])
    b_bundle = fg_response_frontier_bundle_cache_key(song, ref_b)
    b_geo = fg_response_frontier_geometry_cache_key(song, ref_b, ft_stat=3, ff_stat=5)

    # Guard: the eviction keys off the shared prefix (bundle key minus its trailing marker),
    # so the two songs must not collide or the test proves nothing.
    assert a_bundle[:-1] != b_bundle[:-1]

    store.reset_fg_response_frontier_payload_cache()
    try:
        # Values are placeholders: release() evicts purely by tuple-prefix, not value type.
        store._scoring_bundle_cache[a_bundle] = object()
        store._scoring_bundle_cache[b_bundle] = object()
        store._bundle_array_cache[a_bundle] = {}
        store._frontier_cache[a_geo] = object()
        store._frontier_cache[b_geo] = object()
        store._payload_cache[a_payload] = object()

        removed = store.release_fg_response_song_memory(a_bundle)

        # Song A: scoring bundle + slim metadata + frontier + payload = 4 entries.
        assert removed == 4
        assert a_bundle not in store._scoring_bundle_cache
        assert a_bundle not in store._bundle_array_cache
        assert a_geo not in store._frontier_cache
        assert a_payload not in store._payload_cache
        # Song B is a different prefix and must survive untouched.
        assert b_bundle in store._scoring_bundle_cache
        assert b_geo in store._frontier_cache
    finally:
        store.reset_fg_response_frontier_payload_cache()
