"""Prepare request-scoped item domains for the exact Base GPU kernels."""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    MAX_STAT_INDEX,
    TOTAL_GEM_BUDGET,
)
from gear_optimizer.solver.fixed_timing_skyline import reduce_fixed_timing_prefix_skyline
from gear_optimizer.solver.solver_common import GEAR_SLOTS, SolverContext

_GRID_SIZE = int(MAX_STAT_INDEX) + 1
_STAT_COLUMNS = 6
_COLOR_TO_FIXED_INDEX = {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}


@dataclass(frozen=True)
class ExactBaseDomains:
    """Immutable, contiguous request inputs consumed by the exact Base kernels."""

    left_stats: np.ndarray
    left_ids: np.ndarray
    right_stats: np.ndarray
    right_ids: np.ndarray
    mini_stats: np.ndarray
    mini_ids: np.ndarray
    ref_pp: np.ndarray
    fixed_stats: np.ndarray
    fixed_lane: int
    same_color: bool


@dataclass(frozen=True)
class ExactBaseResponseComponent:
    """One scalar-response component of a request-local exact Base domain."""

    domains: ExactBaseDomains
    mini_pp_total: int
    response_class_by_pp: np.ndarray
    response_class: int
    response_delta: np.ndarray


def encode_pool_stats(
    items: Sequence[dict[str, Any]],
    *,
    p_color: str,
    s_color: str,
) -> np.ndarray:
    """Encode selectable items as ``PP, CM, FM, FT, FF, elemental lane`` rows."""

    if not items:
        raise ValueError("Exact Base domains received an empty item pool")

    primary_color = str(p_color or "")
    secondary_color = str(s_color or "")
    rows = np.empty((len(items), _STAT_COLUMNS), dtype=np.int32)
    for row, item in enumerate(items):
        primary = int(item.get(primary_color, 0) or 0) if primary_color else 0
        secondary = (
            int(item.get(secondary_color, 0) or 0)
            if secondary_color and secondary_color != primary_color
            else 0
        )
        rows[row] = (
            int(item.get("Perfect Points", 0) or 0),
            int(item.get("Combo Multiplier", 0) or 0),
            int(item.get("Fever Multiplier", 0) or 0),
            int(item.get("Fever Time", 0) or 0),
            int(item.get("Fever Fill Rate", 0) or 0),
            (2 * primary) + secondary,
        )

    return rows


