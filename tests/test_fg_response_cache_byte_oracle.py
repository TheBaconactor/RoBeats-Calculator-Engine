from __future__ import annotations

import io
import json
import os
import struct
import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
from numpy.lib import format as np_format

from tools.verify import compare_fg_response_cache_bundles as oracle


BASELINE_VERSION = "fg-byte-oracle-baseline-v1"
CANDIDATE_VERSION = "fg-byte-oracle-candidate-v2"


def _npy_bytes(
    array: np.ndarray,
    *,
    version: tuple[int, int] | None = None,
    allow_pickle: bool = False,
) -> bytes:
    buffer = io.BytesIO()
    np_format.write_array(buffer, np.asanyarray(array), version=version, allow_pickle=allow_pickle)
    return buffer.getvalue()


def _canonical_arrays(
    version: str,
    *,
    frontier_ids: np.ndarray | None = None,
    frontier_meta: np.ndarray | None = None,
    first_offsets: np.ndarray | None = None,
    first_counts: np.ndarray | None = None,
    surface_row_count: int = 6,
) -> dict[str, np.ndarray]:
    ft = np.repeat(np.arange(oracle.STAT_AXIS, dtype=np.uint8), oracle.STAT_AXIS)
    ff = np.tile(np.arange(oracle.STAT_AXIS, dtype=np.uint8), oracle.STAT_AXIS)
    stat_keys = np.asfortranarray(np.column_stack((ft, ff)), dtype=np.uint8)
    raw_fill = np.arange(oracle.STAT_AXIS, dtype=np.float64)
    non_fever_base = np.ceil(raw_fill).astype(np.int32)
    ids = np.tile(np.arange(oracle.STAT_AXIS, dtype=np.int32), oracle.STAT_AXIS)
    if frontier_ids is not None:
        ids = np.asarray(frontier_ids)
    meta = (
        np.asfortranarray(
            np.column_stack(
                (
                    np.ones((oracle.STAT_AXIS, 1), dtype=np.int32),
                    np.full((oracle.STAT_AXIS, 1), 2, dtype=np.int32),
                    np.full((oracle.STAT_AXIS, 1), 3, dtype=np.int32),
                    np.full((oracle.STAT_AXIS, 1), 4, dtype=np.int32),
                    np.full((oracle.STAT_AXIS, 1), 5, dtype=np.int32),
                    np.full((oracle.STAT_AXIS, 1), 6, dtype=np.int32),
                    non_fever_base,
                )
            ).astype(np.int32)
        )
        if frontier_meta is None
        else np.asarray(frontier_meta)
    )
    offsets = (
        ((np.arange(meta.shape[0], dtype=np.int32) % 3) * 2).astype(np.int32)
        if first_offsets is None
        else np.asarray(first_offsets)
    )
    counts = (
        np.full((meta.shape[0],), 2, dtype=np.int32)
        if first_counts is None
        else np.asarray(first_counts)
    )
    return {
        "version": np.asarray(version),
        "stat_keys": stat_keys,
        "frontier_ids": ids,
        "raw_fill_by_ff": raw_fill,
        "non_fever_base_by_ff": non_fever_base,
        "real_time_by_ft": np.linspace(1.0, 2.0, oracle.STAT_AXIS, dtype=np.float64),
        "total_notes": np.asarray(6, dtype=np.int32),
        "long_notes": np.asarray(1, dtype=np.int32),
        "use_forced_great_timing": np.asarray(1, dtype=np.int8),
        "first_surface_head_len": np.asarray(6, dtype=np.uint8),
        "frontier_meta": meta,
        "first_offsets": offsets,
        "first_counts": counts,
        "first_surface_row_count": np.asarray(surface_row_count, dtype=np.int64),
    }


