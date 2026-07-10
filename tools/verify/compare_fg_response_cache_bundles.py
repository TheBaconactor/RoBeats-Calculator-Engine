"""Compare two authoritative FG response-frontier cache bundles.

This verifier intentionally does not import the production cache loader.  The loader
normalizes and casts data and may delete malformed cache files; an oracle must instead
inspect the persisted ZIP/NPY representation independently and read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import struct
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from numpy.lib import format as np_format


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.bench.issue116_run_preflight import resolve_production_fg_cache_dir  # noqa: E402

TOTAL_ROWS = 160
STAT_AXIS = TOTAL_ROWS + 1
STAT_KEY_COUNT = STAT_AXIS * STAT_AXIS
SURFACE_POOL_COLUMNS = 11
SURFACE_COEFF_COLUMNS = 4
FRONTIER_META_COLUMNS = 7
STREAM_CHUNK_BYTES = 8 * 1024 * 1024
MAX_NPZ_MEMBER_BYTES = 2 * 1024 * 1024

EXPECTED_MEMBERS = frozenset(
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
INDIRECTION_MEMBERS = frozenset(
    {"frontier_ids", "frontier_meta", "first_offsets", "first_counts"}
)
RAW_COMPARE_EXEMPT_MEMBERS = frozenset({"version", *INDIRECTION_MEMBERS})
RAW_COMPARE_MEMBERS = EXPECTED_MEMBERS - RAW_COMPARE_EXEMPT_MEMBERS
FIXED_MEMBER_SCHEMAS = {
    "stat_keys": (np.dtype(np.uint8), (STAT_KEY_COUNT, 2), True),
    "frontier_ids": (np.dtype(np.int32), (STAT_KEY_COUNT,), False),
    "raw_fill_by_ff": (np.dtype(np.float64), (STAT_AXIS,), False),
    "non_fever_base_by_ff": (np.dtype(np.int32), (STAT_AXIS,), False),
    "real_time_by_ft": (np.dtype(np.float64), (STAT_AXIS,), False),
    "total_notes": (np.dtype(np.int32), (), False),
    "long_notes": (np.dtype(np.int32), (), False),
    "use_forced_great_timing": (np.dtype(np.int8), (), False),
    "first_surface_head_len": (np.dtype(np.uint8), (), False),
    "first_surface_row_count": (np.dtype(np.int64), (), False),
}

PARITY_SCOPE = {
    "explicit_witness_fields": "not_persisted_requires_trace_oracle",
    "head_coefficients": "checked",
    "ordered_surface_rows": "checked",
    "selected_score": "not_computable_from_bundle_alone",
    "surface_index_and_tie_order": "checked_as_ordered_rows",
}


class OracleFailure(Exception):
    exit_code: int
    kind: str

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)
        self.details = details


class BundleMismatch(OracleFailure):
    exit_code = 1
    kind = "mismatch"


class InvalidBundle(OracleFailure):
    exit_code = 2
    kind = "invalid_bundle"


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    path: Path
    device: int
    inode: int
    size: int
    mtime_ns: int

    def summary(self) -> dict[str, Any]:
        return {
            "bytes": self.size,
            "identity": [self.device, self.inode],
            "mtime_ns": self.mtime_ns,
            "path": str(self.path),
        }


@dataclass(frozen=True, slots=True)
class NpyMember:
    array: np.ndarray
    raw: bytes
    sha256: str
    npy_version: tuple[int, int]
    fortran_order: bool

    def summary(self) -> dict[str, Any]:
        return {
            "bytes": len(self.raw),
            "dtype": self.array.dtype.str,
            "fortran_order": bool(self.fortran_order),
            "npy_version": list(self.npy_version),
            "sha256": self.sha256,
            "shape": list(self.array.shape),
        }


@dataclass(frozen=True, slots=True)
class SidecarHeader:
    path: Path
    size: int
    shape: tuple[int, ...]
    dtype: np.dtype
    fortran_order: bool
    npy_version: tuple[int, int]
    data_offset: int

    def summary(self) -> dict[str, Any]:
        return {
            "bytes": int(self.size),
            "dtype": self.dtype.str,
            "data_offset": self.data_offset,
            "fortran_order": bool(self.fortran_order),
            "npy_version": list(self.npy_version),
            "path": str(self.path),
            "shape": list(self.shape),
        }


@dataclass(frozen=True, slots=True)
class Bundle:
    npz_path: Path
    pool_path: Path
    coeff_path: Path
    members: dict[str, NpyMember]
    npz_sha256: str
    version: str
    frontier_count: int
    surface_row_count: int
    pool_header: SidecarHeader
    coeff_header: SidecarHeader
    snapshots: tuple[FileSnapshot, FileSnapshot, FileSnapshot]

    @property
    def arrays(self) -> dict[str, np.ndarray]:
        return {name: member.array for name, member in self.members.items()}

    def summary(self) -> dict[str, Any]:
        npz_snapshot, pool_snapshot, coeff_snapshot = self.snapshots
        return {
            "files": {
                "npz": {
                    **npz_snapshot.summary(),
                    "sha256": self.npz_sha256,
                },
                "surf_coeffs": {**self.coeff_header.summary(), **coeff_snapshot.summary()},
                "surf_pool": {**self.pool_header.summary(), **pool_snapshot.summary()},
            },
            "frontier_count": int(self.frontier_count),
            "members": {
                name: self.members[name].summary() for name in sorted(self.members)
            },
            "stat_key_count": STAT_KEY_COUNT,
            "surface_row_count": int(self.surface_row_count),
            "version": self.version,
        }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(STREAM_CHUNK_BYTES):
                digest.update(chunk)
    except OSError as exc:
        raise InvalidBundle("file_read_failed", f"could not read cache file: {path}", path=str(path)) from exc
    return digest.hexdigest()


def _is_at_or_beneath(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


@lru_cache(maxsize=1)
def _production_cache_dir() -> Path:
    try:
        return resolve_production_fg_cache_dir(REPO_ROOT)
    except (OSError, ValueError, RuntimeError) as exc:
        raise InvalidBundle(
            "production_cache_resolution_failed",
            "could not unambiguously resolve the primary-worktree production FG cache",
            worktree_root=str(REPO_ROOT),
        ) from exc


def _reject_production_path(path: Path) -> None:
    production_cache = _production_cache_dir()
    if _is_at_or_beneath(path, production_cache):
        raise InvalidBundle(
            "production_cache_path",
            "the byte oracle refuses to access the primary-worktree production FG cache",
            path=str(path),
            production_cache=str(production_cache),
        )


def _resolve_existing_file(path: str | Path, *, role: str) -> Path:
    try:
        resolved = Path(path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise InvalidBundle(
            "missing_cache_file", f"{role} cache file does not exist", path=str(path), role=role
        ) from exc
    if not resolved.is_file():
        raise InvalidBundle(
            "cache_path_not_file", f"{role} cache path is not a file", path=str(resolved), role=role
        )
    _reject_production_path(resolved)
    return resolved


def _bundle_paths(npz_path: str | Path, *, role: str) -> tuple[Path, Path, Path]:
    npz = _resolve_existing_file(npz_path, role=f"{role} bundle")
    if npz.suffix != ".npz":
        raise InvalidBundle(
            "invalid_bundle_suffix", f"{role} bundle path must end in .npz", path=str(npz), role=role
        )
    stem = npz.name[: -len(".npz")]
    pool = _resolve_existing_file(
        npz.with_name(f"{stem}.surf_pool.npy"), role=f"{role} surface-pool sidecar"
    )
    coeff = _resolve_existing_file(
        npz.with_name(f"{stem}.surf_coeffs.npy"), role=f"{role} surface-coefficient sidecar"
    )
    return npz, pool, coeff


def _prospective_bundle_paths(npz_path: str | Path) -> tuple[Path, Path, Path]:
    source = Path(npz_path).expanduser()
    try:
        npz = source.resolve(strict=True)
    except (OSError, RuntimeError):
        npz = source.parent.resolve(strict=False) / source.name
    stem = npz.name[: -len(".npz")] if npz.suffix == ".npz" else npz.stem
    return (
        npz,
        npz.with_name(f"{stem}.surf_pool.npy"),
        npz.with_name(f"{stem}.surf_coeffs.npy"),
    )


def _snapshot_file(path: Path) -> FileSnapshot:
    try:
        stat = path.stat()
    except OSError as exc:
        raise InvalidBundle("input_snapshot_failed", "could not snapshot cache input", path=str(path)) from exc
    return FileSnapshot(
        path=path,
        device=int(stat.st_dev),
        inode=int(stat.st_ino),
        size=int(stat.st_size),
        mtime_ns=int(stat.st_mtime_ns),
    )


def _verify_snapshots(snapshots: Iterable[FileSnapshot]) -> None:
    for snapshot in snapshots:
        try:
            current = snapshot.path.stat()
            actual = (
                int(current.st_dev),
                int(current.st_ino),
                int(current.st_size),
                int(current.st_mtime_ns),
            )
        except OSError as exc:
            raise InvalidBundle(
                "input_changed",
                "cache input disappeared or became unreadable during verification",
                path=str(snapshot.path),
            ) from exc
        expected = (snapshot.device, snapshot.inode, snapshot.size, snapshot.mtime_ns)
        if actual != expected:
            raise InvalidBundle(
                "input_changed",
                "cache input identity, size, or mtime changed during verification",
                actual=list(actual),
                expected=list(expected),
                path=str(snapshot.path),
            )


def _read_npy_header(handle: Any, *, source: str) -> tuple[tuple[int, ...], bool, np.dtype, tuple[int, int]]:
    try:
        version = tuple(int(value) for value in np_format.read_magic(handle))
        if version == (1, 0):
            shape, fortran_order, dtype = np_format.read_array_header_1_0(handle)
        elif version == (2, 0):
            shape, fortran_order, dtype = np_format.read_array_header_2_0(handle)
        else:
            raise InvalidBundle(
                "unsupported_npy_version",
                "cache arrays must use the current NPY v1/v2 representation",
                source=source,
                npy_version=list(version),
            )
    except OracleFailure:
        raise
    except (EOFError, ValueError, OSError) as exc:
        raise InvalidBundle("malformed_npy", "cache array has a malformed NPY header", source=source) from exc
    dtype = np.dtype(dtype)
    normalized_shape = tuple(int(dim) for dim in shape)
    if any(dim < 0 for dim in normalized_shape):
        raise InvalidBundle("negative_npy_shape", "cache array has a negative dimension", source=source)
    if dtype.hasobject:
        raise InvalidBundle("object_npy", "object arrays are forbidden in FG cache bundles", source=source)
    return normalized_shape, bool(fortran_order), dtype, version


def _parse_npy_member(raw: bytes, *, source: str) -> NpyMember:
    header = io.BytesIO(raw)
    shape, fortran_order, dtype, version = _read_npy_header(header, source=source)
    expected_size = int(header.tell()) + math.prod(shape) * int(dtype.itemsize)
    if expected_size != len(raw):
        raise InvalidBundle(
            "npy_size_mismatch",
            "cache array is truncated or has trailing bytes",
            actual_bytes=len(raw),
            expected_bytes=expected_size,
            source=source,
        )
    payload = io.BytesIO(raw)
    try:
        array = np.load(payload, allow_pickle=False)
    except (EOFError, ValueError, OSError) as exc:
        raise InvalidBundle("malformed_npy", "cache array could not be decoded", source=source) from exc
    if not isinstance(array, np.ndarray):
        raise InvalidBundle("invalid_npy_payload", "cache member is not one NPY array", source=source)
    if payload.tell() != len(raw):
        raise InvalidBundle(
            "npy_trailing_bytes", "cache array decoder did not consume the complete member", source=source
        )
    if array.shape != shape or array.dtype != dtype:
        raise InvalidBundle("npy_header_drift", "decoded cache array disagrees with its NPY header", source=source)
    return NpyMember(
        array=array,
        raw=raw,
        sha256=hashlib.sha256(raw).hexdigest(),
        npy_version=version,
        fortran_order=fortran_order,
    )


def _validate_zip_termination(path: Path, *, file_size: int) -> None:
    tail_size = min(int(file_size), 22 + 65535)
    try:
        with path.open("rb") as handle:
            if handle.read(4) != b"PK\x03\x04":
                raise InvalidBundle(
                    "prepended_zip_bytes",
                    "FG cache NPZ must begin with its first ZIP local-file header at byte zero",
                    path=str(path),
                )
            handle.seek(int(file_size) - tail_size)
            tail = handle.read(tail_size)
    except OracleFailure:
        raise
    except OSError as exc:
        raise InvalidBundle("file_read_failed", "could not inspect FG cache ZIP termination", path=str(path)) from exc
    signature = b"PK\x05\x06"
    offset = tail.rfind(signature)
    while offset >= 0:
        if offset + 22 <= len(tail):
            comment_len = struct.unpack_from("<H", tail, offset + 20)[0]
            if offset + 22 + comment_len == len(tail):
                return
        offset = tail.rfind(signature, 0, offset)
    raise InvalidBundle(
        "trailing_zip_bytes",
        "FG cache NPZ has trailing bytes outside the committed ZIP archive",
        path=str(path),
    )


def _read_npz_members(path: Path, *, snapshot: FileSnapshot) -> dict[str, NpyMember]:
    try:
        with zipfile.ZipFile(path, mode="r") as archive:
            _validate_zip_termination(path, file_size=snapshot.size)
            infos = archive.infolist()
            if not infos or min(int(info.header_offset) for info in infos) != 0:
                raise InvalidBundle(
                    "prepended_zip_bytes",
                    "FG cache NPZ first ZIP local-file header is not at byte zero",
                    path=str(path),
                )
            by_name: dict[str, zipfile.ZipInfo] = {}
            for info in infos:
                archive_name = info.filename
                if (
                    info.is_dir()
                    or not archive_name.endswith(".npy")
                    or "/" in archive_name
                    or "\\" in archive_name
                ):
                    raise InvalidBundle(
                        "non_npy_npz_member",
                        "FG cache NPZ contains a directory, nested path, or non-NPY member",
                        member=archive_name,
                        path=str(path),
                    )
                logical_name = archive_name[: -len(".npy")]
                if logical_name in by_name:
                    raise InvalidBundle(
                        "duplicate_npz_member",
                        "FG cache NPZ contains a duplicate logical member",
                        member=logical_name,
                        path=str(path),
                    )
                if info.flag_bits & 0x1:
                    raise InvalidBundle(
                        "encrypted_npz_member",
                        "encrypted FG cache NPZ members are unsupported",
                        member=logical_name,
                        path=str(path),
                    )
                by_name[logical_name] = info

            names = set(by_name)
            missing = sorted(EXPECTED_MEMBERS - names)
            extra = sorted(names - EXPECTED_MEMBERS)
            if missing or extra:
                raise InvalidBundle(
                    "npz_member_set_mismatch",
                    "FG cache NPZ member set is not the exact current schema",
                    extra=extra,
                    missing=missing,
                    path=str(path),
                )

            members: dict[str, NpyMember] = {}
            for name in sorted(EXPECTED_MEMBERS):
                info = by_name[name]
                if int(info.file_size) > MAX_NPZ_MEMBER_BYTES:
                    raise InvalidBundle(
                        "npz_member_too_large",
                        "FG cache metadata member exceeds the full-grid schema bound",
                        bytes=int(info.file_size),
                        member=name,
                        path=str(path),
                    )
                try:
                    raw = archive.read(info)
                except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
                    raise InvalidBundle(
                        "npz_member_read_failed",
                        "FG cache NPZ member failed CRC/decompression/read validation",
                        member=name,
                        path=str(path),
                    ) from exc
                if len(raw) != int(info.file_size):
                    raise InvalidBundle(
                        "npz_member_size_mismatch",
                        "FG cache NPZ member size disagrees with its central-directory entry",
                        member=name,
                        path=str(path),
                    )
                members[name] = _parse_npy_member(raw, source=f"{path}!{name}.npy")
            return members
    except OracleFailure:
        raise
    except (zipfile.BadZipFile, OSError) as exc:
        raise InvalidBundle("malformed_npz", "FG cache bundle is not a readable NPZ", path=str(path)) from exc


def _require_member(
    members: dict[str, NpyMember],
    name: str,
    *,
    dtype: np.dtype | type,
    shape: tuple[int, ...],
    fortran_order: bool,
    path: Path,
) -> np.ndarray:
    member = members[name]
    array = member.array
    expected_dtype = np.dtype(dtype)
    if array.dtype != expected_dtype or array.shape != shape or member.fortran_order != bool(fortran_order):
        raise InvalidBundle(
            "npz_member_schema_mismatch",
            "FG cache member has an invalid dtype, shape, or storage order",
            actual={
                "dtype": array.dtype.str,
                "fortran_order": member.fortran_order,
                "shape": list(array.shape),
            },
            expected={
                "dtype": expected_dtype.str,
                "fortran_order": bool(fortran_order),
                "shape": list(shape),
            },
            member=name,
            path=str(path),
        )
    return array


def _validate_stat_keys(stat_keys: np.ndarray, *, path: Path) -> None:
    seen = bytearray(STAT_KEY_COUNT)
    first_order_mismatch: dict[str, Any] | None = None
    for row_idx in range(STAT_KEY_COUNT):
        ft = int(stat_keys[row_idx, 0])
        ff = int(stat_keys[row_idx, 1])
        if ft < 0 or ft > TOTAL_ROWS or ff < 0 or ff > TOTAL_ROWS:
            raise InvalidBundle(
                "stat_key_out_of_range",
                "FG cache contains an out-of-range stat key",
                key=[ft, ff],
                path=str(path),
                row=row_idx,
            )
        flat = ft * STAT_AXIS + ff
        if seen[flat]:
            raise InvalidBundle(
                "duplicate_stat_key",
                "FG cache contains a duplicate stat key",
                key=[ft, ff],
                path=str(path),
                row=row_idx,
            )
        seen[flat] = 1
        expected = (row_idx // STAT_AXIS, row_idx % STAT_AXIS)
        if first_order_mismatch is None and (ft, ff) != expected:
            first_order_mismatch = {"actual": [ft, ff], "expected": list(expected), "row": row_idx}
    try:
        missing_flat = seen.index(0)
    except ValueError:
        missing_flat = -1
    if missing_flat >= 0:
        raise InvalidBundle(
            "missing_stat_key",
            "FG cache is missing a canonical stat key",
            key=[missing_flat // STAT_AXIS, missing_flat % STAT_AXIS],
            path=str(path),
        )
    if first_order_mismatch is not None:
        raise InvalidBundle(
            "stat_key_order_mismatch",
            "FG cache stat keys are not in canonical FT-major order",
            path=str(path),
            **first_order_mismatch,
        )


def _validate_sidecar(
    path: Path,
    *,
    snapshot: FileSnapshot,
    expected_shape: tuple[int, int],
    expected_dtype: np.dtype | type,
) -> SidecarHeader:
    try:
        with path.open("rb") as handle:
            shape, fortran_order, dtype, version = _read_npy_header(handle, source=str(path))
            header_bytes = int(handle.tell())
    except OracleFailure:
        raise
    except OSError as exc:
        raise InvalidBundle("sidecar_read_failed", "FG cache sidecar could not be read", path=str(path)) from exc
    expected_size = header_bytes + math.prod(shape) * int(dtype.itemsize)
    if snapshot.size != expected_size:
        raise InvalidBundle(
            "sidecar_size_mismatch",
            "FG cache sidecar is truncated or has trailing bytes",
            actual_bytes=snapshot.size,
            expected_bytes=expected_size,
            path=str(path),
        )
    canonical_dtype = np.dtype(expected_dtype)
    if shape != expected_shape or dtype != canonical_dtype or fortran_order:
        raise InvalidBundle(
            "sidecar_schema_mismatch",
            "FG cache sidecar has an invalid dtype, shape, or storage order",
            actual={
                "dtype": dtype.str,
                "fortran_order": fortran_order,
                "shape": list(shape),
            },
            expected={
                "dtype": canonical_dtype.str,
                "fortran_order": False,
                "shape": list(expected_shape),
            },
            path=str(path),
        )
    return SidecarHeader(
        path=path,
        size=snapshot.size,
        shape=shape,
        dtype=dtype,
        fortran_order=fortran_order,
        npy_version=version,
        data_offset=header_bytes,
    )


@lru_cache(maxsize=1)
def _u16_head_tables() -> tuple[np.ndarray, np.ndarray]:
    counts = np.zeros((1 << 16,), dtype=np.uint8)
    position_sums = np.zeros((1 << 16,), dtype=np.uint16)
    for value in range(1, 1 << 16):
        low_bit = value & -value
        rest = value ^ low_bit
        counts[value] = counts[rest] + 1
        position_sums[value] = position_sums[rest] + low_bit.bit_length()
    return counts, position_sums


def _validate_surface_sidecars(
    pool_header: SidecarHeader,
    coeff_header: SidecarHeader,
    *,
    total_notes: int,
    head_len: int,
) -> None:
    pool_map = np.memmap(
        pool_header.path,
        mode="r",
        dtype=pool_header.dtype,
        offset=pool_header.data_offset,
        shape=pool_header.shape,
        order="C",
    )
    coeff_map = np.memmap(
        coeff_header.path,
        mode="r",
        dtype=coeff_header.dtype,
        offset=coeff_header.data_offset,
        shape=coeff_header.shape,
        order="C",
    )
    counts, position_sums = _u16_head_tables()
    body_total = int(total_notes) - int(head_len)
    sigma_total = int(head_len) * (int(head_len) + 1) // 2
    try:
        for start_row in range(0, int(pool_header.shape[0]), 32768):
            end_row = min(int(pool_header.shape[0]), start_row + 32768)
            pool = np.asarray(pool_map[start_row:end_row])
            coeffs = np.asarray(coeff_map[start_row:end_row])

            for block in range(4):
                take = max(0, min(32, int(head_len) - block * 32))
                allowed = np.uint32(0xFFFFFFFF if take == 32 else (1 << take) - 1)
                forbidden = np.uint32(~int(allowed) & 0xFFFFFFFF)
                for column, kind in ((block, "fever"), (4 + block, "great")):
                    bad = np.flatnonzero((pool[:, column] & forbidden) != 0)
                    if bad.size:
                        row = start_row + int(bad[0])
                        raise InvalidBundle(
                            "surface_head_mask_out_of_range",
                            "FG cache surface head mask sets a bit beyond first_surface_head_len",
                            block=block,
                            kind=kind,
                            path=str(pool_header.path),
                            row=row,
                        )

            body_fever = pool[:, 8].astype(np.uint64)
            body_great = pool[:, 9].astype(np.uint64)
            body_fever_great = pool[:, 10].astype(np.uint64)
            bad_body = np.flatnonzero(
                (body_fever_great > body_fever)
                | (body_fever_great > body_great)
                | (body_fever + body_great - body_fever_great > body_total)
            )
            if bad_body.size:
                local_row = int(bad_body[0])
                raise InvalidBundle(
                    "surface_body_counts_invalid",
                    "FG cache surface body counts violate overlap or body-size bounds",
                    body_fever=int(body_fever[local_row]),
                    body_fever_great=int(body_fever_great[local_row]),
                    body_great=int(body_great[local_row]),
                    body_total=body_total,
                    path=str(pool_header.path),
                    row=start_row + local_row,
                )

            fever_count = np.zeros((end_row - start_row,), dtype=np.int64)
            fever_sigma = np.zeros((end_row - start_row,), dtype=np.int64)
            for block in range(4):
                words = pool[:, block]
                low = np.asarray(words & np.uint32(0xFFFF), dtype=np.uint16)
                high = np.asarray(words >> np.uint32(16), dtype=np.uint16)
                low_count = counts[low].astype(np.int64)
                high_count = counts[high].astype(np.int64)
                block_count = low_count + high_count
                block_sigma = (
                    position_sums[low].astype(np.int64)
                    + position_sums[high].astype(np.int64)
                    + 16 * high_count
                    + (block * 32) * block_count
                )
                fever_count += block_count
                fever_sigma += block_sigma
            expected_columns = (
                int(head_len) - fever_count,
                fever_count,
                sigma_total - fever_sigma,
                fever_sigma,
            )
            bad_coeff: np.ndarray | None = None
            for column, expected in enumerate(expected_columns):
                mismatch = np.flatnonzero(coeffs[:, column].astype(np.int64) != expected)
                if mismatch.size:
                    bad_coeff = mismatch
                    break
            if bad_coeff is not None:
                local_row = int(bad_coeff[0])
                raise InvalidBundle(
                    "surface_coeff_mismatch",
                    "FG cache surface coefficients disagree with the persisted fever head masks",
                    actual=[int(value) for value in coeffs[local_row]],
                    expected=[int(values[local_row]) for values in expected_columns],
                    path=str(coeff_header.path),
                    row=start_row + local_row,
                )
    finally:
        pool_map._mmap.close()
        coeff_map._mmap.close()


def _load_bundle(
    paths: tuple[Path, Path, Path],
    snapshots: tuple[FileSnapshot, FileSnapshot, FileSnapshot],
    *,
    expected_version: str,
    role: str,
) -> Bundle:
    npz, pool, coeff = paths
    npz_snapshot, pool_snapshot, coeff_snapshot = snapshots
    members = _read_npz_members(npz, snapshot=npz_snapshot)

    version_member = members["version"]
    if version_member.array.shape != () or version_member.array.dtype.kind != "U" or version_member.fortran_order:
        raise InvalidBundle(
            "version_schema_mismatch",
            "FG cache version must be one scalar Unicode NPY value",
            path=str(npz),
            role=role,
        )
    actual_version = str(version_member.array.item())
    if actual_version != str(expected_version):
        raise InvalidBundle(
            "cache_version_mismatch",
            f"{role} FG cache version does not match the required version",
            actual=actual_version,
            expected=str(expected_version),
            path=str(npz),
            role=role,
        )

    fixed_arrays = {
        name: _require_member(
            members,
            name,
            dtype=dtype,
            shape=shape,
            fortran_order=fortran_order,
            path=npz,
        )
        for name, (dtype, shape, fortran_order) in FIXED_MEMBER_SCHEMAS.items()
    }
    stat_keys = fixed_arrays["stat_keys"]
    frontier_ids = fixed_arrays["frontier_ids"]

    meta_member = members["frontier_meta"]
    meta = meta_member.array
    # NumPy records a one-row array as C-order because it is simultaneously C/F-contiguous.
    if (
        meta.dtype != np.dtype(np.int32)
        or meta.ndim != 2
        or int(meta.shape[0]) <= 0
        or int(meta.shape[1]) != FRONTIER_META_COLUMNS
        or (not meta_member.fortran_order and int(meta.shape[0]) != 1)
    ):
        raise InvalidBundle(
            "frontier_meta_schema_mismatch",
            "FG cache frontier_meta must be nonempty column-major int32 M x 7",
            dtype=meta.dtype.str,
            fortran_order=meta_member.fortran_order,
            path=str(npz),
            shape=list(meta.shape),
        )
    frontier_count = int(meta.shape[0])
    if frontier_count > STAT_KEY_COUNT:
        raise InvalidBundle(
            "frontier_count_out_of_range",
            "FG cache has more frontier IDs than canonical stat keys",
            frontier_count=frontier_count,
            path=str(npz),
        )
    first_offsets = _require_member(
        members,
        "first_offsets",
        dtype=np.int32,
        shape=(frontier_count,),
        fortran_order=False,
        path=npz,
    )
    first_counts = _require_member(
        members,
        "first_counts",
        dtype=np.int32,
        shape=(frontier_count,),
        fortran_order=False,
        path=npz,
    )

    total_notes = int(fixed_arrays["total_notes"].item())
    long_notes = int(fixed_arrays["long_notes"].item())
    use_forced_timing = int(fixed_arrays["use_forced_great_timing"].item())
    head_len = int(fixed_arrays["first_surface_head_len"].item())
    surface_row_count = int(fixed_arrays["first_surface_row_count"].item())
    if total_notes < 0 or long_notes < 0 or long_notes > total_notes:
        raise InvalidBundle(
            "invalid_note_counts",
            "FG cache total/long note counts are invalid",
            long_notes=long_notes,
            path=str(npz),
            total_notes=total_notes,
        )
    if use_forced_timing not in (0, 1):
        raise InvalidBundle(
            "invalid_forced_timing_flag",
            "FG cache forced-Great timing flag must be 0 or 1",
            path=str(npz),
            value=use_forced_timing,
        )
    if head_len != min(total_notes, 100):
        raise InvalidBundle(
            "invalid_surface_head_len",
            "FG cache surface-head length disagrees with total_notes",
            actual=head_len,
            expected=min(total_notes, 100),
            path=str(npz),
        )
    if surface_row_count < 0:
        raise InvalidBundle(
            "negative_surface_row_count",
            "FG cache surface row count must be nonnegative",
            path=str(npz),
            value=surface_row_count,
        )

    raw_fill = fixed_arrays["raw_fill_by_ff"]
    non_fever_base = fixed_arrays["non_fever_base_by_ff"]
    real_time = fixed_arrays["real_time_by_ft"]
    invalid_fill = np.flatnonzero(~np.isfinite(raw_fill) | (raw_fill < 0.0))
    if invalid_fill.size:
        idx = int(invalid_fill[0])
        raise InvalidBundle(
            "invalid_raw_fill_axis",
            "FG cache raw-fill axis must be finite and nonnegative",
            index=idx,
            path=str(npz),
            value=repr(float(raw_fill[idx])),
        )
    for idx, value in enumerate(raw_fill):
        expected_base = math.ceil(float(value))
        actual_base = int(non_fever_base[idx])
        if actual_base != expected_base:
            raise InvalidBundle(
                "fill_axis_mismatch",
                "FG cache non-fever-base axis must equal ceil(raw_fill_by_ff)",
                actual=actual_base,
                expected=expected_base,
                index=idx,
                path=str(npz),
            )
    invalid_time = np.flatnonzero(~np.isfinite(real_time) | (real_time <= 0.0))
    if invalid_time.size:
        idx = int(invalid_time[0])
        raise InvalidBundle(
            "invalid_real_time_axis",
            "FG cache real-time axis must be finite and positive",
            index=idx,
            path=str(npz),
            value=repr(float(real_time[idx])),
        )
    negative_meta = np.argwhere(meta < 0)
    if negative_meta.size:
        frontier_id, column = (int(value) for value in negative_meta[0])
        raise InvalidBundle(
            "negative_frontier_meta",
            "FG cache frontier metadata counters must be nonnegative",
            column=column,
            frontier_id=frontier_id,
            path=str(npz),
            value=int(meta[frontier_id, column]),
        )

    _validate_stat_keys(stat_keys, path=npz)
    seen_ids = bytearray(frontier_count)
    for row_idx in range(STAT_KEY_COUNT):
        frontier_id = int(frontier_ids[row_idx])
        if frontier_id < 0 or frontier_id >= frontier_count:
            raise InvalidBundle(
                "frontier_id_out_of_range",
                "FG cache stat key references an invalid frontier ID",
                frontier_count=frontier_count,
                frontier_id=frontier_id,
                path=str(npz),
                row=row_idx,
            )
        ff = int(stat_keys[row_idx, 1])
        if int(meta[frontier_id, 6]) != int(non_fever_base[ff]):
            raise InvalidBundle(
                "frontier_non_fever_base_mismatch",
                "FG cache frontier metadata disagrees with the stat key's FF axis",
                actual=int(meta[frontier_id, 6]),
                expected=int(non_fever_base[ff]),
                frontier_id=frontier_id,
                path=str(npz),
                stat_key=[int(stat_keys[row_idx, 0]), ff],
            )
        seen_ids[frontier_id] = 1
    try:
        unused_id = seen_ids.index(0)
    except ValueError:
        unused_id = -1
    if unused_id >= 0:
        raise InvalidBundle(
            "unreferenced_frontier_id",
            "FG cache indirection table contains an unreferenced frontier ID",
            frontier_id=unused_id,
            path=str(npz),
        )

    segments: set[tuple[int, int]] = set()
    for frontier_id in range(frontier_count):
        offset = int(first_offsets[frontier_id])
        count = int(first_counts[frontier_id])
        end = offset + count
        if offset < 0 or count <= 0 or end > surface_row_count:
            raise InvalidBundle(
                "invalid_frontier_range",
                "FG cache frontier range is negative, empty, or outside the surface pool",
                count=count,
                end=end,
                frontier_id=frontier_id,
                offset=offset,
                path=str(npz),
                surface_row_count=surface_row_count,
            )
        segments.add((offset, count))

    cursor = 0
    for offset, count in sorted(segments):
        if offset < cursor:
            raise InvalidBundle(
                "surface_segment_overlap",
                "unique FG cache surface segments overlap",
                count=count,
                offset=offset,
                path=str(npz),
                previous_end=cursor,
            )
        if offset > cursor:
            raise InvalidBundle(
                "surface_segment_gap",
                "unique FG cache surface segments leave a gap",
                gap_end=offset,
                gap_start=cursor,
                path=str(npz),
            )
        cursor = offset + count
    if cursor != surface_row_count:
        raise InvalidBundle(
            "unreachable_surface_rows",
            "FG cache surface pool contains rows unreachable from every frontier",
            path=str(npz),
            referenced_end=cursor,
            surface_row_count=surface_row_count,
        )

    pool_header = _validate_sidecar(
        pool,
        snapshot=pool_snapshot,
        expected_shape=(surface_row_count, SURFACE_POOL_COLUMNS),
        expected_dtype=np.uint32,
    )
    coeff_header = _validate_sidecar(
        coeff,
        snapshot=coeff_snapshot,
        expected_shape=(surface_row_count, SURFACE_COEFF_COLUMNS),
        expected_dtype=np.uint16,
    )
    _validate_surface_sidecars(
        pool_header,
        coeff_header,
        total_notes=total_notes,
        head_len=head_len,
    )
    return Bundle(
        npz_path=npz,
        pool_path=pool,
        coeff_path=coeff,
        members=members,
        npz_sha256=_sha256_file(npz),
        version=actual_version,
        frontier_count=frontier_count,
        surface_row_count=surface_row_count,
        pool_header=pool_header,
        coeff_header=coeff_header,
        snapshots=snapshots,
    )


def _same_file(left: Path, right: Path) -> bool:
    try:
        return os.path.samefile(left, right)
    except OSError as exc:
        raise InvalidBundle(
            "same_file_check_failed",
            "could not establish whether baseline and candidate files are distinct",
            left=str(left),
            right=str(right),
        ) from exc


def _compare_raw_files(left: Path, right: Path) -> dict[str, Any]:
    left_hash = hashlib.sha256()
    right_hash = hashlib.sha256()
    left_size = 0
    right_size = 0
    first_difference: int | None = None
    offset = 0
    try:
        with left.open("rb") as left_handle, right.open("rb") as right_handle:
            while True:
                left_chunk = left_handle.read(STREAM_CHUNK_BYTES)
                right_chunk = right_handle.read(STREAM_CHUNK_BYTES)
                if not left_chunk and not right_chunk:
                    break
                left_hash.update(left_chunk)
                right_hash.update(right_chunk)
                left_size += len(left_chunk)
                right_size += len(right_chunk)
                if first_difference is None and left_chunk != right_chunk:
                    common = min(len(left_chunk), len(right_chunk))
                    differing = next(
                        (idx for idx in range(common) if left_chunk[idx] != right_chunk[idx]),
                        common,
                    )
                    first_difference = offset + differing
                offset += max(len(left_chunk), len(right_chunk))
    except OSError as exc:
        raise InvalidBundle(
            "file_read_failed",
            "could not stream cache files for raw comparison",
            left=str(left),
            right=str(right),
        ) from exc
    return {
        "equal": first_difference is None and left_size == right_size,
        "first_difference_byte": first_difference,
        "left_bytes": left_size,
        "left_sha256": left_hash.hexdigest(),
        "right_bytes": right_size,
        "right_sha256": right_hash.hexdigest(),
    }


def _resolved_values(arrays: dict[str, np.ndarray], row_idx: int) -> tuple[int, ...]:
    frontier_id = int(arrays["frontier_ids"][row_idx])
    meta = arrays["frontier_meta"][frontier_id]
    return (
        int(arrays["first_offsets"][frontier_id]),
        int(arrays["first_counts"][frontier_id]),
        *(int(value) for value in meta),
    )


def _compare_resolutions(left: Bundle, right: Bundle) -> dict[str, Any]:
    left_digest = hashlib.sha256(b"fg-response-cache-resolution-v1\0")
    right_digest = hashlib.sha256(b"fg-response-cache-resolution-v1\0")
    left_arrays = left.arrays
    right_arrays = right.arrays
    first_mismatch: dict[str, Any] | None = None
    for row_idx in range(STAT_KEY_COUNT):
        ft = row_idx // STAT_AXIS
        ff = row_idx % STAT_AXIS
        left_values = _resolved_values(left_arrays, row_idx)
        right_values = _resolved_values(right_arrays, row_idx)
        left_digest.update(struct.pack("<11q", ft, ff, *left_values))
        right_digest.update(struct.pack("<11q", ft, ff, *right_values))
        if first_mismatch is None and left_values != right_values:
            first_mismatch = {
                "baseline": {
                    "count": left_values[1],
                    "frontier_meta": list(left_values[2:]),
                    "offset": left_values[0],
                },
                "candidate": {
                    "count": right_values[1],
                    "frontier_meta": list(right_values[2:]),
                    "offset": right_values[0],
                },
                "stat_key": [ft, ff],
            }
    return {
        "baseline_sha256": left_digest.hexdigest(),
        "candidate_sha256": right_digest.hexdigest(),
        "equal": first_mismatch is None,
        "first_mismatch": first_mismatch,
        "keys_compared": STAT_KEY_COUNT,
    }


def _semantic_bundle_digest(bundle: Bundle, *, pool_sha256: str, coeff_sha256: str, resolution: str) -> str:
    digest = hashlib.sha256(b"fg-response-cache-semantic-bundle-v1\0")
    digest.update(bytes.fromhex(pool_sha256))
    digest.update(bytes.fromhex(coeff_sha256))
    for name in sorted(RAW_COMPARE_MEMBERS):
        encoded = name.encode("utf-8")
        digest.update(struct.pack("<I", len(encoded)))
        digest.update(encoded)
        digest.update(bytes.fromhex(bundle.members[name].sha256))
    digest.update(bytes.fromhex(resolution))
    return digest.hexdigest()


def compare_bundle_paths(
    baseline_path: str | Path,
    candidate_path: str | Path,
    *,
    baseline_version: str,
    candidate_version: str,
) -> dict[str, Any]:
    baseline_paths = _bundle_paths(baseline_path, role="baseline")
    candidate_paths = _bundle_paths(candidate_path, role="candidate")
    for role, left, right in (
        ("bundle", baseline_paths[0], candidate_paths[0]),
        ("surface-pool sidecar", baseline_paths[1], candidate_paths[1]),
        ("surface-coefficient sidecar", baseline_paths[2], candidate_paths[2]),
    ):
        if _same_file(left, right):
            raise InvalidBundle(
                "same_cache_file",
                f"baseline and candidate {role} must be distinct files",
                path=str(left),
                role=role,
            )

    snapshots = tuple(_snapshot_file(path) for path in (*baseline_paths, *candidate_paths))
    baseline_snapshots = snapshots[:3]
    candidate_snapshots = snapshots[3:]
    try:
        baseline = _load_bundle(
            baseline_paths,
            baseline_snapshots,
            expected_version=baseline_version,
            role="baseline",
        )
        candidate = _load_bundle(
            candidate_paths,
            candidate_snapshots,
            expected_version=candidate_version,
            role="candidate",
        )
    except OracleFailure as exc:
        try:
            _verify_snapshots(snapshots)
        except InvalidBundle as changed:
            raise changed from exc
        raise

    report: dict[str, Any] = {
        "baseline": baseline.summary(),
        "candidate": candidate.summary(),
        "comparison": {
            "candidate_frontier_delta": candidate.frontier_count - baseline.frontier_count,
            "exempt_members": sorted(RAW_COMPARE_EXEMPT_MEMBERS),
            "raw_compared_members": sorted(RAW_COMPARE_MEMBERS),
        },
    }

    member_mismatches = [
        name
        for name in sorted(RAW_COMPARE_MEMBERS)
        if baseline.members[name].raw != candidate.members[name].raw
    ]
    report["comparison"]["non_indirection_members_raw_equal"] = not member_mismatches
    report["comparison"]["raw_member_mismatches"] = member_mismatches

    pool_comparison = _compare_raw_files(baseline.pool_path, candidate.pool_path)
    coeff_comparison = _compare_raw_files(baseline.coeff_path, candidate.coeff_path)
    report["comparison"]["surf_pool"] = pool_comparison
    report["comparison"]["surf_coeffs"] = coeff_comparison
    report["baseline"]["files"]["surf_pool"].update(
        {"sha256": pool_comparison["left_sha256"]}
    )
    report["candidate"]["files"]["surf_pool"].update(
        {"sha256": pool_comparison["right_sha256"]}
    )
    report["baseline"]["files"]["surf_coeffs"].update(
        {"sha256": coeff_comparison["left_sha256"]}
    )
    report["candidate"]["files"]["surf_coeffs"].update(
        {"sha256": coeff_comparison["right_sha256"]}
    )
    resolutions = _compare_resolutions(baseline, candidate)
    report["comparison"]["resolutions"] = resolutions
    baseline_semantic = _semantic_bundle_digest(
        baseline,
        pool_sha256=pool_comparison["left_sha256"],
        coeff_sha256=coeff_comparison["left_sha256"],
        resolution=resolutions["baseline_sha256"],
    )
    candidate_semantic = _semantic_bundle_digest(
        candidate,
        pool_sha256=pool_comparison["right_sha256"],
        coeff_sha256=coeff_comparison["right_sha256"],
        resolution=resolutions["candidate_sha256"],
    )
    report["comparison"]["semantic_bundle"] = {
        "baseline_sha256": baseline_semantic,
        "candidate_sha256": candidate_semantic,
        "equal": baseline_semantic == candidate_semantic,
    }

    _verify_snapshots(snapshots)
    if member_mismatches:
        raise BundleMismatch(
            "npz_member_bytes_mismatch",
            "a non-indirection NPZ member differs byte-for-byte",
            member=member_mismatches[0],
            report=report,
        )
    if not bool(pool_comparison["equal"]):
        raise BundleMismatch(
            "surface_pool_bytes_mismatch",
            "FG cache .surf_pool.npy files differ byte-for-byte",
            report=report,
        )
    if not bool(coeff_comparison["equal"]):
        raise BundleMismatch(
            "surface_coeff_bytes_mismatch",
            "FG cache .surf_coeffs.npy files differ byte-for-byte",
            report=report,
        )
    if not bool(resolutions["equal"]):
        raise BundleMismatch(
            "stat_resolution_mismatch",
            "a stat key resolves to different offset/count/frontier_meta semantics",
            first_mismatch=resolutions["first_mismatch"],
            report=report,
        )
    if baseline_semantic != candidate_semantic:
        raise AssertionError("equal cache semantics produced different canonical digests")
    return report


def _validate_json_output(path: Path, input_paths: Iterable[Path]) -> Path:
    try:
        parent = path.expanduser().parent.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise InvalidBundle(
            "json_parent_missing",
            "JSON output parent does not exist",
            path=str(path),
        ) from exc
    if not parent.is_dir():
        raise InvalidBundle("json_parent_not_directory", "JSON output parent is not a directory", path=str(parent))
    output = parent / path.name
    _reject_production_path(output)
    if output.exists() and output.is_dir():
        raise InvalidBundle("json_output_is_directory", "JSON output path is a directory", path=str(output))
    resolved_output = output.resolve(strict=False)
    lexical_output = os.path.normcase(os.path.abspath(str(path.expanduser())))
    for input_path in input_paths:
        lexical_input = os.path.normcase(os.path.abspath(str(input_path)))
        collision = lexical_output == lexical_input or resolved_output == input_path
        if output.exists() and not collision:
            collision = _same_file(output, input_path)
        if collision:
            raise InvalidBundle(
                "json_output_input_collision",
                "JSON output must not name, resolve to, or hardlink an input cache file",
                input_path=str(input_path),
                json_out=str(output),
            )
    return output


def _atomic_write_json(
    path: Path,
    report: dict[str, Any],
    *,
    input_paths: tuple[Path, ...],
) -> None:
    output = _validate_json_output(path, input_paths)
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    except OSError as exc:
        raise InvalidBundle(
            "json_write_failed",
            "could not create an exclusive temporary JSON output",
            path=str(output),
        ) from exc
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, allow_nan=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        _validate_json_output(output, input_paths)
        if report.get("ok") is True:
            _verify_report_snapshots(report)
        os.replace(tmp, output)
    except OracleFailure:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    except OSError as exc:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise InvalidBundle(
            "json_write_failed",
            "could not write, sync, or atomically replace the JSON output",
            path=str(output),
        ) from exc
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _verify_report_snapshots(report: dict[str, Any]) -> None:
    snapshots: list[FileSnapshot] = []
    for side in ("baseline", "candidate"):
        for name in ("npz", "surf_pool", "surf_coeffs"):
            file_report = report[side]["files"][name]
            device, inode = file_report["identity"]
            snapshots.append(
                FileSnapshot(
                    path=Path(file_report["path"]),
                    device=int(device),
                    inode=int(inode),
                    size=int(file_report["bytes"]),
                    mtime_ns=int(file_report["mtime_ns"]),
                )
            )
    _verify_snapshots(snapshots)


def _mark_report_invalid(report: dict[str, Any], exc: OracleFailure) -> None:
    report["ok"] = False
    report["error"] = {
        "code": exc.code,
        "details": exc.details,
        "kind": exc.kind,
        "message": exc.message,
    }


def _publish_invalid_result(
    path: Path,
    report: dict[str, Any],
    input_paths: tuple[Path, ...],
    exc: InvalidBundle,
) -> None:
    _mark_report_invalid(report, exc)
    try:
        _atomic_write_json(path, report, input_paths=input_paths)
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _base_report(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "expected_versions": {
            "baseline": str(args.baseline_version),
            "candidate": str(args.candidate_version),
        },
        "inputs": {
            "baseline": str(Path(args.baseline).expanduser().absolute()),
            "candidate": str(Path(args.candidate).expanduser().absolute()),
        },
        "ok": False,
        "parity_scope": dict(PARITY_SCOPE),
        "schema": "fg-response-cache-byte-oracle/v1",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, help="Immediate-parent baseline bundle .npz")
    parser.add_argument("--candidate", required=True, help="Candidate bundle .npz")
    parser.add_argument("--baseline-version", required=True, help="Exact expected baseline cache version")
    parser.add_argument("--candidate-version", required=True, help="Exact expected candidate cache version")
    parser.add_argument("--json-out", required=True, help="Atomic machine-readable result path")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    report = _base_report(args)
    try:
        input_paths = (
            *_prospective_bundle_paths(args.baseline),
            *_prospective_bundle_paths(args.candidate),
        )
        json_out = _validate_json_output(Path(args.json_out), input_paths)
    except OracleFailure as exc:
        print(f"FAIL [{exc.code}] {exc.message}", file=sys.stderr)
        return int(exc.exit_code)
    try:
        comparison = compare_bundle_paths(
            args.baseline,
            args.candidate,
            baseline_version=args.baseline_version,
            candidate_version=args.candidate_version,
        )
    except OracleFailure as exc:
        embedded_report = exc.details.pop("report", None)
        if isinstance(embedded_report, dict):
            report.update(embedded_report)
        _mark_report_invalid(report, exc)
        try:
            _atomic_write_json(json_out, report, input_paths=input_paths)
        except OracleFailure as output_exc:
            print(f"FAIL [{output_exc.code}] {output_exc.message}", file=sys.stderr)
            return int(output_exc.exit_code)
        print(f"FAIL [{exc.code}] {exc.message}", file=sys.stderr)
        return int(exc.exit_code)

    report.update(comparison)
    report["ok"] = True
    try:
        _verify_report_snapshots(report)
        _atomic_write_json(json_out, report, input_paths=input_paths)
        _verify_report_snapshots(report)
    except InvalidBundle as exc:
        if exc.code == "input_changed":
            try:
                _publish_invalid_result(json_out, report, input_paths, exc)
            except OracleFailure as output_exc:
                print(f"FAIL [{output_exc.code}] {output_exc.message}", file=sys.stderr)
                return int(output_exc.exit_code)
        print(f"FAIL [{exc.code}] {exc.message}", file=sys.stderr)
        return int(exc.exit_code)
    print(f"PASS: compared {STAT_KEY_COUNT} FG stat keys", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
