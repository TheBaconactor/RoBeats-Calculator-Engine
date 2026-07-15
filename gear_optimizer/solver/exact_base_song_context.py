"""CPU preparation for the exact Base timing-program quotient.

This module turns one canonical timeline-frontier payload into immutable host arrays used by
the exact Base search.  It deliberately stops at NumPy/Numba data: timeline persistence, Taichi
uploads, GPU kernels, and pipeline ownership live elsewhere.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NamedTuple

import numpy as np
from numba import njit

from gear_optimizer.core.constants import GEM_SCALE_FEVER, MAX_STAT_INDEX, TOTAL_GEM_BUDGET
from gear_optimizer.solver import timing_response_antichain
from gear_optimizer.solver.ftff_combos import ftff_combo_arrays

if TYPE_CHECKING:
    from gear_optimizer.solver.solver_common import SolverContext
    from gear_optimizer.solver.timeline_exact_frontier import TimelineFrontierGridPayload


_GRID = int(MAX_STAT_INDEX) + 1
_MAX_TIMELINE_HEAD = 100
_COLOR_FLAG_KEYS = (
    "is_p_ft",
    "is_s_ft",
    "is_p_ff",
    "is_s_ff",
    "is_p_pp",
    "is_s_pp",
    "is_p_cm",
    "is_s_cm",
    "is_p_fm",
    "is_s_fm",
    "is_p_ov",
    "is_s_ov",
)


def _readonly_array(value: Any, dtype: np.dtype[Any] | type[Any]) -> np.ndarray:
    array = np.array(value, dtype=dtype, order="C", copy=True)
    array.setflags(write=False)
    return array


@dataclass(frozen=True, slots=True)
class ExactBaseSongContextInputs:
    """Catalog-independent semantic inputs for one song's exact Base context."""

    calc_song: dict[str, Any]
    ref_arrays: dict[str, Any]
    color_flags: dict[str, int]

    def __post_init__(self) -> None:
        if not isinstance(self.calc_song, dict) or not self.calc_song:
            raise TypeError("Exact Base song-context calc_song must be a non-empty dict")
        if not isinstance(self.ref_arrays, dict) or not self.ref_arrays:
            raise TypeError("Exact Base song-context ref_arrays must be a non-empty dict")
        object.__setattr__(self, "calc_song", dict(self.calc_song))
        object.__setattr__(self, "ref_arrays", dict(self.ref_arrays))
        object.__setattr__(
            self,
            "color_flags",
            _validated_color_flags(dict(self.color_flags or {})),
        )

    @classmethod
    def from_solver_context(cls, context: SolverContext) -> ExactBaseSongContextInputs:
        """Project the catalog-bearing runtime context onto the semantic cache surface."""

        return cls(
            calc_song=context.calc_song,
            ref_arrays=context.ref_arrays,
            color_flags=context.color_flags,
        )


def _validate_program_offsets(offsets: np.ndarray, entry_count: int, *, label: str) -> None:
    if offsets.ndim != 1 or offsets.shape[0] < 2:
        raise ValueError(f"{label} offsets must contain at least one row")
    if int(offsets[0]) != 0 or int(offsets[-1]) != int(entry_count):
        raise ValueError(f"{label} offsets do not span the aligned program arrays")
    if np.any(np.diff(offsets.astype(np.int64, copy=False)) <= 0):
        raise ValueError(f"{label} offsets contain an empty or invalid row")


