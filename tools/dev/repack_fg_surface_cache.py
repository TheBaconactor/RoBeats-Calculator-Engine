from __future__ import annotations

"""One-time re-pack of FG response-frontier scoring-surface bundles to the uncompressed + memmap
sidecar layout (Issue #34).

This is a MECHANICAL storage-format migration, NOT a semantic rebuild. For each existing
``bin/fg_response_frontier_cache/<hash>.npz`` it:

1. Reassembles the contiguous first-surface pool (uint32 N x 11) and head coeffs (uint16 N x 4)
   from the legacy 32768-row ``first_surface_pool_chunk_*`` / ``first_surface_head_coeffs_chunk_*``
   members, validated against ``first_surface_chunk_offsets``.
2. Interns exact head masks/coefficients and writes C-order, memmap-able ``<hash>.surf_rows.npy`` /
   ``<hash>.surf_patterns.npy`` sidecars (atomic tmp + os.replace each).
3. Rewrites the ``.npz`` slim: every non-surface metadata member is copied byte-for-byte from the
   source archive (so stat_keys / frontier_meta keep their exact Fortran-order bytes), the chunk
   members + ``first_surface_chunk_offsets`` are dropped, and a single ``first_surface_row_count``
   scalar is added.

Properties:
- Idempotent: a bundle already in the slim layout (no chunk members, ``first_surface_row_count``
  present, both sidecars present with matching shape/dtype) is left untouched. A slim-shaped .npz
  whose sidecar(s) are missing or mismatched raises ``SlimBundleMissingSidecarError`` (surfaces are
  unrecoverable from a slim .npz -> the bundle must be rebuilt by the optimizer), instead of the
  misleading "neither slim nor legacy-chunked" error.
- Fail-loud: any shape / dtype / row-count / chunk-coverage disagreement raises; nothing partial is
  committed (sidecars are written before the slim .npz, and the .npz is replaced atomically last).
- It NEVER calls ``build_or_load_response_frontier_payload`` or any GPU/Numba frontier build path.

The cache frontier *semantic* version is unchanged, so re-packed bundles stay valid without a slow
rebuild.

Usage::

    python tools/dev/repack_fg_surface_cache.py            # re-pack the default cache dir
    python tools/dev/repack_fg_surface_cache.py --dir PATH  # re-pack a specific dir
    python tools/dev/repack_fg_surface_cache.py --dry-run    # report what would change
"""

import argparse
import io
import os
import re
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
from numpy.lib import format as np_format

REPO_ROOT = Path(__file__).resolve().parents[2]

# Legacy on-disk chunk layout (kept local to this one-time tool; production no longer chunks).
_LEGACY_CHUNK_ROWS = 32768
_POOL_COLUMNS = 11
_COEFF_COLUMNS = 4
_ROW_SIDECAR_SUFFIX = ".surf_rows.npy"
_PATTERN_SIDECAR_SUFFIX = ".surf_patterns.npy"
_ROW_COLUMNS = 4
_PATTERN_COLUMNS = 10

# Members that survive verbatim in the slim .npz (everything except the surface chunks and the
# chunk-offsets array, which are replaced by the sidecars + first_surface_row_count).
_SLIM_METADATA_MEMBERS = (
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
)
_ROW_COUNT_MEMBER = "first_surface_row_count"
_PATTERN_COUNT_MEMBER = "first_surface_pattern_count"
_NPZ_FAST_COMPRESS_LEVEL = 1


class SlimBundleMissingSidecarError(RuntimeError):
    """A bundle .npz is already in the slim (post-re-pack) shape but one/both of its uncompressed
    surface sidecars are missing or shape/dtype/row-count mismatched.

    Surfaces are NOT recoverable from a slim .npz -- the legacy chunk members were dropped during
    the original re-pack -- so this bundle cannot be re-packed; it must be rebuilt by the optimizer.
    Mirrors the production reader's ``FgResponseSurfaceSidecarError`` so the migration tool's
    diagnostic is equally clear on this desync.
    """


def _ensure_repo_on_path() -> None:
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _legacy_pool_chunk_name(chunk_idx: int) -> str:
    return f"first_surface_pool_chunk_{int(chunk_idx):05d}"


