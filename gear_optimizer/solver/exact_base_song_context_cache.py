"""Versioned disk cache for immutable exact-Base per-song contexts.

The cache key is deliberately semantic and catalog-independent.  It contains the exact timeline
payload bytes consumed by :mod:`exact_base_song_context`, the song's note-count contract, color
flags, scoring references, and a fingerprint of the producing logic.  Paths, gear, minis, and
benchmark identities never participate in cache identity.

A missing artifact is the one documented cache-miss boundary and returns ``None``.  An artifact at
the current content-addressed path that is stale, malformed, or corrupt is an invariant violation
and raises :class:`ExactBaseSongContextCacheError`; production must not silently rebuild over it.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, fields
import hashlib
import json
import logging
import os
from pathlib import Path
import threading
import time
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from gear_optimizer.core.array_signature import array_sig16, arrays_sig16
from gear_optimizer.core.constants import GEM_SCALE_FEVER, MAX_STAT_INDEX, PATHS, TOTAL_GEM_BUDGET
from gear_optimizer.core.logic_fingerprint import module_logic_fingerprint
from gear_optimizer.core.parsing import env_get
from gear_optimizer.solver import exact_base_song_context as song_context
from gear_optimizer.solver.frontier_cache_build_lock import FrontierBuildLock
from gear_optimizer.solver.frontier_cache_errors import MissingFrontierCacheError
from gear_optimizer.solver.timing_response_antichain import TimingResponseAntichainTable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from gear_optimizer.solver.timeline_exact_frontier import TimelineFrontierGridPayload


logger = logging.getLogger(__name__)

_GRID = int(MAX_STAT_INDEX) + 1
_FILE_SCHEMA = "exact-base-song-context-npz-v1"
_MULTIPLIER_FILE_SCHEMA = "exact-base-multiplier-bounds-npz-v1"
_MANIFEST_SCHEMA = "exact-base-song-context-manifest-v1"
_MANIFEST_FILE_NAME = "exact_base_song_context_manifest_v1.json"
_CACHE_BASE_VERSION = "exact-base-song-context-v1"
_PRODUCER_SOURCES = (
    Path(__file__).with_name("exact_base_song_context.py"),
    Path(__file__).with_name("timing_response_antichain.py"),
    Path(__file__).with_name("ftff_combos.py"),
)
EXACT_BASE_SONG_CONTEXT_CACHE_VERSION = (
    f"{_CACHE_BASE_VERSION}+logic-{module_logic_fingerprint(_PRODUCER_SOURCES)}"
)

_RESPONSE_ARRAY_FIELDS: dict[str, tuple[str, np.dtype[Any]]] = {
    "response_cells": ("cells", np.dtype(np.int32)),
    "response_cell_to_row": ("cell_to_row", np.dtype(np.int32)),
    "response_offsets_by_row": ("offsets_by_row", np.dtype(np.int32)),
    "response_lengths_by_row": ("lengths_by_row", np.dtype(np.int32)),
    "response_flat_ft": ("flat_ft", np.dtype(np.int32)),
    "response_flat_ff": ("flat_ff", np.dtype(np.int32)),
}
_PROGRAM_MAP_ARRAY_FIELDS: dict[str, tuple[str, np.dtype[Any]]] = {
    "map_class_by_response_row": ("class_by_response_row", np.dtype(np.int32)),
    "map_program_by_cell": ("program_by_cell", np.dtype(np.int32)),
}
_PHYSICAL_ARRAY_FIELDS: dict[str, tuple[str, np.dtype[Any]]] = {
    "physical_surface_offsets": ("surface_offsets", np.dtype(np.int32)),
    "physical_surface_budget": ("surface_budget", np.dtype(np.int16)),
    "physical_surface_direct": ("surface_direct", np.dtype(np.int32)),
    "physical_surface_body_fever": ("surface_body_fever", np.dtype(np.int32)),
    "physical_surface_body_normal": ("surface_body_normal", np.dtype(np.int32)),
    "physical_surface_head_normal": ("surface_head_normal", np.dtype(np.int32)),
    "physical_surface_head_fever": ("surface_head_fever", np.dtype(np.int32)),
    "physical_surface_sigma_normal": ("surface_sigma_normal", np.dtype(np.int32)),
    "physical_surface_sigma_fever": ("surface_sigma_fever", np.dtype(np.int32)),
}
_CLASS_ARRAY_FIELDS: dict[str, tuple[str, np.dtype[Any]]] = {
    "class_program_offsets": ("program_offsets", np.dtype(np.int32)),
    "class_program_budget": ("program_budget", np.dtype(np.int32)),
    "class_program_direct": ("program_direct", np.dtype(np.int32)),
    "class_program_body_fever": ("program_body_fever", np.dtype(np.int32)),
    "class_program_body_normal": ("program_body_normal", np.dtype(np.int32)),
    "class_program_head_normal": ("program_head_normal", np.dtype(np.int32)),
    "class_program_head_fever": ("program_head_fever", np.dtype(np.int32)),
    "class_program_sigma_normal": ("program_sigma_normal", np.dtype(np.int32)),
    "class_program_sigma_fever": ("program_sigma_fever", np.dtype(np.int32)),
}
_MULTIPLIER_ARRAY_FIELDS: dict[str, tuple[str, np.dtype[Any]]] = {
    "multiplier_ref_cm": ("ref_cm", np.dtype(np.float64)),
    "multiplier_ref_fm": ("ref_fm", np.dtype(np.float64)),
    "multiplier_joint_cm_fm": ("joint_cm_fm", np.dtype(np.float64)),
    "multiplier_joint_cm_span_fm": ("joint_cm_span_fm", np.dtype(np.float64)),
}
_MULTIPLIER_META_ARRAY_NAMES = {
    "file_schema",
    "cache_version",
    "multiplier_key_digest",
}
_MULTIPLIER_CACHE_ARRAY_NAMES = frozenset(
    _MULTIPLIER_META_ARRAY_NAMES | set(_MULTIPLIER_ARRAY_FIELDS)
)
_META_ARRAY_NAMES = {
    "file_schema",
    "cache_version",
    "cache_key_digest",
    "response_cache_key_name",
    "response_cache_key_ints",
    "response_max_len",
    "response_legal_combo_count",
    "response_kept_combo_count",
    "response_pack_count",
    "map_program_count",
    "stat_elemental_weight_max",
    "overflow_elemental_weight",
    "multiplier_cache_file",
    "multiplier_key_digest",
}
_CACHE_ARRAY_NAMES = frozenset(
    _META_ARRAY_NAMES
    | set(_RESPONSE_ARRAY_FIELDS)
    | set(_PROGRAM_MAP_ARRAY_FIELDS)
    | set(_PHYSICAL_ARRAY_FIELDS)
    | set(_CLASS_ARRAY_FIELDS)
)

_MULTIPLIER_MEMORY_CACHE_MAX = 4
_multiplier_memory_cache: OrderedDict[
    tuple[str, tuple[Any, ...]], song_context.JointMultiplierBounds
] = OrderedDict()
_multiplier_memory_cache_lock = threading.RLock()


class ExactBaseSongContextCacheError(ValueError):
    """A current exact-Base song-context artifact is stale, malformed, or corrupt."""


@dataclass(frozen=True, slots=True)
class ExactBaseSongContextCacheResult:
    context: song_context.ExactBaseSongContext
    cache_key: tuple[Any, ...]
    disk_path: Path
    cache_source: Literal["built", "disk"]


@dataclass(frozen=True, slots=True)
class ExactBaseSongContextCacheInfo:
    cache_key: tuple[Any, ...]
    disk_path: Path
    cache_source: Literal["disk", "missing"]


@dataclass(frozen=True, slots=True)
class _SemanticInputs:
    total_notes: int
    flags: tuple[int, ...]
    ref_cm: np.ndarray
    ref_fm: np.ndarray
    multiplier_key: tuple[Any, ...]
    multiplier_key_digest: str
    cache_key: tuple[Any, ...]
    key_digest: str


def _cache_dir(cache_dir: str | os.PathLike[str] | None = None) -> Path:
    if cache_dir is not None:
        return Path(cache_dir)
    override = str(env_get("EXACT_BASE_SONG_CONTEXT_CACHE_DIR", "") or "").strip()
    if override:
        return Path(override)
    return Path(PATHS.bin_path("exact_base_song_context_cache"))


def exact_base_song_context_manifest_path(
    cache_dir: str | os.PathLike[str] | None = None,
) -> Path:
    return _cache_dir(cache_dir) / _MANIFEST_FILE_NAME


def _cache_key_digest(cache_key: tuple[Any, ...]) -> str:
    return hashlib.blake2b(repr(cache_key).encode("utf-8"), digest_size=16).hexdigest()


def _entry_lock_dir(root: Path, inputs: _SemanticInputs) -> Path:
    return root / ".entry_locks" / inputs.key_digest


def _semantic_inputs(
    context_inputs: song_context.ExactBaseSongContextInputs,
    timeline_payload: TimelineFrontierGridPayload,
) -> _SemanticInputs:
    if not isinstance(context_inputs, song_context.ExactBaseSongContextInputs):
        raise TypeError("Exact Base context cache requires ExactBaseSongContextInputs")
    flags_by_name = song_context._validated_color_flags(context_inputs.color_flags)
    flags = tuple(int(flags_by_name[name]) for name in song_context._COLOR_FLAG_KEYS)

    metadata = dict((context_inputs.calc_song or {}).get("metadata", {}) or {})
    if "Total Notes" not in metadata:
        raise ValueError("Song metadata is missing Total Notes for exact Base context cache identity")
    total_notes = int(metadata["Total Notes"])
    if total_notes <= 0:
        raise ValueError(f"Song Total Notes must be positive, got {total_notes}")

    ref_pp = np.asarray(context_inputs.ref_arrays.get("Perfect Points"), dtype=np.float64).reshape(-1)
    ref_cm = np.asarray(context_inputs.ref_arrays.get("Combo Multiplier"), dtype=np.float64).reshape(-1)
    ref_fm = np.asarray(context_inputs.ref_arrays.get("Fever Multiplier"), dtype=np.float64).reshape(-1)
    if ref_pp.shape[0] < _GRID:
        raise ValueError("Perfect Points references do not cover the exact stat grid")
    if ref_cm.shape != (_GRID,) or ref_fm.shape != (_GRID,):
        raise ValueError("CM/FM references do not match the exact stat grid")
    for name, references in (
        ("Perfect Points", ref_pp[:_GRID]),
        ("Combo Multiplier", ref_cm),
        ("Fever Multiplier", ref_fm),
    ):
        if not np.all(np.isfinite(references)):
            raise ValueError(f"{name} references contain non-finite values")
        if np.any(np.diff(references) < 0.0):
            raise ValueError(f"{name} references must be nondecreasing")
    if np.any(ref_cm < 1.0) or np.any(ref_fm < 1.0):
        raise ValueError("CM/FM references must be at least one")

    timeline = song_context._timeline_arrays(timeline_payload)
    pool_used = int(timeline.pool_used)
    timeline_signature = bytes(
        arrays_sig16(
            timeline.counts,
            timeline.pool_offsets,
            timeline.body_fever[:pool_used],
            timeline.body_normal[:pool_used],
            timeline.masks[:pool_used],
            timeline.head_coeffs[:pool_used],
            timeline.head_lengths,
        )
    )
    cache_key: tuple[Any, ...] = (
        EXACT_BASE_SONG_CONTEXT_CACHE_VERSION,
        int(MAX_STAT_INDEX),
        int(TOTAL_GEM_BUDGET),
        int(GEM_SCALE_FEVER),
        total_notes,
        flags,
        bytes(array_sig16(ref_pp[:_GRID])),
        bytes(array_sig16(ref_cm)),
        bytes(array_sig16(ref_fm)),
        pool_used,
        timeline_signature,
    )
    multiplier_key: tuple[Any, ...] = (
        EXACT_BASE_SONG_CONTEXT_CACHE_VERSION,
        "joint-multiplier-bounds-v1",
        int(MAX_STAT_INDEX),
        int(TOTAL_GEM_BUDGET),
        bytes(array_sig16(ref_cm)),
        bytes(array_sig16(ref_fm)),
    )
    return _SemanticInputs(
        total_notes=total_notes,
        flags=flags,
        ref_cm=np.ascontiguousarray(ref_cm, dtype=np.float64),
        ref_fm=np.ascontiguousarray(ref_fm, dtype=np.float64),
        multiplier_key=multiplier_key,
        multiplier_key_digest=_cache_key_digest(multiplier_key),
        cache_key=cache_key,
        key_digest=_cache_key_digest(cache_key),
    )


def exact_base_song_context_cache_key(
    context_inputs: song_context.ExactBaseSongContextInputs,
    timeline_payload: TimelineFrontierGridPayload,
) -> tuple[Any, ...]:
    """Return the path-independent semantic cache key for one exact-Base song context."""

    return _semantic_inputs(context_inputs, timeline_payload).cache_key


def exact_base_song_context_cache_path(
    context_inputs: song_context.ExactBaseSongContextInputs,
    timeline_payload: TimelineFrontierGridPayload,
    *,
    cache_dir: str | os.PathLike[str] | None = None,
) -> Path:
    inputs = _semantic_inputs(context_inputs, timeline_payload)
    return _cache_dir(cache_dir) / f"{inputs.key_digest}.npz"


def _flags_dict(inputs: _SemanticInputs) -> dict[str, int]:
    return dict(zip(song_context._COLOR_FLAG_KEYS, inputs.flags, strict=True))


def _expected_response_cache_key(
    inputs: _SemanticInputs,
    *,
    pack_count: int,
) -> tuple[Any, ...]:
    flags = _flags_dict(inputs)
    return (
        "exact-base-song-context-v1",
        int(TOTAL_GEM_BUDGET),
        int(GEM_SCALE_FEVER),
        song_context._lane_weight(flags, "ft", int(GEM_SCALE_FEVER)),
        song_context._lane_weight(flags, "ff", int(GEM_SCALE_FEVER)),
        song_context._lane_weight(flags, "ov", 6),
        int(pack_count),
    )


def _context_arrays(context: song_context.ExactBaseSongContext) -> Iterator[np.ndarray]:
    response = context.program_map.response_table
    for name in (
        "cells",
        "cell_to_row",
        "offsets_by_row",
        "lengths_by_row",
        "flat_ft",
        "flat_ff",
    ):
        yield np.asarray(getattr(response, name))
    for container in (
        context.program_map,
        context.physical_programs,
        context.class_programs,
        context.multiplier_bounds,
    ):
        for field in fields(container):
            value = getattr(container, field.name)
            if isinstance(value, np.ndarray):
                yield value


def _validate_response_table(
    table: TimingResponseAntichainTable,
    inputs: _SemanticInputs,
) -> None:
    row_count = _GRID * _GRID
    cells = np.asarray(table.cells)
    cell_to_row = np.asarray(table.cell_to_row)
    offsets = np.asarray(table.offsets_by_row)
    lengths = np.asarray(table.lengths_by_row)
    flat_ft = np.asarray(table.flat_ft)
    flat_ff = np.asarray(table.flat_ff)
    arrays = (cells, cell_to_row, offsets, lengths, flat_ft, flat_ff)
    if any(array.dtype != np.dtype(np.int32) for array in arrays):
        raise ValueError("Timing-response cache arrays must use int32")
    if cells.shape != (row_count,) or cell_to_row.shape != (row_count,):
        raise ValueError("Timing-response cache does not cover the exact stat grid")
    expected_rows = np.arange(row_count, dtype=np.int32)
    if not np.array_equal(cells, expected_rows) or not np.array_equal(cell_to_row, expected_rows):
        raise ValueError("Timing-response cache rows are not the canonical all-cell order")
    if offsets.shape != (row_count + 1,) or lengths.shape != (row_count,):
        raise ValueError("Timing-response cache row metadata has an invalid shape")
    if int(offsets[0]) != 0 or np.any(np.diff(offsets.astype(np.int64, copy=False)) <= 0):
        raise ValueError("Timing-response cache offsets contain an empty or invalid row")
    if not np.array_equal(np.diff(offsets), lengths):
        raise ValueError("Timing-response cache offsets and lengths disagree")
    kept_count = int(offsets[-1])
    if flat_ft.shape != (kept_count,) or flat_ff.shape != (kept_count,):
        raise ValueError("Timing-response cache FT/FF arrays are not aligned")
    if np.any(flat_ft < 0) or np.any(flat_ff < 0):
        raise ValueError("Timing-response cache contains a negative gem count")
    if np.any(flat_ft.astype(np.int64) + flat_ff.astype(np.int64) > int(TOTAL_GEM_BUDGET)):
        raise ValueError("Timing-response cache overspends the gem budget")
    if int(table.kept_combo_count) != kept_count:
        raise ValueError("Timing-response cache kept-count metadata disagrees with its arrays")
    if int(table.legal_combo_count) < kept_count:
        raise ValueError("Timing-response cache legal-count metadata is too small")
    if int(table.max_len) != int(np.max(lengths)):
        raise ValueError("Timing-response cache max length disagrees with its rows")
    if int(table.pack_count) <= 0:
        raise ValueError("Timing-response cache must contain at least one timeline pack")
    expected_key = _expected_response_cache_key(inputs, pack_count=int(table.pack_count))
    if tuple(table.cache_key) != expected_key:
        raise ValueError("Timing-response cache key disagrees with exact-context inputs")
    if any(array.flags.writeable for array in arrays):
        raise ValueError("Timing-response cache arrays must be read-only")


def _validate_context_matches_inputs(
    context: song_context.ExactBaseSongContext,
    inputs: _SemanticInputs,
) -> None:
    if not isinstance(context, song_context.ExactBaseSongContext):
        raise TypeError("Exact Base song-context cache can store only ExactBaseSongContext values")
    _validate_response_table(context.program_map.response_table, inputs)
    table = context.program_map.response_table
    if context.program_map.class_by_response_row.shape != table.cells.shape:
        raise ValueError("Timing-program classes are not aligned with cached response rows")
    expected_cell_programs = context.program_map.class_by_response_row[table.cell_to_row]
    if not np.array_equal(context.program_map.program_by_cell, expected_cell_programs):
        raise ValueError("Timing-program cell map disagrees with cached response classes")
    if context.physical_programs.surface_offsets.shape != (table.cells.shape[0] + 1,):
        raise ValueError("Physical score programs are not aligned with cached response rows")
    if not np.array_equal(context.multiplier_bounds.ref_cm, inputs.ref_cm):
        raise ValueError("Cached context CM references disagree with cache identity")
    if not np.array_equal(context.multiplier_bounds.ref_fm, inputs.ref_fm):
        raise ValueError("Cached context FM references disagree with cache identity")

    flags = _flags_dict(inputs)
    expected_stat_weight = max(
        song_context._lane_weight(flags, "cm", 3),
        song_context._lane_weight(flags, "fm", 3),
    )
    expected_overflow_weight = song_context._lane_weight(flags, "ov", 6)
    if int(context.stat_elemental_weight_max) != int(expected_stat_weight):
        raise ValueError("Cached context stat elemental weight disagrees with color flags")
    if int(context.overflow_elemental_weight) != int(expected_overflow_weight):
        raise ValueError("Cached context overflow elemental weight disagrees with color flags")

    physical = context.physical_programs
    note_totals = (
        physical.surface_body_fever.astype(np.int64)
        + physical.surface_body_normal.astype(np.int64)
        + physical.surface_head_normal.astype(np.int64)
        + physical.surface_head_fever.astype(np.int64)
    )
    if note_totals.size == 0 or np.any(note_totals != int(inputs.total_notes)):
        raise ValueError("Cached context physical programs disagree with song Total Notes")
    if any(array.flags.writeable for array in _context_arrays(context)):
        raise ValueError("Exact Base song-context arrays must be read-only")


def _bytes_array(value: str) -> np.ndarray:
    return np.frombuffer(value.encode("utf-8"), dtype=np.uint8).copy()


def _context_payload(
    context: song_context.ExactBaseSongContext,
    inputs: _SemanticInputs,
) -> dict[str, np.ndarray]:
    _validate_context_matches_inputs(context, inputs)
    response = context.program_map.response_table
    response_cache_key = tuple(response.cache_key)
    if len(response_cache_key) != 7 or not isinstance(response_cache_key[0], str):
        raise ValueError("Timing-response cache key has an invalid persisted shape")
    try:
        response_cache_key_ints = np.asarray(response_cache_key[1:], dtype=np.int64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Timing-response cache key contains a non-integer field") from exc

    payload: dict[str, np.ndarray] = {
        "file_schema": _bytes_array(_FILE_SCHEMA),
        "cache_version": _bytes_array(EXACT_BASE_SONG_CONTEXT_CACHE_VERSION),
        "cache_key_digest": _bytes_array(inputs.key_digest),
        "response_cache_key_name": _bytes_array(response_cache_key[0]),
        "response_cache_key_ints": response_cache_key_ints,
        "response_max_len": np.asarray(int(response.max_len), dtype=np.int64),
        "response_legal_combo_count": np.asarray(
            int(response.legal_combo_count), dtype=np.int64
        ),
        "response_kept_combo_count": np.asarray(
            int(response.kept_combo_count), dtype=np.int64
        ),
        "response_pack_count": np.asarray(int(response.pack_count), dtype=np.int64),
        "map_program_count": np.asarray(
            int(context.program_map.program_count), dtype=np.int64
        ),
        "stat_elemental_weight_max": np.asarray(
            int(context.stat_elemental_weight_max), dtype=np.int64
        ),
        "overflow_elemental_weight": np.asarray(
            int(context.overflow_elemental_weight), dtype=np.int64
        ),
        "multiplier_cache_file": _bytes_array(_multiplier_cache_file_name(inputs)),
        "multiplier_key_digest": _bytes_array(inputs.multiplier_key_digest),
    }
    for disk_name, (field_name, dtype) in _RESPONSE_ARRAY_FIELDS.items():
        payload[disk_name] = np.ascontiguousarray(getattr(response, field_name), dtype=dtype)
    for disk_name, (field_name, dtype) in _PROGRAM_MAP_ARRAY_FIELDS.items():
        payload[disk_name] = np.ascontiguousarray(
            getattr(context.program_map, field_name), dtype=dtype
        )
    for disk_name, (field_name, dtype) in _PHYSICAL_ARRAY_FIELDS.items():
        payload[disk_name] = np.ascontiguousarray(
            getattr(context.physical_programs, field_name), dtype=dtype
        )
    for disk_name, (field_name, dtype) in _CLASS_ARRAY_FIELDS.items():
        payload[disk_name] = np.ascontiguousarray(
            getattr(context.class_programs, field_name), dtype=dtype
        )
    if set(payload) != _CACHE_ARRAY_NAMES:
        raise RuntimeError("Exact Base song-context serializer schema is incomplete")
    return payload


def _read_typed_array(
    data: Any,
    name: str,
    dtype: np.dtype[Any],
    *,
    ndim: int | None = None,
) -> np.ndarray:
    array = np.asarray(data[name])
    if array.dtype != dtype:
        raise ExactBaseSongContextCacheError(
            f"Exact Base song-context cache field {name} has dtype {array.dtype}, expected {dtype}"
        )
    if ndim is not None and array.ndim != int(ndim):
        raise ExactBaseSongContextCacheError(
            f"Exact Base song-context cache field {name} has {array.ndim} dimensions, expected {ndim}"
        )
    return np.array(array, dtype=dtype, order="C", copy=True)


def _read_int_scalar(data: Any, name: str) -> int:
    array = _read_typed_array(data, name, np.dtype(np.int64), ndim=0)
    return int(array.item())


def _read_text(data: Any, name: str) -> str:
    raw = _read_typed_array(data, name, np.dtype(np.uint8), ndim=1)
    try:
        return raw.tobytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExactBaseSongContextCacheError(
            f"Exact Base song-context cache field {name} is not UTF-8"
        ) from exc


def exact_base_song_context_cache_file_is_complete(
    cache_file: str | os.PathLike[str],
) -> bool:
    """Validate one content-addressed song context and its shared multiplier artifact."""

    path = Path(cache_file)
    try:
        with np.load(path, allow_pickle=False) as data:
            if set(data.files) != _CACHE_ARRAY_NAMES:
                return False
            if _read_text(data, "file_schema") != _FILE_SCHEMA:
                return False
            if _read_text(data, "cache_version") != EXACT_BASE_SONG_CONTEXT_CACHE_VERSION:
                return False
            key_digest = _read_text(data, "cache_key_digest")
            if path.stem != key_digest:
                return False
            multiplier_digest = _read_text(data, "multiplier_key_digest")
            multiplier_file = _read_text(data, "multiplier_cache_file")
            if Path(multiplier_file).name != multiplier_file:
                return False
            if multiplier_file != f"exact_base_multiplier_bounds_{multiplier_digest}.npz":
                return False
            for disk_name, (_field_name, dtype) in _RESPONSE_ARRAY_FIELDS.items():
                _read_typed_array(data, disk_name, dtype, ndim=1)
            for disk_name, (_field_name, dtype) in _PROGRAM_MAP_ARRAY_FIELDS.items():
                _read_typed_array(data, disk_name, dtype, ndim=1)
            for disk_name, (_field_name, dtype) in _PHYSICAL_ARRAY_FIELDS.items():
                _read_typed_array(data, disk_name, dtype, ndim=1)
            for disk_name, (_field_name, dtype) in _CLASS_ARRAY_FIELDS.items():
                _read_typed_array(data, disk_name, dtype, ndim=1)
            for scalar_name in (
                "response_max_len",
                "response_legal_combo_count",
                "response_kept_combo_count",
                "response_pack_count",
                "map_program_count",
                "stat_elemental_weight_max",
                "overflow_elemental_weight",
            ):
                _read_int_scalar(data, scalar_name)

        multiplier_path = path.parent / multiplier_file
        with np.load(multiplier_path, allow_pickle=False) as data:
            if set(data.files) != _MULTIPLIER_CACHE_ARRAY_NAMES:
                return False
            if _read_text(data, "file_schema") != _MULTIPLIER_FILE_SCHEMA:
                return False
            if _read_text(data, "cache_version") != EXACT_BASE_SONG_CONTEXT_CACHE_VERSION:
                return False
            if _read_text(data, "multiplier_key_digest") != multiplier_digest:
                return False
            for disk_name, (field_name, dtype) in _MULTIPLIER_ARRAY_FIELDS.items():
                _read_typed_array(
                    data,
                    disk_name,
                    dtype,
                    ndim=1 if field_name.startswith("ref_") else 3,
                )
        return True
    except (EOFError, KeyError, OSError, TypeError, ValueError, OverflowError):
        return False


def _readonly(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


def _multiplier_cache_file_name(inputs: _SemanticInputs) -> str:
    return f"exact_base_multiplier_bounds_{inputs.multiplier_key_digest}.npz"


def _multiplier_payload(
    bounds: song_context.JointMultiplierBounds,
    inputs: _SemanticInputs,
) -> dict[str, np.ndarray]:
    if not np.array_equal(bounds.ref_cm, inputs.ref_cm):
        raise ValueError("Multiplier-bound CM references disagree with cache identity")
    if not np.array_equal(bounds.ref_fm, inputs.ref_fm):
        raise ValueError("Multiplier-bound FM references disagree with cache identity")
    payload = {
        "file_schema": _bytes_array(_MULTIPLIER_FILE_SCHEMA),
        "cache_version": _bytes_array(EXACT_BASE_SONG_CONTEXT_CACHE_VERSION),
        "multiplier_key_digest": _bytes_array(inputs.multiplier_key_digest),
    }
    for disk_name, (field_name, dtype) in _MULTIPLIER_ARRAY_FIELDS.items():
        payload[disk_name] = np.ascontiguousarray(getattr(bounds, field_name), dtype=dtype)
    if set(payload) != _MULTIPLIER_CACHE_ARRAY_NAMES:
        raise RuntimeError("Exact Base multiplier-bound serializer schema is incomplete")
    return payload


def _load_multiplier_bounds_from_path(
    path: Path,
    inputs: _SemanticInputs,
) -> song_context.JointMultiplierBounds | None:
    if not path.exists():
        return None
    memory_key = (str(path.resolve()), inputs.multiplier_key)
    with _multiplier_memory_cache_lock:
        cached = _multiplier_memory_cache.get(memory_key)
        if cached is not None:
            _multiplier_memory_cache.move_to_end(memory_key)
    if cached is not None:
        return cached
    try:
        with np.load(path, allow_pickle=False) as data:
            if set(data.files) != _MULTIPLIER_CACHE_ARRAY_NAMES:
                raise ExactBaseSongContextCacheError(
                    "Exact Base multiplier-bound cache schema mismatch"
                )
            if _read_text(data, "file_schema") != _MULTIPLIER_FILE_SCHEMA:
                raise ExactBaseSongContextCacheError(
                    "Exact Base multiplier-bound cache file schema is stale"
                )
            if _read_text(data, "cache_version") != EXACT_BASE_SONG_CONTEXT_CACHE_VERSION:
                raise ExactBaseSongContextCacheError(
                    "Exact Base multiplier-bound cache logic version is stale"
                )
            if _read_text(data, "multiplier_key_digest") != inputs.multiplier_key_digest:
                raise ExactBaseSongContextCacheError(
                    "Exact Base multiplier-bound cache semantic key does not match its path"
                )
            values = {
                field_name: _read_typed_array(
                    data,
                    disk_name,
                    dtype,
                    ndim=1 if field_name.startswith("ref_") else 3,
                )
                for disk_name, (field_name, dtype) in _MULTIPLIER_ARRAY_FIELDS.items()
            }
            bounds = song_context.JointMultiplierBounds(**values)
        if not np.array_equal(bounds.ref_cm, inputs.ref_cm):
            raise ExactBaseSongContextCacheError(
                "Exact Base multiplier-bound cache CM references disagree with its key"
            )
        if not np.array_equal(bounds.ref_fm, inputs.ref_fm):
            raise ExactBaseSongContextCacheError(
                "Exact Base multiplier-bound cache FM references disagree with its key"
            )
    except ExactBaseSongContextCacheError:
        raise
    except (EOFError, KeyError, OSError, TypeError, ValueError, OverflowError) as exc:
        raise ExactBaseSongContextCacheError(
            f"Exact Base multiplier-bound cache is corrupt: {path} ({exc})"
        ) from exc
    with _multiplier_memory_cache_lock:
        existing = _multiplier_memory_cache.get(memory_key)
        if existing is None:
            _multiplier_memory_cache[memory_key] = bounds
            existing = bounds
        _multiplier_memory_cache.move_to_end(memory_key)
        while len(_multiplier_memory_cache) > _MULTIPLIER_MEMORY_CACHE_MAX:
            _multiplier_memory_cache.popitem(last=False)
    return existing


def _store_multiplier_bounds_unlocked(
    root: Path,
    inputs: _SemanticInputs,
    bounds: song_context.JointMultiplierBounds,
) -> Path:
    path = root / _multiplier_cache_file_name(inputs)
    cached = _load_multiplier_bounds_from_path(path, inputs)
    if cached is not None:
        return path
    payload = _multiplier_payload(bounds, inputs)
    tmp = path.with_name(
        f"{path.stem}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp.npz"
    )
    try:
        np.savez_compressed(tmp, **payload)
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    with _multiplier_memory_cache_lock:
        memory_key = (str(path.resolve()), inputs.multiplier_key)
        _multiplier_memory_cache[memory_key] = bounds
        _multiplier_memory_cache.move_to_end(memory_key)
        while len(_multiplier_memory_cache) > _MULTIPLIER_MEMORY_CACHE_MAX:
            _multiplier_memory_cache.popitem(last=False)
    return path


def reset_exact_base_song_context_cache_memory() -> None:
    """Release shared multiplier-bound arrays held by the process-local disk-cache LRU."""

    with _multiplier_memory_cache_lock:
        _multiplier_memory_cache.clear()


def _load_context_from_path(
    path: Path,
    inputs: _SemanticInputs,
) -> song_context.ExactBaseSongContext | None:
    if not path.exists():
        return None
    try:
        with np.load(path, allow_pickle=False) as data:
            if set(data.files) != _CACHE_ARRAY_NAMES:
                missing = sorted(_CACHE_ARRAY_NAMES - set(data.files))
                extra = sorted(set(data.files) - _CACHE_ARRAY_NAMES)
                raise ExactBaseSongContextCacheError(
                    "Exact Base song-context cache schema mismatch: "
                    f"missing={missing} extra={extra}"
                )
            if _read_text(data, "file_schema") != _FILE_SCHEMA:
                raise ExactBaseSongContextCacheError(
                    "Exact Base song-context cache file schema is stale"
                )
            if _read_text(data, "cache_version") != EXACT_BASE_SONG_CONTEXT_CACHE_VERSION:
                raise ExactBaseSongContextCacheError(
                    "Exact Base song-context cache logic version is stale"
                )
            if _read_text(data, "cache_key_digest") != inputs.key_digest:
                raise ExactBaseSongContextCacheError(
                    "Exact Base song-context cache semantic key does not match its path"
                )
            multiplier_key_digest = _read_text(data, "multiplier_key_digest")
            multiplier_cache_file = _read_text(data, "multiplier_cache_file")
            if multiplier_key_digest != inputs.multiplier_key_digest:
                raise ExactBaseSongContextCacheError(
                    "Exact Base song-context multiplier key is stale"
                )
            if multiplier_cache_file != _multiplier_cache_file_name(inputs):
                raise ExactBaseSongContextCacheError(
                    "Exact Base song-context multiplier artifact name is stale"
                )
            if Path(multiplier_cache_file).name != multiplier_cache_file:
                raise ExactBaseSongContextCacheError(
                    "Exact Base song-context multiplier artifact name is not relative"
                )

            response_arrays = {
                field_name: _readonly(_read_typed_array(data, disk_name, dtype, ndim=1))
                for disk_name, (field_name, dtype) in _RESPONSE_ARRAY_FIELDS.items()
            }
            response_key_name = _read_text(data, "response_cache_key_name")
            response_key_ints = _read_typed_array(
                data,
                "response_cache_key_ints",
                np.dtype(np.int64),
                ndim=1,
            )
            if response_key_ints.shape != (6,):
                raise ExactBaseSongContextCacheError(
                    "Exact Base song-context response cache key has an invalid shape"
                )
            response_table = TimingResponseAntichainTable(
                **response_arrays,
                max_len=_read_int_scalar(data, "response_max_len"),
                legal_combo_count=_read_int_scalar(data, "response_legal_combo_count"),
                kept_combo_count=_read_int_scalar(data, "response_kept_combo_count"),
                pack_count=_read_int_scalar(data, "response_pack_count"),
                cache_key=(response_key_name, *(int(value) for value in response_key_ints)),
            )

            physical_values = {
                field_name: _read_typed_array(data, disk_name, dtype, ndim=1)
                for disk_name, (field_name, dtype) in _PHYSICAL_ARRAY_FIELDS.items()
            }
            class_values = {
                field_name: _read_typed_array(data, disk_name, dtype, ndim=1)
                for disk_name, (field_name, dtype) in _CLASS_ARRAY_FIELDS.items()
            }
            multiplier_bounds = _load_multiplier_bounds_from_path(
                path.parent / multiplier_cache_file,
                inputs,
            )
            if multiplier_bounds is None:
                raise ExactBaseSongContextCacheError(
                    "Exact Base song-context cache is missing its multiplier-bound artifact"
                )
            program_map = song_context.TimingProgramMap(
                response_table=response_table,
                class_by_response_row=_read_typed_array(
                    data,
                    "map_class_by_response_row",
                    np.dtype(np.int32),
                    ndim=1,
                ),
                program_by_cell=_read_typed_array(
                    data,
                    "map_program_by_cell",
                    np.dtype(np.int32),
                    ndim=1,
                ),
                program_count=_read_int_scalar(data, "map_program_count"),
            )
            context = song_context.ExactBaseSongContext(
                program_map=program_map,
                physical_programs=song_context.TimingBoundPrograms(**physical_values),
                class_programs=song_context.ProgramClassBoundPrograms(**class_values),
                multiplier_bounds=multiplier_bounds,
                stat_elemental_weight_max=_read_int_scalar(
                    data, "stat_elemental_weight_max"
                ),
                overflow_elemental_weight=_read_int_scalar(
                    data, "overflow_elemental_weight"
                ),
            )
        _validate_context_matches_inputs(context, inputs)
        return context
    except ExactBaseSongContextCacheError:
        raise
    except (EOFError, KeyError, OSError, TypeError, ValueError, OverflowError) as exc:
        raise ExactBaseSongContextCacheError(
            f"Exact Base song-context cache is corrupt: {path} ({exc})"
        ) from exc


def _manifest_entries(root: Path) -> dict[str, dict[str, Any]]:
    path = root / _MANIFEST_FILE_NAME
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        logger.warning("[ExactBaseContextCache] Ignoring corrupt manifest %s: %s", path, exc)
        return {}
    if not isinstance(payload, dict):
        return {}
    if payload.get("schema") != _MANIFEST_SCHEMA:
        return {}
    if payload.get("cache_version") != EXACT_BASE_SONG_CONTEXT_CACHE_VERSION:
        return {}
    entries = payload.get("entries", {})
    return dict(entries) if isinstance(entries, dict) else {}


def _manifest_entry_matches(root: Path, inputs: _SemanticInputs, path: Path) -> bool:
    entry = _manifest_entries(root).get(inputs.key_digest)
    if not isinstance(entry, dict) or entry.get("cache_file") != path.name:
        return False
    multiplier_path = root / _multiplier_cache_file_name(inputs)
    if entry.get("multiplier_cache_file") != multiplier_path.name:
        return False
    try:
        return (
            int(entry.get("cache_size", -1)) == int(path.stat().st_size)
            and int(entry.get("multiplier_cache_size", -1))
            == int(multiplier_path.stat().st_size)
        )
    except (OSError, TypeError, ValueError):
        return False


def _save_manifest_unlocked(root: Path, entries: dict[str, dict[str, Any]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    path = root / _MANIFEST_FILE_NAME
    tmp = path.with_name(
        f"{path.name}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp"
    )
    payload = {
        "schema": _MANIFEST_SCHEMA,
        "cache_version": EXACT_BASE_SONG_CONTEXT_CACHE_VERSION,
        "entries": entries,
    }
    try:
        tmp.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _record_manifest_entry_unlocked(
    root: Path,
    inputs: _SemanticInputs,
    path: Path,
) -> None:
    stat = path.stat()
    multiplier_path = root / _multiplier_cache_file_name(inputs)
    multiplier_stat = multiplier_path.stat()
    entries = _manifest_entries(root)
    entries[inputs.key_digest] = {
        "cache_file": path.name,
        "cache_size": int(stat.st_size),
        "multiplier_cache_file": multiplier_path.name,
        "multiplier_cache_size": int(multiplier_stat.st_size),
        "updated_at_ns": int(time.time_ns()),
    }
    _save_manifest_unlocked(root, entries)


def _ensure_manifest_entry(root: Path, inputs: _SemanticInputs, path: Path) -> None:
    if _manifest_entry_matches(root, inputs, path):
        return
    with FrontierBuildLock(root, label="exact_base_song_context"):
        if not path.exists():
            raise FileNotFoundError(
                f"Exact Base song-context cache disappeared while indexing it: {path}"
            )
        if not _manifest_entry_matches(root, inputs, path):
            _record_manifest_entry_unlocked(root, inputs, path)


def _store_context_unlocked(
    root: Path,
    path: Path,
    inputs: _SemanticInputs,
    context: song_context.ExactBaseSongContext,
) -> None:
    payload = _context_payload(context, inputs)
    root.mkdir(parents=True, exist_ok=True)
    _store_multiplier_bounds_unlocked(root, inputs, context.multiplier_bounds)
    tmp = path.with_name(
        f"{path.stem}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp.npz"
    )
    try:
        np.savez_compressed(tmp, **payload)
        os.replace(tmp, path)
        _record_manifest_entry_unlocked(root, inputs, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def build_exact_base_song_context_for_cache(
    context_inputs: song_context.ExactBaseSongContextInputs,
    timeline_payload: TimelineFrontierGridPayload,
) -> song_context.ExactBaseSongContext:
    """Build and validate one cacheable context without reading or writing disk state."""

    inputs = _semantic_inputs(context_inputs, timeline_payload)
    context = song_context.build_exact_base_song_context(context_inputs, timeline_payload)
    _validate_context_matches_inputs(context, inputs)
    return context


def store_exact_base_song_context(
    context_inputs: song_context.ExactBaseSongContextInputs,
    timeline_payload: TimelineFrontierGridPayload,
    context: song_context.ExactBaseSongContext,
    *,
    cache_dir: str | os.PathLike[str] | None = None,
) -> Path:
    """Atomically store one explicitly built context under the semantic cache key."""

    inputs = _semantic_inputs(context_inputs, timeline_payload)
    root = _cache_dir(cache_dir)
    path = root / f"{inputs.key_digest}.npz"
    _validate_context_matches_inputs(context, inputs)
    with FrontierBuildLock(root, label="exact_base_song_context_store"):
        _store_context_unlocked(root, path, inputs, context)
    return path


def load_exact_base_song_context(
    context_inputs: song_context.ExactBaseSongContextInputs,
    timeline_payload: TimelineFrontierGridPayload,
    *,
    cache_dir: str | os.PathLike[str] | None = None,
) -> song_context.ExactBaseSongContext | None:
    """Load a context, returning ``None`` only when its semantic artifact is absent."""

    inputs = _semantic_inputs(context_inputs, timeline_payload)
    path = _cache_dir(cache_dir) / f"{inputs.key_digest}.npz"
    return _load_context_from_path(path, inputs)


def exact_base_song_context_cache_info(
    context_inputs: song_context.ExactBaseSongContextInputs,
    timeline_payload: TimelineFrontierGridPayload,
    *,
    cache_dir: str | os.PathLike[str] | None = None,
) -> ExactBaseSongContextCacheInfo:
    """Fast manifest-backed readiness probe for startup prebuild planning."""

    inputs = _semantic_inputs(context_inputs, timeline_payload)
    root = _cache_dir(cache_dir)
    path = root / f"{inputs.key_digest}.npz"
    source: Literal["disk", "missing"] = (
        "disk" if _manifest_entry_matches(root, inputs, path) else "missing"
    )
    return ExactBaseSongContextCacheInfo(
        cache_key=inputs.cache_key,
        disk_path=path,
        cache_source=source,
    )


def load_prebuilt_exact_base_song_context(
    context_inputs: song_context.ExactBaseSongContextInputs,
    timeline_payload: TimelineFrontierGridPayload,
    *,
    cache_dir: str | os.PathLike[str] | None = None,
) -> ExactBaseSongContextCacheResult:
    """Load the startup-provisioned context without building a cache miss."""

    inputs = _semantic_inputs(context_inputs, timeline_payload)
    path = _cache_dir(cache_dir) / f"{inputs.key_digest}.npz"
    cached = _load_context_from_path(path, inputs)
    if cached is None:
        raise MissingFrontierCacheError(
            "Exact Base song-context artifact is missing. Startup cache prebuild must "
            f"provision it before scoring: {path}"
        )
    return ExactBaseSongContextCacheResult(
        context=cached,
        cache_key=inputs.cache_key,
        disk_path=path,
        cache_source="disk",
    )


def load_or_build_exact_base_song_context(
    context_inputs: song_context.ExactBaseSongContextInputs,
    timeline_payload: TimelineFrontierGridPayload,
    *,
    cache_dir: str | os.PathLike[str] | None = None,
) -> ExactBaseSongContextCacheResult:
    """Load one immutable context or build/store it under a cross-process build lock."""

    inputs = _semantic_inputs(context_inputs, timeline_payload)
    root = _cache_dir(cache_dir)
    path = root / f"{inputs.key_digest}.npz"
    cached = _load_context_from_path(path, inputs)
    if cached is not None:
        _ensure_manifest_entry(root, inputs, path)
        return ExactBaseSongContextCacheResult(
            context=cached,
            cache_key=inputs.cache_key,
            disk_path=path,
            cache_source="disk",
        )

    # Expensive context construction is serialized only per semantic song key.  Different songs
    # can prebuild concurrently; the short artifact/manifest write remains directory-serialized.
    with FrontierBuildLock(
        _entry_lock_dir(root, inputs),
        label=f"exact_base_song_context_{inputs.key_digest}",
    ):
        cached = _load_context_from_path(path, inputs)
        if cached is not None:
            _ensure_manifest_entry(root, inputs, path)
            return ExactBaseSongContextCacheResult(
                context=cached,
                cache_key=inputs.cache_key,
                disk_path=path,
                cache_source="disk",
            )
        context = song_context.build_exact_base_song_context(context_inputs, timeline_payload)
        _validate_context_matches_inputs(context, inputs)
        with FrontierBuildLock(root, label="exact_base_song_context_store"):
            # An explicit store may have won while this process built.  Keep the already validated
            # artifact instead of replacing it; both represent the same semantic key.
            cached = _load_context_from_path(path, inputs)
            if cached is not None:
                _record_manifest_entry_unlocked(root, inputs, path)
                return ExactBaseSongContextCacheResult(
                    context=cached,
                    cache_key=inputs.cache_key,
                    disk_path=path,
                    cache_source="disk",
                )
            _store_context_unlocked(root, path, inputs, context)
    return ExactBaseSongContextCacheResult(
        context=context,
        cache_key=inputs.cache_key,
        disk_path=path,
        cache_source="built",
    )


__all__ = [
    "EXACT_BASE_SONG_CONTEXT_CACHE_VERSION",
    "ExactBaseSongContextCacheError",
    "ExactBaseSongContextCacheInfo",
    "ExactBaseSongContextCacheResult",
    "build_exact_base_song_context_for_cache",
    "exact_base_song_context_cache_file_is_complete",
    "exact_base_song_context_cache_info",
    "exact_base_song_context_cache_key",
    "exact_base_song_context_cache_path",
    "exact_base_song_context_manifest_path",
    "load_exact_base_song_context",
    "load_or_build_exact_base_song_context",
    "load_prebuilt_exact_base_song_context",
    "reset_exact_base_song_context_cache_memory",
    "store_exact_base_song_context",
]