def _validate_physical_program_arrays(
    *,
    budget: np.ndarray,
    direct: np.ndarray,
    body_fever: np.ndarray,
    body_normal: np.ndarray,
    head_normal: np.ndarray,
    head_fever: np.ndarray,
    sigma_normal: np.ndarray,
    sigma_fever: np.ndarray,
    label: str,
) -> None:
    arrays = (
        budget,
        direct,
        body_fever,
        body_normal,
        head_normal,
        head_fever,
        sigma_normal,
        sigma_fever,
    )
    entry_count = int(budget.shape[0])
    if any(array.ndim != 1 or array.shape != (entry_count,) for array in arrays):
        raise ValueError(f"{label} arrays are not one-dimensional and aligned")
    if entry_count <= 0:
        raise ValueError(f"{label} must contain at least one program")
    if np.any(budget < 0) or np.any(budget > int(TOTAL_GEM_BUDGET)):
        raise ValueError(f"{label} gem budgets are outside the legal range")
    if any(np.any(array < 0) for array in arrays[1:]):
        raise ValueError(f"{label} contains a negative physical coefficient")

    head_len = head_normal.astype(np.int64) + head_fever.astype(np.int64)
    sigma_total = sigma_normal.astype(np.int64) + sigma_fever.astype(np.int64)
    if np.any(sigma_total != (head_len * (head_len + 1)) // 2):
        raise ValueError(f"{label} sigma lanes do not partition the timing head")
    note_total = head_len + body_fever.astype(np.int64) + body_normal.astype(np.int64)
    if np.any(note_total <= 0) or np.any(note_total != note_total[0]):
        raise ValueError(f"{label} entries do not describe one physical song")


@dataclass(frozen=True, slots=True)
class TimingBoundPrograms:
    """Full physical score programs, grouped by timing-response row."""

    surface_offsets: np.ndarray
    surface_budget: np.ndarray
    surface_direct: np.ndarray
    surface_body_fever: np.ndarray
    surface_body_normal: np.ndarray
    surface_head_normal: np.ndarray
    surface_head_fever: np.ndarray
    surface_sigma_normal: np.ndarray
    surface_sigma_fever: np.ndarray

    def __post_init__(self) -> None:
        object.__setattr__(self, "surface_offsets", _readonly_array(self.surface_offsets, np.int32))
        object.__setattr__(self, "surface_budget", _readonly_array(self.surface_budget, np.int16))
        for name in (
            "surface_direct",
            "surface_body_fever",
            "surface_body_normal",
            "surface_head_normal",
            "surface_head_fever",
            "surface_sigma_normal",
            "surface_sigma_fever",
        ):
            object.__setattr__(self, name, _readonly_array(getattr(self, name), np.int32))
        _validate_program_offsets(
            self.surface_offsets,
            int(self.surface_budget.shape[0]),
            label="Timing-bound program",
        )
        _validate_physical_program_arrays(
            budget=self.surface_budget,
            direct=self.surface_direct,
            body_fever=self.surface_body_fever,
            body_normal=self.surface_body_normal,
            head_normal=self.surface_head_normal,
            head_fever=self.surface_head_fever,
            sigma_normal=self.surface_sigma_normal,
            sigma_fever=self.surface_sigma_fever,
            label="Timing-bound program",
        )


@dataclass(frozen=True, slots=True)
class ProgramClassBoundPrograms:
    """One physical score-program row per complete timing-program class."""

    program_offsets: np.ndarray
    program_budget: np.ndarray
    program_direct: np.ndarray
    program_body_fever: np.ndarray
    program_body_normal: np.ndarray
    program_head_normal: np.ndarray
    program_head_fever: np.ndarray
    program_sigma_normal: np.ndarray
    program_sigma_fever: np.ndarray

    def __post_init__(self) -> None:
        for name in (
            "program_offsets",
            "program_budget",
            "program_direct",
            "program_body_fever",
            "program_body_normal",
            "program_head_normal",
            "program_head_fever",
            "program_sigma_normal",
            "program_sigma_fever",
        ):
            object.__setattr__(self, name, _readonly_array(getattr(self, name), np.int32))
        _validate_program_offsets(
            self.program_offsets,
            int(self.program_budget.shape[0]),
            label="Program-class bound",
        )
        _validate_physical_program_arrays(
            budget=self.program_budget,
            direct=self.program_direct,
            body_fever=self.program_body_fever,
            body_normal=self.program_body_normal,
            head_normal=self.program_head_normal,
            head_fever=self.program_head_fever,
            sigma_normal=self.program_sigma_normal,
            sigma_fever=self.program_sigma_fever,
            label="Program-class bound",
        )


@dataclass(frozen=True, slots=True)
class TimingProgramMap:
    """Dense all-cell map from FT/FF start cell to complete timing-program class."""

    response_table: timing_response_antichain.TimingResponseAntichainTable
    class_by_response_row: np.ndarray
    program_by_cell: np.ndarray
    program_count: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "class_by_response_row",
            _readonly_array(self.class_by_response_row, np.int32),
        )
        object.__setattr__(
            self,
            "program_by_cell",
            _readonly_array(self.program_by_cell, np.int32),
        )
        table = self.response_table
        cells = np.asarray(table.cells, dtype=np.int32)
        expected_cells = np.arange(_GRID * _GRID, dtype=np.int32)
        if not np.array_equal(cells, expected_cells):
            raise ValueError("Exact Base timing responses must cover every start cell in order")
        if self.class_by_response_row.shape != cells.shape:
            raise ValueError("Timing-program classes are not aligned with response rows")
        if self.program_by_cell.shape != (_GRID * _GRID,):
            raise ValueError("Timing-program cell map does not cover the stat grid")
        program_count = int(self.program_count)
        if program_count <= 0:
            raise ValueError("Timing-program map must contain at least one class")
        if not np.array_equal(
            np.unique(self.class_by_response_row),
            np.arange(program_count, dtype=np.int32),
        ):
            raise ValueError("Timing-program class IDs must be dense from zero")
        if np.any(self.program_by_cell < 0) or np.any(self.program_by_cell >= program_count):
            raise ValueError("Timing-program cell map contains an invalid class ID")
        table_arrays = (
            table.cells,
            table.cell_to_row,
            table.offsets_by_row,
            table.lengths_by_row,
            table.flat_ft,
            table.flat_ff,
        )
        if any(np.asarray(array).flags.writeable for array in table_arrays):
            raise ValueError("Timing-response table arrays must be read-only")


@dataclass(frozen=True, slots=True)
class JointMultiplierBounds:
    """CM/FM upper-bound tables that spend each remaining normal gem once."""

    ref_cm: np.ndarray
    ref_fm: np.ndarray
    joint_cm_fm: np.ndarray
    joint_cm_span_fm: np.ndarray

    def __post_init__(self) -> None:
        object.__setattr__(self, "ref_cm", _readonly_array(self.ref_cm, np.float64))
        object.__setattr__(self, "ref_fm", _readonly_array(self.ref_fm, np.float64))
        object.__setattr__(
            self,
            "joint_cm_fm",
            _readonly_array(self.joint_cm_fm, np.float64),
        )
        object.__setattr__(
            self,
            "joint_cm_span_fm",
            _readonly_array(self.joint_cm_span_fm, np.float64),
        )
        expected_refs = (_GRID,)
        expected_tables = (_GRID, _GRID, int(TOTAL_GEM_BUDGET) + 1)
        if self.ref_cm.shape != expected_refs or self.ref_fm.shape != expected_refs:
            raise ValueError("CM/FM references do not match the exact stat grid")
        if self.joint_cm_fm.shape != expected_tables:
            raise ValueError("Joint CM/FM multiplier table has an invalid shape")
        if self.joint_cm_span_fm.shape != expected_tables:
            raise ValueError("Joint CM-span/FM multiplier table has an invalid shape")
        arrays = (self.ref_cm, self.ref_fm, self.joint_cm_fm, self.joint_cm_span_fm)
        if any(not np.all(np.isfinite(array)) for array in arrays):
            raise ValueError("CM/FM multiplier bounds contain non-finite values")