def _legacy_coeff_chunk_name(chunk_idx: int) -> str:
    return f"first_surface_head_coeffs_chunk_{int(chunk_idx):05d}"


_POOL_CHUNK_MEMBER_RE = re.compile(r"^first_surface_pool_chunk_(\d+)\.npy$")
_COEFF_CHUNK_MEMBER_RE = re.compile(r"^first_surface_head_coeffs_chunk_(\d+)\.npy$")


def _chunk_member_indices(archive_names: set[str], pattern: re.Pattern[str]) -> set[int]:
    """Integer suffixes of every archive member matching a legacy chunk-name pattern."""
    indices: set[int] = set()
    for name in archive_names:
        match = pattern.match(name)
        if match is not None:
            indices.add(int(match.group(1)))
    return indices


def _sidecar_paths(npz_path: Path) -> tuple[Path, Path]:
    if npz_path.suffix != ".npz":
        raise ValueError(f"bundle path must be a .npz: {npz_path}")
    stem = npz_path.name[: -len(".npz")]
    return (
        npz_path.with_name(f"{stem}{_ROW_SIDECAR_SUFFIX}"),
        npz_path.with_name(f"{stem}{_PATTERN_SIDECAR_SUFFIX}"),
    )


def _sidecar_header(path: Path) -> tuple[tuple[int, ...], np.dtype] | None:
    if not path.exists():
        return None
    with open(path, "rb") as handle:
        version = np_format.read_magic(handle)
        if version == (1, 0):
            shape, _fortran_order, dtype = np_format.read_array_header_1_0(handle)
        elif version == (2, 0):
            shape, _fortran_order, dtype = np_format.read_array_header_2_0(handle)
        else:
            return None
    return tuple(int(dim) for dim in shape), np.dtype(dtype)


