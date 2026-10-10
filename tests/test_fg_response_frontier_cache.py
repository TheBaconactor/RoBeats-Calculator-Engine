from __future__ import annotations

from tests.curves_support import synthetic_curves
from tests.songs_support import make_song
from gear_optimizer.gamedata import stat_curves
import concurrent.futures
import multiprocessing
import os
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from gear_optimizer.gamedata import empty_stats
from gear_optimizer.solver.taichi_gem.force_greats import response_cache_types
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import (
    fg_response_frontier_bundle_cache_key,
    fg_response_frontier_geometry_cache_key,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_serde import (
    frontier_result_from_scoring_bundle_for_stats,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import (
    _memory_put,
    gather_surface_patterns,
    read_compatible_bundle,
    reset_fg_response_frontier_payload_cache,
)


def _song(name: str = "FG Cache Unit", timestamps=(0.0, 0.2, 0.4)):
    # non-precise: the chart-only FG inputs (no Perfect-window envelopes, no forced-Great carry).
    return make_song(timestamps, mode="non-precise", name=name, difficulty="Easy", last_note_time=0.4)


def _curves() -> dict[str, np.ndarray]:
    return synthetic_curves({
        "Fever Time": np.ones((161,), dtype=np.float32) * 0.15,
        "Fever Fill Rate": np.ones((161,), dtype=np.float32) * 0.333,
    })


def _varying_ref_arrays() -> dict[str, np.ndarray]:
    return synthetic_curves({
        "Fever Time": np.linspace(1.0, 2.0, 161, dtype=np.float32) * 0.15,
        "Fever Fill Rate": np.linspace(1.0, 2.0, 161, dtype=np.float32) * 0.333,
    })


def _loaded_stat_keys(bundle) -> set[tuple[int, int]]:
    return {(int(ft), int(ff)) for ft, ff in np.argwhere(np.asarray(bundle.frontier_idx_by_stat) >= 0).tolist()}


def _fake_response_frontiers(geometries) -> tuple:
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    rows = tuple(geometries or ())
    return tuple(
        FgResponseFrontierResult(
            first_frontier=(
                FgResponseSurface(
                    (
                        int(round(float(_row[0]) * 1_000_000.0))
                        + int(_row[1]) * 10_000
                        + int(round(float(_row[2]) * 1_000.0))
                        + idx
                    )
                    % (2**31 - 1),
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                ),
            ),
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


def _extend_fg_bundle_worker(cache_dir: str, stat_key: tuple[int, int], start_event, result_queue) -> None:
    try:
        os.environ["FG_RESPONSE_FRONTIER_CACHE_DIR"] = str(cache_dir)
        from gear_optimizer.solver.taichi_gem.force_greats import response_cache

        reset_fg_response_frontier_payload_cache()

        def _delayed_build(*, geometries, **_kwargs):
            time.sleep(0.2)
            return _fake_response_frontiers(geometries)

        response_cache.build_force_greats_response_first_frontiers_gpu_batch = _delayed_build
        if not start_event.wait(timeout=10.0):
            raise TimeoutError("bundle extension start was not released")
        response_cache.build_or_load_response_frontier_payload(
            _song(),
            _varying_ref_arrays(),
            stat_keys=(stat_key,),
        )
        result_queue.put(("ok", stat_key))
    except BaseException as exc:
        result_queue.put(("error", f"{type(exc).__name__}: {exc}"))


def _read_fg_bundle_across_publish_worker(cache_dir: str, ready_event, published_event, result_queue) -> None:
    try:
        os.environ["FG_RESPONSE_FRONTIER_CACHE_DIR"] = str(cache_dir)
        from gear_optimizer.solver.taichi_gem.force_greats import response_cache

        reset_fg_response_frontier_payload_cache()
        scoring = response_cache.load_response_frontier_scoring_bundle(
            _song(),
            _varying_ref_arrays(),
            stat_keys=((0, 0),),
        )
        frontier_idx = int(scoring.frontier_idx_by_stat[0, 0])
        surface_range = (
            int(scoring.frontier_offsets[frontier_idx]),
            int(scoring.frontier_lengths[frontier_idx]),
        )
        ready_event.set()
        if not published_event.wait(timeout=10.0):
            raise TimeoutError("bundle publication did not finish")
        rows, _counts, _words, _coeffs = gather_surface_patterns(
            scoring.surface_rows, scoring.surface_patterns, (surface_range,)
        )
        extended = response_cache.load_response_frontier_scoring_bundle(
            _song(),
            _varying_ref_arrays(),
            stat_keys=((1, 0),),
        )
        if int(extended.frontier_idx_by_stat[1, 0]) < 0:
            raise AssertionError("reader did not observe the completed bundle extension")
        result_queue.put(("reader_ok", int(rows.shape[0])))
    except BaseException as exc:
        result_queue.put(("reader_error", f"{type(exc).__name__}: {exc}"))


def _publish_fg_bundle_worker(cache_dir: str, ready_event, published_event, result_queue) -> None:
    try:
        os.environ["FG_RESPONSE_FRONTIER_CACHE_DIR"] = str(cache_dir)
        from gear_optimizer.solver.taichi_gem.force_greats import response_cache

        reset_fg_response_frontier_payload_cache()
        response_cache.build_force_greats_response_first_frontiers_gpu_batch = (
            lambda *, geometries, **_kwargs: _fake_response_frontiers(geometries)
        )
        if not ready_event.wait(timeout=10.0):
            raise TimeoutError("reader did not load the previous generation")
        response_cache.build_or_load_response_frontier_payload(
            _song(),
            _varying_ref_arrays(),
            stat_keys=((1, 0),),
        )
        result_queue.put(("writer_ok", None))
    except BaseException as exc:
        result_queue.put(("writer_error", f"{type(exc).__name__}: {exc}"))
    finally:
        published_event.set()


class _InjectedPublicationStop(BaseException):
    pass


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
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import build_or_load_response_frontier_payload

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    reset_fg_response_frontier_payload_cache()

    first = build_or_load_response_frontier_payload(_song(), _curves(), stat_keys=((0, 0),))
    assert first.cache_source == "built"
    assert first.disk_path.exists()
    assert len(first.payload.frontiers) == 1
    assert first.payload.frontier_for_stats(ft_stat=0, ff_stat=0).first_frontier

    reset_fg_response_frontier_payload_cache()
    second = build_or_load_response_frontier_payload(_song(), _curves(), stat_keys=((0, 0),))
    assert second.cache_source == "disk"
    assert len(second.payload.frontiers) == 1
    assert second.payload.frontier_for_stats(ft_stat=0, ff_stat=0).first_frontier == (
        first.payload.frontier_for_stats(ft_stat=0, ff_stat=0).first_frontier
    )


def test_fg_response_frontier_payload_reuses_old_disk_cache_without_ttl(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import build_or_load_response_frontier_payload

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ROBEATSMETA_LIVE_CACHE_IDLE_TTL_SECONDS", "1800")
    reset_fg_response_frontier_payload_cache()

    first = build_or_load_response_frontier_payload(_song(), _curves(), stat_keys=((0, 0),))
    assert first.cache_source == "built"
    stale_ts = time.time() - 3700.0
    os.utime(first.disk_path, (stale_ts, stale_ts))

    reset_fg_response_frontier_payload_cache()
    second = build_or_load_response_frontier_payload(_song(), _curves(), stat_keys=((0, 0),))
    assert second.cache_source == "disk"
    assert second.disk_path.exists()
    assert second.disk_path.stat().st_mtime == stale_ts


def test_fg_response_frontier_sparse_bundle_is_single_disk_artifact(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import _BUNDLE_ARRAY_NAMES

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_song(), _curves(), stat_keys=keys)
    assert first.cache_source == "built"
    assert [path.name for path in tmp_path.iterdir() if path.is_file()] == [first.disk_path.name]
    with np.load(first.disk_path, allow_pickle=False) as data:
        assert set(data.files) == _BUNDLE_ARRAY_NAMES
        assert data["stat_keys"].dtype == np.dtype("uint8")
        assert data["stat_keys"].flags.f_contiguous
        assert data["frontier_meta"].flags.f_contiguous
        # Each surface table is stored as byte planes: 4 per uint32 column.
        rows_planes, pattern_planes = data["surface_rows"], data["surface_patterns"]
    assert rows_planes.dtype == pattern_planes.dtype == np.dtype("uint8")
    assert rows_planes.shape[0] == 16 and rows_planes.shape[1] > 0
    assert pattern_planes.shape[0] == 40 and pattern_planes.shape[1] > 0

    def _raise_build(*_args, **_kwargs):
        raise AssertionError("warm sparse bundle should load without rebuilding frontiers")

    reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(response_cache, "build_force_greats_response_first_frontiers_gpu_batch", _raise_build)
    second = response_cache.build_or_load_response_frontier_payload(_song(), _curves(), stat_keys=keys)
    assert second.cache_source == "disk"
    assert set(second.payload.frontier_by_key) == set(keys)


@pytest.mark.parametrize("shape", [(0, 4), (1, 4), (7, 10), (5000, 4)])
def test_fg_response_surface_tables_roundtrip_through_byte_planes_exactly(shape) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import _byte_planes, _columns

    rng = np.random.default_rng(shape[0])
    table = rng.integers(0, 2**32, size=shape, dtype=np.uint64).astype(np.uint32)
    if table.size:
        table.flat[0] = 0xFFFFFFFF
    decoded = _columns(_byte_planes(table))
    assert decoded.dtype == np.dtype("uint32")
    assert np.array_equal(decoded.T, table)


def test_a_damaged_fg_response_bundle_is_deleted_and_rebuilt(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0))
    first = response_cache.build_or_load_response_frontier_payload(_song(), _curves(), stat_keys=keys)
    data = bytearray(first.disk_path.read_bytes())
    data[len(data) // 2] ^= 0xFF  # a flipped byte inside the archive: its CRC no longer matches
    first.disk_path.write_bytes(bytes(data))

    reset_fg_response_frontier_payload_cache()
    second = response_cache.build_or_load_response_frontier_payload(_song(), _curves(), stat_keys=keys)

    assert second.cache_source == "built"
    assert second.payload.frontier_for_stats(ft_stat=3, ff_stat=0).first_frontier == (
        first.payload.frontier_for_stats(ft_stat=3, ff_stat=0).first_frontier
    )


def test_fg_response_frontier_bundle_interns_equal_surface_segments(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_surfaces import SurfaceRowsFirstFrontier
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import _load_payload, _save_payload
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
        raw_fill_by_ff=np.zeros((MAX_STAT + 1,), dtype=np.float64),
        non_fever_base_by_ff=np.zeros((MAX_STAT + 1,), dtype=np.int32),
        real_time_by_ft=np.zeros((MAX_STAT + 1,), dtype=np.float64),
        total_notes=120,
        long_notes=0,
        use_forced_great_timing=True,
    )
    cache_key = ("unit", "equal-frontier-segments")

    _save_payload(cache_key, payload)

    arrays = read_compatible_bundle(cache_key)
    assert arrays["frontier_ids"].tolist() == [0, 1]
    assert arrays["frontier_meta"].shape[0] == 2
    assert arrays["first_offsets"].tolist() == [0, 0]
    assert arrays["first_counts"].tolist() == [2, 2]
    assert arrays["surface_rows"].shape == (4, 2)
    assert arrays["surface_rows"].dtype == np.dtype("uint32")
    assert arrays["surface_patterns"].shape[0] == 10

    loaded = _load_payload(cache_key)
    assert loaded is not None
    assert loaded.frontier_by_key[(0, 0)] is not loaded.frontier_by_key[(1, 0)]
    assert loaded.frontier_by_key[(0, 0)].first_frontier == loaded.frontier_by_key[(1, 0)].first_frontier
    assert loaded.frontier_by_key[(1, 0)].non_fever_base == 14


def test_fg_response_frontier_surface_gather_reads_requested_ranges(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import _save_payload
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
        raw_fill_by_ff=np.zeros((MAX_STAT + 1,), dtype=np.float64),
        non_fever_base_by_ff=np.zeros((MAX_STAT + 1,), dtype=np.int32),
        real_time_by_ft=np.zeros((MAX_STAT + 1,), dtype=np.float64),
        total_notes=3,
        long_notes=0,
        use_forced_great_timing=True,
    )
    cache_key = ("unit", "surface-chunks")

    _save_payload(cache_key, payload)
    arrays = read_compatible_bundle(cache_key)
    ids, counts, words, coeffs = gather_surface_patterns(arrays["surface_rows"], arrays["surface_patterns"], ((1, 2),))

    assert words[ids][:, 0].tolist() == [2, 3]
    assert counts.tolist() == [[20, 1, 0], [30, 2, 1]]
    assert coeffs.shape == (2, 4)
    assert coeffs.dtype == np.dtype("int32")


@pytest.mark.parametrize("cache_mutation", ("missing_core_array", "missing_surface_table", "extra_stale_array"))
def test_fg_response_frontier_disk_info_rejects_non_exact_bundle(
    tmp_path: Path,
    monkeypatch,
    cache_mutation: str,
) -> None:
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import (
        _fg_response_disk_cache_path,
        _payload_disk_is_complete,
        _save_payload,
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
        raw_fill_by_ff=np.zeros((MAX_STAT + 1,), dtype=np.float64),
        non_fever_base_by_ff=np.zeros((MAX_STAT + 1,), dtype=np.int32),
        real_time_by_ft=np.zeros((MAX_STAT + 1,), dtype=np.float64),
        total_notes=3,
        long_notes=0,
        use_forced_great_timing=True,
    )
    cache_key = ("unit", "non-exact-bundle", cache_mutation)

    _save_payload(cache_key, payload)
    cache_path = _fg_response_disk_cache_path(cache_key)
    if cache_mutation == "missing_core_array":
        _remove_npz_array(cache_path, "raw_fill_by_ff")
    elif cache_mutation == "missing_surface_table":
        _remove_npz_array(cache_path, "surface_rows")
    elif cache_mutation == "extra_stale_array":
        _add_npz_array(cache_path, "obsolete_array", np.asarray([1], dtype=np.int32))
    else:
        raise AssertionError(f"Unhandled cache mutation: {cache_mutation}")

    assert not _payload_disk_is_complete(cache_key, ((0, 0),))


def test_fg_response_frontier_scoring_bundle_does_not_unpack_payload_on_disk_hit(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_song(), _varying_ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"
    reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(
        response_cache,
        "_load_payload",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("full payload unpack should not run")),
    )

    bundle = response_cache.load_response_frontier_scoring_bundle(
        _song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )

    assert _loaded_stat_keys(bundle) == set(keys)
    assert bundle.surface_pattern_ids.shape == (0,)
    assert bundle.surface_pattern_words.shape == (0, 8)
    assert int(bundle.surface_row_count) > 0


def test_fg_response_frontier_scoring_bundle_reuses_persisted_head_coeffs(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_song(), _varying_ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"
    with np.load(first.disk_path, allow_pickle=False) as data:
        assert data["first_surface_head_len"].dtype == np.dtype("uint8")
        # Head coeffs persist losslessly as two packed uint32 columns of the pattern table (10 columns).
        assert data["surface_patterns"].shape[0] == 4 * 10

    reset_fg_response_frontier_payload_cache()

    def _raise_recompute(*_args, **_kwargs):
        raise AssertionError("persisted song-only head coeffs should be reused")

    monkeypatch.setattr(response_cache_store, "surface_head_coeffs", _raise_recompute)
    bundle = response_cache.load_response_frontier_scoring_bundle(
        _song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )

    assert _loaded_stat_keys(bundle) == set(keys)
    frontier_idx = int(bundle.frontier_idx_by_stat[0, 0])
    start = int(bundle.frontier_offsets[int(frontier_idx)])
    count = int(bundle.frontier_lengths[int(frontier_idx)])
    _ids, _counts, _words, coeffs = gather_surface_patterns(
        bundle.surface_rows, bundle.surface_patterns, ((start, count),)
    )
    assert coeffs.shape[1] == 4
    assert coeffs.dtype == np.dtype("int32")


def test_a_loaded_scoring_bundle_maps_every_stat_key_its_file_holds(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    reset_fg_response_frontier_payload_cache()
    response_cache.build_or_load_response_frontier_payload(
        _song(), _varying_ref_arrays(), stat_keys=((0, 0), (1, 0), (2, 0))
    )
    reset_fg_response_frontier_payload_cache()

    bundle = response_cache.load_response_frontier_scoring_bundle(_song(), _varying_ref_arrays(), stat_keys=((0, 0),))

    assert _loaded_stat_keys(bundle) == {(0, 0), (1, 0), (2, 0)}
    # A later request for another held key is served by the same bundle, without reading the file again.
    assert response_cache.load_response_frontier_scoring_bundle(
        _song(), _varying_ref_arrays(), stat_keys=((2, 0),)
    ) is bundle
    assert bundle.frontier_idx_by_key.get((5, 9)) is None


def test_fg_response_frontier_scoring_bundle_disk_hit_skips_redundant_disk_info_probe(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_song(), _varying_ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"
    reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(
        response_cache,
        "_payload_disk_is_complete",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("disk info probe should be skipped")),
    )

    bundle = response_cache.load_response_frontier_scoring_bundle(
        _song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )

    assert _loaded_stat_keys(bundle) == set(keys)
    assert bundle.surface_pattern_ids.shape == (0,)
    assert bundle.surface_pattern_words.shape == (0, 8)
    assert int(bundle.surface_row_count) > 0


def test_fg_response_frontier_scoring_bundle_requires_startup_cache(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    reset_fg_response_frontier_payload_cache()

    with pytest.raises(ValueError, match="Startup cache prebuild must build"):
        response_cache.load_response_frontier_scoring_bundle(
            _song(),
            _varying_ref_arrays(),
            stat_keys=((0, 0),),
        )
    assert not list(tmp_path.glob("*.npz"))


def test_fg_response_frontier_scoring_bundle_rejects_partial_runtime_cache(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    reset_fg_response_frontier_payload_cache()

    response_cache.build_or_load_response_frontier_payload(
        _song(),
        _varying_ref_arrays(),
        stat_keys=((0, 0),),
    )
    reset_fg_response_frontier_payload_cache()

    with pytest.raises(ValueError, match="all-FT/FF bundle"):
        response_cache.load_response_frontier_scoring_bundle(
            _song(),
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
        [str(first_path), str(second_path)],
        _curves(),
        "precise",
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
    reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (1, 0))
    response_cache.build_or_load_response_frontier_payload(_song(), _varying_ref_arrays(), stat_keys=keys)
    reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(
        response_cache,
        "_load_payload",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("full payload unpack should not run")),
    )

    scoring_bundle = response_cache.load_response_frontier_scoring_bundle(
        _song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )
    result = frontier_result_from_scoring_bundle_for_stats(
        _song(),
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
    reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (1, 0))

    monkeypatch.setattr(response_cache_types, "_FG_RESPONSE_CACHE_VERSION", "fg-response-frontier-legacy-v1")
    legacy = response_cache.build_or_load_response_frontier_payload(_song(), _varying_ref_arrays(), stat_keys=keys)
    assert legacy.cache_source == "built"

    reset_fg_response_frontier_payload_cache()
    build_calls: list[int] = []
    real_build = response_cache.build_force_greats_response_first_frontiers_gpu_batch

    def _record_build(*args, **kwargs):
        build_calls.append(len(tuple(kwargs.get("geometries") or ())))
        return real_build(*args, **kwargs)

    monkeypatch.setattr(response_cache, "build_force_greats_response_first_frontiers_gpu_batch", _record_build)
    monkeypatch.setattr(response_cache_types, "_FG_RESPONSE_CACHE_VERSION", "fg-response-frontier-sparse-bundle-v2-test")
    current = response_cache.build_or_load_response_frontier_payload(_song(), _varying_ref_arrays(), stat_keys=keys)

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
    reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (1, 0))
    # A synthetic ratified lineage: the mechanism, independent of which versions are ratified today.
    current_version = "fg-response-frontier-test+logic-current"
    lineage = tuple(f"fg-response-frontier-test+logic-older{n}" for n in (1, 2, 3))
    monkeypatch.setitem(response_cache_store._EXACT_COMPATIBLE_PREDECESSOR_VERSIONS, current_version, lineage)
    monkeypatch.setattr(response_cache_types, "_FG_RESPONSE_CACHE_VERSION", current_version)
    compatible_versions = response_cache_store.FG_RESPONSE_FRONTIER_CACHE.compatible_versions()
    assert compatible_versions == (current_version, *lineage)
    predecessor = compatible_versions[int(predecessor_index)]

    monkeypatch.setattr(response_cache_types, "_FG_RESPONSE_CACHE_VERSION", predecessor)
    legacy = response_cache.build_or_load_response_frontier_payload(
        _song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )
    assert legacy.cache_source == "built"
    legacy_path = Path(legacy.disk_path)
    assert legacy_path.exists()

    reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(response_cache_types, "_FG_RESPONSE_CACHE_VERSION", current_version)

    def _build_must_not_run(*_args, **_kwargs):
        raise AssertionError("ratified compatible cache hit must not rebuild")

    monkeypatch.setattr(
        response_cache,
        "build_force_greats_response_first_frontiers_gpu_batch",
        _build_must_not_run,
    )
    reused = response_cache.build_or_load_response_frontier_payload(
        _song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )
    scoring = response_cache.load_response_frontier_scoring_bundle(
        _song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )

    assert reused.cache_source == "disk"
    assert Path(reused.disk_path) == legacy_path
    assert response_cache_store.FG_RESPONSE_FRONTIER_CACHE.serving_path(scoring.cache_key) == legacy_path
    assert response_cache_store.purge_stale_version_cache_files() == 0
    assert legacy_path.exists()


def test_purge_stale_version_cache_files_removes_only_superseded(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store as store
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import (
        _FG_RESPONSE_CACHE_VERSION,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))

    def _plant(digest: str, version: str | None) -> None:
        members = {"payload": np.arange(3)}
        if version is not None:
            members["version"] = np.array(version)
        np.savez(str(tmp_path / f"{digest}.npz"), **members)

    _plant("stale_a", "fg-response-frontier-visible-first-v29")
    _plant("stale_b", "fg-response-frontier-legacy-v2")
    _plant("current", _FG_RESPONSE_CACHE_VERSION)
    compatible_predecessors = store.FG_RESPONSE_FRONTIER_CACHE.compatible_versions()[1:]
    for index, compatible_predecessor in enumerate(compatible_predecessors):
        _plant(f"compatible_{index}", compatible_predecessor)
    _plant("noversion", None)  # missing version field: must be kept, never guessed stale

    with pytest.raises(RuntimeError, match="destructive cache rotation was not explicitly authorized"):
        store.purge_stale_version_cache_files()
    assert (tmp_path / "stale_a.npz").exists()

    removed = store.purge_stale_version_cache_files(authorize_rotation=True)

    assert removed == 2
    # The current entry AND the version-less entry survive (never guess-delete), plus the marker.
    expected_names = {"current.npz", "noversion.npz", store._PURGED_VERSION_MARKER}
    expected_names.update(f"compatible_{index}.npz" for index in range(len(compatible_predecessors)))
    assert {p.name for p in tmp_path.iterdir()} == expected_names
    assert (
        (tmp_path / store._PURGED_VERSION_MARKER).read_text(encoding="utf-8").strip()
        == "\n".join(store.FG_RESPONSE_FRONTIER_CACHE.compatible_versions())
    )
    # The marker gates the rescan: a second call short-circuits without re-reading bundles.
    assert store.purge_stale_version_cache_files() == 0


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
    reset_fg_response_frontier_payload_cache()
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
    curves = _varying_ref_arrays()

    first = response_cache.build_or_load_response_frontier_payload(
        _song(),
        curves,
        stat_keys=((0, 0), (1, 0)),
    )
    assert first.cache_source == "built"
    assert [len(call) for call in calls] == [2]

    reset_fg_response_frontier_payload_cache()
    second = response_cache.build_or_load_response_frontier_payload(
        _song(),
        curves,
        stat_keys=((1, 0), (2, 0)),
    )

    assert second.cache_source == "built"
    assert set(second.payload.frontier_by_key) == {(1, 0), (2, 0)}
    assert [len(call) for call in calls] == [2, 1]
    assert len(list(tmp_path.glob("*.npz"))) == 1


def test_fg_response_frontier_bundle_extensions_union_across_processes(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(
        response_cache,
        "build_force_greats_response_first_frontiers_gpu_batch",
        lambda *, geometries, **_kwargs: _fake_response_frontiers(geometries),
    )
    reset_fg_response_frontier_payload_cache()
    response_cache.build_or_load_response_frontier_payload(
        _song(),
        _varying_ref_arrays(),
        stat_keys=((0, 0),),
    )
    reset_fg_response_frontier_payload_cache()

    context = multiprocessing.get_context("spawn")
    start_event = context.Event()
    result_queue = context.Queue()
    workers = (
        context.Process(target=_extend_fg_bundle_worker, args=(str(tmp_path), (1, 0), start_event, result_queue)),
        context.Process(target=_extend_fg_bundle_worker, args=(str(tmp_path), (2, 0), start_event, result_queue)),
    )
    for worker in workers:
        worker.start()
    start_event.set()
    results = [result_queue.get(timeout=20.0) for _worker in workers]
    for worker in workers:
        worker.join(timeout=20.0)
        assert worker.exitcode == 0
    assert sorted(results) == [("ok", (1, 0)), ("ok", (2, 0))]

    reset_fg_response_frontier_payload_cache()
    bundle_key = fg_response_frontier_bundle_cache_key(_song(), _varying_ref_arrays())
    bundle = response_cache._load_payload(bundle_key)
    assert bundle is not None
    assert set(bundle.frontier_by_key) == {(0, 0), (1, 0), (2, 0)}


def test_fg_response_frontier_reader_keeps_one_generation_during_publish(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(
        response_cache,
        "build_force_greats_response_first_frontiers_gpu_batch",
        lambda *, geometries, **_kwargs: _fake_response_frontiers(geometries),
    )
    reset_fg_response_frontier_payload_cache()
    response_cache.build_or_load_response_frontier_payload(
        _song(),
        _varying_ref_arrays(),
        stat_keys=((0, 0),),
    )

    context = multiprocessing.get_context("spawn")
    ready_event = context.Event()
    published_event = context.Event()
    result_queue = context.Queue()
    reader = context.Process(
        target=_read_fg_bundle_across_publish_worker,
        args=(str(tmp_path), ready_event, published_event, result_queue),
    )
    writer = context.Process(
        target=_publish_fg_bundle_worker,
        args=(str(tmp_path), ready_event, published_event, result_queue),
    )
    reader.start()
    writer.start()
    results = [result_queue.get(timeout=20.0) for _process in (reader, writer)]
    for process in (reader, writer):
        process.join(timeout=20.0)
        assert process.exitcode == 0
    result_kinds = {kind for kind, _value in results}
    assert result_kinds == {"reader_ok", "writer_ok"}, results


def test_fg_response_frontier_failed_publish_keeps_previous_bundle_readable(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store as store

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(
        response_cache,
        "build_force_greats_response_first_frontiers_gpu_batch",
        lambda *, geometries, **_kwargs: _fake_response_frontiers(geometries),
    )
    reset_fg_response_frontier_payload_cache()
    response_cache.build_or_load_response_frontier_payload(
        _song(),
        _varying_ref_arrays(),
        stat_keys=((0, 0),),
    )
    bundle_key = fg_response_frontier_bundle_cache_key(_song(), _varying_ref_arrays())
    previous_bundle = store._load_payload(bundle_key)
    assert previous_bundle is not None
    update, _source = response_cache._build_response_frontier_cache_payload(
        _song(),
        _varying_ref_arrays(),
        stat_keys=((1, 0),),
    )
    merged = response_cache._merge_payloads(previous_bundle, update)
    real_save = store._save_npz_fast_compressed

    def _stop_after_writing(path: Path, arrays) -> None:
        real_save(path, arrays)
        raise _InjectedPublicationStop

    monkeypatch.setattr(store, "_save_npz_fast_compressed", _stop_after_writing)
    with pytest.raises(_InjectedPublicationStop):
        store._save_payload(bundle_key, merged)

    reset_fg_response_frontier_payload_cache()
    assert [path.suffix for path in tmp_path.iterdir() if path.is_file()] == [".npz"]  # no temporary file left
    restored = store._load_payload(bundle_key)
    assert restored is not None
    assert set(restored.frontier_by_key) == {(0, 0)}


def test_fg_response_frontier_bundle_builds_are_single_owner(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    reset_fg_response_frontier_payload_cache()
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
    curves = _varying_ref_arrays()

    def _build(name: str) -> None:
        response_cache.build_or_load_response_frontier_payload(
            _song(name),
            curves,
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
    reset_fg_response_frontier_payload_cache()

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
    monkeypatch.setattr(response_cache, "_memory_put", _forbid_geometry_lru, raising=False)

    result = response_cache.build_or_load_response_frontier_payload(
        _song(),
        _varying_ref_arrays(),
        stat_keys=((0, 0), (1, 0), (2, 0)),
    )

    assert result.cache_source == "built"
    assert set(result.payload.frontier_by_key) == {(0, 0), (1, 0), (2, 0)}


def test_fg_response_frontier_payload_loads_slim_scoring_frontiers(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    reset_fg_response_frontier_payload_cache()
    curves = _varying_ref_arrays()
    keys = ((0, 0), (1, 0))

    full = response_cache.build_or_load_response_frontier_payload(_song(), curves, stat_keys=keys)
    assert all(frontier.first_frontier for frontier in full.payload.frontiers)
    assert all(not frontier.state_frontiers for frontier in full.payload.frontiers)

    reset_fg_response_frontier_payload_cache()
    warm = response_cache.build_or_load_response_frontier_payload(_song(), curves, stat_keys=keys)
    assert warm.cache_source == "disk"
    assert all(frontier.first_frontier for frontier in warm.payload.frontiers)
    assert all(not frontier.state_frontiers for frontier in warm.payload.frontiers)

    restored = response_cache.build_or_load_response_frontier_payload(_song(), curves, stat_keys=((1, 0),))
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
    reset_fg_response_frontier_payload_cache()
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
    curves = _varying_ref_arrays()

    with pytest.raises(ValueError, match="requires first-frontier surfaces"):
        response_cache.build_or_load_response_frontier_payload(_song(), curves, stat_keys=keys)
    assert calls == [2]


def test_fg_response_frontier_payload_memory_cache_precedes_disk(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_song(), _curves(), stat_keys=keys)
    assert first.cache_source == "built"

    def _raise_disk_load(_cache_key):
        raise AssertionError("resident response-frontier payload should not hit disk")

    monkeypatch.setattr(response_cache, "_load_payload", _raise_disk_load)
    info = response_cache.fg_response_frontier_payload_cache_info(_song(), _curves(), stat_keys=keys)
    assert info.cache_source == "memory"

    second = response_cache.build_or_load_response_frontier_payload(_song(), _curves(), stat_keys=keys)
    assert second.cache_source == "memory"
    assert second.payload is first.payload


def test_fg_response_frontier_cache_info_ignores_obsolete_geometry_lru(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    reset_fg_response_frontier_payload_cache()
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
    first_key = fg_response_frontier_geometry_cache_key(
        _song(),
        _curves(),
        ft_stat=0,
        ff_stat=0,
    )
    _memory_put(first_key, complete_frontier)

    info = response_cache.fg_response_frontier_payload_cache_info(
        _song(),
        _curves(),
        stat_keys=keys,
    )

    assert info.cache_source == "missing"


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


def test_packed_scoring_batch_loads_canonical_bundle_during_prepare(monkeypatch) -> None:
    from gear_optimizer.rules import MAX_STAT, STAT_GEM_GAIN_FEVER
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
        (0, STAT_GEM_GAIN_FEVER),
        (STAT_GEM_GAIN_FEVER, 0),
        (MAX_STAT, MAX_STAT),
    )

    monkeypatch.setattr(response_frontier, "all_response_stat_keys", lambda: canonical_keys)

    def _fake_build_bundle(song, curves, *, stat_keys):
        keys = tuple(stat_keys)
        seen["song_inputs"] = song.fg_inputs
        seen["curves"] = curves
        seen["stat_keys"] = keys
        frontier_idx_by_stat = np.full((MAX_STAT + 1, MAX_STAT + 1), -1, dtype=np.int32)
        for ft_stat, ff_stat in keys:
            frontier_idx_by_stat[int(ft_stat), int(ff_stat)] = 0
        surface_words = np.zeros((1, 8), dtype=np.uint32)
        bundle = SimpleNamespace(
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
        song=SimpleNamespace(fg_inputs=song_inputs),
        curves={"ref": object()},
        selected_color="Rush",
        total_budget=1,
    )

    assert batch.scoring_bundle is seen["bundle"]
    assert seen["song_inputs"] is song_inputs
    assert seen["curves"] == {"ref": batch.curves["ref"]}
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


def test_required_response_stat_keys_are_the_complete_legal_ftff_projection() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        required_response_stat_keys_for_scoring_batch,
    )

    rows = (
        {"Fever Time": -2, "Fever Fill Rate": 158},
        {"Fever Time": 159, "Fever Fill Rate": 159},
    )
    expected = (
        (0, 158),
        (0, 160),
        (1, 158),
        (1, 160),
        (4, 158),
        (159, 159),
        (159, 160),
        (160, 159),
        (160, 160),
    )

    assert required_response_stat_keys_for_scoring_batch(
        base_stats_list=rows,
        total_budget=2,
    ) == expected
    assert required_response_stat_keys_for_scoring_batch(
        base_stats_list=({}, {}),
        base_stats7_list=(
            (0, 0, 0, 0, 0, -2, 158),
            (0, 0, 0, 0, 0, 159, 159),
        ),
        total_budget=2,
    ) == expected


def test_packed_scoring_batch_uses_supplied_prewarmed_bundle(monkeypatch) -> None:
    from gear_optimizer.rules import MAX_STAT
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
    frontier_idx_by_stat = np.full((MAX_STAT + 1, MAX_STAT + 1), -1, dtype=np.int32)
    frontier_idx_by_stat[0, 0] = 0
    prewarmed_bundle = SimpleNamespace(
        frontier_idx_by_stat=frontier_idx_by_stat,
        frontier_offsets=np.asarray([0], dtype=np.int32),
        frontier_lengths=np.asarray([1], dtype=np.int32),
        surface_pattern_ids=np.zeros((1,), dtype=np.int32),
        surface_pattern_words=np.zeros((1, 8), dtype=np.uint32),
        surface_counts=np.zeros((1, 3), dtype=np.int32),
        surface_pattern_head_coeffs=np.zeros((1, 4), dtype=np.int32),
        total_notes=1,
    )

    monkeypatch.setattr(
        response_frontier,
        "load_response_frontier_scoring_bundle",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must use prewarmed bundle")),
    )

    batch = response_frontier.prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=({"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0},),
        song=SimpleNamespace(fg_inputs=song_inputs),
        curves={"ref": object()},
        selected_color="Rush",
        total_budget=0,
        scoring_bundle=prewarmed_bundle,
    )

    assert batch.scoring_bundle is prewarmed_bundle
    assert batch.kept_stat_keys == ()
    assert batch.group_meta is None
    assert batch.scoring_surface_pattern_head_coeffs is None


def test_packed_scoring_batch_builds_its_groups_over_the_in_memory_pool() -> None:
    from gear_optimizer.rules import MAX_STAT
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
    frontier_idx_by_stat = np.full((MAX_STAT + 1, MAX_STAT + 1), -1, dtype=np.int32)
    frontier_idx_by_stat[0, 0] = 1
    surface_words = np.arange(24, dtype=np.uint32).reshape(3, 8)
    surface_counts = np.arange(9, dtype=np.int32).reshape(3, 3)
    surface_head_coeffs = np.full((3, 4), 3, dtype=np.int32)
    prewarmed_bundle = SimpleNamespace(
        frontier_idx_by_stat=frontier_idx_by_stat,
        frontier_offsets=np.asarray([0, 2], dtype=np.int32),
        frontier_lengths=np.asarray([2, 1], dtype=np.int32),
        surface_pattern_ids=np.arange(3, dtype=np.int32),
        surface_pattern_words=surface_words,
        surface_counts=surface_counts,
        surface_pattern_head_coeffs=surface_head_coeffs,
        total_notes=3,
    )


    batch = response_frontier.prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=({"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0},),
        song=SimpleNamespace(fg_inputs=song_inputs),
        curves={"ref": object()},
        selected_color="Rush",
        total_budget=0,
        scoring_bundle=prewarmed_bundle,
    )
    assert batch.scoring_surface_pattern_ids is None

    built = response_frontier.build_prepared_force_greats_response_frontier_group_arrays(batch)

    # One FT/FF split (budget 0) reaching frontier 1: one group over its single surface, scored in place.
    assert built.group_meta.tolist() == [[0, 0, 0, 0, 0, 0, 3, 0]]
    assert built.candidate_slices == ((0, 1),)
    assert built.kept_stat_keys == ((0, 0),)
    assert built.scoring_group_offsets.tolist() == [2]
    assert built.scoring_group_lengths.tolist() == [1]
    assert np.shares_memory(built.scoring_surface_pattern_words, surface_words)
    assert np.shares_memory(built.scoring_surface_counts, surface_counts)


def test_packed_scoring_batch_scores_in_memory_pool_in_place() -> None:
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    frontier_idx_by_stat = np.full((MAX_STAT + 1, MAX_STAT + 1), -1, dtype=np.int32)
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
    # The session-pruned in-memory pool is scored in place: no per-batch copy of the pool.
    assert np.shares_memory(packed_pattern_ids, bundle.surface_pattern_ids)
    assert np.shares_memory(packed_counts, bundle.surface_counts)
    assert np.shares_memory(packed_words, bundle.surface_pattern_words)
    assert np.shares_memory(packed_coeffs, bundle.surface_pattern_head_coeffs)

    # A subset batch with nonzero offsets and non-dense pattern IDs keeps absolute pool offsets.
    subset_idx_by_stat = np.full((MAX_STAT + 1, MAX_STAT + 1), -1, dtype=np.int32)
    subset_idx_by_stat[0, 0] = 1
    subset_idx_by_stat[1, 0] = 2
    subset_bundle = SimpleNamespace(
        frontier_idx_by_stat=subset_idx_by_stat,
        frontier_offsets=np.asarray([0, 3, 5], dtype=np.int32),
        frontier_lengths=np.asarray([3, 2, 1], dtype=np.int32),
        surface_pattern_ids=np.asarray([4, 0, 4, 2, 4, 1], dtype=np.int32),
        surface_pattern_words=np.arange(40, dtype=np.uint32).reshape(5, 8),
        surface_counts=np.arange(18, dtype=np.int32).reshape(6, 3),
        surface_pattern_head_coeffs=np.arange(20, dtype=np.int32).reshape(5, 4),
        cache_key=("unit", "unused"),
    )
    subset_packed = response_frontier._pack_scoring_surfaces_for_batch(
        scoring_bundle=subset_bundle,
        group_meta=np.asarray([[0, 0, 0, 0, 0, 0, 3, 0]] * 3, dtype=np.int32),
        group_ft_stat=np.asarray([1, 0, 1], dtype=np.int32),
        group_ff_stat=np.asarray([0, 0, 0], dtype=np.int32),
    )
    assert subset_packed[6] == 2
    assert subset_packed[4].tolist() == [5, 3, 5]
    assert subset_packed[5].tolist() == [1, 2, 1]
    assert np.shares_memory(subset_packed[0], subset_bundle.surface_pattern_ids)
    for group_offset, group_length in zip(subset_packed[4], subset_packed[5], strict=True):
        rows = slice(int(group_offset), int(group_offset) + int(group_length))
        np.testing.assert_array_equal(
            subset_packed[1][subset_packed[0][rows]],
            subset_bundle.surface_pattern_words[subset_bundle.surface_pattern_ids[rows]],
        )


def test_packed_scoring_batch_rejects_frontier_outside_in_memory_pool() -> None:
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    frontier_idx_by_stat = np.full((MAX_STAT + 1, MAX_STAT + 1), -1, dtype=np.int32)
    frontier_idx_by_stat[0, 0] = 0
    bundle = SimpleNamespace(
        frontier_idx_by_stat=frontier_idx_by_stat,
        frontier_offsets=np.asarray([2], dtype=np.int32),
        frontier_lengths=np.asarray([2], dtype=np.int32),
        surface_pattern_ids=np.zeros((3,), dtype=np.int32),
        surface_pattern_words=np.zeros((1, 8), dtype=np.uint32),
        surface_counts=np.zeros((3, 3), dtype=np.int32),
        surface_pattern_head_coeffs=np.zeros((1, 4), dtype=np.int32),
        cache_key=("unit", "unused"),
    )
    with pytest.raises(ValueError, match="outside the in-memory surface pool"):
        response_frontier._pack_scoring_surfaces_for_batch(
            scoring_bundle=bundle,
            group_meta=np.asarray([[0, 0, 0, 0, 0, 0, 3, 0]], dtype=np.int32),
            group_ft_stat=np.asarray([0], dtype=np.int32),
            group_ff_stat=np.asarray([0], dtype=np.int32),
        )


def test_release_fg_response_song_memory_evicts_only_target_song():
    """`release_fg_response_song_memory` must drop every memory tier for the target song's
    surfaces (scoring bundle, frontier, payload) while leaving other songs'
    entries resident. This is the per-song release that keeps a standalone optimizer run from
    accumulating one ~0.5-1.5 GB surface pool per scored song until the memory guard restarts it."""
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store as store
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import (
        fg_response_frontier_bundle_cache_key,
        fg_response_frontier_geometry_cache_key,
        fg_response_frontier_payload_cache_key,
    )

    song = _song()
    ref_a = _curves()
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
        store._scoring_bundle_memory.put(a_bundle, object())
        store._scoring_bundle_memory.put(b_bundle, object())
        store._geometry_frontier_memory.put(a_geo, object())
        store._geometry_frontier_memory.put(b_geo, object())
        store._payload_memory.put(a_payload, object())

        removed = store.release_fg_response_song_memory(a_bundle)

        # Song A: scoring bundle + frontier + payload = 3 entries.
        assert removed == 3
        assert a_bundle not in store._scoring_bundle_memory
        assert a_geo not in store._geometry_frontier_memory
        assert a_payload not in store._payload_memory
        # Song B is a different prefix and must survive untouched.
        assert b_bundle in store._scoring_bundle_memory
        assert b_geo in store._geometry_frontier_memory
    finally:
        store.reset_fg_response_frontier_payload_cache()


def _other_song():
    return _song(timestamps=(0.0, 0.3, 0.6))


def test_ensure_response_frontier_cache_releases_song_memory_after_cold_build(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store as store
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import (
        fg_response_frontier_bundle_cache_key,
        fg_response_frontier_payload_cache_key,
    )

    song = _song()
    ref_a = _curves()
    a_bundle = fg_response_frontier_bundle_cache_key(song, ref_a)
    a_payload = fg_response_frontier_payload_cache_key(song, ref_a, [(3, 5)])
    b_bundle = fg_response_frontier_bundle_cache_key(song, _varying_ref_arrays())
    assert a_bundle[:-1] != b_bundle[:-1]
    built: list[tuple] = []

    def _fake_build(song, curves, *, stat_keys):
        built.append(tuple(stat_keys))
        store._payload_memory.put(a_bundle, object())
        store._payload_memory.put(a_payload, object())
        store._payload_memory.put(b_bundle, object())
        return SimpleNamespace(cache_source="built", elapsed_ms=1.0, disk_path=Path("bundle.npz"))

    monkeypatch.setattr(
        response_cache,
        "fg_response_frontier_payload_cache_info",
        lambda *_args, **_kwargs: SimpleNamespace(cache_source="missing"),
    )
    monkeypatch.setattr(response_cache, "build_or_load_response_frontier_payload", _fake_build)
    store.reset_fg_response_frontier_payload_cache()
    try:
        response_cache.ensure_response_frontier_cache_for_song(song, ref_a, stat_keys=((3, 5),))

        assert built == [((3, 5),)]
        assert a_bundle not in store._payload_memory
        assert a_payload not in store._payload_memory
        assert b_bundle in store._payload_memory
    finally:
        store.reset_fg_response_frontier_payload_cache()


def test_ensure_response_frontier_cache_warm_hit_keeps_memos(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store as store
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import fg_response_frontier_bundle_cache_key

    song = _song()
    ref_a = _curves()
    a_bundle = fg_response_frontier_bundle_cache_key(song, ref_a)
    monkeypatch.setattr(
        response_cache,
        "fg_response_frontier_payload_cache_info",
        lambda *_args, **_kwargs: SimpleNamespace(cache_source="disk", disk_path=Path("bundle.npz")),
    )
    monkeypatch.setattr(
        response_cache,
        "build_or_load_response_frontier_payload",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("warm hit must not build")),
    )
    monkeypatch.setattr(
        response_cache,
        "release_fg_response_song_memory",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("warm hit must not release memos")),
    )
    store.reset_fg_response_frontier_payload_cache()
    try:
        store._scoring_bundle_memory.put(a_bundle, object())
        response_cache.ensure_response_frontier_cache_for_song(song, ref_a, stat_keys=((3, 5),))
        assert a_bundle in store._scoring_bundle_memory
    finally:
        store.reset_fg_response_frontier_payload_cache()


def test_ensure_response_frontier_cache_releases_on_build_failure(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store as store
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import fg_response_frontier_payload_cache_key

    song = _song()
    ref_a = _curves()
    a_payload = fg_response_frontier_payload_cache_key(song, ref_a, [(3, 5)])

    def _failing_build(*_args, **_kwargs):
        store._payload_memory.put(a_payload, object())
        raise ValueError("simulated cold build failure")

    monkeypatch.setattr(
        response_cache,
        "fg_response_frontier_payload_cache_info",
        lambda *_args, **_kwargs: SimpleNamespace(cache_source="missing"),
    )
    monkeypatch.setattr(response_cache, "build_or_load_response_frontier_payload", _failing_build)
    store.reset_fg_response_frontier_payload_cache()
    try:
        with pytest.raises(ValueError, match="simulated cold build failure"):
            response_cache.ensure_response_frontier_cache_for_song(song, ref_a, stat_keys=((3, 5),))
        assert a_payload not in store._payload_memory
    finally:
        store.reset_fg_response_frontier_payload_cache()


def _seed_fixed_timing_song_memos(store, song, refs, other_song) -> tuple[list[tuple[object, tuple]], tuple]:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import (
        fg_response_frontier_bundle_cache_key,
        fg_response_frontier_geometry_cache_key,
        fg_response_frontier_payload_cache_key,
    )

    a_bundle = fg_response_frontier_bundle_cache_key(song, refs)
    seeded = [
        (store._scoring_bundle_memory, a_bundle),
        (store._geometry_frontier_memory, fg_response_frontier_geometry_cache_key(song, refs, ft_stat=3, ff_stat=5)),
        (store._payload_memory, fg_response_frontier_payload_cache_key(song, refs, [(3, 5)])),
    ]
    for cache, key in seeded:
        cache.put(key, object())
    b_bundle = fg_response_frontier_bundle_cache_key(other_song, refs)
    assert a_bundle[:-1] != b_bundle[:-1]
    store._scoring_bundle_memory.put(b_bundle, object())
    return seeded, b_bundle


def test_fixed_timing_fg_replays_release_song_memory_on_failure(monkeypatch) -> None:
    from gear_optimizer.solver.fg_response_scoring import fixed_timing
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store as store

    song = _song()
    refs = stat_curves()
    store.reset_fg_response_frontier_payload_cache()
    try:
        seeded: list = []
        other: list = []

        def _failing_solve(*_args, **_kwargs):
            rows, b_bundle = _seed_fixed_timing_song_memos(store, song, refs, _other_song())
            seeded.extend(rows)
            other.append(b_bundle)
            raise RuntimeError("simulated FG solve failure")

        monkeypatch.setattr(fixed_timing, "_solve_fixed_timing_response_results", _failing_solve)
        with pytest.raises(RuntimeError, match="simulated FG solve failure"):
            fixed_timing.build_fixed_timing_fg_replays(
                fg_stats_list=[{"Perfect Points": 1}],
                base_stats_list=[{"Perfect Points": 1}],
                song=song,
                curves=refs,
                selected_color="Rush",
            )
        assert len(seeded) == 3
        for cache, key in seeded:
            assert key not in cache
        assert other[0] in store._scoring_bundle_memory
    finally:
        store.reset_fg_response_frontier_payload_cache()


def test_fixed_timing_fg_replays_release_song_memory_on_success(monkeypatch) -> None:
    from gear_optimizer.solver.fg_response_scoring import fixed_timing, reducer
    from gear_optimizer.solver.scoring import exact_rescore
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store as store

    song = _song()
    refs = stat_curves()
    store.reset_fg_response_frontier_payload_cache()
    try:
        seeded: list = []
        other: list = []
        result = SimpleNamespace(surface="surface-0", stats={"Perfect Points": 1})

        def _solve(*_args, **_kwargs):
            rows, b_bundle = _seed_fixed_timing_song_memos(store, song, refs, _other_song())
            seeded.extend(rows)
            other.append(b_bundle)
            return [result]

        monkeypatch.setattr(fixed_timing, "_solve_fixed_timing_response_results", _solve)
        monkeypatch.setattr(exact_rescore, "score_stats_fixed_timing_exact_batch", lambda rows, *_args: [100] * len(rows))
        monkeypatch.setattr(
            reducer,
            "materialize_force_payload_from_response_frontier",
            lambda **kwargs: {"paired_base": int(kwargs["paired_base_score"])},
        )
        replays = fixed_timing.build_fixed_timing_fg_replays(
            fg_stats_list=[{"Perfect Points": 1}],
            base_stats_list=[{"Perfect Points": 1}],
            song=song,
            curves=refs,
            selected_color="Rush",
        )
        assert replays == [{"surface": "surface-0", "force": {"paired_base": 100}}]
        for cache, key in seeded:
            assert key not in cache
        assert other[0] in store._scoring_bundle_memory
    finally:
        store.reset_fg_response_frontier_payload_cache()