@dataclass(frozen=True, slots=True)
class ExactBaseSongContext:
    """Immutable CPU context shared by one song's exact Base search."""

    program_map: TimingProgramMap
    physical_programs: TimingBoundPrograms
    class_programs: ProgramClassBoundPrograms
    multiplier_bounds: JointMultiplierBounds
    stat_elemental_weight_max: int
    overflow_elemental_weight: int

    def __post_init__(self) -> None:
        if int(self.stat_elemental_weight_max) < 0:
            raise ValueError("Stat elemental weight must be nonnegative")
        if int(self.overflow_elemental_weight) < 0:
            raise ValueError("Overflow elemental weight must be nonnegative")
        if int(self.program_map.program_count) + 1 != int(
            self.class_programs.program_offsets.shape[0]
        ):
            raise ValueError("Program map and class-bound programs disagree on class count")


class _TimelineArrays(NamedTuple):
    counts: np.ndarray
    pool_offsets: np.ndarray
    body_fever: np.ndarray
    body_normal: np.ndarray
    masks: np.ndarray
    head_coeffs: np.ndarray
    head_lengths: np.ndarray
    pool_used: int


def _slot_array(
    payload: TimelineFrontierGridPayload,
    name: str,
    *,
    dtype: np.dtype[Any] | type[Any],
    dimensions: int,
) -> np.ndarray:
    try:
        value = getattr(payload, name)
    except AttributeError as exc:
        raise TypeError(f"Timeline frontier payload is missing {name}") from exc
    array = np.asarray(value, dtype=dtype)
    if array.ndim != int(dimensions) or int(array.shape[0]) != 1:
        raise ValueError(
            f"Timeline frontier {name} must have one leading song slot and "
            f"{dimensions} dimensions, got {array.shape}"
        )
    return array[0]


def _timeline_arrays(payload: TimelineFrontierGridPayload) -> _TimelineArrays:
    counts = _slot_array(payload, "grid_frontier_count", dtype=np.int32, dimensions=3)
    pool_offsets = _slot_array(payload, "grid_frontier_offset", dtype=np.int32, dimensions=3)
    body_fever = _slot_array(
        payload,
        "grid_frontier_body_fever_pool",
        dtype=np.int32,
        dimensions=2,
    )
    body_normal = _slot_array(
        payload,
        "grid_frontier_body_normal_pool",
        dtype=np.int32,
        dimensions=2,
    )
    masks = _slot_array(
        payload,
        "grid_frontier_masks_bits_pool",
        dtype=np.uint32,
        dimensions=3,
    )
    head_coeffs = _slot_array(
        payload,
        "grid_frontier_head_coeffs_pool",
        dtype=np.int32,
        dimensions=3,
    )
    head_lengths = _slot_array(payload, "grid_head_len", dtype=np.int32, dimensions=3)
    if counts.shape != (_GRID, _GRID) or pool_offsets.shape != (_GRID, _GRID):
        raise ValueError("Timeline frontier grid does not match the exact stat grid")
    if head_lengths.shape != (_GRID, _GRID):
        raise ValueError("Timeline head-length grid does not match the exact stat grid")
    if masks.ndim != 2 or masks.shape[1] < 4:
        raise ValueError("Timeline frontier masks are missing head-mask words")
    if head_coeffs.ndim != 2 or head_coeffs.shape[1] < 4:
        raise ValueError("Timeline frontier head coefficients are missing count/sigma lanes")
    pool_used = int(payload.frontier_pool_used)
    pool_capacities = (
        int(body_fever.shape[0]),
        int(body_normal.shape[0]),
        int(masks.shape[0]),
        int(head_coeffs.shape[0]),
    )
    if pool_used <= 0 or any(pool_used > capacity for capacity in pool_capacities):
        raise ValueError("Timeline frontier reports an invalid used-pool length")
    return _TimelineArrays(
        counts=counts,
        pool_offsets=pool_offsets,
        body_fever=body_fever,
        body_normal=body_normal,
        masks=masks,
        head_coeffs=head_coeffs,
        head_lengths=head_lengths,
        pool_used=pool_used,
    )


def _validated_color_flags(raw_flags: dict[str, int]) -> dict[str, int]:
    flags = {name: int(raw_flags.get(name, 0) or 0) for name in _COLOR_FLAG_KEYS}
    if any(value not in (0, 1) for value in flags.values()):
        raise ValueError(f"Exact Base color flags must be binary, got {flags}")
    return flags


def _lane_weight(flags: dict[str, int], stat: str, scale: int) -> int:
    return int(scale) * ((2 * int(flags[f"is_p_{stat}"])) + int(flags[f"is_s_{stat}"]))


def _frontier_pack_grid(timeline: _TimelineArrays) -> tuple[np.ndarray, int]:
    pack_to_id: dict[tuple[Any, ...], int] = {}
    cell_pack = np.empty((_GRID, _GRID), dtype=np.int32)
    for ft in range(_GRID):
        for ff in range(_GRID):
            count = int(timeline.counts[ft, ff])
            offset = int(timeline.pool_offsets[ft, ff])
            end = offset + count
            if count <= 0 or offset < 0 or end > int(timeline.pool_used):
                raise ValueError(
                    f"Timeline frontier cell ({ft}, {ff}) has invalid pool range "
                    f"[{offset}, {end})"
                )
            head_len = int(timeline.head_lengths[ft, ff])
            if head_len < 0 or head_len > _MAX_TIMELINE_HEAD:
                raise ValueError(
                    f"Timeline frontier cell ({ft}, {ff}) has invalid head length {head_len}"
                )
            surfaces = tuple(
                (
                    int(timeline.masks[pool_idx, 0]),
                    int(timeline.masks[pool_idx, 1]),
                    int(timeline.masks[pool_idx, 2]),
                    int(timeline.masks[pool_idx, 3]),
                    int(timeline.body_fever[pool_idx]),
                    int(timeline.body_normal[pool_idx]),
                )
                for pool_idx in range(offset, end)
            )
            key = (head_len, surfaces)
            pack_id = pack_to_id.get(key)
            if pack_id is None:
                pack_id = len(pack_to_id)
                pack_to_id[key] = int(pack_id)
            cell_pack[ft, ff] = int(pack_id)
    return np.ascontiguousarray(cell_pack), int(len(pack_to_id))


