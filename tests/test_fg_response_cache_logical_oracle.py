from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
import pytest

from gear_optimizer.solver.taichi_gem.force_greats.response_cache_patterns import intern_surface_rows
from tools.verify import compare_fg_response_cache_logical_bundles as oracle


BASE_VERSION = "fg-response-frontier-visible-first-v29+logic-baseline"
CANDIDATE_VERSION = "fg-response-frontier-visible-first-v30+logic-candidate"


def _npy_bytes(array: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    np.lib.format.write_array(buffer, np.asanyarray(array), allow_pickle=False)
    return buffer.getvalue()


def _metadata(*, version: str, row_count: int, pattern_count: int | None = None) -> dict[str, np.ndarray]:
    stat_keys = np.asarray(
        [(ft, ff) for ft in range(oracle.STAT_AXIS) for ff in range(oracle.STAT_AXIS)],
        dtype=np.uint8,
    )
    arrays = {
        "version": np.asarray(version),
        "stat_keys": stat_keys,
        "frontier_ids": np.zeros((oracle.STAT_KEY_COUNT,), dtype=np.int32),
        "raw_fill_by_ff": np.linspace(1.0, 2.0, oracle.STAT_AXIS, dtype=np.float64),
        "non_fever_base_by_ff": np.arange(oracle.STAT_AXIS, dtype=np.int32),
        "real_time_by_ft": np.linspace(0.5, 1.5, oracle.STAT_AXIS, dtype=np.float64),
        "total_notes": np.asarray(12, dtype=np.int32),
        "long_notes": np.asarray(2, dtype=np.int32),
        "use_forced_great_timing": np.asarray(1, dtype=np.int8),
        "first_surface_head_len": np.asarray(12, dtype=np.uint8),
        "frontier_meta": np.asarray(((1, 2, 3, 4, 5, 6, 7),), dtype=np.int32),
        "first_offsets": np.asarray((0,), dtype=np.int32),
        "first_counts": np.asarray((row_count,), dtype=np.int32),
        "first_surface_row_count": np.asarray(row_count, dtype=np.int64),
    }
    if pattern_count is not None:
        arrays["first_surface_pattern_count"] = np.asarray(pattern_count, dtype=np.int64)
    return arrays


def _write_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for name, array in arrays.items():
            archive.writestr(f"{name}.npy", _npy_bytes(array))


def _fixture(tmp_path: Path) -> tuple[Path, Path, np.ndarray, np.ndarray]:
    pool = np.asarray(
        [
            (1, 0, 0, 0, 0, 0, 0, 0, 5, 1, 0),
            (1, 0, 0, 0, 0, 0, 0, 0, 6, 2, 1),
            (3, 0, 0, 0, 1, 0, 0, 0, 7, 3, 1),
            (1, 0, 0, 0, 0, 0, 0, 0, 8, 4, 2),
        ],
        dtype=np.uint32,
    )
    coeffs = np.asarray(
        ((11, 1, 12, 2), (11, 1, 12, 2), (9, 3, 10, 4), (11, 1, 12, 2)),
        dtype=np.uint16,
    )
    row_refs, patterns = intern_surface_rows(pool, coeffs)
    baseline = tmp_path / "baseline.npz"
    candidate = tmp_path / "candidate.npz"
    _write_npz(baseline, _metadata(version=BASE_VERSION, row_count=pool.shape[0]))
    _write_npz(
        candidate,
        _metadata(
            version=CANDIDATE_VERSION,
            row_count=pool.shape[0],
            pattern_count=patterns.shape[0],
        ),
    )
    np.save(tmp_path / "baseline.surf_pool.npy", pool)
    np.save(tmp_path / "baseline.surf_coeffs.npy", coeffs)
    np.save(tmp_path / "candidate.surf_rows.npy", row_refs)
    np.save(tmp_path / "candidate.surf_patterns.npy", patterns)
    return baseline, candidate, row_refs, patterns


def _compare(baseline: Path, candidate: Path) -> dict:
    return oracle.compare(
        baseline,
        candidate,
        baseline_version=BASE_VERSION,
        candidate_version=CANDIDATE_VERSION,
    )


def test_logical_oracle_accepts_exact_interned_rotation(tmp_path: Path) -> None:
    baseline, candidate, _row_refs, patterns = _fixture(tmp_path)

    report = _compare(baseline, candidate)

    assert report["ok"] is True
    assert report["comparison"]["logical"]["equal"] is True
    assert report["comparison"]["resolutions"]["keys"] == oracle.STAT_KEY_COUNT
    assert report["candidate"]["pattern_count"] == int(patterns.shape[0])
    assert report["comparison"]["sidecar_logical_ratio"] > 1.0


def test_logical_oracle_rejects_ordered_surface_drift(tmp_path: Path) -> None:
    baseline, candidate, row_refs, _patterns = _fixture(tmp_path)
    row_refs[1, 1] += np.uint32(1)
    np.save(tmp_path / "candidate.surf_rows.npy", row_refs)

    with pytest.raises(oracle.OracleFailure) as caught:
        _compare(baseline, candidate)

    assert caught.value.code == "ordered_surface_mismatch"
    assert caught.value.details["row"] == 1


def test_logical_oracle_rejects_invalid_pattern_id(tmp_path: Path) -> None:
    baseline, candidate, row_refs, patterns = _fixture(tmp_path)
    row_refs[0, 0] = np.uint32(patterns.shape[0])
    np.save(tmp_path / "candidate.surf_rows.npy", row_refs)

    with pytest.raises(oracle.OracleFailure) as caught:
        _compare(baseline, candidate)

    assert caught.value.code == "invalid_pattern_id"


def test_logical_oracle_rejects_common_metadata_drift(tmp_path: Path) -> None:
    baseline, candidate, _row_refs, patterns = _fixture(tmp_path)
    arrays = _metadata(
        version=CANDIDATE_VERSION,
        row_count=4,
        pattern_count=patterns.shape[0],
    )
    arrays["raw_fill_by_ff"] = arrays["raw_fill_by_ff"].copy()
    arrays["raw_fill_by_ff"][0] += 0.5
    _write_npz(candidate, arrays)

    with pytest.raises(oracle.OracleFailure) as caught:
        _compare(baseline, candidate)

    assert caught.value.code == "metadata_bytes_mismatch"
