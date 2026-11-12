from __future__ import annotations

from tests.curves_support import synthetic_curves
from tests.songs_support import make_song
from tests.fg_cache_support import (
    build_or_load_payload,
    ensure_cache,
    forget_scoring_bundles,
    load_scoring_bundle,
    surface_frontier,
)
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
from gear_optimizer.frontier import fg_cache_types
from gear_optimizer.frontier.fg_cache_keys import fg_response_frontier_bundle_cache_key
from gear_optimizer.frontier.fg_cache_store import read_compatible_bundle


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
    from gear_optimizer.frontier.types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    rows = tuple(geometries or ())
    return tuple(
        FgResponseFrontierResult(
            first_frontier=surface_frontier(
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
            states_evaluated=1,
            actions=1,
            transitions_evaluated=1,
            generated_surfaces=1,
            retained_surfaces_total=1,
            max_state_frontier=1,
            non_fever_base=0,
        )
        for idx, _row in enumerate(rows, start=1)
    )


def _extend_fg_bundle_worker(cache_dir: str, stat_key: tuple[int, int], start_event, result_queue) -> None:
    try:
        os.environ["FG_RESPONSE_FRONTIER_CACHE_DIR"] = str(cache_dir)
        from gear_optimizer.frontier import fg_cache

        forget_scoring_bundles()

        def _delayed_build(_song_arrays, geometries, _use_forced_great_timing):
            time.sleep(0.2)
            return _fake_response_frontiers(geometries)

        fg_cache.build_frontiers = _delayed_build
        if not start_event.wait(timeout=10.0):
            raise TimeoutError("bundle extension start was not released")
        build_or_load_payload(
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
        from gear_optimizer.frontier import fg_cache

        forget_scoring_bundles()
        scoring = load_scoring_bundle(
            _song(),
            _varying_ref_arrays(),
            stat_keys=((0, 0),),
        )
        frontier_idx = int(scoring.frontier_idx_by_stat[0, 0])
        start, length = int(scoring.pool.frontier_offsets[frontier_idx]), int(scoring.pool.frontier_lengths[frontier_idx])
        ready_event.set()
        if not published_event.wait(timeout=10.0):
            raise TimeoutError("bundle publication did not finish")
        rows = scoring.pool.pattern_ids[start : start + length]
        extended = load_scoring_bundle(
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
        from gear_optimizer.frontier import fg_cache

        forget_scoring_bundles()
        fg_cache.build_frontiers = (
            lambda _song_arrays, geometries, _use_forced_great_timing: _fake_response_frontiers(geometries)
        )
        if not ready_event.wait(timeout=10.0):
            raise TimeoutError("reader did not load the previous generation")
        build_or_load_payload(
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

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    forget_scoring_bundles()

    first = build_or_load_payload(_song(), _curves(), stat_keys=((0, 0),))
    assert first.cache_source == "built"
    assert first.disk_path.exists()
    assert len(first.payload.frontiers) == 1
    assert first.payload.frontier_for_stats(ft_stat=0, ff_stat=0).first_frontier

    forget_scoring_bundles()
    second = build_or_load_payload(_song(), _curves(), stat_keys=((0, 0),))
    assert second.cache_source == "disk"
    assert len(second.payload.frontiers) == 1
    assert second.payload.frontier_for_stats(ft_stat=0, ff_stat=0).first_frontier == (
        first.payload.frontier_for_stats(ft_stat=0, ff_stat=0).first_frontier
    )


def test_fg_response_frontier_payload_reuses_old_disk_cache_without_ttl(tmp_path: Path, monkeypatch) -> None:

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ROBEATSMETA_LIVE_CACHE_IDLE_TTL_SECONDS", "1800")
    forget_scoring_bundles()

    first = build_or_load_payload(_song(), _curves(), stat_keys=((0, 0),))
    assert first.cache_source == "built"
    stale_ts = time.time() - 3700.0
    os.utime(first.disk_path, (stale_ts, stale_ts))

    forget_scoring_bundles()
    second = build_or_load_payload(_song(), _curves(), stat_keys=((0, 0),))
    assert second.cache_source == "disk"
    assert second.disk_path.exists()
    assert second.disk_path.stat().st_mtime == stale_ts


def test_fg_response_frontier_sparse_bundle_is_single_disk_artifact(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.frontier import fg_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    forget_scoring_bundles()
    keys = ((0, 0), (3, 0), (0, 3))

    first = build_or_load_payload(_song(), _curves(), stat_keys=keys)
    assert first.cache_source == "built"
    assert [path.name for path in tmp_path.iterdir() if path.is_file()] == [first.disk_path.name]
    with np.load(first.disk_path, allow_pickle=False) as data:
        assert set(data.files) == {
            "version", "stat_keys", "frontier_ids", "raw_fill_by_ff", "non_fever_base_by_ff", "real_time_by_ft",
            "total_notes", "long_notes", "use_forced_great_timing", "first_surface_head_len", "frontier_meta",
            "first_offsets", "first_counts", "surface_rows", "surface_patterns",
        }
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

    forget_scoring_bundles()
    monkeypatch.setattr(fg_cache, "build_frontiers", _raise_build)
    second = build_or_load_payload(_song(), _curves(), stat_keys=keys)
    assert second.cache_source == "disk"
    assert set(second.payload.frontier_by_key) == set(keys)


def test_a_damaged_fg_response_bundle_is_deleted_and_rebuilt(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.frontier import fg_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    forget_scoring_bundles()
    keys = ((0, 0), (3, 0))
    first = build_or_load_payload(_song(), _curves(), stat_keys=keys)
    data = bytearray(first.disk_path.read_bytes())
    data[len(data) // 2] ^= 0xFF  # a flipped byte inside the archive: its CRC no longer matches
    first.disk_path.write_bytes(bytes(data))

    forget_scoring_bundles()
    second = build_or_load_payload(_song(), _curves(), stat_keys=keys)

    assert second.cache_source == "built"
    assert second.payload.frontier_for_stats(ft_stat=3, ff_stat=0).first_frontier == (
        first.payload.frontier_for_stats(ft_stat=3, ff_stat=0).first_frontier
    )


def test_a_bundle_with_a_broken_deflate_stream_is_deleted_and_rebuilt(tmp_path: Path, monkeypatch) -> None:
    """Not every damaged archive fails its CRC check: a broken deflate stream raises zlib.error first, and that file too
    is rebuilt instead of stopping the prebuild."""
    import io
    import zlib

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    forget_scoring_bundles()
    keys = ((0, 0), (3, 0))
    first = build_or_load_payload(_song(), _curves(), stat_keys=keys)
    intact = first.disk_path.read_bytes()

    def _read_error(data: bytes) -> type | None:
        try:
            with np.load(io.BytesIO(data), allow_pickle=False) as archive:
                for name in archive.files:
                    archive[name]
        except Exception as exc:  # the kind of failure is what this helper reports
            return type(exc)
        return None

    damaged = next(
        data for data in (intact[:at] + bytes([intact[at] ^ 0x07]) + intact[at + 1 :] for at in range(len(intact)))
        if _read_error(data) is zlib.error
    )
    first.disk_path.write_bytes(damaged)

    forget_scoring_bundles()
    second = build_or_load_payload(_song(), _curves(), stat_keys=keys)

    assert second.cache_source == "built"
    assert _read_error(second.disk_path.read_bytes()) is None


def test_fg_response_frontier_bundle_interns_equal_surface_segments(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.frontier.producer_surfaces import SurfaceRowsFirstFrontier
    from gear_optimizer.frontier.fg_cache_store import load_payload, save_payload
    from gear_optimizer.frontier.fg_cache_types import FgResponseFrontierCachePayload
    from gear_optimizer.frontier.types import FgResponseFrontierResult

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    rows = np.asarray(
        [
            [1, 0, 0, 0, 0, 0, 0],
            [3, 0, 1, 0, 5, 2, 1],
        ],
        dtype=np.uint64,
    )
    first = FgResponseFrontierResult(SurfaceRowsFirstFrontier(rows.copy()), 1, 2, 3, 4, 5, 6, 7)
    second = FgResponseFrontierResult(SurfaceRowsFirstFrontier(rows.copy()), 8, 9, 10, 11, 12, 13, 14)
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

    save_payload(cache_key, payload)

    arrays = read_compatible_bundle(cache_key)
    assert arrays["frontier_ids"].tolist() == [0, 1]
    assert arrays["frontier_meta"].shape[0] == 2
    assert arrays["first_offsets"].tolist() == [0, 0]
    assert arrays["first_counts"].tolist() == [2, 2]
    assert arrays["surface_rows"].shape == (4, 2)
    assert arrays["surface_rows"].dtype == np.dtype("uint32")
    assert arrays["surface_patterns"].shape[0] == 10

    loaded = load_payload(cache_key)
    assert loaded is not None
    assert loaded.frontier_by_key[(0, 0)] is not loaded.frontier_by_key[(1, 0)]
    assert loaded.frontier_by_key[(0, 0)].first_frontier == loaded.frontier_by_key[(1, 0)].first_frontier
    assert loaded.frontier_by_key[(1, 0)].non_fever_base == 14




@pytest.mark.parametrize("cache_mutation", ("missing_core_array", "missing_surface_table", "extra_stale_array"))
def test_fg_response_frontier_disk_info_rejects_non_exact_bundle(
    tmp_path: Path,
    monkeypatch,
    cache_mutation: str,
) -> None:
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.frontier.fg_cache_store import (
        FG_RESPONSE_FRONTIER_CACHE,
        bundle_file_holds,
        save_payload,
    )
    from gear_optimizer.frontier.fg_cache_types import FgResponseFrontierCachePayload
    from gear_optimizer.frontier.types import FgResponseFrontierResult, FgResponseSurface

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    surfaces = (
        FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 10, 0, 0),
        FgResponseSurface(2, 0, 0, 0, 0, 0, 0, 0, 20, 1, 0),
        FgResponseSurface(3, 0, 0, 0, 0, 0, 0, 0, 30, 2, 1),
    )
    payload = FgResponseFrontierCachePayload(
        frontier_by_key={(0, 0): FgResponseFrontierResult(surface_frontier(*surfaces), 1, 2, 3, 4, 5, 6, 7)},
        raw_fill_by_ff=np.zeros((MAX_STAT + 1,), dtype=np.float64),
        non_fever_base_by_ff=np.zeros((MAX_STAT + 1,), dtype=np.int32),
        real_time_by_ft=np.zeros((MAX_STAT + 1,), dtype=np.float64),
        total_notes=3,
        long_notes=0,
        use_forced_great_timing=True,
    )
    cache_key = ("unit", "non-exact-bundle", cache_mutation)

    save_payload(cache_key, payload)
    cache_path = FG_RESPONSE_FRONTIER_CACHE.file_path(cache_key)
    if cache_mutation == "missing_core_array":
        _remove_npz_array(cache_path, "raw_fill_by_ff")
    elif cache_mutation == "missing_surface_table":
        _remove_npz_array(cache_path, "surface_rows")
    elif cache_mutation == "extra_stale_array":
        _add_npz_array(cache_path, "obsolete_array", np.asarray([1], dtype=np.int32))
    else:
        raise AssertionError(f"Unhandled cache mutation: {cache_mutation}")

    assert not bundle_file_holds(cache_path, np.asarray([[0, 0]], dtype=np.int32))


def test_fg_response_frontier_scoring_bundle_does_not_unpack_payload_on_disk_hit(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.frontier import fg_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    forget_scoring_bundles()
    keys = ((0, 0), (3, 0), (0, 3))

    first = build_or_load_payload(_song(), _varying_ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"
    forget_scoring_bundles()
    monkeypatch.setattr(
        fg_cache,
        "load_payload",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("full payload unpack should not run")),
    )

    bundle = load_scoring_bundle(
        _song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )

    assert _loaded_stat_keys(bundle) == set(keys)
    assert int(bundle.pool.pattern_ids.shape[0]) > 0
    assert bundle.pool.pattern_words.shape[1] == 8


def test_fg_response_frontier_scoring_bundle_reuses_persisted_head_coeffs(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.frontier import fg_cache
    from gear_optimizer.frontier import fg_cache_store

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    forget_scoring_bundles()
    keys = ((0, 0), (3, 0), (0, 3))

    first = build_or_load_payload(_song(), _varying_ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"
    with np.load(first.disk_path, allow_pickle=False) as data:
        assert data["first_surface_head_len"].dtype == np.dtype("uint8")
        # Head coeffs persist losslessly as two packed uint32 columns of the pattern table (10 columns).
        assert data["surface_patterns"].shape[0] == 4 * 10

    forget_scoring_bundles()

    def _raise_recompute(*_args, **_kwargs):
        raise AssertionError("persisted song-only head coeffs should be reused")

    monkeypatch.setattr(fg_cache_store, "surface_head_coeffs", _raise_recompute)
    bundle = load_scoring_bundle(
        _song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )

    assert _loaded_stat_keys(bundle) == set(keys)
    assert bundle.pool.head_coeffs.shape[1] == 4
    assert bundle.pool.head_coeffs.dtype == np.dtype("int32")


def test_a_loaded_scoring_bundle_maps_every_stat_key_its_file_holds(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.frontier import fg_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    forget_scoring_bundles()
    build_or_load_payload(
        _song(), _varying_ref_arrays(), stat_keys=((0, 0), (1, 0), (2, 0))
    )
    forget_scoring_bundles()

    bundle = load_scoring_bundle(_song(), _varying_ref_arrays(), stat_keys=((0, 0),))

    assert _loaded_stat_keys(bundle) == {(0, 0), (1, 0), (2, 0)}
    # A later request for another held key is served by the same bundle, without reading the file again.
    assert load_scoring_bundle(
        _song(), _varying_ref_arrays(), stat_keys=((2, 0),)
    ) is bundle
    assert bundle.frontier_idx_by_stat[5, 9] == -1




def test_fg_response_frontier_scoring_bundle_requires_startup_cache(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.frontier import fg_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    forget_scoring_bundles()

    with pytest.raises(ValueError, match="Startup cache prebuild must build"):
        load_scoring_bundle(
            _song(),
            _varying_ref_arrays(),
            stat_keys=((0, 0),),
        )
    assert not list(tmp_path.glob("*.npz"))


def test_fg_response_frontier_scoring_bundle_rejects_partial_runtime_cache(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.frontier import fg_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    forget_scoring_bundles()

    build_or_load_payload(
        _song(),
        _varying_ref_arrays(),
        stat_keys=((0, 0),),
    )
    forget_scoring_bundles()

    with pytest.raises(ValueError, match="all-FT/FF bundle"):
        load_scoring_bundle(
            _song(),
            _varying_ref_arrays(),
            stat_keys=((3, 3),),
        )


def test_fg_response_frontier_payload_load_is_not_a_production_api() -> None:
    from gear_optimizer.frontier import fg_cache

    assert not hasattr(fg_cache, "load_response_frontier_payload")


def test_fg_response_frontier_bundle_version_change_invalidates_legacy_disk_bundle(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.frontier import fg_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    forget_scoring_bundles()
    keys = ((0, 0), (1, 0))

    monkeypatch.setattr(fg_cache_types, "_FG_RESPONSE_CACHE_VERSION", "fg-response-frontier-legacy-v1")
    legacy = build_or_load_payload(_song(), _varying_ref_arrays(), stat_keys=keys)
    assert legacy.cache_source == "built"

    forget_scoring_bundles()
    build_calls: list[int] = []
    real_build = fg_cache.build_frontiers

    def _record_build(song_arrays, geometries, use_forced_great_timing):
        build_calls.append(len(geometries))
        return real_build(song_arrays, geometries, use_forced_great_timing)

    monkeypatch.setattr(fg_cache, "build_frontiers", _record_build)
    monkeypatch.setattr(fg_cache_types, "_FG_RESPONSE_CACHE_VERSION", "fg-response-frontier-sparse-bundle-v2-test")
    current = build_or_load_payload(_song(), _varying_ref_arrays(), stat_keys=keys)

    assert current.cache_source == "built"
    assert build_calls == [2]
    assert len(list(tmp_path.glob("*.npz"))) == 2


@pytest.mark.parametrize("predecessor_index", (1, 2, 3))
def test_ratified_compatible_version_reuses_complete_bundle_without_build(
    tmp_path: Path,
    monkeypatch,
    predecessor_index: int,
) -> None:
    from gear_optimizer.frontier import fg_cache
    from gear_optimizer.frontier import fg_cache_store

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    forget_scoring_bundles()
    keys = ((0, 0), (1, 0))
    # A synthetic ratified lineage: the mechanism, independent of which versions are ratified today.
    current_version = "fg-response-frontier-test+logic-current"
    lineage = tuple(f"fg-response-frontier-test+logic-older{n}" for n in (1, 2, 3))
    monkeypatch.setitem(fg_cache_store._EXACT_COMPATIBLE_PREDECESSOR_VERSIONS, current_version, lineage)
    monkeypatch.setattr(fg_cache_types, "_FG_RESPONSE_CACHE_VERSION", current_version)
    compatible_versions = fg_cache_store.FG_RESPONSE_FRONTIER_CACHE.compatible_versions()
    assert compatible_versions == (current_version, *lineage)
    predecessor = compatible_versions[int(predecessor_index)]

    monkeypatch.setattr(fg_cache_types, "_FG_RESPONSE_CACHE_VERSION", predecessor)
    legacy = build_or_load_payload(
        _song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )
    assert legacy.cache_source == "built"
    legacy_path = Path(legacy.disk_path)
    assert legacy_path.exists()

    forget_scoring_bundles()
    monkeypatch.setattr(fg_cache_types, "_FG_RESPONSE_CACHE_VERSION", current_version)

    def _build_must_not_run(*_args, **_kwargs):
        raise AssertionError("ratified compatible cache hit must not rebuild")

    monkeypatch.setattr(
        fg_cache,
        "build_frontiers",
        _build_must_not_run,
    )
    reused = build_or_load_payload(
        _song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )
    scoring = load_scoring_bundle(
        _song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )

    assert reused.cache_source == "disk"
    assert Path(reused.disk_path) == legacy_path
    assert fg_cache_store.FG_RESPONSE_FRONTIER_CACHE.serving_path(scoring.cache_key) == legacy_path
    assert fg_cache_store.purge_stale_version_cache_files() == 0
    assert legacy_path.exists()


def test_purge_stale_version_cache_files_removes_only_superseded(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.frontier import fg_cache_store as store
    from gear_optimizer.frontier.fg_cache_types import (
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
    expected_names = {"current.npz", "noversion.npz", ".purged_version"}
    expected_names.update(f"compatible_{index}.npz" for index in range(len(compatible_predecessors)))
    assert {p.name for p in tmp_path.iterdir()} == expected_names
    assert (
        (tmp_path / ".purged_version").read_text(encoding="utf-8").strip()
        == "\n".join(store.FG_RESPONSE_FRONTIER_CACHE.compatible_versions())
    )
    # The marker gates the rescan: a second call short-circuits without re-reading bundles.
    assert store.purge_stale_version_cache_files() == 0


def test_purge_opens_no_bundle_while_the_lineage_reads_every_swept_version(tmp_path: Path, monkeypatch) -> None:
    """The marker lists the versions every bundle had at the last sweep. A restart, and a start after a ratified version
    change, read nothing; a lineage that dropped one of those versions sweeps again and refuses to delete unasked."""
    from gear_optimizer.frontier import fg_cache_store as store

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    marker = tmp_path / ".purged_version"
    old, new, unrelated = (f"fg-response-frontier-test+logic-{name}" for name in ("old", "new", "unrelated"))
    np.savez(str(tmp_path / "bundle.npz"), version=np.array(old))
    monkeypatch.setattr(fg_cache_types, "_FG_RESPONSE_CACHE_VERSION", old)
    assert store.purge_stale_version_cache_files() == 0  # no marker yet: swept
    assert marker.read_text(encoding="utf-8") == old

    opened: list[str] = []
    real_load = np.load
    monkeypatch.setattr(store.np, "load", lambda path, **kwargs: opened.append(str(path)) or real_load(path, **kwargs))
    assert store.purge_stale_version_cache_files() == 0  # a restart
    monkeypatch.setattr(fg_cache_types, "_FG_RESPONSE_CACHE_VERSION", new)
    monkeypatch.setitem(store._EXACT_COMPATIBLE_PREDECESSOR_VERSIONS, new, (old,))
    assert store.purge_stale_version_cache_files() == 0  # a ratified version change
    assert opened == []
    assert marker.read_text(encoding="utf-8") == f"{new}\n{old}"

    monkeypatch.setattr(fg_cache_types, "_FG_RESPONSE_CACHE_VERSION", unrelated)
    with pytest.raises(RuntimeError, match="destructive cache rotation was not explicitly authorized"):
        store.purge_stale_version_cache_files()
    assert opened == [str(tmp_path / "bundle.npz")] and (tmp_path / "bundle.npz").exists()
    assert marker.read_text(encoding="utf-8") == f"{new}\n{old}"


def test_fg_response_frontier_uint8_persistence_bounds_fail_loud(tmp_path: Path, monkeypatch) -> None:
    """Stat keys are stored as uint8: one that does not fit is refused, never wrapped."""
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.frontier.fg_cache_store import save_payload
    from gear_optimizer.frontier.fg_cache_types import FgResponseFrontierCachePayload
    from gear_optimizer.frontier.types import FgResponseFrontierResult, FgResponseSurface

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    frontier = FgResponseFrontierResult(surface_frontier(FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 0, 0)), 1, 2, 3, 4, 5, 6, 7)
    payload = FgResponseFrontierCachePayload(
        frontier_by_key={(0, 256): frontier},
        raw_fill_by_ff=np.zeros((MAX_STAT + 1,), dtype=np.float64),
        non_fever_base_by_ff=np.zeros((MAX_STAT + 1,), dtype=np.int32),
        real_time_by_ft=np.zeros((MAX_STAT + 1,), dtype=np.float64),
        total_notes=3,
        long_notes=0,
        use_forced_great_timing=True,
    )

    with pytest.raises(ValueError, match="exceeds persisted uint8 bounds"):
        save_payload(("unit", "uint8-bounds"), payload)
    assert not list(tmp_path.glob("*.npz"))


def test_fg_response_frontier_disk_bundle_reuses_overlapping_stat_keys(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.frontier import fg_cache
    from gear_optimizer.frontier.types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    forget_scoring_bundles()
    calls: list[tuple[tuple[float, int, float], ...]] = []

    def _fake_build(_song_arrays, geometries, _use_forced_great_timing):
        rows = tuple((float(row[0]), int(row[1]), float(row[2])) for row in geometries)
        calls.append(rows)
        return tuple(
            FgResponseFrontierResult(
                first_frontier=surface_frontier(FgResponseSurface(idx, 0, 0, 0, 0, 0, 0, 0, 0, 0)),
                states_evaluated=1,
                actions=1,
                transitions_evaluated=1,
                generated_surfaces=1,
                retained_surfaces_total=1,
                max_state_frontier=1,
                non_fever_base=0,
            )
            for idx, _row in enumerate(rows, start=1)
        )

    monkeypatch.setattr(fg_cache, "build_frontiers", _fake_build)
    curves = _varying_ref_arrays()

    first = build_or_load_payload(
        _song(),
        curves,
        stat_keys=((0, 0), (1, 0)),
    )
    assert first.cache_source == "built"
    assert [len(call) for call in calls] == [2]

    forget_scoring_bundles()
    second = build_or_load_payload(
        _song(),
        curves,
        stat_keys=((1, 0), (2, 0)),
    )

    assert second.cache_source == "built"
    assert set(second.payload.frontier_by_key) == {(1, 0), (2, 0)}
    assert [len(call) for call in calls] == [2, 1]
    assert len(list(tmp_path.glob("*.npz"))) == 1


def test_fg_response_frontier_bundle_extensions_union_across_processes(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.frontier import fg_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(
        fg_cache,
        "build_frontiers",
        lambda _song_arrays, geometries, _use_forced_great_timing: _fake_response_frontiers(geometries),
    )
    forget_scoring_bundles()
    build_or_load_payload(
        _song(),
        _varying_ref_arrays(),
        stat_keys=((0, 0),),
    )
    forget_scoring_bundles()

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

    forget_scoring_bundles()
    bundle_key = fg_response_frontier_bundle_cache_key(_song(), _varying_ref_arrays())
    bundle = fg_cache.load_payload(bundle_key)
    assert bundle is not None
    assert set(bundle.frontier_by_key) == {(0, 0), (1, 0), (2, 0)}


def test_fg_response_frontier_reader_keeps_one_generation_during_publish(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.frontier import fg_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(
        fg_cache,
        "build_frontiers",
        lambda _song_arrays, geometries, _use_forced_great_timing: _fake_response_frontiers(geometries),
    )
    forget_scoring_bundles()
    build_or_load_payload(
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
    from gear_optimizer.frontier import fg_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(
        fg_cache,
        "build_frontiers",
        lambda _song_arrays, geometries, _use_forced_great_timing: _fake_response_frontiers(geometries),
    )
    forget_scoring_bundles()
    ensure_cache(_song(), _varying_ref_arrays(), stat_keys=((0, 0),))

    def _stop_before_publishing(_tmp: Path, _target: Path) -> None:
        raise _InjectedPublicationStop

    with monkeypatch.context() as publication:
        publication.setattr(Path, "replace", _stop_before_publishing)  # the extended bundle is written, never renamed
        with pytest.raises(_InjectedPublicationStop):
            ensure_cache(_song(), _varying_ref_arrays(), stat_keys=((1, 0),))

    forget_scoring_bundles()
    assert [path.suffix for path in tmp_path.iterdir() if path.is_file()] == [".npz"]  # no temporary file left
    restored = load_scoring_bundle(_song(), _varying_ref_arrays(), stat_keys=((0, 0),))
    assert _loaded_stat_keys(restored) == {(0, 0)}


def test_fg_response_frontier_bundle_builds_are_single_owner(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.frontier import fg_cache
    from gear_optimizer.frontier.types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    forget_scoring_bundles()
    active = 0
    max_active = 0
    lock = threading.Lock()

    def _fake_build(_song_arrays, geometries, _use_forced_great_timing):
        nonlocal active, max_active
        rows = tuple(geometries or ())
        with lock:
            active += 1
            max_active = max(int(max_active), int(active))
        try:
            time.sleep(0.05)
            return tuple(
                FgResponseFrontierResult(
                    first_frontier=surface_frontier(FgResponseSurface(idx, 0, 0, 0, 0, 0, 0, 0, 0, 0)),
                    states_evaluated=1,
                    actions=1,
                    transitions_evaluated=1,
                    generated_surfaces=1,
                    retained_surfaces_total=1,
                    max_state_frontier=1,
                    non_fever_base=0,
                    )
                for idx, _row in enumerate(rows, start=1)
            )
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(fg_cache, "build_frontiers", _fake_build)
    curves = _varying_ref_arrays()

    def _build(name: str) -> None:
        build_or_load_payload(
            _song(name),
            curves,
            stat_keys=((0, 0), (1, 0), (2, 0)),
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(_build, "FG Cache Unit A"), executor.submit(_build, "FG Cache Unit B")]
        for future in futures:
            future.result()

    assert max_active == 1




def test_fg_response_frontier_payload_loads_slim_scoring_frontiers(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.frontier import fg_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    forget_scoring_bundles()
    curves = _varying_ref_arrays()
    keys = ((0, 0), (1, 0))

    full = build_or_load_payload(_song(), curves, stat_keys=keys)
    assert all(frontier.first_frontier for frontier in full.payload.frontiers)

    forget_scoring_bundles()
    warm = build_or_load_payload(_song(), curves, stat_keys=keys)
    assert warm.cache_source == "disk"
    assert all(frontier.first_frontier for frontier in warm.payload.frontiers)

    restored = build_or_load_payload(_song(), curves, stat_keys=((1, 0),))
    restored_frontier = restored.payload.frontier_for_stats(ft_stat=1, ff_stat=0)
    assert restored_frontier.first_frontier
    assert restored_frontier.first_frontier == full.payload.frontier_for_stats(ft_stat=1, ff_stat=0).first_frontier


def test_fg_response_frontier_cache_rejects_incomplete_frontiers(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.frontier import fg_cache
    from gear_optimizer.frontier.types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    forget_scoring_bundles()
    calls: list[int] = []

    def _fake_build(_song_arrays, geometries, _use_forced_great_timing):
        rows = tuple(geometries)
        calls.append(len(rows))
        out = []
        for idx, _geometry in enumerate(rows, start=1):
            surface = FgResponseSurface(idx, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            out.append(
                FgResponseFrontierResult(
                    first_frontier=surface_frontier(),
                    states_evaluated=1,
                    actions=1,
                    transitions_evaluated=1,
                    generated_surfaces=1,
                    retained_surfaces_total=1,
                    max_state_frontier=1,
                    non_fever_base=0,
                    )
            )
        return tuple(out)

    monkeypatch.setattr(fg_cache, "build_frontiers", _fake_build)
    keys = ((0, 0), (1, 0))
    curves = _varying_ref_arrays()

    with pytest.raises(ValueError, match="requires first-frontier surfaces"):
        build_or_load_payload(_song(), curves, stat_keys=keys)
    assert calls == [2]






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
        Path("gear_optimizer/frontier/fg_cache.py"),
        Path("gear_optimizer/frontier/fg_prebuild.py"),
    }
    offenders: list[str] = []
    for path in Path("gear_optimizer").rglob("*.py"):
        if path in allowed:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "build_or_load_response_frontier_payload" in text:
            offenders.append(str(path))

    assert offenders == []


def test_required_response_stat_keys_are_the_complete_legal_ftff_projection() -> None:
    from gear_optimizer.rules import GEM_BUDGET, MAX_STAT, STAT_GEM_GAIN_FEVER
    from gear_optimizer.solver.fg_scoring import required_response_stat_keys
    from gear_optimizer.solver.ftff_combos import ftff_combo_arrays

    rows = [{"Fever Time": -2, "Fever Fill Rate": 158}, {"Fever Time": 159, "Fever Fill Rate": 159}]
    ft_gems, ff_gems, _left = ftff_combo_arrays(GEM_BUDGET)

    def clipped(stat: int) -> int:
        return max(0, min(MAX_STAT, stat))

    expected = sorted({
        (clipped(row["Fever Time"] + ft * STAT_GEM_GAIN_FEVER), clipped(row["Fever Fill Rate"] + ff * STAT_GEM_GAIN_FEVER))
        for row in rows
        for ft, ff in zip(ft_gems.tolist(), ff_gems.tolist())
    })
    assert required_response_stat_keys(rows).tolist() == [list(key) for key in expected]


def test_release_fg_response_song_memory_evicts_only_target_song(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.frontier import fg_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(
        fg_cache,
        "build_frontiers",
        lambda _song_arrays, geometries, _use_forced_great_timing: _fake_response_frontiers(geometries),
    )
    forget_scoring_bundles()
    loaded = {}
    for name, curves in (("target", _curves()), ("other", _varying_ref_arrays())):
        ensure_cache(_song(), curves, stat_keys=((0, 0),))
        loaded[name] = load_scoring_bundle(_song(), curves, stat_keys=((0, 0),))
    assert loaded["target"].cache_key != loaded["other"].cache_key

    fg_cache.release_fg_response_song_memory(loaded["target"].cache_key)

    assert load_scoring_bundle(_song(), _curves(), stat_keys=((0, 0),)) is not loaded["target"]  # read again
    assert load_scoring_bundle(_song(), _varying_ref_arrays(), stat_keys=((0, 0),)) is loaded["other"]
    forget_scoring_bundles()