def build_three_slot_gear_product(
    stats_by_slot: tuple[np.ndarray, np.ndarray, np.ndarray],
    ids_by_slot: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    """Enumerate the legal Cartesian product of three distinct gear slots."""

    normalized_stats: list[np.ndarray] = []
    normalized_ids: list[np.ndarray] = []
    for slot_idx, (stats, item_ids) in enumerate(zip(stats_by_slot, ids_by_slot, strict=True)):
        slot_stats = np.asarray(stats, dtype=np.int32)
        slot_ids = np.asarray(item_ids, dtype=np.int32)
        if slot_stats.ndim != 2 or slot_stats.shape[1] != _STAT_COLUMNS or slot_stats.shape[0] == 0:
            raise ValueError(f"Gear product slot {slot_idx} stats must have nonempty shape (n, 6)")
        if slot_ids.ndim != 1 or slot_ids.shape[0] != slot_stats.shape[0]:
            raise ValueError(f"Gear product slot {slot_idx} item IDs must align with its stats")
        if np.any(slot_ids <= 0):
            raise ValueError(f"Gear product slot {slot_idx} contains invalid item IDs")
        normalized_stats.append(slot_stats)
        normalized_ids.append(slot_ids)

    a_stats, b_stats, c_stats = normalized_stats
    a_ids, b_ids, c_ids = normalized_ids
    na, nb, nc = int(a_stats.shape[0]), int(b_stats.shape[0]), int(c_stats.shape[0])
    ai = np.repeat(np.arange(na, dtype=np.int32), nb * nc)
    bi = np.tile(np.repeat(np.arange(nb, dtype=np.int32), nc), na)
    ci = np.tile(np.arange(nc, dtype=np.int32), na * nb)
    stats = a_stats[ai] + b_stats[bi] + c_stats[ci]
    item_ids = np.column_stack((a_ids[ai], b_ids[bi], c_ids[ci])).astype(np.int32, copy=False)
    return np.ascontiguousarray(stats), np.ascontiguousarray(item_ids)


def build_distinct_mini_triples(
    mini_stats: np.ndarray,
    mini_item_ids: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Enumerate each unordered triple of three distinct selectable minis once."""

    stats_by_mini = np.asarray(mini_stats, dtype=np.int32)
    item_ids_by_mini = np.asarray(mini_item_ids, dtype=np.int32)
    if stats_by_mini.ndim != 2 or stats_by_mini.shape[1] != _STAT_COLUMNS:
        raise ValueError("Mini stats must have shape (n, 6)")
    if item_ids_by_mini.ndim != 1 or item_ids_by_mini.shape[0] != stats_by_mini.shape[0]:
        raise ValueError("Mini item IDs must be a 1-D array aligned with mini stats")
    if np.any(item_ids_by_mini <= 0):
        raise ValueError("Mini triples contain invalid item IDs")

    count = int(stats_by_mini.shape[0])
    if count < 3:
        raise ValueError("Exact Base domains require at least three selectable minis")
    flat = np.fromiter(
        itertools.chain.from_iterable(itertools.combinations(range(count), 3)),
        dtype=np.int32,
        count=3 * math.comb(count, 3),
    )
    triples = flat.reshape(-1, 3)
    stats = (
        stats_by_mini[triples[:, 0]]
        + stats_by_mini[triples[:, 1]]
        + stats_by_mini[triples[:, 2]]
    )
    item_ids = item_ids_by_mini[triples]
    return np.ascontiguousarray(stats), np.ascontiguousarray(item_ids, dtype=np.int32)


def reduce_fixed_timing_domain(
    stats: np.ndarray,
    item_ids: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Reduce a three-item domain while retaining the aligned witness item IDs."""

    points = np.ascontiguousarray(stats, dtype=np.int32)
    ids = np.ascontiguousarray(item_ids, dtype=np.int32)
    if points.ndim != 2 or points.shape[1] != _STAT_COLUMNS or points.shape[0] == 0:
        raise ValueError("Partial-domain stats must have nonempty shape (n, 6)")
    if ids.ndim != 2 or ids.shape != (int(points.shape[0]), 3):
        raise ValueError("Partial-domain item IDs must have shape (n, 3)")
    if np.any(ids <= 0):
        raise ValueError("Partial-domain witness item IDs must be positive")

    row_codes = np.arange(int(points.shape[0]), dtype=np.uint64)
    coordinate_min = np.min(points[:, :5], axis=0).astype(np.int64, copy=False)
    coordinate_max = np.max(points[:, :5], axis=0).astype(np.int64, copy=False)
    coordinate_ranges = coordinate_max - coordinate_min
    dynamic_max_index = max(1, int(np.max(coordinate_ranges)))
    _stats, reduced, kept_codes = reduce_fixed_timing_prefix_skyline(
        points,
        row_codes,
        max_stat_index=dynamic_max_index,
    )
    kept = kept_codes.astype(np.intp, copy=False)
    return (
        np.ascontiguousarray(reduced, dtype=np.int32),
        np.ascontiguousarray(ids[kept], dtype=np.int32),
    )


def fixed_elemental_lane(
    ctx: SolverContext,
    fixed_stats: np.ndarray,
    *,
    same_color: bool,
) -> int:
    """Return the fixed-stat contribution in the quotient's elemental lane."""

    fixed = np.asarray(fixed_stats, dtype=np.int32).reshape(-1)
    if fixed.shape != (10,) or np.any(fixed < 0):
        raise ValueError(f"Exact Base domains expected ten nonnegative fixed stats, got {fixed.shape}")

    primary_color = str(ctx.p_color or "")
    secondary_color = str(ctx.s_color or "")
    if primary_color not in _COLOR_TO_FIXED_INDEX:
        raise ValueError(f"Exact Base domains received invalid primary color {primary_color!r}")
    if bool(same_color):
        if secondary_color != primary_color:
            raise ValueError("Same-color elemental folding requires matching primary and secondary colors")
        return 3 * int(fixed[_COLOR_TO_FIXED_INDEX[primary_color]])

    lane = 2 * int(fixed[_COLOR_TO_FIXED_INDEX[primary_color]])
    if secondary_color:
        if secondary_color not in _COLOR_TO_FIXED_INDEX:
            raise ValueError(f"Exact Base domains received invalid secondary color {secondary_color!r}")
        if secondary_color == primary_color:
            raise ValueError("Two-color elemental encoding requires distinct primary and secondary colors")
        lane += int(fixed[_COLOR_TO_FIXED_INDEX[secondary_color]])
    return int(lane)


def _validated_response_flags(ctx: SolverContext) -> dict[str, int]:
    names = ("is_p_pp", "is_s_pp", "is_p_ov", "is_s_ov")
    values = {name: int(ctx.color_flags.get(name, 0) or 0) for name in names}
    if any(value not in (0, 1) for value in values.values()):
        raise ValueError(f"Exact Base response classes require binary color flags, got {values}")
    return values


def build_pp_response_classes(
    ref_pp: np.ndarray,
    *,
    color_flags: dict[str, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Partition PP states by their exact PP/overflow response profile.

    For one response class, ``response_delta[class_id, budget]`` is identical
    for every PP state in that class.  A candidate in that class therefore has
    the exact response profile ``lane + ref_pp[pp] + response_delta`` and can be
    reduced by the existing scalar max-plus quotient without losing a winner.
    """

    refs = np.asarray(ref_pp, dtype=np.int32)
    if refs.shape != (_GRID_SIZE,):
        raise ValueError("Exact Base PP response classes require a 161-row reference table")
    names = ("is_p_pp", "is_s_pp", "is_p_ov", "is_s_ov")
    flags = {name: int(color_flags.get(name, 0) or 0) for name in names}
    if any(value not in (0, 1) for value in flags.values()):
        raise ValueError(f"Exact Base response classes require binary color flags, got {flags}")

    allow_pp = bool(flags["is_p_pp"] or flags["is_s_pp"])
    pp_weight = int(GEM_STAT_TO_ELEMENT_SCALE) * (
        (2 * flags["is_p_pp"]) + flags["is_s_pp"]
    )
    overflow_weight = int(ELEMENTAL_GEM_SCALE) * (
        (2 * flags["is_p_ov"]) + flags["is_s_ov"]
    )
    budget_size = int(TOTAL_GEM_BUDGET) + 1
    pp = np.arange(_GRID_SIZE, dtype=np.int64)[:, None, None]
    budget = np.arange(budget_size, dtype=np.int64)[None, :, None]
    pp_gems = np.arange(budget_size, dtype=np.int64)[None, None, :]
    if allow_pp:
        pp_cap = (
            int(MAX_STAT_INDEX)
            - np.arange(_GRID_SIZE, dtype=np.int64)
            + int(GEM_SCALE_NORMAL)
            - 1
        ) // int(GEM_SCALE_NORMAL)
    else:
        pp_cap = np.zeros(_GRID_SIZE, dtype=np.int64)
    legal = (pp_gems <= budget) & (pp_gems <= pp_cap[:, None, None])
    pp_stat = np.minimum(
        int(MAX_STAT_INDEX),
        pp + (pp_gems * int(GEM_SCALE_NORMAL)),
    )
    values = (
        refs[pp_stat].astype(np.int64, copy=False)
        - refs[:, None, None].astype(np.int64, copy=False)
        + (pp_gems * pp_weight)
        + ((budget - pp_gems) * overflow_weight)
    )
    profiles_i64 = np.max(np.where(legal, values, np.iinfo(np.int64).min), axis=2)
    if np.any(profiles_i64 < 0) or np.any(profiles_i64 > np.iinfo(np.int32).max):
        raise OverflowError("Exact Base PP response profile exceeds nonnegative i32 storage")
    profiles = np.ascontiguousarray(profiles_i64, dtype=np.int32)

    class_by_pp = np.empty(_GRID_SIZE, dtype=np.int32)
    class_rows: list[np.ndarray] = []
    class_ids: dict[bytes, int] = {}
    for pp in range(_GRID_SIZE):
        row = np.ascontiguousarray(profiles[pp], dtype=np.int32)
        key = row.tobytes()
        class_id = class_ids.get(key)
        if class_id is None:
            class_id = len(class_rows) + 1
            class_ids[key] = int(class_id)
            class_rows.append(row)
        class_by_pp[pp] = int(class_id)
    response_delta = np.ascontiguousarray(np.vstack(class_rows), dtype=np.int32)
    return _freeze(class_by_pp), _freeze(response_delta)


def validate_exact_quotient(
    ctx: SolverContext,
    *,
    left: np.ndarray,
    right: np.ndarray,
    minis: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, bool]:
    """Validate exact Base quotient inputs and return request constants."""

    domains: list[tuple[str, np.ndarray]] = []
    for name, raw_rows in (("left", left), ("right", right), ("minis", minis)):
        rows = np.asarray(raw_rows, dtype=np.int32)
        if rows.ndim != 2 or rows.shape[1] != _STAT_COLUMNS or rows.shape[0] == 0:
            raise ValueError(f"Exact Base {name} rows must have nonempty shape (n, 6)")
        domains.append((name, rows))
    left_rows, right_rows, mini_rows = (rows for _name, rows in domains)

    fixed = np.asarray(ctx.base_fixed_stats_arr, dtype=np.int32).reshape(-1)
    if fixed.shape != (10,) or np.any(fixed < 0):
        raise ValueError(f"Exact Base domains expected ten nonnegative fixed stats, got {fixed.shape}")

    ref_pp_f32 = np.asarray(ctx.ref_arrays["Perfect Points"], dtype=np.float32)
    if ref_pp_f32.shape != (_GRID_SIZE,) or not np.all(np.isfinite(ref_pp_f32)):
        raise ValueError("Dense Base quotient requires a finite 161-row PP reference table")
    if not np.all(ref_pp_f32 == np.rint(ref_pp_f32)):
        raise RuntimeError("Dense Base quotient requires integral reachable PP references")
    if np.any(ref_pp_f32 < 0) or np.any(np.diff(ref_pp_f32) < 0):
        raise ValueError("Dense Base quotient requires nonnegative nondecreasing PP references")
    ref_pp = np.rint(ref_pp_f32).astype(np.int32)

    for stat_name in ("Combo Multiplier", "Fever Multiplier"):
        refs = np.asarray(ctx.ref_arrays[stat_name], dtype=np.float32)
        if (
            refs.shape != (_GRID_SIZE,)
            or not np.all(np.isfinite(refs))
            or np.any(refs < 1.0)
            or np.any(np.diff(refs) < 0)
        ):
            raise ValueError(f"Dense Base quotient requires finite nondecreasing {stat_name} references >= 1")

    _validated_response_flags(ctx)

    same_color = bool(str(ctx.p_color or "") == str(ctx.s_color or ""))
    if same_color:
        for name, rows in domains:
            if np.any((rows[:, 5] & 1) != 0):
                raise AssertionError(f"Same-color folded {name} elemental lane must be even")

    fixed_lane = fixed_elemental_lane(ctx, fixed, same_color=same_color)
    max_raw_pp = int(
        np.clip(
            int(np.max(left_rows[:, 0]))
        + int(np.max(right_rows[:, 0]))
        + int(fixed[0])
        + int(np.max(mini_rows[:, 0])),
            0,
            int(MAX_STAT_INDEX),
        )
    )
    max_lane = int(np.max(left_rows[:, 5])) + int(np.max(right_rows[:, 5]))
    if same_color:
        max_lane = (3 * max_lane) // 2
    max_q = int(max_lane + fixed_lane + int(ref_pp[max_raw_pp]))
    mini_lane_max = int(np.max(mini_rows[:, 5]))
    if same_color:
        mini_lane_max = (3 * mini_lane_max) // 2
    max_q += mini_lane_max
    if max_q < 0 or max_q >= int(np.iinfo(np.int32).max):
        raise OverflowError(f"Dense Base quotient exceeds i32 storage: {max_q}")

    return ref_pp, fixed, bool(same_color)


def _freeze(array: np.ndarray, *, copy: bool = False) -> np.ndarray:
    out = np.array(array, dtype=np.int32, order="C", copy=True) if copy else np.ascontiguousarray(array, dtype=np.int32)
    out.setflags(write=False)
    return out


def build_exact_base_response_components(
    ctx: SolverContext,
    domains: ExactBaseDomains,
) -> tuple[ExactBaseResponseComponent, ...]:
    """Split a request into lossless scalar PP-response components."""

    if not isinstance(domains, ExactBaseDomains):
        raise TypeError("Exact Base response components require ExactBaseDomains")
    class_by_pp, response_delta = build_pp_response_classes(
        domains.ref_pp,
        color_flags=_validated_response_flags(ctx),
    )
    left_pp = np.unique(np.asarray(domains.left_stats[:, 0], dtype=np.int32))
    right_pp = np.unique(np.asarray(domains.right_stats[:, 0], dtype=np.int32))
    fixed_pp = int(domains.fixed_stats[0])
    mini_pp_values = np.unique(np.asarray(domains.mini_stats[:, 0], dtype=np.int32))

    components: list[ExactBaseResponseComponent] = []
    for mini_pp_total in mini_pp_values.tolist():
        mini_rows = np.flatnonzero(domains.mini_stats[:, 0] == int(mini_pp_total))
        if mini_rows.shape[0] == 0:
            raise AssertionError("Exact Base mini PP partition produced an empty component")
        component_domains = ExactBaseDomains(
            left_stats=domains.left_stats,
            left_ids=domains.left_ids,
            right_stats=domains.right_stats,
            right_ids=domains.right_ids,
            mini_stats=_freeze(domains.mini_stats[mini_rows]),
            mini_ids=_freeze(domains.mini_ids[mini_rows]),
            ref_pp=domains.ref_pp,
            fixed_stats=domains.fixed_stats,
            fixed_lane=int(domains.fixed_lane),
            same_color=bool(domains.same_color),
        )
        reachable_pp = np.unique(
            np.clip(
                left_pp[:, None]
                + right_pp[None, :]
                + fixed_pp
                + int(mini_pp_total),
                0,
                int(MAX_STAT_INDEX),
            )
        ).astype(np.intp, copy=False)
        reachable_classes = np.unique(class_by_pp[reachable_pp])
        for response_class in reachable_classes.tolist():
            components.append(
                ExactBaseResponseComponent(
                    domains=component_domains,
                    mini_pp_total=int(mini_pp_total),
                    response_class_by_pp=class_by_pp,
                    response_class=int(response_class),
                    response_delta=_freeze(
                        response_delta[int(response_class) - 1],
                        copy=True,
                    ),
                )
            )
    if not components:
        raise RuntimeError("Exact Base response decomposition produced no reachable component")
    return tuple(components)


def build_exact_base_domains(ctx: SolverContext) -> ExactBaseDomains:
    """Build the reduced request domains and quotient constants from ``SolverContext``."""

    if len(ctx.slot_item_ids) != len(GEAR_SLOTS):
        raise ValueError(f"Exact Base domains require {len(GEAR_SLOTS)} slot item-ID arrays")

    gear_stats = tuple(
        encode_pool_stats(
            list(ctx.gear_pool.get(slot, []) or []),
            p_color=str(ctx.p_color or ""),
            s_color=str(ctx.s_color or ""),
        )
        for slot in GEAR_SLOTS
    )
    mini_stats = encode_pool_stats(
        list(ctx.mini_pool),
        p_color=str(ctx.p_color or ""),
        s_color=str(ctx.s_color or ""),
    )

    left_raw = build_three_slot_gear_product(
        (gear_stats[0], gear_stats[1], gear_stats[2]),
        (
            np.asarray(ctx.slot_item_ids[0], dtype=np.int32),
            np.asarray(ctx.slot_item_ids[1], dtype=np.int32),
            np.asarray(ctx.slot_item_ids[2], dtype=np.int32),
        ),
    )
    right_raw = build_three_slot_gear_product(
        (gear_stats[3], gear_stats[4], gear_stats[5]),
        (
            np.asarray(ctx.slot_item_ids[3], dtype=np.int32),
            np.asarray(ctx.slot_item_ids[4], dtype=np.int32),
            np.asarray(ctx.slot_item_ids[5], dtype=np.int32),
        ),
    )
    mini_raw = build_distinct_mini_triples(mini_stats, np.asarray(ctx.mini_item_ids, dtype=np.int32))

    left, left_ids = reduce_fixed_timing_domain(*left_raw)
    right, right_ids = reduce_fixed_timing_domain(*right_raw)
    minis, mini_ids = reduce_fixed_timing_domain(*mini_raw)
    ref_pp, fixed, same_color = validate_exact_quotient(
        ctx,
        left=left,
        right=right,
        minis=minis,
    )
    fixed_lane = fixed_elemental_lane(ctx, fixed, same_color=same_color)

    return ExactBaseDomains(
        left_stats=_freeze(left),
        left_ids=_freeze(left_ids),
        right_stats=_freeze(right),
        right_ids=_freeze(right_ids),
        mini_stats=_freeze(minis),
        mini_ids=_freeze(mini_ids),
        ref_pp=_freeze(ref_pp),
        fixed_stats=_freeze(fixed, copy=True),
        fixed_lane=int(fixed_lane),
        same_color=bool(same_color),
    )


def witness_item_ids(
    domains: ExactBaseDomains,
    selected: np.ndarray,
    *,
    final_owner: np.ndarray,
    gear_owner: np.ndarray,
) -> np.ndarray:
    """Resolve downloaded semiring owner chains into immutable nine-item loadouts."""

    selected_rows = np.asarray(selected, dtype=np.int64)
    final_owners = np.asarray(final_owner, dtype=np.int64)
    gear_owners = np.asarray(gear_owner, dtype=np.int64)
    if selected_rows.ndim != 1 or selected_rows.shape[0] == 0:
        raise ValueError("Exact Base state selection must be a nonempty 1-D array")
    if final_owners.ndim != 1 or gear_owners.ndim != 1:
        raise ValueError("Exact Base owner tables must be 1-D arrays")
    if np.any(selected_rows < 0) or np.any(selected_rows >= final_owners.shape[0]):
        raise RuntimeError("Exact Base state selection exceeded the final owner table")

    mini_count = int(domains.mini_stats.shape[0])
    right_count = int(domains.right_stats.shape[0])
    pair_owner = final_owners[selected_rows]
    gear_idx, mini_idx = np.divmod(pair_owner, mini_count)
    if np.any(gear_idx < 0) or np.any(gear_idx >= gear_owners.shape[0]):
        raise RuntimeError("Exact Base witness reconstruction exceeded the gear owner table")
    gear_pair = gear_owners[gear_idx]
    left_idx, right_idx = np.divmod(gear_pair, right_count)
    if (
        np.any(left_idx < 0)
        or np.any(left_idx >= domains.left_stats.shape[0])
        or np.any(right_idx < 0)
        or np.any(right_idx >= right_count)
        or np.any(mini_idx < 0)
        or np.any(mini_idx >= mini_count)
    ):
        raise RuntimeError("Exact Base witness reconstruction exceeded a request domain")

    candidate_ids = np.empty((int(selected_rows.shape[0]), 9), dtype=np.int32)
    candidate_ids[:, :3] = domains.left_ids[left_idx]
    candidate_ids[:, 3:6] = domains.right_ids[right_idx]
    candidate_ids[:, 6:] = domains.mini_ids[mini_idx]
    if np.any(candidate_ids <= 0):
        raise RuntimeError("Exact Base witness reconstruction produced an incomplete loadout")
    return _freeze(candidate_ids)


__all__ = [
    "ExactBaseDomains",
    "ExactBaseResponseComponent",
    "build_distinct_mini_triples",
    "build_exact_base_domains",
    "build_exact_base_response_components",
    "build_pp_response_classes",
    "build_three_slot_gear_product",
    "encode_pool_stats",
    "fixed_elemental_lane",
    "reduce_fixed_timing_domain",
    "validate_exact_quotient",
    "witness_item_ids",
]
