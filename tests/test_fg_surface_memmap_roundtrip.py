"""Issue #34 parity gate: the uncompressed + memmap sidecar surface store must return rows/coeffs
BIT-IDENTICAL to the legacy 32768-row ZIP_DEFLATED chunked store, over a range sweep.

The production code now has only the memmap reader/writer, so the legacy chunked writer + reader are
captured here as local helpers (mirroring the pre-change ``_persisted_packed_frontiers`` /
``_persisted_surface_head_coeff_chunks`` / chunked ``load_first_surface_scoring_rows``). Parity is
asserted three ways for the same synthetic surfaces:

1. production memmap read of a ``_save_payload`` bundle  ==  legacy chunked read of a legacy bundle;
2. both readers agree on a real 32768-row chunk boundary.

CPU-only; no GPU. Synthesizes everything in a temp dir -- never touches bin/fg_response_frontier_cache.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
import pytest

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_patterns import (
    expand_surface_rows,
    intern_surface_rows,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import (
    _fg_response_disk_cache_path,
    _save_payload,
    _surface_sidecar_paths,
    load_first_surface_scoring_patterns,
    load_first_surface_scoring_rows,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import FgResponseFrontierCachePayload
from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import _precompute_surface_head_coeffs
from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseFrontierResult, FgResponseSurface

pytestmark = pytest.mark.filterwarnings("ignore")

_LEGACY_CHUNK_ROWS = 32768


# --------------------------------------------------------------------------------------------------
# Legacy chunked writer + reader (snapshot of the pre-change production storage format).
# --------------------------------------------------------------------------------------------------
def _legacy_pool_chunk_name(chunk_idx: int) -> str:
    return f"first_surface_pool_chunk_{int(chunk_idx):05d}"


def _legacy_coeff_chunk_name(chunk_idx: int) -> str:
    return f"first_surface_head_coeffs_chunk_{int(chunk_idx):05d}"


def _write_legacy_chunked_bundle(
    npz_path: Path,
    *,
    pool: np.ndarray,
    coeffs: np.ndarray,
    chunk_rows: int,
) -> None:
    """Write a legacy bundle .npz: fortran-order uint32 pool chunks + C-order uint16 coeff chunks
    + int32 first_surface_chunk_offsets, exactly as the pre-change writer did."""
    pool = np.asfortranarray(np.asarray(pool, dtype=np.uint32))
    coeffs = np.ascontiguousarray(np.asarray(coeffs, dtype=np.uint16))
    row_count = int(pool.shape[0])
    chunk_offsets = np.asarray(
        list(range(0, row_count, int(chunk_rows))) + [row_count], dtype=np.int32
    )
    members: dict[str, np.ndarray] = {"first_surface_chunk_offsets": chunk_offsets}
    for chunk_idx, start in enumerate(range(0, row_count, int(chunk_rows))):
        end = min(row_count, int(start) + int(chunk_rows))
        members[_legacy_pool_chunk_name(chunk_idx)] = np.asfortranarray(pool[start:end])
        members[_legacy_coeff_chunk_name(chunk_idx)] = np.ascontiguousarray(coeffs[start:end])
    from numpy.lib import format as np_format

    npz_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(npz_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as archive:
        for name, array in members.items():
            with archive.open(f"{name}.npy", mode="w", force_zip64=True) as handle:
                np_format.write_array(handle, np.asanyarray(array), allow_pickle=False)


def _read_legacy_chunked_rows(
    npz_path: Path,
    ranges: tuple[tuple[int, int], ...],
) -> tuple[np.ndarray, np.ndarray]:
    """Pre-change reader: chunk-index resolution + Python range-loop copy. Returns uint32 rows N x 11
    and int32 coeffs N x 4 (coeffs stored uint16, widened on read)."""
    with zipfile.ZipFile(npz_path, mode="r") as archive:
        names = set(archive.namelist())

        def _load(member: str, dtype) -> np.ndarray:
            with archive.open(f"{member}.npy", mode="r") as handle:
                return np.asarray(np.load(io.BytesIO(handle.read()), allow_pickle=False), dtype=dtype)

        offsets = np.asarray(_load("first_surface_chunk_offsets", np.int64)).reshape(-1)
        total_rows = int(offsets[-1])
        out_rows = sum(int(count) for _start, count in ranges)
        rows = np.empty((out_rows, 11), dtype=np.uint32)
        coeffs = np.empty((out_rows, 4), dtype=np.int32)
        for out_array, name_fn, col, dtype in (
            (rows, _legacy_pool_chunk_name, 11, np.uint32),
            (coeffs, _legacy_coeff_chunk_name, 4, np.int32),
        ):
            cursor = 0
            for start, count in ranges:
                end = int(start) + int(count)
                if end > total_rows:
                    raise ValueError("legacy range exceeds cached rows")
                first_chunk = int(np.searchsorted(offsets, int(start), side="right") - 1)
                last_chunk = int(np.searchsorted(offsets, end - 1, side="right") - 1)
                for chunk_idx in range(first_chunk, last_chunk + 1):
                    chunk_start = int(offsets[chunk_idx])
                    chunk_end = int(offsets[chunk_idx + 1])
                    copy_start = max(int(start), chunk_start)
                    copy_end = min(end, chunk_end)
                    member = name_fn(chunk_idx)
                    if f"{member}.npy" not in names:
                        raise ValueError(f"legacy bundle missing {member}")
                    chunk = _load(member, dtype)
                    out_array[cursor : cursor + (copy_end - copy_start)] = chunk[
                        copy_start - chunk_start : copy_end - chunk_start
                    ]
                    cursor += copy_end - copy_start
    return np.ascontiguousarray(rows, dtype=np.uint32), np.ascontiguousarray(coeffs, dtype=np.int32)


# --------------------------------------------------------------------------------------------------
# Synthetic surface helpers.
# --------------------------------------------------------------------------------------------------
def _synthetic_pool(row_count: int) -> np.ndarray:
    """A deterministic uint32 N x 11 pool with distinct, head-coeff-meaningful column values."""
    rng = np.random.default_rng(2026_06_10)
    pool = np.empty((int(row_count), 11), dtype=np.uint32)
    # cols 0-3 are fever words (drive head coeffs): mix of small bit patterns so coeffs are non-trivial.
    pool[:, 0:4] = rng.integers(0, np.iinfo(np.uint32).max, size=(row_count, 4), dtype=np.uint64).astype(np.uint32)
    # cols 4-7 great words.
    pool[:, 4:8] = rng.integers(0, np.iinfo(np.uint32).max, size=(row_count, 4), dtype=np.uint64).astype(np.uint32)
    # cols 8-10 body counts: keep modest so values are obviously distinct per row.
    pool[:, 8] = np.arange(row_count, dtype=np.uint32) * 3 + 7
    pool[:, 9] = np.arange(row_count, dtype=np.uint32) * 2 + 1
    pool[:, 10] = np.arange(row_count, dtype=np.uint32)
    return pool


def _surfaces_from_pool(pool: np.ndarray) -> tuple[FgResponseSurface, ...]:
    return tuple(FgResponseSurface(*(int(v) for v in pool[idx, :11])) for idx in range(int(pool.shape[0])))


def _coeffs_for(pool: np.ndarray, *, total_notes: int) -> np.ndarray:
    head_len = min(int(total_notes), 100)
    coeffs = _precompute_surface_head_coeffs(np.ascontiguousarray(pool, dtype=np.uint32), head_len=int(head_len))
    return np.ascontiguousarray(np.asarray(coeffs, dtype=np.uint16))


def _build_payload(pool: np.ndarray, *, total_notes: int) -> FgResponseFrontierCachePayload:
    surfaces = _surfaces_from_pool(pool)
    frontier = FgResponseFrontierResult(surfaces, {}, 1, 2, 3, 4, 5, 6, 7, 0.0)
    return FgResponseFrontierCachePayload(
        frontier_by_key={(0, 0): frontier},
        raw_fill_by_ff=np.zeros((TOTAL_ROWS + 1,), dtype=np.float64),
        non_fever_base_by_ff=np.zeros((TOTAL_ROWS + 1,), dtype=np.int32),
        real_time_by_ft=np.zeros((TOTAL_ROWS + 1,), dtype=np.float64),
        total_notes=int(total_notes),
        long_notes=0,
        use_forced_great_timing=True,
    )


def _range_sweep(row_count: int) -> tuple[tuple[tuple[int, int], ...], ...]:
    """A range sweep covering: single row, full span, multiple disjoint ranges, boundary stat keys."""
    sweeps: list[tuple[tuple[int, int], ...]] = [
        ((0, 1),),  # single first row
        ((int(row_count) - 1, 1),),  # single last row (boundary)
        ((0, int(row_count)),),  # full span
        ((0, 1), (2, 2), (int(row_count) - 1, 1)),  # multiple disjoint ranges incl. boundaries
    ]
    if row_count >= 4:
        sweeps.append(((1, 2), (0, 1)))  # out-of-order / overlapping starts, range-packed order matters
    return tuple(sweeps)


# --------------------------------------------------------------------------------------------------
# Tests.
# --------------------------------------------------------------------------------------------------
def test_memmap_read_matches_legacy_chunked_read(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache_store.reset_fg_response_frontier_payload_cache()

    total_notes = 80
    row_count = 70  # exercises legacy chunk-boundary logic via a small chunk size below
    pool = _synthetic_pool(row_count)
    coeffs = _coeffs_for(pool, total_notes=total_notes)

    # New path: production writer + memmap reader.
    cache_key = ("unit", "memmap-vs-legacy")
    _save_payload(cache_key, _build_payload(pool, total_notes=total_notes))
    new_npz = _fg_response_disk_cache_path(cache_key)
    row_sidecar, pattern_sidecar = _surface_sidecar_paths(new_npz)
    assert row_sidecar.exists() and pattern_sidecar.exists()
    row_refs = np.load(row_sidecar, allow_pickle=False)
    patterns = np.load(pattern_sidecar, allow_pickle=False)
    expanded_rows, expanded_coeffs = expand_surface_rows(row_refs, patterns)
    assert np.array_equal(expanded_rows, pool)
    assert np.array_equal(expanded_coeffs, coeffs.astype(np.int32))

    # Legacy path: chunked bundle with a deliberately tiny chunk size to force many chunks.
    legacy_npz = tmp_path / "legacy.npz"
    _write_legacy_chunked_bundle(legacy_npz, pool=pool, coeffs=coeffs, chunk_rows=8)

    for ranges in _range_sweep(row_count):
        legacy_rows, legacy_coeffs = _read_legacy_chunked_rows(legacy_npz, ranges)
        new_rows, new_coeffs = load_first_surface_scoring_rows(cache_key, ranges)
        assert new_rows.dtype == np.dtype("uint32")
        assert new_coeffs.dtype == np.dtype("int32")
        assert np.array_equal(new_rows, legacy_rows), f"row mismatch for ranges={ranges}"
        assert np.array_equal(new_coeffs, legacy_coeffs), f"coeff mismatch for ranges={ranges}"


def test_memmap_read_matches_legacy_across_real_chunk_boundary(tmp_path: Path, monkeypatch) -> None:
    """Span a single range across the real 32768-row chunk boundary the legacy reader used."""
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache_store.reset_fg_response_frontier_payload_cache()

    total_notes = 60
    row_count = _LEGACY_CHUNK_ROWS + 5  # 32773 -> straddles one legacy chunk boundary
    pool = _synthetic_pool(row_count)
    coeffs = _coeffs_for(pool, total_notes=total_notes)

    cache_key = ("unit", "real-chunk-boundary")
    _save_payload(cache_key, _build_payload(pool, total_notes=total_notes))

    legacy_npz = tmp_path / "legacy_big.npz"
    _write_legacy_chunked_bundle(legacy_npz, pool=pool, coeffs=coeffs, chunk_rows=_LEGACY_CHUNK_ROWS)

    boundary_ranges: tuple[tuple[tuple[int, int], ...], ...] = (
        ((_LEGACY_CHUNK_ROWS - 3, 6),),  # straddles the boundary
        ((0, row_count),),  # full span across 2 chunks
        ((_LEGACY_CHUNK_ROWS, 1),),  # exactly the first row of chunk 1
    )
    for ranges in boundary_ranges:
        legacy_rows, legacy_coeffs = _read_legacy_chunked_rows(legacy_npz, ranges)
        new_rows, new_coeffs = load_first_surface_scoring_rows(cache_key, ranges)
        assert np.array_equal(new_rows, legacy_rows), f"row mismatch for ranges={ranges}"
        assert np.array_equal(new_coeffs, legacy_coeffs), f"coeff mismatch for ranges={ranges}"


def test_reader_fails_loud_on_missing_sidecar(tmp_path: Path, monkeypatch) -> None:
    """A current-version slim .npz whose pool sidecar is gone must fail loud, never silently rebuild."""
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import FgResponseSurfaceSidecarError

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache_store.reset_fg_response_frontier_payload_cache()

    cache_key = ("unit", "missing-sidecar")
    pool = _synthetic_pool(12)
    _save_payload(cache_key, _build_payload(pool, total_notes=40))
    pool_sidecar, _coeff_sidecar = _surface_sidecar_paths(_fg_response_disk_cache_path(cache_key))
    pool_sidecar.unlink()
    response_cache_store.reset_fg_response_frontier_payload_cache()

    with pytest.raises(FgResponseSurfaceSidecarError):
        load_first_surface_scoring_rows(cache_key, ((0, 1),))


def test_surface_pattern_interning_preserves_row_order_and_repeated_patterns() -> None:
    pool = _synthetic_pool(6)
    pool[2, :8] = pool[0, :8]
    pool[4, :8] = pool[0, :8]
    coeffs = _coeffs_for(pool, total_notes=80)

    row_refs, patterns = intern_surface_rows(pool, coeffs)
    expanded_rows, expanded_coeffs = expand_surface_rows(row_refs, patterns)

    assert row_refs.shape == (6, 4)
    assert int(row_refs[0, 0]) == int(row_refs[2, 0]) == int(row_refs[4, 0])
    assert np.array_equal(expanded_rows, pool)
    assert np.array_equal(expanded_coeffs, coeffs.astype(np.int32))


def test_surface_pattern_interning_rejects_equal_masks_with_different_coefficients() -> None:
    pool = _synthetic_pool(2)
    pool[1, :8] = pool[0, :8]
    coeffs = _coeffs_for(pool, total_notes=80)
    coeffs[1, 0] = np.uint16(int(coeffs[1, 0]) + 1)

    with pytest.raises(ValueError, match="inconsistent scoring coefficients"):
        intern_surface_rows(pool, coeffs)


def test_issue116_writer_derives_head_coefficients_after_exact_pattern_interning(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner_host

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache_store.reset_fg_response_frontier_payload_cache()

    total_notes = 80
    pool = _synthetic_pool(8)
    pool[2, :8] = pool[0, :8]
    pool[5, :8] = pool[0, :8]
    pool[7, :8] = pool[1, :8]
    expected_pattern_words = np.unique(pool[:, :8], axis=0)
    expected_coeffs = _coeffs_for(pool, total_notes=total_notes).astype(np.int32)
    real_precompute = response_inner_host._precompute_surface_head_coeffs
    precompute_inputs: list[np.ndarray] = []

    def _track_pattern_precompute(surface_words: np.ndarray, *, head_len: int) -> np.ndarray:
        precompute_inputs.append(np.asarray(surface_words).copy())
        return real_precompute(surface_words, head_len=int(head_len))

    monkeypatch.setattr(response_inner_host, "_precompute_surface_head_coeffs", _track_pattern_precompute)
    cache_key = ("unit", "issue116-pattern-coeff-owner")
    _save_payload(cache_key, _build_payload(pool, total_notes=total_notes))

    assert len(precompute_inputs) == 1
    assert np.array_equal(precompute_inputs[0], expected_pattern_words)
    assert int(precompute_inputs[0].shape[0]) < int(pool.shape[0])

    row_sidecar, pattern_sidecar = _surface_sidecar_paths(_fg_response_disk_cache_path(cache_key))
    row_refs = np.load(row_sidecar, allow_pickle=False)
    patterns = np.load(pattern_sidecar, allow_pickle=False)
    expected_row_refs, expected_patterns = intern_surface_rows(pool, expected_coeffs)
    assert np.array_equal(row_refs, expected_row_refs)
    assert np.array_equal(patterns, expected_patterns)
    expanded_rows, expanded_coeffs = expand_surface_rows(row_refs, patterns)
    assert np.array_equal(expanded_rows, pool)
    assert np.array_equal(expanded_coeffs, expected_coeffs)


def test_surface_pattern_expansion_rejects_invalid_pattern_id() -> None:
    row_refs = np.asarray([[1, 2, 3, 4]], dtype=np.uint32)
    patterns = np.zeros((1, 10), dtype=np.uint32)

    with pytest.raises(ValueError, match="invalid head-pattern ID"):
        expand_surface_rows(row_refs, patterns)


def test_compact_scoring_loader_preserves_range_order_and_pattern_sharing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache_store.reset_fg_response_frontier_payload_cache()
    pool = _synthetic_pool(6)
    pool[2, :8] = pool[0, :8]
    pool[4, :8] = pool[0, :8]
    cache_key = ("unit", "compact-scoring-loader")
    _save_payload(cache_key, _build_payload(pool, total_notes=80))
    ranges = ((4, 2), (0, 3))

    pattern_ids, counts, pattern_words, pattern_coeffs = load_first_surface_scoring_patterns(
        cache_key,
        ranges,
    )
    expanded_rows, expanded_coeffs = load_first_surface_scoring_rows(cache_key, ranges)

    assert pattern_ids.shape == (5,)
    assert counts.shape == (5, 3)
    assert pattern_words.shape[0] < pattern_ids.shape[0]
    np.testing.assert_array_equal(pattern_words[pattern_ids], expanded_rows[:, :8])
    np.testing.assert_array_equal(counts, expanded_rows[:, 8:11].astype(np.int32))
    np.testing.assert_array_equal(pattern_coeffs[pattern_ids], expanded_coeffs)