def _copy_arrays(arrays: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {name: np.array(value, copy=True, order="K") for name, value in arrays.items()}


def _derive_head_coeffs(pool: np.ndarray, *, head_len: int = 6) -> np.ndarray:
    coeffs = np.zeros((pool.shape[0], oracle.SURFACE_COEFF_COLUMNS), dtype=np.uint16)
    sigma_total = head_len * (head_len + 1) // 2
    for row_idx in range(pool.shape[0]):
        fever_positions = [
            block * 32 + bit
            for block in range(4)
            for bit in range(32)
            if block * 32 + bit < head_len and int(pool[row_idx, block]) & (1 << bit)
        ]
        fever_count = len(fever_positions)
        fever_sigma = sum(position + 1 for position in fever_positions)
        coeffs[row_idx] = np.asarray(
            [head_len - fever_count, fever_count, sigma_total - fever_sigma, fever_sigma],
            dtype=np.uint16,
        )
    return coeffs


def _surface_arrays(row_count: int = 6) -> tuple[np.ndarray, np.ndarray]:
    pool = np.zeros((row_count, oracle.SURFACE_POOL_COLUMNS), dtype=np.uint32)
    fever_masks = (0b000000, 0b000001, 0b000011, 0b000101, 0b001111, 0b100000)
    great_masks = (0b000000, 0b000010, 0b000100, 0b001000, 0b010000, 0b100000)
    for row_idx in range(row_count):
        pool[row_idx, 0] = fever_masks[row_idx % len(fever_masks)]
        pool[row_idx, 4] = great_masks[row_idx % len(great_masks)]
    return pool, _derive_head_coeffs(pool)


def _write_bundle(
    path: Path,
    arrays: dict[str, np.ndarray],
    pool: np.ndarray,
    coeffs: np.ndarray,
    *,
    compression: int = zipfile.ZIP_DEFLATED,
    member_versions: dict[str, tuple[int, int]] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    versions = member_versions or {}
    with zipfile.ZipFile(path, mode="w", compression=compression) as archive:
        for name, array in arrays.items():
            archive.writestr(f"{name}.npy", _npy_bytes(array, version=versions.get(name)))
    stem = path.name[: -len(".npz")]
    path.with_name(f"{stem}.surf_pool.npy").write_bytes(_npy_bytes(pool))
    path.with_name(f"{stem}.surf_coeffs.npy").write_bytes(_npy_bytes(coeffs))


@dataclass
class BundlePair:
    baseline: Path
    candidate: Path
    baseline_arrays: dict[str, np.ndarray]
    candidate_arrays: dict[str, np.ndarray]
    pool: np.ndarray
    coeffs: np.ndarray

    def write_baseline(
        self,
        *,
        pool: np.ndarray | None = None,
        coeffs: np.ndarray | None = None,
    ) -> None:
        _write_bundle(
            self.baseline,
            self.baseline_arrays,
            self.pool if pool is None else pool,
            self.coeffs if coeffs is None else coeffs,
        )

    def write_candidate(
        self,
        *,
        compression: int = zipfile.ZIP_DEFLATED,
        member_versions: dict[str, tuple[int, int]] | None = None,
        pool: np.ndarray | None = None,
        coeffs: np.ndarray | None = None,
    ) -> None:
        _write_bundle(
            self.candidate,
            self.candidate_arrays,
            self.pool if pool is None else pool,
            self.coeffs if coeffs is None else coeffs,
            compression=compression,
            member_versions=member_versions,
        )

    def write_both(
        self,
        *,
        pool: np.ndarray | None = None,
        coeffs: np.ndarray | None = None,
    ) -> None:
        self.write_baseline(pool=pool, coeffs=coeffs)
        self.write_candidate(pool=pool, coeffs=coeffs)


@pytest.fixture
def bundle_pair(tmp_path: Path) -> BundlePair:
    pool, coeffs = _surface_arrays()
    baseline_arrays = _canonical_arrays(BASELINE_VERSION)
    candidate_arrays = _canonical_arrays(CANDIDATE_VERSION)
    baseline = tmp_path / "baseline" / "baseline.npz"
    candidate = tmp_path / "candidate" / "candidate.npz"
    _write_bundle(baseline, baseline_arrays, pool, coeffs)
    _write_bundle(candidate, candidate_arrays, pool, coeffs)
    return BundlePair(
        baseline=baseline,
        candidate=candidate,
        baseline_arrays=baseline_arrays,
        candidate_arrays=candidate_arrays,
        pool=pool,
        coeffs=coeffs,
    )


def _run_cli(
    pair: BundlePair,
    output: Path,
    *,
    baseline: Path | None = None,
    candidate: Path | None = None,
    baseline_version: str = BASELINE_VERSION,
    candidate_version: str = CANDIDATE_VERSION,
) -> int:
    return oracle.main(
        [
            "--baseline",
            str(pair.baseline if baseline is None else baseline),
            "--candidate",
            str(pair.candidate if candidate is None else candidate),
            "--baseline-version",
            baseline_version,
            "--candidate-version",
            candidate_version,
            "--json-out",
            str(output),
        ]
    )


def _invoke(
    pair: BundlePair,
    output: Path,
    **kwargs,
) -> tuple[int, dict]:
    result = _run_cli(pair, output, **kwargs)
    return result, json.loads(output.read_text(encoding="utf-8"))


def _rewrite_archive(
    path: Path,
    *,
    omit: set[str] | None = None,
    replacements: dict[str, bytes] | None = None,
    extra: list[tuple[str, bytes]] | None = None,
) -> None:
    omitted = omit or set()
    replaced = replacements or {}
    additions = extra or []
    with zipfile.ZipFile(path, mode="r") as source:
        rows = [(info.filename, source.read(info)) for info in source.infolist()]
    tmp = path.with_suffix(".rewrite.npz")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(tmp, mode="w", compression=zipfile.ZIP_DEFLATED) as target:
            for name, raw in rows:
                if name not in omitted:
                    target.writestr(name, replaced.get(name, raw))
            for name, raw in additions:
                target.writestr(name, raw)
    os.replace(tmp, path)


def _corrupt_stored_member_crc(path: Path, member_name: str) -> None:
    with zipfile.ZipFile(path, mode="r") as archive:
        info = archive.getinfo(member_name)
        assert info.compress_type == zipfile.ZIP_STORED
    raw = bytearray(path.read_bytes())
    filename_len, extra_len = struct.unpack_from("<HH", raw, info.header_offset + 26)
    payload_offset = info.header_offset + 30 + filename_len + extra_len
    raw[payload_offset + info.compress_size - 1] ^= 0x01
    path.write_bytes(raw)


def test_byte_oracle_passes_exact_pair_and_emits_stable_json(bundle_pair: BundlePair, tmp_path: Path) -> None:
    assert set(bundle_pair.baseline_arrays["first_offsets"].tolist()) == {0, 2, 4}
    assert len(np.unique(bundle_pair.pool, axis=0)) == bundle_pair.pool.shape[0]
    assert bundle_pair.coeffs[0].tolist() == [6, 0, 21, 0]
    first_rc, first = _invoke(bundle_pair, tmp_path / "first.json")
    second_rc, second = _invoke(bundle_pair, tmp_path / "second.json")

    assert first_rc == second_rc == 0
    assert first == second
    assert first["ok"] is True
    assert first["comparison"]["resolutions"]["keys_compared"] == oracle.STAT_KEY_COUNT
    assert first["comparison"]["semantic_bundle"]["equal"] is True
    assert first["parity_scope"]["explicit_witness_fields"] == "not_persisted_requires_trace_oracle"
    assert first["parity_scope"]["selected_score"] == "not_computable_from_bundle_alone"


def test_committed_production_serializer_full_grid_canary_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _fg_response_disk_cache_path
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import _save_payload
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import (
        FgResponseFrontierCachePayload,
        _FG_RESPONSE_CACHE_VERSION,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    cache_dir = tmp_path / "production-serializer"
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(cache_dir))
    raw_fill = np.arange(oracle.STAT_AXIS, dtype=np.float64)
    non_fever_base = np.ceil(raw_fill).astype(np.int32)
    empty_surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    frontiers = tuple(
        FgResponseFrontierResult(
            first_frontier=(empty_surface,),
            state_frontiers={},
            states_evaluated=1,
            actions=2,
            transitions_evaluated=3,
            generated_surfaces=4,
            retained_surfaces_total=5,
            max_state_frontier=6,
            non_fever_base=int(non_fever_base[ff]),
            seconds=0.0,
        )
        for ff in range(oracle.STAT_AXIS)
    )
    payload = FgResponseFrontierCachePayload(
        frontier_by_key={
            (ft, ff): frontiers[ff]
            for ft in range(oracle.STAT_AXIS)
            for ff in range(oracle.STAT_AXIS)
        },
        raw_fill_by_ff=raw_fill,
        non_fever_base_by_ff=non_fever_base,
        real_time_by_ft=np.linspace(1.0, 2.0, oracle.STAT_AXIS, dtype=np.float64),
        total_notes=6,
        long_notes=1,
        use_forced_great_timing=True,
    )
    baseline_key = ("byte-oracle-canary", "baseline")
    candidate_key = ("byte-oracle-canary", "candidate")
    _save_payload(baseline_key, payload)
    _save_payload(candidate_key, payload)
    pair = BundlePair(
        baseline=_fg_response_disk_cache_path(baseline_key),
        candidate=_fg_response_disk_cache_path(candidate_key),
        baseline_arrays={},
        candidate_arrays={},
        pool=np.empty((0, 0)),
        coeffs=np.empty((0, 0)),
    )

    from tools.verify import compare_fg_response_cache_logical_bundles as logical_oracle

    report = logical_oracle.compare(
        pair.baseline,
        pair.candidate,
        baseline_version=_FG_RESPONSE_CACHE_VERSION,
        candidate_version=_FG_RESPONSE_CACHE_VERSION,
    )

    assert report["comparison"]["resolutions"]["equal"] is True
    assert report["comparison"]["logical"]["equal"] is True


def test_byte_oracle_accepts_cross_word_one_indexed_head_coefficients(
    bundle_pair: BundlePair,
    tmp_path: Path,
) -> None:
    pool = bundle_pair.pool.copy()
    pool[0, :4] = 0
    pool[0, 0] = np.uint32(1 << 31)
    pool[0, 1] = np.uint32(1)
    coeffs = _derive_head_coeffs(pool, head_len=40)
    for arrays in (bundle_pair.baseline_arrays, bundle_pair.candidate_arrays):
        arrays["total_notes"] = np.asarray(40, dtype=np.int32)
        arrays["first_surface_head_len"] = np.asarray(40, dtype=np.uint8)
    bundle_pair.write_both(pool=pool, coeffs=coeffs)

    rc, report = _invoke(bundle_pair, tmp_path / "cross-word-coeffs.json")

    assert coeffs[0].tolist() == [38, 2, 755, 65]
    assert rc == 0
    assert report["ok"] is True


def test_byte_oracle_accepts_frontier_id_permutation(bundle_pair: BundlePair, tmp_path: Path) -> None:
    permutation = np.roll(np.arange(oracle.STAT_AXIS, dtype=np.int32), 1)
    inverse = np.empty_like(permutation)
    inverse[permutation] = np.arange(permutation.shape[0], dtype=np.int32)
    base = bundle_pair.baseline_arrays
    candidate = bundle_pair.candidate_arrays
    candidate["frontier_meta"] = np.asfortranarray(base["frontier_meta"][permutation])
    candidate["first_offsets"] = base["first_offsets"][permutation]
    candidate["first_counts"] = base["first_counts"][permutation]
    candidate["frontier_ids"] = inverse[base["frontier_ids"]]
    bundle_pair.write_candidate()

    rc, report = _invoke(bundle_pair, tmp_path / "permuted.json")

    assert rc == 0
    assert report["comparison"]["resolutions"]["equal"] is True


def test_byte_oracle_accepts_semantic_indirection_compaction(tmp_path: Path) -> None:
    pool, coeffs = _surface_arrays(row_count=2)
    baseline_ids = np.arange(oracle.STAT_KEY_COUNT, dtype=np.int32) % 3
    baseline_meta = np.asfortranarray(
        np.asarray(
            [
                [10, 11, 12, 13, 14, 15, 0],
                [10, 11, 12, 13, 14, 15, 0],
                [10, 11, 12, 13, 14, 15, 0],
            ],
            dtype=np.int32,
        )
    )
    baseline_arrays = _canonical_arrays(
        BASELINE_VERSION,
        frontier_ids=baseline_ids,
        frontier_meta=baseline_meta,
        first_offsets=np.asarray([0, 0, 0], dtype=np.int32),
        first_counts=np.asarray([2, 2, 2], dtype=np.int32),
        surface_row_count=2,
    )
    candidate_ids = np.zeros_like(baseline_ids)
    candidate_arrays = _canonical_arrays(
        CANDIDATE_VERSION,
        frontier_ids=candidate_ids,
        frontier_meta=np.asfortranarray(baseline_meta[[0]]),
        first_offsets=np.asarray([0], dtype=np.int32),
        first_counts=np.asarray([2], dtype=np.int32),
        surface_row_count=2,
    )
    for arrays in (baseline_arrays, candidate_arrays):
        arrays["raw_fill_by_ff"] = np.zeros((oracle.STAT_AXIS,), dtype=np.float64)
        arrays["non_fever_base_by_ff"] = np.zeros((oracle.STAT_AXIS,), dtype=np.int32)
    pair = BundlePair(
        baseline=tmp_path / "base" / "base.npz",
        candidate=tmp_path / "candidate" / "candidate.npz",
        baseline_arrays=baseline_arrays,
        candidate_arrays=candidate_arrays,
        pool=pool,
        coeffs=coeffs,
    )
    _write_bundle(pair.baseline, baseline_arrays, pool, coeffs)
    pair.write_candidate()

    rc, report = _invoke(pair, tmp_path / "compacted.json")

    assert rc == 0
    assert report["comparison"]["candidate_frontier_delta"] == -2


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("pool", "surface_pool_bytes_mismatch"),
        ("coeffs", "surface_coeff_bytes_mismatch"),
        ("npz_member", "npz_member_bytes_mismatch"),
        ("npz_header", "npz_member_bytes_mismatch"),
    ],
)
def test_byte_oracle_rejects_raw_byte_mismatches(
    bundle_pair: BundlePair,
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    if mutation == "pool":
        bundle_pair.candidate.with_name("candidate.surf_pool.npy").write_bytes(
            _npy_bytes(bundle_pair.pool, version=(2, 0))
        )
    elif mutation == "coeffs":
        bundle_pair.candidate.with_name("candidate.surf_coeffs.npy").write_bytes(
            _npy_bytes(bundle_pair.coeffs, version=(2, 0))
        )
    elif mutation == "npz_member":
        bundle_pair.candidate_arrays["long_notes"] = np.asarray(2, dtype=np.int32)
        bundle_pair.write_candidate()
    elif mutation == "npz_header":
        bundle_pair.write_candidate(member_versions={"raw_fill_by_ff": (2, 0)})
    else:
        raise AssertionError(f"unknown mutation: {mutation}")

    rc, report = _invoke(bundle_pair, tmp_path / f"{mutation}.json")
    repeat_rc, repeated = _invoke(bundle_pair, tmp_path / f"{mutation}-repeat.json")

    assert rc == repeat_rc == 1
    assert report == repeated
    assert report["ok"] is False
    assert report["error"]["code"] == expected_code
    comparison = report["comparison"]
    assert set(comparison["surf_pool"]) >= {"equal", "left_sha256", "right_sha256"}
    assert set(comparison["surf_coeffs"]) >= {"equal", "left_sha256", "right_sha256"}
    assert comparison["resolutions"]["keys_compared"] == oracle.STAT_KEY_COUNT
    assert set(comparison["semantic_bundle"]) == {
        "baseline_sha256",
        "candidate_sha256",
        "equal",
    }
    assert "raw_member_mismatches" in comparison
    assert report["schema"] == "fg-response-cache-byte-oracle/v1"
    assert report["parity_scope"]["selected_score"] == "not_computable_from_bundle_alone"


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("missing", "npz_member_set_mismatch"),
        ("extra", "npz_member_set_mismatch"),
        ("non_npy", "non_npy_npz_member"),
        ("duplicate", "duplicate_npz_member"),
        ("malformed_zip", "malformed_npz"),
        ("zip_prefix", "prepended_zip_bytes"),
        ("zip_junk", "trailing_zip_bytes"),
        ("malformed_npy", "malformed_npy"),
        ("trailing_npy", "npy_size_mismatch"),
        ("object_npy", "object_npy"),
        ("oversized_member", "npz_member_too_large"),
        ("crc", "npz_member_read_failed"),
    ],
)
def test_byte_oracle_rejects_malformed_npz_contracts(
    bundle_pair: BundlePair,
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    candidate = bundle_pair.candidate
    if mutation == "missing":
        _rewrite_archive(candidate, omit={"raw_fill_by_ff.npy"})
    elif mutation == "extra":
        _rewrite_archive(candidate, extra=[("obsolete.npy", _npy_bytes(np.asarray(1)))])
    elif mutation == "non_npy":
        _rewrite_archive(candidate, extra=[("README.txt", b"not an array")])
    elif mutation == "duplicate":
        with zipfile.ZipFile(candidate, mode="r") as archive:
            duplicate = archive.read("stat_keys.npy")
        _rewrite_archive(candidate, extra=[("stat_keys.npy", duplicate)])
    elif mutation == "malformed_zip":
        candidate.write_bytes(b"not a zip file")
    elif mutation == "zip_prefix":
        candidate.write_bytes(b"PREPENDED-JUNK" + candidate.read_bytes())
    elif mutation == "zip_junk":
        candidate.write_bytes(candidate.read_bytes() + b"junk outside archive")
    elif mutation == "malformed_npy":
        _rewrite_archive(candidate, replacements={"stat_keys.npy": b"not an npy"})
    elif mutation == "trailing_npy":
        with zipfile.ZipFile(candidate, mode="r") as archive:
            raw = archive.read("raw_fill_by_ff.npy")
        _rewrite_archive(candidate, replacements={"raw_fill_by_ff.npy": raw + b"trailing"})
    elif mutation == "object_npy":
        raw = _npy_bytes(np.asarray([object()], dtype=object), allow_pickle=True)
        _rewrite_archive(candidate, replacements={"raw_fill_by_ff.npy": raw})
    elif mutation == "oversized_member":
        _rewrite_archive(
            candidate,
            replacements={"raw_fill_by_ff.npy": b"x" * (oracle.MAX_NPZ_MEMBER_BYTES + 1)},
        )
    elif mutation == "crc":
        bundle_pair.write_candidate(compression=zipfile.ZIP_STORED)
        _corrupt_stored_member_crc(candidate, "raw_fill_by_ff.npy")
    else:
        raise AssertionError(f"unknown mutation: {mutation}")

    rc, report = _invoke(bundle_pair, tmp_path / f"malformed-{mutation}.json")

    assert rc == 2
    assert report["error"]["code"] == expected_code


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("missing", "missing_cache_file"),
        ("dtype", "sidecar_schema_mismatch"),
        ("shape", "sidecar_schema_mismatch"),
        ("fortran", "sidecar_schema_mismatch"),
        ("trailing", "sidecar_size_mismatch"),
    ],
)
def test_byte_oracle_rejects_bad_sidecars(
    bundle_pair: BundlePair,
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    pool_path = bundle_pair.candidate.with_name("candidate.surf_pool.npy")
    if mutation == "missing":
        pool_path.unlink()
    elif mutation == "dtype":
        pool_path.write_bytes(_npy_bytes(bundle_pair.pool.astype(np.int32)))
    elif mutation == "shape":
        pool_path.write_bytes(_npy_bytes(bundle_pair.pool[:, :-1]))
    elif mutation == "fortran":
        pool_path.write_bytes(_npy_bytes(np.asfortranarray(bundle_pair.pool)))
    elif mutation == "trailing":
        pool_path.write_bytes(pool_path.read_bytes() + b"trailing")
    else:
        raise AssertionError(f"unknown mutation: {mutation}")

    rc, report = _invoke(bundle_pair, tmp_path / f"sidecar-{mutation}.json")

    assert rc == 2
    assert report["error"]["code"] == expected_code


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("coeff", "surface_coeff_mismatch"),
        ("fever_head_bit", "surface_head_mask_out_of_range"),
        ("great_head_bit", "surface_head_mask_out_of_range"),
        ("body_union", "surface_body_counts_invalid"),
        ("body_overlap", "surface_body_counts_invalid"),
    ],
)
def test_byte_oracle_rejects_equally_invalid_surface_semantics(
    bundle_pair: BundlePair,
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    pool = bundle_pair.pool.copy()
    coeffs = bundle_pair.coeffs.copy()
    if mutation == "coeff":
        coeffs[0] = 0
    elif mutation == "fever_head_bit":
        pool[0, 0] |= np.uint32(1 << 6)
    elif mutation == "great_head_bit":
        pool[0, 4] |= np.uint32(1 << 6)
    elif mutation == "body_union":
        pool[0, 8] = 1
    elif mutation == "body_overlap":
        pool[0, 10] = 1
    else:
        raise AssertionError(f"unknown mutation: {mutation}")
    bundle_pair.write_both(pool=pool, coeffs=coeffs)

    rc, report = _invoke(bundle_pair, tmp_path / f"surface-{mutation}.json")

    assert rc == 2
    assert report["error"]["code"] == expected_code


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("duplicate", "duplicate_stat_key"),
        ("out_of_range", "stat_key_out_of_range"),
        ("reordered", "stat_key_order_mismatch"),
        ("missing", "npz_member_schema_mismatch"),
        ("dtype", "npz_member_schema_mismatch"),
    ],
)
def test_byte_oracle_rejects_bad_stat_key_grids(
    bundle_pair: BundlePair,
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    keys = bundle_pair.candidate_arrays["stat_keys"]
    if mutation == "duplicate":
        keys[1] = keys[0]
    elif mutation == "out_of_range":
        keys[0, 0] = oracle.TOTAL_ROWS + 1
    elif mutation == "reordered":
        keys[[0, 1]] = keys[[1, 0]]
    elif mutation == "missing":
        bundle_pair.candidate_arrays["stat_keys"] = np.asfortranarray(keys[:-1])
    elif mutation == "dtype":
        bundle_pair.candidate_arrays["stat_keys"] = np.asfortranarray(keys.astype(np.int16))
    else:
        raise AssertionError(f"unknown mutation: {mutation}")
    bundle_pair.write_candidate()

    rc, report = _invoke(bundle_pair, tmp_path / f"stat-{mutation}.json")

    assert rc == 2
    assert report["error"]["code"] == expected_code


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("raw_nan", "invalid_raw_fill_axis"),
        ("raw_negative", "invalid_raw_fill_axis"),
        ("fill_ceil", "fill_axis_mismatch"),
        ("time_nan", "invalid_real_time_axis"),
        ("time_zero", "invalid_real_time_axis"),
        ("meta_negative", "negative_frontier_meta"),
        ("meta_non_fever", "frontier_non_fever_base_mismatch"),
    ],
)
def test_byte_oracle_rejects_equally_invalid_producer_state(
    bundle_pair: BundlePair,
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    for arrays in (bundle_pair.baseline_arrays, bundle_pair.candidate_arrays):
        if mutation == "raw_nan":
            arrays["raw_fill_by_ff"][0] = np.nan
        elif mutation == "raw_negative":
            arrays["raw_fill_by_ff"][0] = -0.25
        elif mutation == "fill_ceil":
            arrays["non_fever_base_by_ff"][0] += 1
        elif mutation == "time_nan":
            arrays["real_time_by_ft"][0] = np.nan
        elif mutation == "time_zero":
            arrays["real_time_by_ft"][0] = 0.0
        elif mutation == "meta_negative":
            arrays["frontier_meta"][0, 0] = -1
        elif mutation == "meta_non_fever":
            arrays["frontier_meta"][0, 6] += 1
        else:
            raise AssertionError(f"unknown mutation: {mutation}")
    bundle_pair.write_both()

    rc, report = _invoke(bundle_pair, tmp_path / f"invalid-{mutation}.json")

    assert rc == 2
    assert report["ok"] is False
    assert report["error"]["code"] == expected_code


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("negative_id", "frontier_id_out_of_range"),
        ("large_id", "frontier_id_out_of_range"),
        ("unreferenced_id", "unreferenced_frontier_id"),
        ("id_dtype", "npz_member_schema_mismatch"),
        ("negative_offset", "invalid_frontier_range"),
        ("zero_count", "invalid_frontier_range"),
        ("range_end", "invalid_frontier_range"),
        ("meta_shape", "frontier_meta_schema_mismatch"),
    ],
)
def test_byte_oracle_rejects_bad_indirection(
    bundle_pair: BundlePair,
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    arrays = bundle_pair.candidate_arrays
    if mutation == "negative_id":
        arrays["frontier_ids"][0] = -1
    elif mutation == "large_id":
        arrays["frontier_ids"][0] = arrays["frontier_meta"].shape[0]
    elif mutation == "unreferenced_id":
        arrays["frontier_meta"] = np.asfortranarray(
            np.vstack((arrays["frontier_meta"], arrays["frontier_meta"][0]))
        )
        arrays["first_offsets"] = np.append(arrays["first_offsets"], 0).astype(np.int32)
        arrays["first_counts"] = np.append(arrays["first_counts"], 1).astype(np.int32)
    elif mutation == "id_dtype":
        arrays["frontier_ids"] = arrays["frontier_ids"].astype(np.int64)
    elif mutation == "negative_offset":
        arrays["first_offsets"][0] = -1
    elif mutation == "zero_count":
        arrays["first_counts"][0] = 0
    elif mutation == "range_end":
        arrays["first_offsets"][2] = 5
    elif mutation == "meta_shape":
        arrays["frontier_meta"] = np.asfortranarray(arrays["frontier_meta"][:, :-1])
    else:
        raise AssertionError(f"unknown mutation: {mutation}")
    bundle_pair.write_candidate()

    rc, report = _invoke(bundle_pair, tmp_path / f"indirection-{mutation}.json")

    assert rc == 2
    assert report["error"]["code"] == expected_code


@pytest.mark.parametrize(
    ("mutation", "row_count", "expected_code"),
    [
        ("gap", 6, "surface_segment_gap"),
        ("overlap", 6, "surface_segment_overlap"),
        ("unreachable", 7, "unreachable_surface_rows"),
    ],
)
def test_byte_oracle_rejects_nonpartitioned_surface_segments(
    bundle_pair: BundlePair,
    tmp_path: Path,
    mutation: str,
    row_count: int,
    expected_code: str,
) -> None:
    for arrays in (bundle_pair.baseline_arrays, bundle_pair.candidate_arrays):
        arrays["first_surface_row_count"] = np.asarray(row_count, dtype=np.int64)
        if mutation == "gap":
            arrays["first_offsets"][arrays["first_offsets"] == 2] = 3
        elif mutation == "overlap":
            arrays["first_offsets"][arrays["first_offsets"] == 2] = 1
        elif mutation != "unreachable":
            raise AssertionError(f"unknown mutation: {mutation}")
    pool, coeffs = _surface_arrays(row_count=row_count)
    bundle_pair.write_both(pool=pool, coeffs=coeffs)

    rc, report = _invoke(bundle_pair, tmp_path / f"partition-{mutation}.json")

    assert rc == 2
    assert report["error"]["code"] == expected_code


def test_byte_oracle_rejects_per_key_semantic_drift(bundle_pair: BundlePair, tmp_path: Path) -> None:
    bundle_pair.candidate_arrays["frontier_meta"][0, 0] += 1
    bundle_pair.write_candidate()

    rc, report = _invoke(bundle_pair, tmp_path / "semantic-drift.json")

    assert rc == 1
    assert report["error"]["code"] == "stat_resolution_mismatch"
    assert report["error"]["details"]["first_mismatch"]["stat_key"] == [0, 0]


def test_byte_oracle_accepts_semantically_identical_indirection_growth(
    bundle_pair: BundlePair,
    tmp_path: Path,
) -> None:
    arrays = bundle_pair.candidate_arrays
    old_ids = arrays["frontier_ids"]
    new_id = int(arrays["frontier_meta"].shape[0])
    split = (old_ids == 0) & ((np.arange(oracle.STAT_KEY_COUNT) % 2) == 0)
    arrays["frontier_ids"] = np.where(split, new_id, old_ids).astype(np.int32)
    arrays["frontier_meta"] = np.asfortranarray(np.vstack((arrays["frontier_meta"], arrays["frontier_meta"][0])))
    arrays["first_offsets"] = np.append(arrays["first_offsets"], arrays["first_offsets"][0]).astype(np.int32)
    arrays["first_counts"] = np.append(arrays["first_counts"], arrays["first_counts"][0]).astype(np.int32)
    bundle_pair.write_candidate()

    rc, report = _invoke(bundle_pair, tmp_path / "growth.json")

    assert rc == 0
    assert report["comparison"]["candidate_frontier_delta"] == 1
    assert report["comparison"]["resolutions"]["equal"] is True


def test_byte_oracle_rejects_wrong_version_and_same_files(bundle_pair: BundlePair, tmp_path: Path) -> None:
    wrong_rc, wrong = _invoke(
        bundle_pair,
        tmp_path / "wrong-version.json",
        candidate_version="not-the-candidate-version",
    )
    same_rc, same = _invoke(
        bundle_pair,
        tmp_path / "same-file.json",
        candidate=bundle_pair.baseline,
        candidate_version=BASELINE_VERSION,
    )

    assert wrong_rc == 2
    assert wrong["error"]["code"] == "cache_version_mismatch"
    assert same_rc == 2
    assert same["error"]["code"] == "same_cache_file"


def _prospective_test_paths(bundle: Path) -> tuple[Path, Path, Path]:
    stem = bundle.name[: -len(".npz")]
    return (
        bundle,
        bundle.with_name(f"{stem}.surf_pool.npy"),
        bundle.with_name(f"{stem}.surf_coeffs.npy"),
    )


def _input_artifact(pair: BundlePair, side: str, artifact: str) -> Path:
    bundle = pair.baseline if side == "baseline" else pair.candidate
    if artifact == "npz":
        return bundle
    return _prospective_test_paths(bundle)[1 if artifact == "pool" else 2]


@pytest.mark.parametrize("side", ["baseline", "candidate"])
@pytest.mark.parametrize("artifact", ["npz", "pool", "coeffs"])
@pytest.mark.parametrize("collision", ["equal", "hardlink"])
def test_json_output_never_overwrites_input_artifacts(
    bundle_pair: BundlePair,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    side: str,
    artifact: str,
    collision: str,
) -> None:
    target = _input_artifact(bundle_pair, side, artifact)
    before = target.read_bytes()
    output = target if collision == "equal" else tmp_path / f"{side}-{artifact}-hardlink.json"
    if collision == "hardlink":
        os.link(target, output)

    rc = _run_cli(bundle_pair, output)

    assert rc == 2
    assert "json_output_input_collision" in capsys.readouterr().err
    assert target.read_bytes() == before
    assert output.read_bytes() == before
    if collision == "hardlink":
        assert os.path.samefile(target, output)


@pytest.mark.parametrize("artifact", ["npz", "pool", "coeffs"])
def test_json_output_rejects_symlink_to_input(
    bundle_pair: BundlePair,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    artifact: str,
) -> None:
    target = _input_artifact(bundle_pair, "candidate", artifact)
    before = target.read_bytes()
    output = tmp_path / f"{artifact}-symlink.json"
    output.symlink_to(target)

    rc = _run_cli(bundle_pair, output)

    assert rc == 2
    assert "json_output_input_collision" in capsys.readouterr().err
    assert target.read_bytes() == before
    assert output.read_bytes() == before
    assert output.resolve(strict=True) == target.resolve(strict=True)


def test_json_write_permission_error_is_invalid_and_cleans_temp(
    bundle_pair: BundlePair,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "permission-error.json"
    before = {
        path: path.read_bytes()
        for path in (
            *_prospective_test_paths(bundle_pair.baseline),
            *_prospective_test_paths(bundle_pair.candidate),
        )
    }

    def _deny_replace(*_args, **_kwargs):
        raise PermissionError("output is read-only")

    monkeypatch.setattr(oracle.os, "replace", _deny_replace)

    rc = _run_cli(bundle_pair, output)

    assert rc == 2
    assert "json_write_failed" in capsys.readouterr().err
    assert not output.exists()
    assert not list(tmp_path.glob(".permission-error.json.*.tmp"))
    assert all(path.read_bytes() == content for path, content in before.items())


def test_success_publication_detects_candidate_mutation_and_replaces_result_with_invalid(
    bundle_pair: BundlePair,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "publication-race.json"
    real_replace = oracle.os.replace
    mutated = False

    def _mutate_at_publication(source, destination):
        nonlocal mutated
        if not mutated and Path(destination) == output:
            bundle_pair.candidate.write_bytes(bundle_pair.candidate.read_bytes() + b"corrupt-after-verify")
            mutated = True
        return real_replace(source, destination)

    monkeypatch.setattr(oracle.os, "replace", _mutate_at_publication)

    rc, report = _invoke(bundle_pair, output)
    stderr = capsys.readouterr().err

    assert mutated is True
    assert rc == 2
    assert "PASS:" not in stderr
    assert "input_changed" in stderr
    assert report["ok"] is False
    assert report["error"]["code"] == "input_changed"


def test_byte_oracle_rejects_production_cache_descendants(
    bundle_pair: BundlePair,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    linked_worktree = (tmp_path / "linked-worktree").resolve()
    primary_worktree = (tmp_path / "primary-worktree").resolve()
    primary_production = primary_worktree / "bin" / "fg_response_frontier_cache"
    linked_production = linked_worktree / "bin" / "fg_response_frontier_cache"
    assert primary_production != linked_production
    production_bundle = primary_production / "nested" / "production.npz"
    _write_bundle(
        production_bundle,
        bundle_pair.baseline_arrays,
        bundle_pair.pool,
        bundle_pair.coeffs,
    )
    monkeypatch.setattr(oracle, "REPO_ROOT", linked_worktree)
    monkeypatch.setattr(
        oracle,
        "resolve_production_fg_cache_dir",
        lambda worktree: primary_production if Path(worktree) == linked_worktree else None,
    )
    oracle._production_cache_dir.cache_clear()
    try:
        rc, report = _invoke(
            bundle_pair,
            tmp_path / "production-path.json",
            baseline=production_bundle,
        )
    finally:
        oracle._production_cache_dir.cache_clear()

    assert rc == 2
    assert report["error"]["code"] == "production_cache_path"
    assert report["error"]["details"]["production_cache"] == str(primary_production)


def test_byte_oracle_rejects_input_replaced_after_load(
    bundle_pair: BundlePair,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replacement = tmp_path / "candidate-replacement.npz"
    replacement.write_bytes(bundle_pair.candidate.read_bytes() + b"replacement")
    original_load = oracle._load_bundle

    def _load_then_replace(*args, **kwargs):
        loaded = original_load(*args, **kwargs)
        if kwargs["role"] == "candidate":
            os.replace(replacement, bundle_pair.candidate)
        return loaded

    monkeypatch.setattr(oracle, "_load_bundle", _load_then_replace)

    rc, report = _invoke(bundle_pair, tmp_path / "input-changed.json")

    assert rc == 2
    assert report["ok"] is False
    assert report["error"]["code"] == "input_changed"


def test_byte_oracle_does_not_swallow_unexpected_failures(
    bundle_pair: BundlePair,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _explode(*_args, **_kwargs):
        raise RuntimeError("unexpected verifier defect")

    monkeypatch.setattr(oracle, "compare_bundle_paths", _explode)

    with pytest.raises(RuntimeError, match="unexpected verifier defect"):
        _invoke(bundle_pair, tmp_path / "unexpected.json")