def _validate_response_references(ref_arrays: dict[str, Any]) -> None:
    for name in ("Perfect Points", "Combo Multiplier", "Fever Multiplier"):
        references = np.asarray(ref_arrays.get(name), dtype=np.float64).reshape(-1)
        if references.shape[0] < _GRID:
            raise ValueError(f"{name} references do not cover the exact stat grid")
        references = references[:_GRID]
        if not np.all(np.isfinite(references)):
            raise ValueError(f"{name} references contain non-finite values")
        if np.any(np.diff(references) < 0.0):
            raise ValueError(f"{name} references must be nondecreasing")


def _build_all_cell_response_table(
    *,
    ref_arrays: dict[str, Any],
    flags: dict[str, int],
    cell_pack: np.ndarray,
    pack_count: int,
) -> timing_response_antichain.TimingResponseAntichainTable:
    _validate_response_references(ref_arrays)
    if cell_pack.shape != (_GRID, _GRID):
        raise ValueError("Timeline pack grid does not match the exact stat grid")
    cells = np.arange(_GRID * _GRID, dtype=np.int32)
    offsets = np.zeros(int(cells.shape[0]) + 1, dtype=np.int32)
    lengths = np.zeros(cells.shape[0], dtype=np.int32)
    ft_weight = _lane_weight(flags, "ft", int(GEM_SCALE_FEVER))
    ff_weight = _lane_weight(flags, "ff", int(GEM_SCALE_FEVER))
    overflow_weight = _lane_weight(flags, "ov", 6)

    # NOTE: this function spans ALL 25,921 cells (tens of millions of combos);
    # a single batched keep-mask lexsort measured 5x SLOWER than the per-cell
    # loop here, so unlike the antichain builder this loop stays per-cell.
    flat_ft_parts: list[np.ndarray] = []
    flat_ff_parts: list[np.ndarray] = []
    legal_total = 0
    kept_total = 0
    max_len = 0
    for row, cell in enumerate(cells.tolist()):
        start_ft = int(cell) // _GRID
        start_ff = int(cell) % _GRID
        cap_ft = max(0, (int(MAX_STAT_INDEX) - start_ft) // int(GEM_SCALE_FEVER))
        cap_ff = max(0, (int(MAX_STAT_INDEX) - start_ff) // int(GEM_SCALE_FEVER))
        ft, ff, remaining = ftff_combo_arrays(
            int(TOTAL_GEM_BUDGET),
            max_ft_gems=int(cap_ft),
            max_ff_gems=int(cap_ff),
        )
        if ft.size == 0:
            raise RuntimeError(f"Start cell {cell} has no legal FT/FF allocation")
        final_ft = np.minimum(
            int(MAX_STAT_INDEX),
            start_ft + ft.astype(np.int32, copy=False) * int(GEM_SCALE_FEVER),
        )
        final_ff = np.minimum(
            int(MAX_STAT_INDEX),
            start_ff + ff.astype(np.int32, copy=False) * int(GEM_SCALE_FEVER),
        )
        packs = cell_pack[final_ft, final_ff].astype(np.int32, copy=False)
        lane_value = (
            int(ft_weight) * ft.astype(np.int32, copy=False)
            + int(ff_weight) * ff.astype(np.int32, copy=False)
            + int(overflow_weight) * remaining.astype(np.int32, copy=False)
        )
        keep = timing_response_antichain.timing_response_antichain_keep_mask(
            packs=packs,
            remaining=remaining,
            lane_value=lane_value,
        )
        kept_ft = np.ascontiguousarray(ft[keep], dtype=np.int32)
        kept_ff = np.ascontiguousarray(ff[keep], dtype=np.int32)
        if kept_ft.size == 0:
            raise RuntimeError(f"Start cell {cell} has an empty exact timing antichain")
        flat_ft_parts.append(kept_ft)
        flat_ff_parts.append(kept_ff)
        legal_total += int(ft.shape[0])
        kept = int(kept_ft.shape[0])
        kept_total += kept
        lengths[row] = kept
        max_len = max(max_len, kept)
        offsets[row + 1] = kept_total

    flat_ft = np.concatenate(flat_ft_parts).astype(np.int32, copy=False)
    flat_ff = np.concatenate(flat_ff_parts).astype(np.int32, copy=False)
    cell_to_row = np.arange(_GRID * _GRID, dtype=np.int32)
    arrays = (cells, cell_to_row, offsets, lengths, flat_ft, flat_ff)
    for array in arrays:
        array.setflags(write=False)
    return timing_response_antichain.TimingResponseAntichainTable(
        cells=cells,
        cell_to_row=cell_to_row,
        offsets_by_row=offsets,
        lengths_by_row=lengths,
        flat_ft=flat_ft,
        flat_ff=flat_ff,
        max_len=int(max_len),
        legal_combo_count=int(legal_total),
        kept_combo_count=int(kept_total),
        pack_count=int(pack_count),
        cache_key=(
            "exact-base-song-context-v1",
            int(TOTAL_GEM_BUDGET),
            int(GEM_SCALE_FEVER),
            int(ft_weight),
            int(ff_weight),
            int(overflow_weight),
            int(pack_count),
        ),
    )


def _timing_program_classes(
    *,
    response_table: timing_response_antichain.TimingResponseAntichainTable,
    cell_pack: np.ndarray,
    flags: dict[str, int],
) -> tuple[np.ndarray, int]:
    ft_weight = _lane_weight(flags, "ft", int(GEM_SCALE_FEVER))
    ff_weight = _lane_weight(flags, "ff", int(GEM_SCALE_FEVER))
    class_by_row = np.empty(int(response_table.cells.shape[0]), dtype=np.int32)
    signature_to_class: dict[bytes, int] = {}

    # NOTE: stays per-row on purpose - a single global lexsort over every
    # row's combos measured SLOWER than the per-row sorts at monster-chart
    # scale (tens of millions of combos), same lesson as the all-cell
    # response-table loop above.
    for row, cell in enumerate(np.asarray(response_table.cells, dtype=np.int32).tolist()):
        offset = int(response_table.offsets_by_row[row])
        length = int(response_table.lengths_by_row[row])
        end = offset + length
        if length <= 0 or offset < 0 or end > int(response_table.flat_ft.shape[0]):
            raise ValueError(f"Timing-response row {row} has an invalid FT combo range")
        if end > int(response_table.flat_ff.shape[0]):
            raise ValueError(f"Timing-response row {row} has misaligned FT/FF combos")
        ft = np.asarray(response_table.flat_ft[offset:end], dtype=np.int32)
        ff = np.asarray(response_table.flat_ff[offset:end], dtype=np.int32)
        start_ft = int(cell) // _GRID
        start_ff = int(cell) % _GRID
        final_ft = np.minimum(
            int(MAX_STAT_INDEX),
            start_ft + int(GEM_SCALE_FEVER) * ft,
        )
        final_ff = np.minimum(
            int(MAX_STAT_INDEX),
            start_ff + int(GEM_SCALE_FEVER) * ff,
        )
        packs = cell_pack[final_ft, final_ff].astype(np.int32, copy=False)
        remaining = (int(TOTAL_GEM_BUDGET) - ft - ff).astype(np.int32, copy=False)
        if np.any(remaining < 0):
            raise ValueError(f"Timing-response row {row} overspends the gem budget")
        direct_lane = (int(ft_weight) * ft + int(ff_weight) * ff).astype(
            np.int32,
            copy=False,
        )
        triples = np.column_stack((packs, remaining, direct_lane)).astype(
            np.int32,
            copy=False,
        )
        order = np.lexsort((triples[:, 2], triples[:, 1], triples[:, 0]))
        triples = np.ascontiguousarray(triples[order], dtype=np.int32)
        if int(triples.shape[0]) > 1:
            unique = np.ones(int(triples.shape[0]), dtype=np.bool_)
            unique[1:] = np.any(triples[1:] != triples[:-1], axis=1)
            triples = np.ascontiguousarray(triples[unique], dtype=np.int32)
        signature = triples.tobytes()
        class_id = signature_to_class.get(signature)
        if class_id is None:
            class_id = len(signature_to_class)
            signature_to_class[signature] = int(class_id)
        class_by_row[row] = int(class_id)
    return np.ascontiguousarray(class_by_row), int(len(signature_to_class))


def _build_program_map(
    *,
    ref_arrays: dict[str, Any],
    flags: dict[str, int],
    timeline: _TimelineArrays,
) -> TimingProgramMap:
    cell_pack, pack_count = _frontier_pack_grid(timeline)
    response_table = _build_all_cell_response_table(
        ref_arrays=ref_arrays,
        flags=flags,
        cell_pack=cell_pack,
        pack_count=pack_count,
    )
    class_by_row, program_count = _timing_program_classes(
        response_table=response_table,
        cell_pack=cell_pack,
        flags=flags,
    )
    program_by_cell = class_by_row[response_table.cell_to_row]
    return TimingProgramMap(
        response_table=response_table,
        class_by_response_row=class_by_row,
        program_by_cell=program_by_cell,
        program_count=program_count,
    )


def _timing_bound_programs(
    *,
    calc_song: dict[str, Any],
    flags: dict[str, int],
    response_table: timing_response_antichain.TimingResponseAntichainTable,
    timeline: _TimelineArrays,
) -> TimingBoundPrograms:
    metadata = dict((calc_song or {}).get("metadata", {}) or {})
    if "Total Notes" not in metadata:
        raise ValueError("Song metadata is missing Total Notes for exact Base score programs")
    expected_total_notes = int(metadata["Total Notes"])
    if expected_total_notes <= 0:
        raise ValueError(f"Song Total Notes must be positive, got {expected_total_notes}")

    ft_weight = _lane_weight(flags, "ft", int(GEM_SCALE_FEVER))
    ff_weight = _lane_weight(flags, "ff", int(GEM_SCALE_FEVER))

    # Fully vectorized rebuild of the historical (row -> combo -> pool-entry)
    # loop. Every guard below checks the same invariant as the historical
    # per-item loop; when several DIFFERENT invariants are violated at once
    # the first reported row may differ (each guard scans all rows), which is
    # acceptable for impossible-state guards.
    cells = np.asarray(response_table.cells, dtype=np.int64)
    row_count = int(cells.shape[0])
    combo_offsets = np.asarray(response_table.offsets_by_row, dtype=np.int64)[:row_count]
    combo_lengths = np.asarray(response_table.lengths_by_row, dtype=np.int64)
    combo_ends = combo_offsets + combo_lengths

    bad = (combo_lengths <= 0) | (combo_offsets < 0)
    if np.any(bad):
        row = int(np.argmax(bad))
        raise ValueError(f"Timing-response row {row} has no score-bound entries")
    bad = combo_ends > int(np.asarray(response_table.flat_ft).shape[0])
    if np.any(bad):
        row = int(np.argmax(bad))
        raise ValueError(f"Timing-response row {row} points outside the FT combo table")
    bad = combo_ends > int(np.asarray(response_table.flat_ff).shape[0])
    if np.any(bad):
        row = int(np.argmax(bad))
        raise ValueError(f"Timing-response row {row} points outside the FF combo table")

    total_combos = int(combo_lengths.sum())
    combo_row = np.repeat(np.arange(row_count, dtype=np.int32), combo_lengths)
    combo_starts = np.cumsum(combo_lengths) - combo_lengths
    combo_index = np.repeat(combo_offsets, combo_lengths) + (
        np.arange(total_combos, dtype=np.int64) - np.repeat(combo_starts, combo_lengths)
    )
    ft_gems = np.asarray(response_table.flat_ft, dtype=np.int64)[combo_index]
    ff_gems = np.asarray(response_table.flat_ff, dtype=np.int64)[combo_index]
    budget = int(TOTAL_GEM_BUDGET) - ft_gems - ff_gems
    bad = (ft_gems < 0) | (ff_gems < 0) | (budget < 0)
    if np.any(bad):
        row = int(combo_row[int(np.argmax(bad))])
        raise ValueError(f"Timing-response row {row} has an invalid gem allocation")

    start_ft = cells // _GRID
    start_ff = cells % _GRID
    final_ft = np.minimum(
        int(MAX_STAT_INDEX), start_ft[combo_row] + int(GEM_SCALE_FEVER) * ft_gems
    )
    final_ff = np.minimum(
        int(MAX_STAT_INDEX), start_ff[combo_row] + int(GEM_SCALE_FEVER) * ff_gems
    )
    surface_counts = np.asarray(timeline.counts, dtype=np.int64)[final_ft, final_ff]
    surface_starts = np.asarray(timeline.pool_offsets, dtype=np.int64)[final_ft, final_ff]
    surface_ends = surface_starts + surface_counts
    bad = (surface_counts <= 0) | (surface_starts < 0) | (surface_ends > int(timeline.pool_used))
    if np.any(bad):
        idx = int(np.argmax(bad))
        raise ValueError(
            f"Timing-response row {int(combo_row[idx])} reaches invalid surface range "
            f"[{int(surface_starts[idx])}, {int(surface_ends[idx])})"
        )
    head_len = np.asarray(timeline.head_lengths, dtype=np.int64)[final_ft, final_ff]
    bad = (head_len < 0) | (head_len > _MAX_TIMELINE_HEAD)
    if np.any(bad):
        idx = int(np.argmax(bad))
        raise ValueError(f"Timeline frontier has invalid head length {int(head_len[idx])}")
    direct = (int(ft_weight) * ft_gems) + (int(ff_weight) * ff_gems)

    total_pool = int(surface_counts.sum())
    pool_combo = np.repeat(np.arange(total_combos, dtype=np.int64), surface_counts)
    pool_starts = np.cumsum(surface_counts) - surface_counts
    pool_idx = np.repeat(surface_starts, surface_counts) + (
        np.arange(total_pool, dtype=np.int64) - np.repeat(pool_starts, surface_counts)
    )
    head_coeffs = np.asarray(timeline.head_coeffs, dtype=np.int64)
    n_hn = head_coeffs[pool_idx, 0]
    n_hf = head_coeffs[pool_idx, 1]
    sigma_hn = head_coeffs[pool_idx, 2]
    sigma_hf = head_coeffs[pool_idx, 3]
    b_fever = np.asarray(timeline.body_fever, dtype=np.int64)[pool_idx]
    b_normal = np.asarray(timeline.body_normal, dtype=np.int64)[pool_idx]
    head_per_pool = head_len[pool_combo]

    if np.any(
        (n_hn < 0) | (n_hf < 0) | (sigma_hn < 0) | (sigma_hf < 0) | (b_fever < 0) | (b_normal < 0)
    ):
        raise ValueError("Timeline frontier contains negative note coefficients")
    if np.any(n_hn + n_hf != head_per_pool):
        raise ValueError("Timeline frontier contains inconsistent head-note counts")
    if np.any(sigma_hn + sigma_hf != (head_per_pool * (head_per_pool + 1)) // 2):
        raise ValueError("Timeline frontier sigma lanes do not partition the head")
    for count, sigma in ((n_hn, sigma_hn), (n_hf, sigma_hf)):
        sigma_min = (count * (count + 1)) // 2
        sigma_max = (count * ((2 * head_per_pool) - count + 1)) // 2
        if np.any(sigma < sigma_min) or np.any(sigma > sigma_max):
            raise ValueError("Timeline frontier has an infeasible head-position sum")
    bad = (n_hn + n_hf + b_fever + b_normal) != expected_total_notes
    if np.any(bad):
        idx = int(np.argmax(bad))
        raise ValueError(
            "Timeline surface note count does not match song metadata: "
            f"row={int(combo_row[pool_combo[idx]])} pool={int(pool_idx[idx])}"
        )

    # Per-row sorted(set(...)) over the 8-tuples, vectorized. The nine sort
    # keys are packed most-significant-first into two int64 words, which is
    # order-preserving iff every field is non-negative and fits its fixed
    # width - enforced fail-loud below - so lexsort((lo, hi)) orders exactly
    # like the 9-key lexsort while sorting 4.5x fewer key arrays.
    entry_row = combo_row[pool_combo].astype(np.int64)
    col_budget = budget[pool_combo]
    col_direct = direct[pool_combo]
    # Packed-width guards. Every per-element bound is already enforced
    # fail-loud above (coefficients nonnegative; n_hn/n_hf <= head <=
    # _MAX_TIMELINE_HEAD < 2^7; sigma <= head^2 < 2^14 via the infeasible-sum
    # check; b_fever/b_normal <= expected_total_notes via the note-count
    # identity; 0 <= budget <= TOTAL_GEM_BUDGET < 2^7), so only the two
    # scalar bounds need checking here.
    if row_count >= (1 << 15):
        raise OverflowError("Timing-bound program row count exceeds packed sort width")
    if expected_total_notes >= (1 << 17):
        raise OverflowError("Timing-bound program note count exceeds packed sort width")
    max_weight = max(int(ft_weight), int(ff_weight))
    if max_weight * int(TOTAL_GEM_BUDGET) * 2 >= (1 << 11):
        raise OverflowError("Timing-bound program direct lane exceeds packed sort width")
    if int(TOTAL_GEM_BUDGET) >= (1 << 7) or int(_MAX_TIMELINE_HEAD) >= (1 << 7):
        raise OverflowError("Timing-bound program budget/head cap exceeds packed sort width")
    hi = (((entry_row << 7) | col_budget) << 11 | col_direct) << 17 | b_fever
    lo = ((((b_normal << 7) | n_hn) << 7 | n_hf) << 14 | sigma_hn) << 14 | sigma_hf
    order = np.lexsort((lo, hi))
    s_hi = hi[order]
    s_lo = lo[order]
    unique = np.empty(total_pool, dtype=np.bool_)
    unique[0] = True
    unique[1:] = (s_hi[1:] != s_hi[:-1]) | (s_lo[1:] != s_lo[:-1])
    keep_idx = order[unique]
    kept_rows = entry_row[keep_idx]
    per_row = np.bincount(kept_rows, minlength=row_count)
    if np.any(per_row <= 0):
        row = int(np.argmax(per_row <= 0))
        raise RuntimeError(f"Timing-response row {row} produced no physical score program")
    surface_offsets = np.zeros(row_count + 1, dtype=np.int32)
    surface_offsets[1:] = np.cumsum(per_row).astype(np.int32)

    return TimingBoundPrograms(
        surface_offsets=surface_offsets,
        surface_budget=col_budget[keep_idx].astype(np.int16),
        surface_direct=col_direct[keep_idx].astype(np.int32),
        surface_body_fever=b_fever[keep_idx].astype(np.int32),
        surface_body_normal=b_normal[keep_idx].astype(np.int32),
        surface_head_normal=n_hn[keep_idx].astype(np.int32),
        surface_head_fever=n_hf[keep_idx].astype(np.int32),
        surface_sigma_normal=sigma_hn[keep_idx].astype(np.int32),
        surface_sigma_fever=sigma_hf[keep_idx].astype(np.int32),
    )


def _program_class_bound_programs(
    class_by_row: np.ndarray,
    programs: TimingBoundPrograms,
) -> ProgramClassBoundPrograms:
    classes = np.asarray(class_by_row, dtype=np.int32)
    if classes.ndim != 1 or classes.shape[0] + 1 != programs.surface_offsets.shape[0]:
        raise ValueError("Timing classes and physical score programs are not row-aligned")
    if classes.size == 0:
        raise ValueError("Timing classes must contain at least one response row")
    program_count = int(np.max(classes)) + 1
    if program_count <= 0 or not np.array_equal(
        np.unique(classes),
        np.arange(program_count, dtype=np.int32),
    ):
        raise ValueError("Timing class IDs must be dense from zero")

    source_arrays = tuple(
        np.asarray(array, dtype=np.int32)
        for array in (
            programs.surface_budget,
            programs.surface_direct,
            programs.surface_body_fever,
            programs.surface_body_normal,
            programs.surface_head_normal,
            programs.surface_head_fever,
            programs.surface_sigma_normal,
            programs.surface_sigma_fever,
        )
    )
    entry_count = int(source_arrays[0].shape[0])
    if any(array.shape != (entry_count,) for array in source_arrays):
        raise ValueError("Physical score-program arrays are not aligned")
    rows = np.column_stack(source_arrays).astype(np.int32, copy=False)
    representatives: list[np.ndarray | None] = [None] * program_count
    for row, class_id in enumerate(classes.tolist()):
        start = int(programs.surface_offsets[row])
        end = int(programs.surface_offsets[row + 1])
        if start < 0 or end <= start or end > entry_count:
            raise ValueError(f"Physical score-program row {row} has an invalid range")
        candidate = rows[start:end]
        representative = representatives[int(class_id)]
        if representative is None:
            representatives[int(class_id)] = np.ascontiguousarray(candidate)
        elif not np.array_equal(representative, candidate):
            raise RuntimeError(
                "Equivalent timing-response classes disagree on physical score programs: "
                f"class={class_id} row={row}"
            )

    if any(representative is None for representative in representatives):
        raise RuntimeError("One or more timing classes have no physical score program")
    concrete = [part for part in representatives if part is not None]
    lengths = np.asarray([int(part.shape[0]) for part in concrete], dtype=np.int64)
    total_entries = int(np.sum(lengths, dtype=np.int64))
    if total_entries > int(np.iinfo(np.int32).max):
        raise OverflowError("Program-class score table exceeds int32 offsets")
    offsets = np.zeros(program_count + 1, dtype=np.int32)
    offsets[1:] = np.cumsum(lengths, dtype=np.int64).astype(np.int32)
    flat = np.concatenate(concrete, axis=0).astype(np.int32, copy=False)
    return ProgramClassBoundPrograms(
        program_offsets=offsets,
        program_budget=flat[:, 0],
        program_direct=flat[:, 1],
        program_body_fever=flat[:, 2],
        program_body_normal=flat[:, 3],
        program_head_normal=flat[:, 4],
        program_head_fever=flat[:, 5],
        program_sigma_normal=flat[:, 6],
        program_sigma_fever=flat[:, 7],
    )


@njit(cache=False, nogil=True)
def _build_cm_fm_joint_multiplier_bound(
    ref_cm: np.ndarray,
    ref_fm: np.ndarray,
    total_budget: int,
) -> np.ndarray:
    grid = int(ref_cm.shape[0])
    table = np.empty((grid, grid, int(total_budget) + 1), dtype=np.float64)
    for cm in range(grid):
        for fm in range(grid):
            for budget in range(int(total_budget) + 1):
                best = 0.0
                for cm_gems in range(budget + 1):
                    fm_gems = budget - cm_gems
                    cm_idx = min(grid - 1, cm + (2 * cm_gems))
                    fm_idx = min(grid - 1, fm + (3 * fm_gems))
                    value = ref_cm[cm_idx] * ref_fm[fm_idx]
                    if value > best:
                        best = value
                table[cm, fm, budget] = best
    return table


@njit(cache=False, nogil=True)
def _build_cm_span_fm_joint_multiplier_bound(
    ref_cm: np.ndarray,
    ref_fm: np.ndarray,
    total_budget: int,
) -> np.ndarray:
    grid = int(ref_cm.shape[0])
    table = np.empty((grid, grid, int(total_budget) + 1), dtype=np.float64)
    for cm in range(grid):
        for fm in range(grid):
            for budget in range(int(total_budget) + 1):
                best = 0.0
                for cm_gems in range(budget + 1):
                    fm_gems = budget - cm_gems
                    cm_idx = min(grid - 1, cm + (2 * cm_gems))
                    fm_idx = min(grid - 1, fm + (3 * fm_gems))
                    value = (ref_cm[cm_idx] - 1.0) * ref_fm[fm_idx]
                    if value > best:
                        best = value
                table[cm, fm, budget] = best
    return table


_JOINT_MULTIPLIER_MEMO_MAX = 4
_JOINT_MULTIPLIER_MEMO: "OrderedDict[tuple[bytes, bytes], JointMultiplierBounds]" = OrderedDict()
_JOINT_MULTIPLIER_MEMO_LOCK = threading.Lock()


def _clear_joint_multiplier_memo() -> None:
    """Test-isolation hook mirroring the sibling multiplier-cache resets."""
    with _JOINT_MULTIPLIER_MEMO_LOCK:
        _JOINT_MULTIPLIER_MEMO.clear()


def _joint_multiplier_bounds(ref_arrays: dict[str, Any]) -> JointMultiplierBounds:
    # The joint tables are a pure function of the CM/FM reference arrays and
    # are identical for every song solved against the same references, so the
    # ~217M-op numba rebuild is memoized on the reference bytes. Cached arrays
    # are decoupled copies of the caller's references and frozen read-only.
    # The lock makes concurrent same-reference callers share one build.
    ref_cm = np.array(ref_arrays.get("Combo Multiplier"), dtype=np.float64, copy=True)
    ref_fm = np.array(ref_arrays.get("Fever Multiplier"), dtype=np.float64, copy=True)
    for name, references in (("CM", ref_cm), ("FM", ref_fm)):
        if references.shape != (_GRID,):
            raise ValueError(f"{name} references do not match the exact stat grid")
        if not np.all(np.isfinite(references)) or np.any(references < 1.0):
            raise ValueError(f"{name} references must be finite and at least one")
        if np.any(np.diff(references) < 0.0):
            raise ValueError(f"{name} references must be nondecreasing")
    key = (ref_cm.tobytes(), ref_fm.tobytes())
    with _JOINT_MULTIPLIER_MEMO_LOCK:
        cached = _JOINT_MULTIPLIER_MEMO.get(key)
        if cached is not None:
            _JOINT_MULTIPLIER_MEMO.move_to_end(key)
            return cached
        joint_cm_fm = _build_cm_fm_joint_multiplier_bound(
            ref_cm,
            ref_fm,
            int(TOTAL_GEM_BUDGET),
        )
        joint_cm_span_fm = _build_cm_span_fm_joint_multiplier_bound(
            ref_cm,
            ref_fm,
            int(TOTAL_GEM_BUDGET),
        )
        for array in (ref_cm, ref_fm, joint_cm_fm, joint_cm_span_fm):
            array.setflags(write=False)
        result = JointMultiplierBounds(
            ref_cm=ref_cm,
            ref_fm=ref_fm,
            joint_cm_fm=joint_cm_fm,
            joint_cm_span_fm=joint_cm_span_fm,
        )
        _JOINT_MULTIPLIER_MEMO[key] = result
        _JOINT_MULTIPLIER_MEMO.move_to_end(key)
        while len(_JOINT_MULTIPLIER_MEMO) > int(_JOINT_MULTIPLIER_MEMO_MAX):
            _JOINT_MULTIPLIER_MEMO.popitem(last=False)
        return result


def build_exact_base_song_context(
    inputs: ExactBaseSongContextInputs,
    timeline_payload: TimelineFrontierGridPayload,
) -> ExactBaseSongContext:
    """Build the immutable host-only context for one song's exact Base search."""

    if not isinstance(inputs, ExactBaseSongContextInputs):
        raise TypeError("Exact Base context build requires ExactBaseSongContextInputs")
    flags = _validated_color_flags(inputs.color_flags)
    timeline = _timeline_arrays(timeline_payload)
    program_map = _build_program_map(
        ref_arrays=inputs.ref_arrays,
        flags=flags,
        timeline=timeline,
    )
    physical_programs = _timing_bound_programs(
        calc_song=inputs.calc_song,
        flags=flags,
        response_table=program_map.response_table,
        timeline=timeline,
    )
    class_programs = _program_class_bound_programs(
        program_map.class_by_response_row,
        physical_programs,
    )
    multiplier_bounds = _joint_multiplier_bounds(inputs.ref_arrays)
    cm_weight = _lane_weight(flags, "cm", 3)
    fm_weight = _lane_weight(flags, "fm", 3)
    overflow_weight = _lane_weight(flags, "ov", 6)
    return ExactBaseSongContext(
        program_map=program_map,
        physical_programs=physical_programs,
        class_programs=class_programs,
        multiplier_bounds=multiplier_bounds,
        stat_elemental_weight_max=max(cm_weight, fm_weight),
        overflow_elemental_weight=overflow_weight,
    )


__all__ = [
    "ExactBaseSongContext",
    "ExactBaseSongContextInputs",
    "JointMultiplierBounds",
    "ProgramClassBoundPrograms",
    "TimingBoundPrograms",
    "TimingProgramMap",
    "build_exact_base_song_context",
]