def _atomic_write_sidecar(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{time.perf_counter_ns()}.tmp")
    try:
        with open(tmp, "wb") as handle:
            np_format.write_array(handle, np.ascontiguousarray(array), allow_pickle=False)
        os.replace(tmp, path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def _reassemble_chunked_pool(archive: zipfile.ZipFile, chunk_offsets: np.ndarray) -> np.ndarray:
    row_count = int(chunk_offsets[-1])
    pool = np.empty((row_count, _POOL_COLUMNS), dtype=np.uint32)
    names = set(archive.namelist())
    for chunk_idx in range(int(chunk_offsets.shape[0]) - 1):
        start = int(chunk_offsets[chunk_idx])
        end = int(chunk_offsets[chunk_idx + 1])
        member = f"{_legacy_pool_chunk_name(chunk_idx)}.npy"
        if member not in names:
            raise ValueError(f"missing pool chunk member: {member}")
        with archive.open(member, mode="r") as handle:
            chunk = np.load(io.BytesIO(handle.read()), allow_pickle=False)
        if chunk.shape != (end - start, _POOL_COLUMNS) or chunk.dtype != np.dtype(np.uint32):
            raise ValueError(f"pool chunk {member} has unexpected shape/dtype: {chunk.shape} {chunk.dtype}")
        pool[start:end] = np.asarray(chunk, dtype=np.uint32)
    return pool


def _reassemble_chunked_coeffs(archive: zipfile.ZipFile, chunk_offsets: np.ndarray) -> np.ndarray:
    row_count = int(chunk_offsets[-1])
    coeffs = np.empty((row_count, _COEFF_COLUMNS), dtype=np.uint16)
    names = set(archive.namelist())
    for chunk_idx in range(int(chunk_offsets.shape[0]) - 1):
        start = int(chunk_offsets[chunk_idx])
        end = int(chunk_offsets[chunk_idx + 1])
        member = f"{_legacy_coeff_chunk_name(chunk_idx)}.npy"
        if member not in names:
            raise ValueError(f"missing head-coeff chunk member: {member}")
        with archive.open(member, mode="r") as handle:
            chunk = np.load(io.BytesIO(handle.read()), allow_pickle=False)
        if chunk.shape != (end - start, _COEFF_COLUMNS) or chunk.dtype != np.dtype(np.uint16):
            raise ValueError(f"coeff chunk {member} has unexpected shape/dtype: {chunk.shape} {chunk.dtype}")
        coeffs[start:end] = np.asarray(chunk, dtype=np.uint16)
    return coeffs


def _npz_has_slim_shape(archive_names: set[str]) -> bool:
    """True iff the .npz is already in the slim (post-re-pack) shape: a ``first_surface_row_count``
    scalar and NO legacy surface chunk members / chunk-offsets.

    This describes the .npz ALONE; it says nothing about the sidecars on disk. The sidecars are
    validated separately because surfaces are not recoverable from a slim .npz, so a slim-shaped
    archive with a missing/mismatched sidecar is a desync (fail-loud), not a re-packable input.
    """
    has_chunks = any(
        name.startswith("first_surface_pool_chunk_") or name.startswith("first_surface_head_coeffs_chunk_")
        for name in archive_names
    )
    has_chunk_offsets = "first_surface_chunk_offsets.npy" in archive_names
    has_row_count = f"{_ROW_COUNT_MEMBER}.npy" in archive_names
    has_pattern_count = f"{_PATTERN_COUNT_MEMBER}.npy" in archive_names
    return has_row_count and has_pattern_count and not has_chunks and not has_chunk_offsets


def _slim_sidecar_problems(npz_path: Path, row_count: int, pattern_count: int) -> list[str]:
    """Describe any problem with a slim bundle's surface sidecars (empty list == both present + OK).

    Mirrors the production reader's ``_open_surface_sidecar_memmap`` checks (existence, 2-D shape
    with the right column count, dtype, and exact row count) so the tool's diagnostic matches the
    runtime fail-loud behavior.
    """
    row_sidecar, pattern_sidecar = _sidecar_paths(npz_path)
    problems: list[str] = []
    for path, rows, columns, dtype in (
        (row_sidecar, row_count, _ROW_COLUMNS, np.dtype(np.uint32)),
        (pattern_sidecar, pattern_count, _PATTERN_COLUMNS, np.dtype(np.uint32)),
    ):
        if not path.exists():
            problems.append(f"{path.name} is missing")
            continue
        header = _sidecar_header(path)
        if header is None:
            problems.append(f"{path.name} is unreadable or not a .npy")
            continue
        shape, header_dtype = header
        if shape != (int(rows), int(columns)) or header_dtype != dtype:
            problems.append(
                f"{path.name} has shape/dtype {shape}/{header_dtype}, "
                f"expected {(int(rows), int(columns))}/{dtype}"
            )
    return problems


def _write_slim_npz(
    npz_path: Path,
    *,
    metadata_bytes: dict[str, bytes],
    row_count: int,
    pattern_count: int,
) -> None:
    """Write the slim .npz from pre-buffered metadata .npy bytes plus a fresh row-count scalar.

    Bytes are pre-read by the caller so the SOURCE archive can be closed first -- on Windows you
    cannot os.replace over a file that still has an open handle (the source IS npz_path).
    """
    for member in _SLIM_METADATA_MEMBERS:
        if member not in metadata_bytes:
            raise ValueError(f"source bundle is missing required member: {member}")
    tmp = npz_path.with_name(f"{npz_path.stem}.{os.getpid()}.{time.perf_counter_ns()}.repack.tmp.npz")
    try:
        with zipfile.ZipFile(
            tmp,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=int(_NPZ_FAST_COMPRESS_LEVEL),
            allowZip64=True,
        ) as target:
            for member in _SLIM_METADATA_MEMBERS:
                # Copy the .npy bytes verbatim so Fortran-order metadata (stat_keys, frontier_meta)
                # stays byte-identical to the source.
                with target.open(f"{member}.npy", mode="w", force_zip64=True) as handle:
                    handle.write(metadata_bytes[member])
            with target.open(f"{_ROW_COUNT_MEMBER}.npy", mode="w", force_zip64=True) as handle:
                np_format.write_array(handle, np.asarray(int(row_count), dtype=np.int64), allow_pickle=False)
            with target.open(f"{_PATTERN_COUNT_MEMBER}.npy", mode="w", force_zip64=True) as handle:
                np_format.write_array(handle, np.asarray(int(pattern_count), dtype=np.int64), allow_pickle=False)
        os.replace(tmp, npz_path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def repack_bundle(npz_path: Path, *, dry_run: bool = False) -> str:
    """Re-pack one bundle. Returns one of 'repacked', 'skipped', 'dry-run'.

    Raises on any malformed/inconsistent source. Idempotent on already-slim bundles.
    """
    row_sidecar, pattern_sidecar = _sidecar_paths(npz_path)
    # Read EVERYTHING needed out of the source while it is open, then close it before writing the
    # sidecars / replacing the .npz (Windows can't os.replace over an open file).
    with zipfile.ZipFile(npz_path, mode="r") as source:
        names = set(source.namelist())
        if _npz_has_slim_shape(names):
            # Already migrated by .npz shape: the surfaces live ONLY in the sidecars now and CANNOT
            # be reassembled from this slim .npz (the legacy chunk members were dropped during the
            # original re-pack). Present + consistent sidecars => idempotent skip; a missing or
            # mismatched one is a desync that must surface loudly (not the misleading
            # "neither slim nor legacy-chunked" error from the legacy branch below).
            with source.open(f"{_ROW_COUNT_MEMBER}.npy", mode="r") as handle:
                row_count = int(np.asarray(np.load(io.BytesIO(handle.read()), allow_pickle=False)).item())
            with source.open(f"{_PATTERN_COUNT_MEMBER}.npy", mode="r") as handle:
                pattern_count = int(np.asarray(np.load(io.BytesIO(handle.read()), allow_pickle=False)).item())
            problems = _slim_sidecar_problems(npz_path, row_count, pattern_count)
            if not problems:
                return "skipped"
            raise SlimBundleMissingSidecarError(
                f"slim bundle {npz_path} is missing its surface sidecar(s): {'; '.join(problems)}. "
                "Surfaces are not recoverable from the slim .npz (the legacy chunk members were "
                "dropped during the original re-pack) -- this bundle must be rebuilt by the "
                "optimizer, not re-packed."
            )
        if "first_surface_chunk_offsets.npy" not in names:
            raise ValueError(f"bundle is neither slim nor legacy-chunked (no chunk offsets): {npz_path}")
        with source.open("first_surface_chunk_offsets.npy", mode="r") as handle:
            chunk_offsets = np.asarray(
                np.load(io.BytesIO(handle.read()), allow_pickle=False), dtype=np.int64
            ).reshape(-1)
        if int(chunk_offsets.shape[0]) < 2 or int(chunk_offsets[0]) != 0:
            raise ValueError(f"bundle has invalid chunk offsets: {npz_path}")
        if bool(np.any(chunk_offsets[1:] < chunk_offsets[:-1])):
            raise ValueError(f"bundle has non-monotonic chunk offsets: {npz_path}")
        # Cross-check the chunk MEMBERS actually present against the chunk indices the offsets
        # reference. _reassemble_chunked_* only reads the offset-referenced members, so without this
        # an offsets/members disagreement (truncated offsets, or stale/extra trailing chunks) would
        # silently reassemble a too-small pool and write an internally-consistent slim bundle with a
        # wrong first_surface_row_count -- permanent, downstream-undetectable surface data loss.
        expected_chunks = set(range(int(chunk_offsets.shape[0]) - 1))
        pool_chunk_indices = _chunk_member_indices(names, _POOL_CHUNK_MEMBER_RE)
        coeff_chunk_indices = _chunk_member_indices(names, _COEFF_CHUNK_MEMBER_RE)
        if pool_chunk_indices != expected_chunks:
            raise ValueError(
                f"bundle pool chunk members {sorted(pool_chunk_indices)} disagree with the chunk "
                f"indices implied by first_surface_chunk_offsets {sorted(expected_chunks)} "
                f"(offsets/members mismatch would drop or duplicate surface rows): {npz_path}"
            )
        if coeff_chunk_indices != expected_chunks:
            raise ValueError(
                f"bundle head-coeff chunk members {sorted(coeff_chunk_indices)} disagree with the "
                f"chunk indices implied by first_surface_chunk_offsets {sorted(expected_chunks)} "
                f"(offsets/members mismatch would drop or duplicate surface rows): {npz_path}"
            )
        row_count = int(chunk_offsets[-1])
        pool = _reassemble_chunked_pool(source, chunk_offsets)
        coeffs = _reassemble_chunked_coeffs(source, chunk_offsets)
        if int(pool.shape[0]) != row_count or int(coeffs.shape[0]) != row_count:
            raise ValueError(f"reassembled surface row count disagrees with chunk offsets: {npz_path}")
        missing_meta = [member for member in _SLIM_METADATA_MEMBERS if f"{member}.npy" not in names]
        if missing_meta:
            raise ValueError(f"bundle is missing required metadata members {missing_meta!r}: {npz_path}")
        metadata_bytes = {member: source.read(f"{member}.npy") for member in _SLIM_METADATA_MEMBERS}

    if dry_run:
        return "dry-run"
    _ensure_repo_on_path()
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_patterns import intern_surface_rows

    row_refs, patterns = intern_surface_rows(pool, coeffs)
    pattern_count = int(patterns.shape[0])
    # Sidecars first (atomic each), then the slim .npz last so a present slim .npz implies present
    # sidecars.
    _atomic_write_sidecar(row_sidecar, row_refs)
    _atomic_write_sidecar(pattern_sidecar, patterns)
    _write_slim_npz(
        npz_path,
        metadata_bytes=metadata_bytes,
        row_count=row_count,
        pattern_count=pattern_count,
    )

    # Post-write fail-loud validation: sidecars must match the recorded row count exactly.
    row_header = _sidecar_header(row_sidecar)
    pattern_header = _sidecar_header(pattern_sidecar)
    if row_header != ((row_count, _ROW_COLUMNS), np.dtype(np.uint32)):
        raise ValueError(f"row sidecar failed post-write validation: {row_sidecar} -> {row_header}")
    if pattern_header != ((pattern_count, _PATTERN_COLUMNS), np.dtype(np.uint32)):
        raise ValueError(
            f"pattern sidecar failed post-write validation: {pattern_sidecar} -> {pattern_header}"
        )
    return "repacked"


def _default_cache_dir() -> Path:
    _ensure_repo_on_path()
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _fg_response_disk_cache_dir

    return _fg_response_disk_cache_dir()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "One-time re-pack of FG response-frontier scoring-surface bundles to the uncompressed + "
            "memmap sidecar layout (Issue #34). Mechanical chunk->sidecar migration; not a semantic "
            "rebuild. Idempotent and fail-loud."
        )
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Cache directory of *.npz bundles. Defaults to the resolved FG response frontier cache dir.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N bundles after sorting.")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing.")
    parser.add_argument("--strict", action="store_true", help="Stop at the first bundle error.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    cache_dir = Path(args.dir) if args.dir is not None else _default_cache_dir()
    if not cache_dir.exists():
        print(f"Cache directory does not exist: {cache_dir}")
        return 1
    bundles = sorted(p for p in cache_dir.glob("*.npz") if not p.name.endswith(".tmp.npz"))
    if args.limit and args.limit > 0:
        bundles = bundles[: int(args.limit)]
    if not bundles:
        print(f"No *.npz bundles found in {cache_dir}")
        return 0
    print(f"Re-packing {len(bundles)} FG surface bundles in {cache_dir} (dry_run={bool(args.dry_run)})", flush=True)

    counts = {"repacked": 0, "skipped": 0, "dry-run": 0}
    failures: list[tuple[Path, str]] = []
    t0 = time.perf_counter()
    for index, npz_path in enumerate(bundles, start=1):
        try:
            status = repack_bundle(npz_path, dry_run=bool(args.dry_run))
        except Exception as exc:  # noqa: BLE001 - tool boundary: report and continue/stop per --strict
            failures.append((npz_path, str(exc)))
            print(f"[{index:>5}/{len(bundles):<5}] ERROR  {npz_path.name}: {exc}", flush=True)
            if args.strict:
                break
            continue
        counts[status] += 1
        if status != "skipped":
            print(f"[{index:>5}/{len(bundles):<5}] {status:<8} {npz_path.name}", flush=True)

    elapsed = time.perf_counter() - t0
    print("")
    print(
        f"Done in {elapsed:.1f}s: repacked={counts['repacked']} skipped={counts['skipped']} "
        f"dry-run={counts['dry-run']} failures={len(failures)}"
    )
    if failures:
        for path, reason in failures[:10]:
            print(f"  {path.name}: {reason}")
        if len(failures) > 10:
            print(f"  ... {len(failures) - 10} more")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
