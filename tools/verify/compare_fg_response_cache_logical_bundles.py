"""Compare expanded v29 and interned v30+ FG cache bundles without production loaders.

The physical sidecars intentionally differ. This oracle validates each format independently,
expands compact rows in bounded chunks, and requires exact ordered logical rows, coefficients,
common metadata bytes, and stat-key resolution semantics. Transactional compact bundles may name
their immutable sidecars with the UUID generation referenced by NPZ metadata; that generation is
physical publication identity, not logical frontier output.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.bench.issue116_run_preflight import resolve_production_fg_cache_dir  # noqa: E402


TOTAL_ROWS = 160
STAT_AXIS = TOTAL_ROWS + 1
STAT_KEY_COUNT = STAT_AXIS * STAT_AXIS
CHUNK_ROWS = 65536

COMMON_MEMBERS = frozenset(
    {
        "version",
        "stat_keys",
        "frontier_ids",
        "raw_fill_by_ff",
        "non_fever_base_by_ff",
        "real_time_by_ft",
        "total_notes",
        "long_notes",
        "use_forced_great_timing",
        "first_surface_head_len",
        "frontier_meta",
        "first_offsets",
        "first_counts",
        "first_surface_row_count",
    }
)
COMPACT_ONLY_MEMBERS = frozenset({"first_surface_pattern_count"})
TRANSACTIONAL_COMPACT_MEMBERS = frozenset({"surface_generation"})
INDIRECTION_MEMBERS = frozenset({"frontier_ids", "frontier_meta", "first_offsets", "first_counts"})
RAW_COMPARE_MEMBERS = COMMON_MEMBERS - {"version", *INDIRECTION_MEMBERS}


class OracleFailure(RuntimeError):
    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


@dataclass(slots=True)
class Bundle:
    npz_path: Path
    sidecar_paths: tuple[Path, Path]
    format: str
    version: str
    arrays: dict[str, np.ndarray]
    raw_members: dict[str, bytes]
    rows: np.ndarray
    patterns_or_coeffs: np.ndarray
    row_count: int
    pattern_count: int | None


def _is_at_or_beneath(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _resolve_input(path: str | Path) -> Path:
    try:
        resolved = Path(path).expanduser().resolve(strict=True)
    except OSError as exc:
        raise OracleFailure("missing_input", "cache bundle does not exist", path=str(path)) from exc
    if not resolved.is_file() or resolved.suffix != ".npz":
        raise OracleFailure("invalid_input", "cache bundle must be an NPZ file", path=str(resolved))
    production = resolve_production_fg_cache_dir(REPO_ROOT)
    if _is_at_or_beneath(resolved, production):
        raise OracleFailure(
            "production_cache_path",
            "logical oracle refuses to read the production FG cache",
            path=str(resolved),
            production_cache=str(production),
        )
    return resolved


def _read_npz(path: Path) -> tuple[dict[str, np.ndarray], dict[str, bytes]]:
    arrays: dict[str, np.ndarray] = {}
    raw: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            logical_names: set[str] = set()
            for info in infos:
                if info.is_dir() or "/" in info.filename or "\\" in info.filename or not info.filename.endswith(".npy"):
                    raise OracleFailure("invalid_npz_member", "bundle contains a non-NPY member", member=info.filename)
                name = info.filename[:-4]
                if name in logical_names:
                    raise OracleFailure("duplicate_npz_member", "bundle contains a duplicate member", member=name)
                logical_names.add(name)
                payload = archive.read(info)
                try:
                    array = np.load(io.BytesIO(payload), allow_pickle=False)
                except (ValueError, EOFError, OSError) as exc:
                    raise OracleFailure("invalid_npy_member", "bundle member is not a valid NPY array", member=name) from exc
                if not isinstance(array, np.ndarray) or array.dtype.hasobject:
                    raise OracleFailure("invalid_npy_member", "bundle member has an invalid dtype", member=name)
                arrays[name] = array
                raw[name] = payload
    except OracleFailure:
        raise
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        raise OracleFailure("invalid_npz", "bundle is not a readable NPZ archive", path=str(path)) from exc
    compact = "first_surface_pattern_count" in arrays
    expected = COMMON_MEMBERS | (COMPACT_ONLY_MEMBERS if compact else frozenset())
    allowed_sets = (expected, expected | TRANSACTIONAL_COMPACT_MEMBERS) if compact else (expected,)
    if set(arrays) not in allowed_sets:
        raise OracleFailure(
            "member_set_mismatch",
            "bundle member set does not match its physical format",
            extra=sorted(set(arrays) - expected),
            missing=sorted(expected - set(arrays)),
        )
    return arrays, raw


def _require_array(
    arrays: dict[str, np.ndarray],
    name: str,
    *,
    dtype: np.dtype | type,
    shape: tuple[int, ...],
) -> np.ndarray:
    value = arrays[name]
    if value.dtype != np.dtype(dtype) or value.shape != shape:
        raise OracleFailure(
            "member_schema_mismatch",
            "bundle member has the wrong dtype or shape",
            member=name,
            actual_dtype=value.dtype.str,
            actual_shape=list(value.shape),
            expected_dtype=np.dtype(dtype).str,
            expected_shape=list(shape),
        )
    return value


def _load_sidecar(path: Path, *, dtype: np.dtype | type, shape: tuple[int, int]) -> np.ndarray:
    if not path.is_file():
        raise OracleFailure("missing_sidecar", "bundle sidecar is missing", path=str(path))
    try:
        value = np.load(path, mmap_mode="r", allow_pickle=False)
    except (ValueError, OSError) as exc:
        raise OracleFailure("invalid_sidecar", "bundle sidecar is not a readable NPY array", path=str(path)) from exc
    if value.dtype != np.dtype(dtype) or value.shape != shape or not value.flags.c_contiguous:
        raise OracleFailure(
            "sidecar_schema_mismatch",
            "bundle sidecar has the wrong dtype, shape, or order",
            path=str(path),
            actual_dtype=value.dtype.str,
            actual_shape=list(value.shape),
            expected_dtype=np.dtype(dtype).str,
            expected_shape=list(shape),
        )
    return value


def _validate_stat_keys(stat_keys: np.ndarray) -> None:
    expected = np.asarray(
        [(ft, ff) for ft in range(STAT_AXIS) for ff in range(STAT_AXIS)],
        dtype=np.uint8,
    )
    if not np.array_equal(stat_keys, expected):
        raise OracleFailure("stat_key_order_mismatch", "bundle does not contain the canonical full stat-key grid")


def _validate_frontier_ranges(arrays: dict[str, np.ndarray], row_count: int) -> None:
    meta = arrays["frontier_meta"]
    frontier_count = int(meta.shape[0])
    if meta.dtype != np.dtype(np.int32) or meta.ndim != 2 or meta.shape[1] != 7 or frontier_count <= 0:
        raise OracleFailure("frontier_meta_schema", "frontier metadata has an invalid schema")
    offsets = _require_array(arrays, "first_offsets", dtype=np.int32, shape=(frontier_count,))
    counts = _require_array(arrays, "first_counts", dtype=np.int32, shape=(frontier_count,))
    frontier_ids = _require_array(arrays, "frontier_ids", dtype=np.int32, shape=(STAT_KEY_COUNT,))
    if bool(np.any(frontier_ids < 0)) or bool(np.any(frontier_ids >= frontier_count)):
        raise OracleFailure("invalid_frontier_id", "stat key references an invalid frontier")
    if bool(np.any(offsets < 0)) or bool(np.any(counts <= 0)) or bool(np.any(offsets.astype(np.int64) + counts > row_count)):
        raise OracleFailure("invalid_frontier_range", "frontier range is empty or outside the surface rows")
    segments = sorted({(int(offsets[idx]), int(counts[idx])) for idx in range(frontier_count)})
    cursor = 0
    for offset, count in segments:
        if offset != cursor:
            raise OracleFailure("surface_segment_layout", "unique surface segments overlap or leave a gap")
        cursor += count
    if cursor != row_count:
        raise OracleFailure("unreachable_surface_rows", "surface rows are not fully covered by frontier segments")


def _load_bundle(path_arg: str | Path, *, expected_version: str) -> Bundle:
    path = _resolve_input(path_arg)
    arrays, raw = _read_npz(path)
    version = str(np.asarray(arrays["version"]).item())
    if version != expected_version:
        raise OracleFailure(
            "version_mismatch",
            "bundle version does not match the expected commit",
            actual=version,
            expected=expected_version,
        )
    _require_array(arrays, "stat_keys", dtype=np.uint8, shape=(STAT_KEY_COUNT, 2))
    _validate_stat_keys(arrays["stat_keys"])
    _require_array(arrays, "raw_fill_by_ff", dtype=np.float64, shape=(STAT_AXIS,))
    _require_array(arrays, "non_fever_base_by_ff", dtype=np.int32, shape=(STAT_AXIS,))
    _require_array(arrays, "real_time_by_ft", dtype=np.float64, shape=(STAT_AXIS,))
    total_notes = int(_require_array(arrays, "total_notes", dtype=np.int32, shape=()).item())
    long_notes = int(_require_array(arrays, "long_notes", dtype=np.int32, shape=()).item())
    _require_array(arrays, "use_forced_great_timing", dtype=np.int8, shape=())
    head_len = int(_require_array(arrays, "first_surface_head_len", dtype=np.uint8, shape=()).item())
    row_count = int(_require_array(arrays, "first_surface_row_count", dtype=np.int64, shape=()).item())
    if total_notes < 0 or long_notes < 0 or long_notes > total_notes or head_len != min(total_notes, 100) or row_count <= 0:
        raise OracleFailure("invalid_bundle_scalars", "bundle scalar metadata is inconsistent")
    _validate_frontier_ranges(arrays, row_count)
    stem = path.name[:-4]
    compact = "first_surface_pattern_count" in arrays
    if compact:
        pattern_count = int(
            _require_array(arrays, "first_surface_pattern_count", dtype=np.int64, shape=()).item()
        )
        if pattern_count <= 0:
            raise OracleFailure("invalid_pattern_count", "compact bundle has no head patterns")
        surface_generation = None
        if "surface_generation" in arrays:
            generation_array = arrays["surface_generation"]
            if generation_array.shape != () or generation_array.dtype.kind != "U":
                raise OracleFailure(
                    "invalid_surface_generation",
                    "compact bundle has invalid surface-generation metadata",
                )
            raw_generation = generation_array.item()
            try:
                surface_generation = uuid.UUID(hex=str(raw_generation)).hex
            except (AttributeError, ValueError) as exc:
                raise OracleFailure(
                    "invalid_surface_generation",
                    "compact bundle has invalid surface-generation metadata",
                ) from exc
            if surface_generation != str(raw_generation):
                raise OracleFailure(
                    "invalid_surface_generation",
                    "compact bundle has non-canonical surface-generation metadata",
                )
        sidecar_stem = stem if surface_generation is None else f"{stem}.{surface_generation}"
        row_path = path.with_name(f"{sidecar_stem}.surf_rows.npy")
        pattern_path = path.with_name(f"{sidecar_stem}.surf_patterns.npy")
        rows = _load_sidecar(row_path, dtype=np.uint32, shape=(row_count, 4))
        patterns = _load_sidecar(pattern_path, dtype=np.uint32, shape=(pattern_count, 10))
        if bool(np.any(np.asarray(rows[:, 0], dtype=np.uint64) >= pattern_count)):
            raise OracleFailure("invalid_pattern_id", "compact surface row references an invalid pattern")
        return Bundle(path, (row_path, pattern_path), "interned-v30", version, arrays, raw, rows, patterns, row_count, pattern_count)
    pool_path = path.with_name(f"{stem}.surf_pool.npy")
    coeff_path = path.with_name(f"{stem}.surf_coeffs.npy")
    rows = _load_sidecar(pool_path, dtype=np.uint32, shape=(row_count, 11))
    coeffs = _load_sidecar(coeff_path, dtype=np.uint16, shape=(row_count, 4))
    return Bundle(path, (pool_path, coeff_path), "expanded-v29", version, arrays, raw, rows, coeffs, row_count, None)


def _logical_chunk(bundle: Bundle, start: int, stop: int) -> tuple[np.ndarray, np.ndarray]:
    if bundle.format == "expanded-v29":
        return (
            np.ascontiguousarray(bundle.rows[start:stop], dtype=np.uint32),
            np.ascontiguousarray(bundle.patterns_or_coeffs[start:stop], dtype=np.uint16),
        )
    refs = np.asarray(bundle.rows[start:stop], dtype=np.uint32)
    pattern_ids = np.asarray(refs[:, 0], dtype=np.intp)
    patterns = np.asarray(bundle.patterns_or_coeffs[pattern_ids], dtype=np.uint32)
    rows = np.empty((stop - start, 11), dtype=np.uint32)
    rows[:, :8] = patterns[:, :8]
    rows[:, 8:11] = refs[:, 1:4]
    coeffs = np.empty((stop - start, 4), dtype=np.uint16)
    coeffs[:, 0] = np.asarray(patterns[:, 8] & np.uint32(0xFFFF), dtype=np.uint16)
    coeffs[:, 1] = np.asarray(patterns[:, 8] >> np.uint32(16), dtype=np.uint16)
    coeffs[:, 2] = np.asarray(patterns[:, 9] & np.uint32(0xFFFF), dtype=np.uint16)
    coeffs[:, 3] = np.asarray(patterns[:, 9] >> np.uint32(16), dtype=np.uint16)
    return rows, coeffs


def _compare_logical_rows(baseline: Bundle, candidate: Bundle) -> dict[str, Any]:
    if baseline.row_count != candidate.row_count:
        raise OracleFailure(
            "surface_row_count_mismatch",
            "baseline and candidate surface row counts differ",
            baseline=baseline.row_count,
            candidate=candidate.row_count,
        )
    row_hash = hashlib.sha256(b"fg-logical-surface-rows-v2\0")
    coeff_hash = hashlib.sha256(b"fg-logical-surface-coeffs-v2\0")
    for start in range(0, baseline.row_count, CHUNK_ROWS):
        stop = min(baseline.row_count, start + CHUNK_ROWS)
        left_rows, left_coeffs = _logical_chunk(baseline, start, stop)
        right_rows, right_coeffs = _logical_chunk(candidate, start, stop)
        if not np.array_equal(left_rows, right_rows):
            mismatch = np.argwhere(left_rows != right_rows)[0]
            raise OracleFailure(
                "ordered_surface_mismatch",
                "expanded ordered surface rows differ",
                row=start + int(mismatch[0]),
                column=int(mismatch[1]),
            )
        if not np.array_equal(left_coeffs, right_coeffs):
            mismatch = np.argwhere(left_coeffs != right_coeffs)[0]
            raise OracleFailure(
                "surface_coefficient_mismatch",
                "expanded surface coefficients differ",
                row=start + int(mismatch[0]),
                column=int(mismatch[1]),
            )
        row_hash.update(left_rows.view(np.uint8))
        coeff_hash.update(left_coeffs.view(np.uint8))
    return {
        "equal": True,
        "rows": baseline.row_count,
        "ordered_rows_sha256": row_hash.hexdigest(),
        "coefficients_sha256": coeff_hash.hexdigest(),
    }


def _resolution(bundle: Bundle, row_idx: int) -> tuple[int, ...]:
    arrays = bundle.arrays
    frontier_id = int(arrays["frontier_ids"][row_idx])
    return (
        int(arrays["first_offsets"][frontier_id]),
        int(arrays["first_counts"][frontier_id]),
        *(int(value) for value in arrays["frontier_meta"][frontier_id]),
    )


def _compare_resolutions(baseline: Bundle, candidate: Bundle) -> dict[str, Any]:
    digest = hashlib.sha256(b"fg-stat-resolution-v2\0")
    for row_idx in range(STAT_KEY_COUNT):
        left = _resolution(baseline, row_idx)
        right = _resolution(candidate, row_idx)
        if left != right:
            raise OracleFailure(
                "stat_resolution_mismatch",
                "a stat key resolves to different frontier semantics",
                stat_key=[row_idx // STAT_AXIS, row_idx % STAT_AXIS],
                baseline=list(left),
                candidate=list(right),
            )
        digest.update(np.asarray(left, dtype=np.int64).tobytes())
    return {"equal": True, "keys": STAT_KEY_COUNT, "sha256": digest.hexdigest()}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compare_same_version_physical_bytes(baseline: Bundle, candidate: Bundle) -> dict[str, Any] | None:
    if baseline.format != candidate.format or baseline.version != candidate.version:
        return None
    compared_members = (set(baseline.raw_members) | set(candidate.raw_members)) - {"surface_generation"}
    for name in sorted(compared_members):
        if baseline.raw_members[name] != candidate.raw_members[name]:
            raise OracleFailure(
                "repeated_npz_member_mismatch",
                "same-version repeated build has a byte-different NPZ member",
                member=name,
            )
    sidecar_hashes: list[str] = []
    for sidecar_idx, (left, right) in enumerate(
        zip(baseline.sidecar_paths, candidate.sidecar_paths, strict=True)
    ):
        left_hash = _file_sha256(left)
        right_hash = _file_sha256(right)
        if left.stat().st_size != right.stat().st_size or left_hash != right_hash:
            raise OracleFailure(
                "repeated_sidecar_mismatch",
                "same-version repeated build has a byte-different sidecar",
                sidecar_index=int(sidecar_idx),
            )
        sidecar_hashes.append(left_hash)
    return {
        "equal": True,
        "npz_members": len(baseline.raw_members),
        "sidecar_sha256": sidecar_hashes,
    }


def compare(
    baseline_path: str | Path,
    candidate_path: str | Path,
    *,
    baseline_version: str,
    candidate_version: str,
) -> dict[str, Any]:
    baseline = _load_bundle(baseline_path, expected_version=baseline_version)
    candidate = _load_bundle(candidate_path, expected_version=candidate_version)
    mismatched_members = [
        name for name in sorted(RAW_COMPARE_MEMBERS) if baseline.raw_members[name] != candidate.raw_members[name]
    ]
    if mismatched_members:
        raise OracleFailure(
            "metadata_bytes_mismatch",
            "a common non-indirection metadata member differs byte-for-byte",
            member=mismatched_members[0],
        )
    logical = _compare_logical_rows(baseline, candidate)
    resolutions = _compare_resolutions(baseline, candidate)
    repeated_physical = _compare_same_version_physical_bytes(baseline, candidate)
    baseline_physical = sum(path.stat().st_size for path in baseline.sidecar_paths)
    candidate_physical = sum(path.stat().st_size for path in candidate.sidecar_paths)
    return {
        "ok": True,
        "schema": "fg-response-cache-logical-oracle/v2",
        "baseline": {
            "format": baseline.format,
            "path": str(baseline.npz_path),
            "sidecar_logical_bytes": baseline_physical,
            "version": baseline.version,
        },
        "candidate": {
            "format": candidate.format,
            "path": str(candidate.npz_path),
            "pattern_count": candidate.pattern_count,
            "sidecar_logical_bytes": candidate_physical,
            "version": candidate.version,
        },
        "comparison": {
            "common_metadata_bytes_equal": True,
            "logical": logical,
            "resolutions": resolutions,
            "same_version_physical_bytes": repeated_physical,
            "sidecar_logical_ratio": baseline_physical / candidate_physical,
        },
    }


def _write_json(path: Path, report: dict[str, Any], *, inputs: tuple[Path, Path]) -> None:
    output = path.expanduser().resolve(strict=False)
    production = resolve_production_fg_cache_dir(REPO_ROOT)
    if _is_at_or_beneath(output, production) or output in inputs:
        raise OracleFailure("invalid_json_output", "JSON output collides with protected cache input")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, allow_nan=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, output)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--baseline-version", required=True)
    parser.add_argument("--candidate-version", required=True)
    parser.add_argument("--json-out", required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        report = compare(
            args.baseline,
            args.candidate,
            baseline_version=args.baseline_version,
            candidate_version=args.candidate_version,
        )
        _write_json(
            Path(args.json_out),
            report,
            inputs=(Path(args.baseline).resolve(), Path(args.candidate).resolve()),
        )
    except OracleFailure as exc:
        print(f"FAIL [{exc.code}] {exc.message}", file=os.sys.stderr)
        return 1
    print(f"PASS: {STAT_KEY_COUNT} stat keys and ordered logical surfaces match", file=os.sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
