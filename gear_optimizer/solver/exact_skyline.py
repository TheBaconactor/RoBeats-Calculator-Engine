from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

import numpy as np

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    LOADOUTS_PER_SONG_LIMIT,
    MAX_STAT_INDEX,
    TOTAL_GEM_BUDGET,
)
from gear_optimizer.core.config import read_fg_search_radius
from gear_optimizer.core.parsing import env_get
from gear_optimizer.solver.combined_skyline_sparse import (
    combined_global_skyline_pairs_6d_sparse,
    get_last_combined_skyline_stats,
)
from gear_optimizer.solver.combined_skyline_dense_gpu import combined_global_skyline_pairs_6d_dense_gpu
from gear_optimizer.solver.gear_skyline_gpu import global_gear_skyline_points_6d_gpu_from_arrays
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.mini_skyline import (
    LaneAwareMiniSkylineStats as _LaneAwareMiniSkylineStats_common,
    mini_combo_skyline as _mini_combo_skyline_common,
)
from gear_optimizer.solver.solver_common import (
    GEAR_SLOTS,
    BitPack as _BitPack_common,
    SolverContext,
    batched_registry_eval,
    build_candidate_payload as _build_candidate_payload_common,
    build_solver_cfg_data as _build_cfg_data_common,
    build_solver_override_cfg,
    gear_ids_from_code as _gear_ids_from_code_common,
    mini_ids_from_code as _mini_ids_from_code_common,
    make_pack as _make_pack_common,
    prepare_solver_context,
)
from gear_optimizer.solver.skyline_force_greats import score_retained_skyline_force_greats
from gear_optimizer.solver.taichi_gem import fields as gem_fields
LaneAwareMiniSkylineStats = _LaneAwareMiniSkylineStats_common
_SLOTS = GEAR_SLOTS
_BitPack = _BitPack_common
_make_pack = _make_pack_common
_build_cfg_data = _build_cfg_data_common
_gear_ids_from_code = _gear_ids_from_code_common
_mini_ids_from_code = _mini_ids_from_code_common
_build_candidate_payload = _build_candidate_payload_common
_mini_combo_skyline_points_6d_lane_base_with_codes = _mini_combo_skyline_common

SKYLINE_CERTIFICATION_STATUS = "timing_cell_candidate_frontier"
SKYLINE_CERTIFICATION_NOTE = (
    "Raw dominance is restricted to fixed final FT/FF timing cells. "
    "FG is exact over the configured retained candidate set; set SKYLINE_FG_CANDIDATES=all "
    "for the full timing-cell frontier research mode."
)


def _read_skyline_fg_candidate_mode() -> str:
    raw = str(env_get("SKYLINE_FG_CANDIDATES", "topk") or "topk").strip().lower().replace("-", "_")
    if raw in {"all", "full", "entire", "skyline"}:
        return "all"
    if raw in {"sample", "stratified", "stratified_sample", "bands"}:
        return "sample"
    return "topk"


def _read_skyline_fg_sample_limit() -> int:
    try:
        return max(0, int(env_get("SKYLINE_FG_SAMPLE_RANDOM", "1000") or "1000"))
    except (TypeError, ValueError):
        return 1000


def _record_phase(phase_seconds: dict[str, float], name: str, started: float) -> None:
    phase_seconds[str(name)] = float(phase_seconds.get(str(name), 0.0) + (time.perf_counter() - float(started)))


def _rounded_phase_seconds(phase_seconds: dict[str, float]) -> dict[str, float]:
    return {str(key): round(float(value), 6) for key, value in phase_seconds.items()}


def _slowest_phase_label(phase_seconds: dict[str, float], *, limit: int = 5) -> str:
    pairs = sorted(phase_seconds.items(), key=lambda item: float(item[1]), reverse=True)[: int(limit)]
    return ", ".join(f"{name}={seconds:.2f}s" for name, seconds in pairs)


def _read_combined_dense_max_gib() -> float:
    raw = str(env_get("SKYLINE_COMBINED_DENSE_MAX_GIB", "3.0") or "3.0").strip()
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = 3.0
    return max(0.0, float(value))


def _read_combined_dense_mode() -> str:
    raw = str(env_get("SKYLINE_COMBINED_DENSE", "sparse") or "sparse").strip().lower()
    if raw in {"0", "false", "no", "off", "sparse"}:
        return "sparse"
    if raw in {"1", "true", "yes", "on", "dense"}:
        return "dense"
    return "sparse"


def _read_combined_dense_gpu_mode() -> str:
    raw = str(env_get("SKYLINE_COMBINED_DENSE_GPU", "auto") or "auto").strip().lower()
    if raw in {"0", "false", "no", "off", "sparse"}:
        return "sparse"
    if raw in {"1", "true", "yes", "on", "gpu", "dense"}:
        return "gpu"
    return "auto"


def _sample_pair_indices(
    total: int,
    *,
    top_limits: tuple[int, ...] = (51, 250, 1000),
    random_after: int = 1000,
    random_count: int = 1000,
    seed: int = 20260510,
) -> np.ndarray:
    total = max(0, int(total))
    if total <= 0:
        return np.zeros(0, dtype=np.int64)

    keep: set[int] = set()
    for limit in top_limits:
        limit_i = max(0, min(total, int(limit)))
        for idx in range(limit_i):
            keep.add(int(idx))

    start = max(0, min(total, int(random_after)))
    remaining = total - start
    if remaining > 0 and int(random_count) > 0:
        n = min(int(random_count), int(remaining))
        rng = np.random.default_rng(int(seed))
        sampled = rng.choice(np.arange(start, total, dtype=np.int64), size=int(n), replace=False)
        for idx in sampled.tolist():
            keep.add(int(idx))

    return np.asarray(sorted(keep), dtype=np.int64)


@dataclass(frozen=True)
class LaneAwareGearDPStats:
    keys_4d: int
    pairs_6d: int
    frontier_mean: float
    frontier_p95: float
    frontier_max: int
    seconds: float


@dataclass(frozen=True)
class LaneAwareGlobalSkylineStats:
    points_in: int
    points_out: int
    seconds: float


@dataclass(frozen=True)
class EnvelopeReductionStats:
    points_in: int
    points_out: int
    groups: int
    groups_multi: int
    max_group_size: int
    seconds: float


@dataclass(frozen=True)
class EnvelopeDominanceLUT:
    pp_max_idx: int
    budget_max: int
    delta_max: np.ndarray
    delta_min: np.ndarray


_ENVELOPE_DOMINANCE_TOL = np.float32(1.0e-6)


def _item_vec_5(item: dict) -> tuple[int, int, int, int, int]:
    return (
        int(item.get("Perfect Points", 0) or 0),
        int(item.get("Combo Multiplier", 0) or 0),
        int(item.get("Fever Multiplier", 0) or 0),
        int(item.get("Fever Time", 0) or 0),
        int(item.get("Fever Fill Rate", 0) or 0),
    )


def _lane_base_init(item: dict, p_color: str, s_color: str) -> int:
    p = int(item.get(p_color, 0) or 0) if p_color else 0
    s = int(item.get(s_color, 0) or 0) if s_color and s_color != p_color else 0
    return (2 * p) + s


def _clamp_idx(v: int) -> int:
    if v < 0:
        return 0
    if v > MAX_STAT_INDEX:
        return MAX_STAT_INDEX
    return int(v)


def _ceil_div_pos(num: int, den: int) -> int:
    num_i = int(num)
    den_i = int(den)
    if den_i <= 0:
        raise ValueError("den must be positive")
    if num_i <= 0:
        return 0
    return (num_i + den_i - 1) // den_i


def _lane_weight(color: str, *, p_color: str, s_color: str, scale: int) -> int:
    return int(scale) * ((2 if p_color == color else 0) + (1 if s_color == color else 0))


def _build_envelope_dominance_lut(
    *,
    ref_pp: np.ndarray,
    budget_max: int,
    w_pp: int,
    w_ov: int,
) -> EnvelopeDominanceLUT:
    budget = max(0, int(budget_max))
    pp_max_idx = int(MAX_STAT_INDEX)
    pp_states = int(pp_max_idx) + 1

    ref_raw = np.asarray(ref_pp, dtype=np.float32).reshape(-1)
    if ref_raw.size == 0:
        ref_vals = np.zeros(pp_states, dtype=np.float32)
    elif int(ref_raw.shape[0]) < pp_states:
        ref_vals = np.empty(pp_states, dtype=np.float32)
        ref_vals[: int(ref_raw.shape[0])] = ref_raw
        ref_vals[int(ref_raw.shape[0]) :] = np.float32(ref_raw[-1])
    else:
        ref_vals = ref_raw[:pp_states].astype(np.float32, copy=False)

    g_table = np.empty((pp_states, budget + 1), dtype=np.float32)
    pp_vs_ov_delta = np.float32(float(int(w_pp) - int(w_ov)))

    for p_idx in range(pp_states):
        if p_idx >= int(pp_max_idx):
            pp_cap = 0
        else:
            pp_cap = min(int(budget), _ceil_div_pos(int(pp_max_idx) - int(p_idx), int(GEM_SCALE_NORMAL)))

        prefix_best = np.empty(pp_cap + 1, dtype=np.float32)
        best = np.float32(ref_vals[int(p_idx)])
        prefix_best[0] = best

        for pp_steps in range(1, pp_cap + 1):
            pp_idx = int(p_idx) + int(pp_steps) * int(GEM_SCALE_NORMAL)
            if pp_idx > int(pp_max_idx):
                pp_idx = int(pp_max_idx)
            cand = np.float32(float(pp_steps) * float(pp_vs_ov_delta) + float(ref_vals[int(pp_idx)]))
            if cand > best:
                best = cand
            prefix_best[pp_steps] = best

        g_table[int(p_idx), : int(pp_cap) + 1] = prefix_best
        if int(pp_cap) < int(budget):
            g_table[int(p_idx), int(pp_cap) + 1 :] = prefix_best[int(pp_cap)]

    # Delta theorem table: state B dominates state A iff base_diff >= max_L(G_A(L)-G_B(L)).
    diff = g_table[:, None, :] - g_table[None, :, :]
    delta_max = diff.max(axis=2).astype(np.float32, copy=False)
    delta_min = diff.min(axis=2).astype(np.float32, copy=False)

    return EnvelopeDominanceLUT(
        pp_max_idx=int(pp_max_idx),
        budget_max=int(budget),
        delta_max=delta_max,
        delta_min=delta_min,
    )


def _envelope_dominates_from_delta(
    base_diff: np.ndarray,
    delta_max: np.ndarray,
    delta_min: np.ndarray,
) -> np.ndarray:
    ge = base_diff >= (delta_max + _ENVELOPE_DOMINANCE_TOL)
    strict = (base_diff > (delta_max + _ENVELOPE_DOMINANCE_TOL)) | (
        (delta_max - delta_min) > _ENVELOPE_DOMINANCE_TOL
    )
    return ge & strict


def _pp_ov_envelope_curve(
    *,
    pp_stat: int,
    base_lane: int,
    ref_pp: np.ndarray,
    budget_max: int,
    w_pp: int,
    w_ov: int,
) -> np.ndarray:
    budget = max(0, int(budget_max))
    if int(pp_stat) >= int(MAX_STAT_INDEX):
        pp_cap = 0
    else:
        pp_cap = min(int(budget), _ceil_div_pos(int(MAX_STAT_INDEX) - int(pp_stat), int(GEM_SCALE_NORMAL)))

    prefix_best = np.empty(pp_cap + 1, dtype=np.float32)
    best = np.float32(ref_pp[_clamp_idx(int(pp_stat))])
    prefix_best[0] = best

    delta = np.float32(float(int(w_pp) - int(w_ov)))
    for p in range(1, pp_cap + 1):
        pp_idx = _clamp_idx(int(pp_stat) + int(p) * int(GEM_SCALE_NORMAL))
        cand = np.float32(float(p) * float(delta) + float(ref_pp[pp_idx]))
        if cand > best:
            best = cand
        prefix_best[p] = best

    curve = np.empty(budget + 1, dtype=np.float32)
    base_f = np.float32(float(base_lane))
    w_ov_f = np.float32(float(w_ov))
    for l_budget in range(budget + 1):
        lim = pp_cap if l_budget >= pp_cap else int(l_budget)
        curve[l_budget] = base_f + np.float32(float(l_budget) * float(w_ov_f)) + prefix_best[lim]
    return curve


def _reduce_same_stat_envelope_frontier_with_codes(
    points: np.ndarray,
    codes: np.ndarray,
    *,
    p_color: str,
    s_color: str,
    selected_color: str,
    ref_pp: np.ndarray,
    budget_max: int = TOTAL_GEM_BUDGET,
    dominance_lut: EnvelopeDominanceLUT | None = None,
) -> tuple[EnvelopeReductionStats, np.ndarray, np.ndarray]:
    t0 = time.perf_counter()
    if points.size == 0 or codes.size == 0:
        stats = EnvelopeReductionStats(
            points_in=0,
            points_out=0,
            groups=0,
            groups_multi=0,
            max_group_size=0,
            seconds=float(time.perf_counter() - t0),
        )
        return stats, np.zeros((0, 6), dtype=np.int32), np.zeros(0, dtype=np.uint64)

    pts = np.asarray(points, dtype=np.int32)
    c_arr = np.asarray(codes, dtype=np.uint64)
    if int(pts.shape[0]) != int(c_arr.shape[0]):
        raise ValueError("points/codes length mismatch")

    stat_size = int(MAX_STAT_INDEX) + 1
    group_keys = (
        (((pts[:, 1].astype(np.int64, copy=False) * stat_size) + pts[:, 2].astype(np.int64, copy=False)) * stat_size)
        + pts[:, 3].astype(np.int64, copy=False)
    ) * stat_size + pts[:, 4].astype(np.int64, copy=False)
    group_order = np.argsort(group_keys, kind="stable")
    sorted_keys = group_keys[group_order]
    if int(sorted_keys.shape[0]) > 0:
        group_starts = np.concatenate(
            (
                np.asarray([0], dtype=np.int64),
                np.flatnonzero(sorted_keys[1:] != sorted_keys[:-1]).astype(np.int64) + 1,
            )
        )
    else:
        group_starts = np.zeros(0, dtype=np.int64)

    if dominance_lut is None:
        w_pp = _lane_weight("Chill", p_color=p_color, s_color=s_color, scale=GEM_STAT_TO_ELEMENT_SCALE)
        w_ov = _lane_weight(str(selected_color or ""), p_color=p_color, s_color=s_color, scale=ELEMENTAL_GEM_SCALE)
        lut = _build_envelope_dominance_lut(
            ref_pp=ref_pp,
            budget_max=int(budget_max),
            w_pp=int(w_pp),
            w_ov=int(w_ov),
        )
    else:
        lut = dominance_lut

    keep = np.ones(int(pts.shape[0]), dtype=np.bool_)
    groups_multi = 0
    max_group_size = 1

    for group_pos, start in enumerate(group_starts.tolist()):
        end = int(group_starts[group_pos + 1]) if group_pos + 1 < int(group_starts.shape[0]) else int(group_order.shape[0])
        g = int(end) - int(start)
        if g <= 1:
            continue
        groups_multi += 1
        if g > max_group_size:
            max_group_size = g

        idx_arr = group_order[int(start) : int(end)].astype(np.int64, copy=False)
        group_pp = np.clip(pts[idx_arr, 0], 0, int(lut.pp_max_idx)).astype(np.int32, copy=False)
        group_base = pts[idx_arr, 5].astype(np.float32, copy=False)

        if g <= 2048:
            delta_max_g = lut.delta_max[np.ix_(group_pp, group_pp)]
            delta_min_g = lut.delta_min[np.ix_(group_pp, group_pp)]
            base_diff = group_base[np.newaxis, :] - group_base[:, np.newaxis]
            dominates = _envelope_dominates_from_delta(base_diff, delta_max_g, delta_min_g)
            np.fill_diagonal(dominates, False)
            dominated = np.any(dominates, axis=1)
        else:
            dominated = np.zeros(g, dtype=np.bool_)
            for i in range(g):
                if dominated[i]:
                    continue
                delta_max_row = lut.delta_max[int(group_pp[i]), group_pp]
                delta_min_row = lut.delta_min[int(group_pp[i]), group_pp]
                base_diff = group_base - group_base[i]
                dominates_row = _envelope_dominates_from_delta(base_diff, delta_max_row, delta_min_row)
                dominates_row[i] = False
                if np.any(dominates_row):
                    dominated[i] = True

        if np.any(dominated):
            keep[idx_arr[dominated]] = False

    reduced_points = pts[keep].astype(np.int32, copy=False)
    reduced_codes = c_arr[keep].astype(np.uint64, copy=False)
    stats = EnvelopeReductionStats(
        points_in=int(pts.shape[0]),
        points_out=int(reduced_points.shape[0]),
        groups=int(group_starts.shape[0]),
        groups_multi=int(groups_multi),
        max_group_size=int(max_group_size),
        seconds=float(time.perf_counter() - t0),
    )
    return stats, reduced_points, reduced_codes


def _reduce_combined_pair_envelope_fast(
    *,
    gear_points: np.ndarray,
    mini_points: np.ndarray,
    pair_gear_idx: np.ndarray,
    pair_mini_idx: np.ndarray,
    dominance_lut: EnvelopeDominanceLUT,
) -> tuple[EnvelopeReductionStats, np.ndarray, np.ndarray]:
    t0 = time.perf_counter()
    if pair_gear_idx.size == 0:
        stats = EnvelopeReductionStats(
            points_in=0,
            points_out=0,
            groups=0,
            groups_multi=0,
            max_group_size=0,
            seconds=float(time.perf_counter() - t0),
        )
        return stats, np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32)

    gp = np.asarray(gear_points, dtype=np.int32)
    mp = np.asarray(mini_points, dtype=np.int32)
    gi = np.asarray(pair_gear_idx, dtype=np.int32)
    mi = np.asarray(pair_mini_idx, dtype=np.int32)

    g_pp = gp[gi, 0]
    cm = np.minimum(int(MAX_STAT_INDEX), gp[gi, 1] + mp[mi, 0])
    fm = np.minimum(int(MAX_STAT_INDEX), gp[gi, 2] + mp[mi, 1])
    ft = np.minimum(int(MAX_STAT_INDEX), gp[gi, 3] + mp[mi, 2])
    ff = np.minimum(int(MAX_STAT_INDEX), gp[gi, 4] + mp[mi, 3])
    base = (gp[gi, 5] + mp[mi, 4]).astype(np.float32, copy=False)

    stat_size = int(MAX_STAT_INDEX) + 1
    group_keys = ((((cm.astype(np.int64) * stat_size) + fm) * stat_size + ft) * stat_size) + ff
    order = np.argsort(group_keys, kind="stable")
    sorted_keys = group_keys[order]
    if int(sorted_keys.shape[0]) > 1:
        group_starts = np.concatenate(
            (
                np.asarray([0], dtype=np.int64),
                np.flatnonzero(sorted_keys[1:] != sorted_keys[:-1]).astype(np.int64) + 1,
            )
        )
        group_ends = np.concatenate((group_starts[1:], np.asarray([int(sorted_keys.shape[0])], dtype=np.int64)))
        group_sizes = group_ends - group_starts
        max_group_size = int(group_sizes.max()) if group_sizes.size else 1
        groups_multi = int(np.count_nonzero(group_sizes > 1))
    else:
        group_starts = np.zeros(1 if int(sorted_keys.shape[0]) else 0, dtype=np.int64)
        max_group_size = int(sorted_keys.shape[0])
        groups_multi = 0

    # Exact but intentionally conservative: the combined frontier usually has tiny
    # timing slices. If a future inventory produces large slices, skip this optional
    # reduction rather than making the hot path worse.
    if max_group_size > 64:
        stats = EnvelopeReductionStats(
            points_in=int(gi.shape[0]),
            points_out=int(gi.shape[0]),
            groups=int(group_starts.shape[0]),
            groups_multi=int(groups_multi),
            max_group_size=int(max_group_size),
            seconds=float(time.perf_counter() - t0),
        )
        return stats, gi, mi

    sorted_pp = np.clip(g_pp[order], 0, int(dominance_lut.pp_max_idx)).astype(np.int32, copy=False)
    sorted_base = base[order]
    dominated_sorted = np.zeros(int(order.shape[0]), dtype=np.bool_)

    for offset in range(1, int(max_group_size)):
        same_group = sorted_keys[int(offset) :] == sorted_keys[: -int(offset)]
        if not np.any(same_group):
            continue
        left = np.flatnonzero(same_group)
        right = left + int(offset)

        pp_left = sorted_pp[left]
        pp_right = sorted_pp[right]
        base_left = sorted_base[left]
        base_right = sorted_base[right]

        right_dominates_left = _envelope_dominates_from_delta(
            base_right - base_left,
            dominance_lut.delta_max[pp_left, pp_right],
            dominance_lut.delta_min[pp_left, pp_right],
        )
        if np.any(right_dominates_left):
            dominated_sorted[left[right_dominates_left]] = True

        left_dominates_right = _envelope_dominates_from_delta(
            base_left - base_right,
            dominance_lut.delta_max[pp_right, pp_left],
            dominance_lut.delta_min[pp_right, pp_left],
        )
        if np.any(left_dominates_right):
            dominated_sorted[right[left_dominates_right]] = True

    keep = np.ones(int(order.shape[0]), dtype=np.bool_)
    if np.any(dominated_sorted):
        keep[order[dominated_sorted]] = False

    stats = EnvelopeReductionStats(
        points_in=int(gi.shape[0]),
        points_out=int(np.count_nonzero(keep)),
        groups=int(group_starts.shape[0]),
        groups_multi=int(groups_multi),
        max_group_size=int(max_group_size),
        seconds=float(time.perf_counter() - t0),
    )
    return stats, gi[keep].astype(np.int32, copy=False), mi[keep].astype(np.int32, copy=False)


def _reduce_gear_dp_frontier_arrays(stats: np.ndarray, codes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if stats.size == 0 or codes.size == 0:
        return np.zeros((0, 6), dtype=np.int32), np.zeros(0, dtype=np.uint64)

    pts = np.asarray(stats, dtype=np.int32)
    code_arr = np.asarray(codes, dtype=np.uint64)
    if pts.ndim != 2 or int(pts.shape[1]) != 6:
        raise ValueError(f"gear DP stats must have shape (n, 6), got {tuple(pts.shape)}")
    if int(pts.shape[0]) != int(code_arr.shape[0]):
        raise ValueError("gear DP stats/code length mismatch")

    stride = np.uint64(int(MAX_STAT_INDEX) + 1)
    stat_key = pts[:, 0].astype(np.uint64, copy=False)
    for col in range(1, 5):
        stat_key = (stat_key * stride) + pts[:, col].astype(np.uint64, copy=False)

    order = np.lexsort(
        (
            -pts[:, 5].astype(np.int64, copy=False),
            stat_key,
        )
    )
    sorted_pts = pts[order]
    sorted_codes = code_arr[order]
    sorted_key = stat_key[order]

    same_key = np.zeros(int(sorted_pts.shape[0]), dtype=np.bool_)
    if int(sorted_pts.shape[0]) > 1:
        same_key[1:] = sorted_key[1:] == sorted_key[:-1]
    keep = ~same_key
    return sorted_pts[keep].astype(np.int32, copy=False), sorted_codes[keep].astype(np.uint64, copy=False)


def _dp_gear_ff_base_frontier_with_codes(
    gear_pool: dict[str, list[dict]],
    *,
    p_color: str,
    s_color: str,
    pack: _BitPack,
) -> tuple[np.ndarray, np.ndarray, LaneAwareGearDPStats]:
    t0 = time.perf_counter()

    stats = np.zeros((1, 6), dtype=np.int32)
    codes = np.zeros(1, dtype=np.uint64)

    slot_items: list[tuple[np.ndarray, np.ndarray]] = []
    for slot_idx, slot in enumerate(_SLOTS):
        items = gear_pool.get(slot, [])
        if not items:
            return (
                np.zeros((0, 6), dtype=np.int32),
                np.zeros(0, dtype=np.uint64),
                LaneAwareGearDPStats(0, 0, 0.0, 0.0, 0, float(time.perf_counter() - t0)),
            )
        item_stats = np.zeros((len(items), 6), dtype=np.int32)
        item_codes = np.zeros(len(items), dtype=np.uint64)
        shift = pack.shifts[slot_idx]
        for item_idx, it in enumerate(items):
            dpp, dcm, dfm, dft, dff = _item_vec_5(it)
            dbase = _lane_base_init(it, p_color, s_color)
            item_stats[int(item_idx), 0] = int(dpp)
            item_stats[int(item_idx), 1] = int(dcm)
            item_stats[int(item_idx), 2] = int(dfm)
            item_stats[int(item_idx), 3] = int(dft)
            item_stats[int(item_idx), 4] = int(dff)
            item_stats[int(item_idx), 5] = int(dbase)
            item_codes[int(item_idx)] = np.uint64(int(item_idx) << int(shift))
        slot_items.append((item_stats, item_codes))

    for item_stats, item_codes in slot_items:
        row_count = int(stats.shape[0])
        item_count = int(item_stats.shape[0])
        expanded = np.empty((row_count * item_count, 6), dtype=np.int32)

        expanded[:, 0] = (stats[:, 0, None] + item_stats[None, :, 0]).ravel()
        expanded[:, 1] = (stats[:, 1, None] + item_stats[None, :, 1]).ravel()
        expanded[:, 2] = (stats[:, 2, None] + item_stats[None, :, 2]).ravel()
        expanded[:, 3] = (stats[:, 3, None] + item_stats[None, :, 3]).ravel()
        expanded[:, 4] = (stats[:, 4, None] + item_stats[None, :, 4]).ravel()
        expanded[:, 5] = (stats[:, 5, None] + item_stats[None, :, 5]).ravel()
        np.clip(expanded[:, :5], 0, int(MAX_STAT_INDEX), out=expanded[:, :5])

        expanded_codes = (codes[:, None] | item_codes[None, :]).ravel()
        stats, codes = _reduce_gear_dp_frontier_arrays(expanded, expanded_codes)

    if int(stats.shape[0]) > 0:
        group_start = np.ones(int(stats.shape[0]), dtype=np.bool_)
        if int(stats.shape[0]) > 1:
            group_start[1:] = np.any(stats[1:, :4] != stats[:-1, :4], axis=1)
        starts = np.flatnonzero(group_start)
        sizes = np.diff(np.append(starts, int(stats.shape[0]))).astype(np.int32, copy=False)
    else:
        sizes = np.zeros(0, dtype=np.int32)
    pairs = int(sizes.sum())
    dp_stats = LaneAwareGearDPStats(
        keys_4d=int(sizes.shape[0]),
        pairs_6d=pairs,
        frontier_mean=float(sizes.mean()) if sizes.size else 0.0,
        frontier_p95=float(np.percentile(sizes, 95)) if sizes.size else 0.0,
        frontier_max=int(sizes.max()) if sizes.size else 0,
        seconds=float(time.perf_counter() - t0),
    )
    return stats.astype(np.int32, copy=False), codes.astype(np.uint64, copy=False), dp_stats


def _suffix_max_4d(src: np.ndarray, dst: np.ndarray) -> None:
    np.copyto(dst, src)

    v0 = dst[::-1, :, :, :]
    np.maximum.accumulate(v0, axis=0, out=v0)
    v1 = dst[:, ::-1, :, :]
    np.maximum.accumulate(v1, axis=1, out=v1)
    v2 = dst[:, :, ::-1, :]
    np.maximum.accumulate(v2, axis=2, out=v2)
    v3 = dst[:, :, :, ::-1]
    np.maximum.accumulate(v3, axis=3, out=v3)


def _suffix_max_4d_inplace(dst: np.ndarray) -> None:
    """In-place 4D suffix max.

    This is equivalent to `_suffix_max_4d(src, dst)` with `src == dst`, but avoids
    the full-array copy.
    """

    v0 = dst[::-1, :, :, :]
    np.maximum.accumulate(v0, axis=0, out=v0)
    v1 = dst[:, ::-1, :, :]
    np.maximum.accumulate(v1, axis=1, out=v1)
    v2 = dst[:, :, ::-1, :]
    np.maximum.accumulate(v2, axis=2, out=v2)
    v3 = dst[:, :, :, ::-1]
    np.maximum.accumulate(v3, axis=3, out=v3)


def _suffix_max_cm_fm_inplace(dst: np.ndarray) -> None:
    v0 = dst[::-1, :, :, :]
    np.maximum.accumulate(v0, axis=0, out=v0)
    v1 = dst[:, ::-1, :, :]
    np.maximum.accumulate(v1, axis=1, out=v1)


_PAIR_CODE_MASK = np.uint64(0xFFFF_FFFF)


def _pack_pair_indices(gear_idx: np.ndarray, mini_idx: np.ndarray) -> np.ndarray:
    g = np.asarray(gear_idx, dtype=np.uint64)
    m = np.asarray(mini_idx, dtype=np.uint64)
    if g.shape != m.shape:
        raise ValueError("pair idx shape mismatch")
    return (g << np.uint64(32)) | (m & _PAIR_CODE_MASK)


def _unpack_pair_codes(pair_codes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    c = np.asarray(pair_codes, dtype=np.uint64)
    g = (c >> np.uint64(32)).astype(np.int32, copy=False)
    m = (c & _PAIR_CODE_MASK).astype(np.int32, copy=False)
    return g, m


def _global_gear_skyline_points_6d_lane_base_with_codes_cpu_reference(
    states: dict[tuple[int, int, int, int], list[tuple[int, int, int]]],
) -> tuple[LaneAwareGlobalSkylineStats, np.ndarray, np.ndarray]:
    t0 = time.perf_counter()
    if not states:
        return (
            LaneAwareGlobalSkylineStats(points_in=0, points_out=0, seconds=float(time.perf_counter() - t0)),
            np.zeros((0, 6), dtype=np.int32),
            np.zeros(0, dtype=np.uint64),
        )

    keys = list(states.keys())
    max_pp = max(k[0] for k in keys)
    max_cm = max(k[1] for k in keys)
    max_fm = max(k[2] for k in keys)
    max_ft = max(k[3] for k in keys)

    counts = np.zeros(max_pp + 1, dtype=np.int64)
    total_points = 0
    max_ff = 0
    for (pp, _cm, _fm, _ft), frontier in states.items():
        n = len(frontier)
        counts[int(pp)] += n
        total_points += n
        for ff, _base, _code in frontier:
            if ff > max_ff:
                max_ff = int(ff)

    cm_size = int(max_cm) + 1
    fm_size = int(max_fm) + 1
    ft_size = int(max_ft) + 1
    ff_size = int(max_ff) + 1

    offsets = np.zeros(max_pp + 2, dtype=np.int64)
    offsets[1:] = np.cumsum(counts)

    flat = np.empty(total_points, dtype=np.int32)
    base = np.empty(total_points, dtype=np.int16)
    code = np.empty(total_points, dtype=np.uint64)
    curs = offsets[:-1].copy()

    for (pp, cm, fm, ft), frontier in states.items():
        pp_i = int(pp)
        cur = int(curs[pp_i])
        prefix = ((int(cm) * fm_size + int(fm)) * ft_size + int(ft)) * ff_size
        for ff, b, c in frontier:
            flat[cur] = prefix + int(ff)
            base[cur] = np.int16(int(b))
            code[cur] = np.uint64(int(c))
            cur += 1
        curs[pp_i] = cur

    shape = (cm_size, fm_size, ft_size, ff_size)
    grid_elems = int(cm_size) * int(fm_size) * int(ft_size) * int(ff_size)
    if grid_elems > 250_000_000:
        raise MemoryError(f"Gear skyline grid too large: {shape} ({grid_elems:,} elems). Try reducing pools.")

    layer_grid = np.full(shape, -1, dtype=np.int16)
    layer_suffix = np.empty(shape, dtype=np.int16)
    higher_grid = np.full(shape, -1, dtype=np.int16)
    higher_suffix = np.full(shape, -1, dtype=np.int16)

    layer_flat = layer_grid.reshape(-1)
    higher_flat = higher_grid.reshape(-1)

    kept_chunks: list[np.ndarray] = []
    kept_codes: list[np.ndarray] = []
    kept_total = 0
    higher_valid = False

    for pp in range(int(max_pp), -1, -1):
        s = int(offsets[pp])
        e = int(offsets[pp + 1])
        if s >= e:
            continue

        slice_flat = flat[s:e]
        slice_base = base[s:e]
        slice_code = code[s:e]

        order = np.lexsort((-slice_base.astype(np.int32, copy=False), slice_flat))
        flat_sorted = slice_flat[order]
        base_sorted = slice_base[order]
        code_sorted = slice_code[order]

        uniq_flat, first_idx = np.unique(flat_sorted, return_index=True)
        base_u = base_sorted[first_idx]
        code_u = code_sorted[first_idx]

        layer_flat.fill(-1)
        layer_flat[uniq_flat] = base_u

        _suffix_max_4d(layer_grid, layer_suffix)

        ff = uniq_flat % ff_size
        tmp = uniq_flat // ff_size
        ft = tmp % ft_size
        tmp //= ft_size
        fm = tmp % fm_size
        cm = tmp // fm_size

        strict = np.full_like(base_u, -1)
        m0 = (cm + 1) < cm_size
        if np.any(m0):
            strict[m0] = np.maximum(strict[m0], layer_suffix[cm[m0] + 1, fm[m0], ft[m0], ff[m0]])
        m1 = (fm + 1) < fm_size
        if np.any(m1):
            strict[m1] = np.maximum(strict[m1], layer_suffix[cm[m1], fm[m1] + 1, ft[m1], ff[m1]])
        m2 = (ft + 1) < ft_size
        if np.any(m2):
            strict[m2] = np.maximum(strict[m2], layer_suffix[cm[m2], fm[m2], ft[m2] + 1, ff[m2]])
        m3 = (ff + 1) < ff_size
        if np.any(m3):
            strict[m3] = np.maximum(strict[m3], layer_suffix[cm[m3], fm[m3], ft[m3], ff[m3] + 1])

        layer_sky = base_u > strict
        if higher_valid:
            layer_sky &= base_u > higher_suffix[cm, fm, ft, ff]

        if not np.any(layer_sky):
            continue

        keep_n = int(np.count_nonzero(layer_sky))
        kept_total += keep_n

        cm_k = cm[layer_sky].astype(np.int32)
        fm_k = fm[layer_sky].astype(np.int32)
        ft_k = ft[layer_sky].astype(np.int32)
        ff_k = ff[layer_sky].astype(np.int32)
        b_k = base_u[layer_sky].astype(np.int32)
        kept_chunks.append(
            np.column_stack(
                (
                    np.full(cm_k.shape, int(pp), dtype=np.int32),
                    cm_k,
                    fm_k,
                    ft_k,
                    ff_k,
                    b_k,
                )
            )
        )
        kept_codes.append(code_u[layer_sky].astype(np.uint64, copy=False))

        idx = uniq_flat[layer_sky]
        vals = base_u[layer_sky]
        higher_flat[idx] = np.maximum(higher_flat[idx], vals)
        _suffix_max_4d(higher_grid, higher_suffix)
        higher_valid = True

    points = np.concatenate(kept_chunks, axis=0) if kept_chunks else np.zeros((0, 6), dtype=np.int32)
    codes = np.concatenate(kept_codes, axis=0) if kept_codes else np.zeros(0, dtype=np.uint64)
    stats = LaneAwareGlobalSkylineStats(
        points_in=int(total_points),
        points_out=int(kept_total),
        seconds=float(time.perf_counter() - t0),
    )
    return stats, points, codes


def _global_gear_skyline_points_6d_lane_base_with_codes(
    gear_points: np.ndarray,
    gear_codes: np.ndarray,
) -> tuple[LaneAwareGlobalSkylineStats, np.ndarray, np.ndarray]:
    points_in, points, codes, seconds = global_gear_skyline_points_6d_gpu_from_arrays(gear_points, gear_codes)
    stats = LaneAwareGlobalSkylineStats(
        points_in=int(points_in),
        points_out=int(points.shape[0]),
        seconds=float(seconds),
    )
    return stats, points, codes


def _evaluate_product_exact(
    *,
    registry: ItemRegistry,
    gpu_arrays: dict[str, np.ndarray],
    base_fixed_stats_arr: np.ndarray,
    calc_song: dict,
    ref_arrays: dict,
    flags: dict[str, int],
    song_slot: int,
    gpu_client: Any | None = None,
    gear_ids: np.ndarray,
    mini_ids: np.ndarray,
    gear_codes: np.ndarray,
    mini_codes: np.ndarray,
    keep_top_k: int,
    status_cb: Callable[[str], None] | None,
) -> tuple[np.ndarray | None, list[tuple[int, int, int]]]:
    if gear_ids.size == 0 or mini_ids.size == 0:
        return None, []

    default_eval_batch = min(int(gem_fields.MAX_GENOMES), 8192)
    max_batch = max(1, min(int(gem_fields.MAX_GENOMES), int(env_get("SKYLINE_BASE_EVAL_BATCH", default_eval_batch))))
    total = int(gear_ids.shape[0]) * int(mini_ids.shape[0])
    g_n = int(gear_ids.shape[0])
    m_n = int(mini_ids.shape[0])

    g_idx = np.repeat(np.arange(g_n, dtype=np.int32), m_n)
    m_idx = np.tile(np.arange(m_n, dtype=np.int32), g_n)

    def _candidate_batches() -> Iterable[tuple[np.ndarray, np.ndarray, np.ndarray]]:
        for offset in range(0, int(total), int(max_batch)):
            n = min(int(max_batch), int(total) - int(offset))
            seg = slice(offset, offset + n)

            batch = np.empty((n, 9), dtype=np.int32)
            batch[:, :6] = gear_ids[g_idx[seg]]
            batch[:, 6:] = mini_ids[m_idx[seg]]

            batch_gc = gear_codes[g_idx[seg]].astype(np.uint64, copy=False)
            batch_mc = mini_codes[m_idx[seg]].astype(np.uint64, copy=False)
            yield batch, batch_gc, batch_mc

    return batched_registry_eval(
        gpu_arrays=gpu_arrays,
        base_fixed_stats_arr=base_fixed_stats_arr,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        flags=flags,
        song_slot=int(song_slot),
        candidate_total=total,
        candidate_batches=_candidate_batches(),
        keep_top_k=int(keep_top_k),
        gpu_client=gpu_client,
        status_cb=status_cb,
        status_label="skyline",
        status_every=max_batch * 16,
    )


def _combined_global_skyline_pairs_6d_lane_base_with_indices_cpu_reference(
    gear_points: np.ndarray,
    mini_points: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute the exact global skyline for (gear ⊕ minis) and return argmax pairs.

    Dimensions (maximize):
      (PP, CM, FM, FT, FF, base_lane)

    Inputs are already reduced skylines:
    - gear_points: (G,6) => (pp,cm,fm,ft,ff,base_lane)
    - mini_points: (M,5) => (cm,fm,ft,ff,base_lane)

    Returns:
      (gear_idx, mini_idx) arrays (int32) indexing into the original gear/minis skyline arrays.

    Notes:
    - Minis have no PP dimension in the current dataset; PP is just the gear PP.
    - We clamp combined (CM,FM,FT,FF) coordinates to MAX_STAT_INDEX because the scorer clamps
      these stats; larger values are score-equivalent.
    """

    if gear_points.size == 0 or mini_points.size == 0:
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32)

    gear_points = gear_points.astype(np.int32, copy=False)
    mini_points = mini_points.astype(np.int32, copy=False)

    max_pp = int(np.max(gear_points[:, 0]))
    max_cm = int(min(MAX_STAT_INDEX, int(np.max(gear_points[:, 1]) + np.max(mini_points[:, 0]))))
    max_fm = int(min(MAX_STAT_INDEX, int(np.max(gear_points[:, 2]) + np.max(mini_points[:, 1]))))
    max_ft = int(min(MAX_STAT_INDEX, int(np.max(gear_points[:, 3]) + np.max(mini_points[:, 2]))))
    max_ff = int(min(MAX_STAT_INDEX, int(np.max(gear_points[:, 4]) + np.max(mini_points[:, 3]))))

    cm_size = max_cm + 1
    fm_size = max_fm + 1
    ft_size = max_ft + 1
    ff_size = max_ff + 1

    shape = (cm_size, fm_size, ft_size, ff_size)
    grid_elems = int(cm_size) * int(fm_size) * int(ft_size) * int(ff_size)
    base_max = int(np.max(gear_points[:, 5]) + np.max(mini_points[:, 4]))
    base_dtype = np.int16 if base_max <= int(np.iinfo(np.int16).max) else np.int32

    # Guardrail: combined skylines can inflate ranges; keep this as an opt-in optimization.
    # Use a bytes-based guard so we can safely take advantage of int16 grids.
    approx_bytes = int(grid_elems) * int(np.dtype(base_dtype).itemsize) * 3
    dense_limit_gib = _read_combined_dense_max_gib()
    if approx_bytes > int(float(dense_limit_gib) * float(1024**3)):
        gib = float(approx_bytes) / float(1024**3)
        raise MemoryError(
            f"Combined skyline grid too large: {shape} ({grid_elems:,} elems, ~{gib:.2f} GiB, "
            f"limit={dense_limit_gib:.2f} GiB)"
        )

    gear_pp = gear_points[:, 0]
    pp_order = np.argsort(gear_pp, kind="stable")
    g_sorted = gear_points[pp_order]
    g_orig_idx_sorted = pp_order.astype(np.int32, copy=False)

    pp_sorted = g_sorted[:, 0]
    pp_counts = np.bincount(pp_sorted, minlength=max_pp + 1).astype(np.int64, copy=False)
    pp_offsets = np.zeros(max_pp + 2, dtype=np.int64)
    pp_offsets[1:] = np.cumsum(pp_counts)

    m_cm = mini_points[:, 0].astype(np.int32, copy=False)
    m_fm = mini_points[:, 1].astype(np.int32, copy=False)
    m_ft = mini_points[:, 2].astype(np.int32, copy=False)
    m_ff = mini_points[:, 3].astype(np.int32, copy=False)
    m_base = mini_points[:, 4].astype(np.int32, copy=False)
    m_idx = np.arange(int(mini_points.shape[0]), dtype=np.int32)

    layer_grid = np.full(shape, -1, dtype=base_dtype)
    higher_grid = np.full(shape, -1, dtype=base_dtype)
    higher_suffix = np.empty(shape, dtype=base_dtype)

    layer_flat = layer_grid.reshape(-1)
    higher_flat = higher_grid.reshape(-1)

    kept_g_idx: list[np.ndarray] = []
    kept_m_idx: list[np.ndarray] = []

    higher_valid = False

    for pp in range(int(max_pp), -1, -1):
        s = int(pp_offsets[pp])
        e = int(pp_offsets[pp + 1])
        if s >= e:
            continue

        g_pp_pts = g_sorted[s:e]
        g_idx = g_orig_idx_sorted[s:e]

        g_cm = g_pp_pts[:, 1].astype(np.int32, copy=False)
        g_fm = g_pp_pts[:, 2].astype(np.int32, copy=False)
        g_ft = g_pp_pts[:, 3].astype(np.int32, copy=False)
        g_ff = g_pp_pts[:, 4].astype(np.int32, copy=False)
        g_base = g_pp_pts[:, 5].astype(np.int32, copy=False)

        # Enumerate product points for this PP (gear_pp ⊕ mini_skyline).
        cm_all = (g_cm[:, None] + m_cm[None, :]).astype(np.int32, copy=False)
        fm_all = (g_fm[:, None] + m_fm[None, :]).astype(np.int32, copy=False)
        ft_all = (g_ft[:, None] + m_ft[None, :]).astype(np.int32, copy=False)
        ff_all = (g_ff[:, None] + m_ff[None, :]).astype(np.int32, copy=False)
        base_all = (g_base[:, None] + m_base[None, :]).astype(np.int32, copy=False)

        # Clamp combined stat coordinates.
        np.minimum(cm_all, max_cm, out=cm_all)
        np.minimum(fm_all, max_fm, out=fm_all)
        np.minimum(ft_all, max_ft, out=ft_all)
        np.minimum(ff_all, max_ff, out=ff_all)

        cm_flat = cm_all.reshape(-1)
        fm_flat = fm_all.reshape(-1)
        ft_flat = ft_all.reshape(-1)
        ff_flat = ff_all.reshape(-1)
        base_flat = base_all.reshape(-1)

        flat = (((cm_flat * fm_size) + fm_flat) * ft_size + ft_flat) * ff_size + ff_flat

        # Argmax carriers: indices into (gear_points, mini_points).
        g_idx_flat = np.repeat(g_idx, int(m_cm.shape[0])).astype(np.int32, copy=False)
        m_idx_flat = np.tile(m_idx, int(g_cm.shape[0])).astype(np.int32, copy=False)

        order = np.lexsort((-base_flat.astype(np.int64, copy=False), flat.astype(np.int64, copy=False)))
        flat_sorted = flat[order].astype(np.int32, copy=False)
        base_sorted = base_flat[order].astype(np.int32, copy=False)
        g_sorted_idx = g_idx_flat[order]
        m_sorted_idx = m_idx_flat[order]

        uniq_flat, first_idx = np.unique(flat_sorted, return_index=True)
        base_u = base_sorted[first_idx]
        g_u = g_sorted_idx[first_idx]
        m_u = m_sorted_idx[first_idx]

        layer_flat.fill(-1)
        layer_flat[uniq_flat] = base_u
        _suffix_max_cm_fm_inplace(layer_grid)

        ff_u = uniq_flat % ff_size
        tmp = uniq_flat // ff_size
        ft_u = tmp % ft_size
        tmp //= ft_size
        fm_u = tmp % fm_size
        cm_u = tmp // fm_size

        strict = np.full_like(base_u, -1)
        m0 = (cm_u + 1) < cm_size
        if np.any(m0):
            strict[m0] = np.maximum(strict[m0], layer_grid[cm_u[m0] + 1, fm_u[m0], ft_u[m0], ff_u[m0]])
        m1 = (fm_u + 1) < fm_size
        if np.any(m1):
            strict[m1] = np.maximum(strict[m1], layer_grid[cm_u[m1], fm_u[m1] + 1, ft_u[m1], ff_u[m1]])

        layer_sky = base_u > strict
        if higher_valid:
            layer_sky &= base_u > higher_suffix[cm_u, fm_u, ft_u, ff_u]

        if not np.any(layer_sky):
            continue

        kept_g_idx.append(g_u[layer_sky].astype(np.int32, copy=False))
        kept_m_idx.append(m_u[layer_sky].astype(np.int32, copy=False))

        idx = uniq_flat[layer_sky]
        vals_h = base_u[layer_sky]
        higher_flat[idx] = np.maximum(higher_flat[idx], vals_h)
        np.copyto(higher_suffix, higher_grid)
        _suffix_max_cm_fm_inplace(higher_suffix)
        higher_valid = True

    if not kept_g_idx:
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32)

    return np.concatenate(kept_g_idx, axis=0), np.concatenate(kept_m_idx, axis=0)


def _combined_global_skyline_pairs_6d_lane_base_with_indices(
    gear_points: np.ndarray,
    mini_points: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Timing-cell skyline over gear ⊕ mini stat products."""

    gpu_mode = _read_combined_dense_gpu_mode()
    if gpu_mode in {"auto", "gpu"}:
        try:
            pair_g, pair_m, _seconds = combined_global_skyline_pairs_6d_dense_gpu(gear_points, mini_points)
            return pair_g, pair_m
        except MemoryError:
            if gpu_mode == "gpu":
                raise

    mode = _read_combined_dense_mode()
    if mode in {"auto", "dense"}:
        try:
            return _combined_global_skyline_pairs_6d_lane_base_with_indices_cpu_reference(gear_points, mini_points)
        except MemoryError:
            if mode == "dense":
                raise
    return combined_global_skyline_pairs_6d_sparse(gear_points, mini_points)


def _pair_ftff_cap_arrays(
    *,
    base_fixed_stats_arr: np.ndarray,
    gear_points: np.ndarray,
    mini_points: np.ndarray,
    pair_gear_idx: np.ndarray,
    pair_mini_idx: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    if pair_gear_idx.size == 0:
        return np.zeros(0, dtype=np.int16), np.zeros(0, dtype=np.int16)

    base_arr = np.asarray(base_fixed_stats_arr, dtype=np.int32).reshape(-1)
    base_ft = int(base_arr[3]) if int(base_arr.shape[0]) > 3 else 0
    base_ff = int(base_arr[4]) if int(base_arr.shape[0]) > 4 else 0

    gp = np.asarray(gear_points, dtype=np.int32)
    mp = np.asarray(mini_points, dtype=np.int32)
    gi = np.asarray(pair_gear_idx, dtype=np.int32)
    mi = np.asarray(pair_mini_idx, dtype=np.int32)

    pair_ft = np.minimum(int(MAX_STAT_INDEX), gp[gi, 3] + mp[mi, 2]) + int(base_ft)
    pair_ff = np.minimum(int(MAX_STAT_INDEX), gp[gi, 4] + mp[mi, 3]) + int(base_ff)
    rem_ft = np.maximum(0, int(MAX_STAT_INDEX) - pair_ft)
    rem_ff = np.maximum(0, int(MAX_STAT_INDEX) - pair_ff)
    ft_caps = np.minimum(int(TOTAL_GEM_BUDGET), rem_ft // int(GEM_SCALE_FEVER)).astype(np.int16, copy=False)
    ff_caps = np.minimum(int(TOTAL_GEM_BUDGET), rem_ff // int(GEM_SCALE_FEVER)).astype(np.int16, copy=False)
    return ft_caps, ff_caps


def _evaluate_pairs_exact(
    *,
    gpu_arrays: dict[str, np.ndarray],
    base_fixed_stats_arr: np.ndarray,
    calc_song: dict,
    ref_arrays: dict,
    flags: dict[str, int],
    song_slot: int,
    gpu_client: Any | None = None,
    gear_ids: np.ndarray,
    mini_ids: np.ndarray,
    gear_codes: np.ndarray,
    mini_codes: np.ndarray,
    pair_gear_idx: np.ndarray,
    pair_mini_idx: np.ndarray,
    pair_max_ft_gems: np.ndarray | None = None,
    pair_max_ff_gems: np.ndarray | None = None,
    keep_top_k: int,
    status_cb: Callable[[str], None] | None,
) -> tuple[np.ndarray | None, list[tuple[int, int, int]]]:
    if pair_gear_idx.size == 0 or pair_mini_idx.size == 0:
        return None, []

    default_eval_batch = min(int(gem_fields.MAX_GENOMES), 8192)
    max_batch = max(1, min(int(gem_fields.MAX_GENOMES), int(env_get("SKYLINE_BASE_EVAL_BATCH", default_eval_batch))))
    total = int(pair_gear_idx.shape[0])
    g_idx = np.asarray(pair_gear_idx, dtype=np.int32)
    m_idx = np.asarray(pair_mini_idx, dtype=np.int32)
    ft_caps = None if pair_max_ft_gems is None else np.asarray(pair_max_ft_gems, dtype=np.int16)
    ff_caps = None if pair_max_ff_gems is None else np.asarray(pair_max_ff_gems, dtype=np.int16)
    if ft_caps is not None and ff_caps is not None and int(ft_caps.shape[0]) == total and int(ff_caps.shape[0]) == total:
        cap_key = ft_caps.astype(np.int32, copy=False) * (int(TOTAL_GEM_BUDGET) + 1)
        cap_key += ff_caps.astype(np.int32, copy=False)
        order = np.argsort(cap_key, kind="stable")
        g_idx = g_idx[order]
        m_idx = m_idx[order]
        ft_caps = ft_caps[order]
        ff_caps = ff_caps[order]
    else:
        ft_caps = None
        ff_caps = None

    warmup_batch = min(int(total), max(1, min(int(max_batch), 256)))

    def _build_candidate_batch(
        offset: int,
        n: int,
    ) -> (
        tuple[np.ndarray, np.ndarray, np.ndarray]
        | tuple[np.ndarray, np.ndarray, np.ndarray, int, int]
    ):
        seg = slice(int(offset), int(offset) + int(n))
        g_seg = g_idx[seg]
        m_seg = m_idx[seg]

        batch = np.empty((int(n), 9), dtype=np.int32)
        batch[:, :6] = gear_ids[g_seg]
        batch[:, 6:] = mini_ids[m_seg]
        batch_gc = gear_codes[g_seg].astype(np.uint64, copy=False)
        batch_mc = mini_codes[m_seg].astype(np.uint64, copy=False)
        if ft_caps is not None and ff_caps is not None:
            max_ft = int(np.max(ft_caps[seg])) if int(n) > 0 else int(TOTAL_GEM_BUDGET)
            max_ff = int(np.max(ff_caps[seg])) if int(n) > 0 else int(TOTAL_GEM_BUDGET)
            return batch, batch_gc, batch_mc, max_ft, max_ff
        return batch, batch_gc, batch_mc

    def _candidate_batches() -> Iterable[
        tuple[np.ndarray, np.ndarray, np.ndarray]
        | tuple[np.ndarray, np.ndarray, np.ndarray, int, int]
    ]:
        offset = 0
        if int(warmup_batch) > 0:
            yield _build_candidate_batch(0, int(warmup_batch))
            offset = int(warmup_batch)

        for offset in range(int(offset), int(total), int(max_batch)):
            n = min(int(max_batch), int(total) - int(offset))
            yield _build_candidate_batch(int(offset), int(n))

    return batched_registry_eval(
        gpu_arrays=gpu_arrays,
        base_fixed_stats_arr=base_fixed_stats_arr,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        flags=flags,
        song_slot=int(song_slot),
        candidate_total=total,
        candidate_batches=_candidate_batches(),
        keep_top_k=int(keep_top_k),
        gpu_client=gpu_client,
        status_cb=status_cb,
        status_label="exact_skyline combined-skyline",
        status_every=max_batch * 32,
    )

def _solve_exact_skyline_ctx(ctx: SolverContext) -> tuple[dict | None, list, list, None, list, list, list[dict]]:
    solve_started = time.perf_counter()
    phase_seconds: dict[str, float] = {}
    phase_counts: dict[str, int] = {}
    status_cb = ctx.status_cb
    if status_cb is None:

        def _noop_status_cb(_message: str) -> None:
            return None

        status_cb = _noop_status_cb

    mini_points = ctx.mini_points
    mini_codes = ctx.mini_codes
    if mini_points.size == 0:
        return None, [], [], None, [], [], []

    status_cb("skyline: gear DP")
    phase_started = time.perf_counter()
    dp_points, dp_codes, dp_stats = _dp_gear_ff_base_frontier_with_codes(
        ctx.gear_pool,
        p_color=ctx.p_color,
        s_color=ctx.s_color,
        pack=ctx.gear_pack,
    )
    _record_phase(phase_seconds, "gear_dp_cpu", phase_started)
    phase_counts["gear_dp_pairs"] = int(dp_stats.pairs_6d)
    phase_counts["gear_dp_keys_4d"] = int(dp_stats.keys_4d)
    if dp_points.size == 0:
        return None, [], [], None, [], [], []

    status_cb("skyline: gear timing-cell skyline")
    phase_started = time.perf_counter()
    gear_sky_stats, gear_points, gear_codes = _global_gear_skyline_points_6d_lane_base_with_codes(dp_points, dp_codes)
    _record_phase(phase_seconds, "gear_global_skyline_gpu", phase_started)
    phase_counts["gear_global_skyline_in"] = int(gear_sky_stats.points_in)
    phase_counts["gear_global_skyline_out"] = int(gear_sky_stats.points_out)
    if gear_points.size == 0:
        return None, [], [], None, [], [], []

    ref_pp_raw = ctx.ref_arrays.get("Perfect Points") if isinstance(ctx.ref_arrays, dict) else None
    ref_pp = np.asarray(ref_pp_raw, dtype=np.float32) if ref_pp_raw is not None else np.zeros(0, dtype=np.float32)
    envelope_lut: EnvelopeDominanceLUT | None = None
    if ref_pp.ndim == 1 and ref_pp.shape[0] > 0:
        phase_started = time.perf_counter()
        w_pp = _lane_weight("Chill", p_color=ctx.p_color, s_color=ctx.s_color, scale=GEM_STAT_TO_ELEMENT_SCALE)
        w_ov = _lane_weight(
            str(ctx.selected_color or ""),
            p_color=ctx.p_color,
            s_color=ctx.s_color,
            scale=ELEMENTAL_GEM_SCALE,
        )
        envelope_lut = _build_envelope_dominance_lut(
            ref_pp=ref_pp,
            budget_max=int(TOTAL_GEM_BUDGET),
            w_pp=int(w_pp),
            w_ov=int(w_ov),
        )
        _record_phase(phase_seconds, "envelope_lut_cpu", phase_started)
        status_cb("skyline: local envelope prune")
        phase_started = time.perf_counter()
        env_stats, gear_points, gear_codes = _reduce_same_stat_envelope_frontier_with_codes(
            gear_points,
            gear_codes,
            p_color=ctx.p_color,
            s_color=ctx.s_color,
            selected_color=ctx.selected_color,
            ref_pp=ref_pp,
            budget_max=int(TOTAL_GEM_BUDGET),
            dominance_lut=envelope_lut,
        )
        _record_phase(phase_seconds, "gear_local_envelope_cpu", phase_started)
        phase_counts["gear_local_envelope_in"] = int(env_stats.points_in)
        phase_counts["gear_local_envelope_out"] = int(env_stats.points_out)
        status_cb(
            "skyline: local envelope kept "
            f"{int(env_stats.points_out):,}/{int(env_stats.points_in):,} "
            f"(groups={int(env_stats.groups_multi):,}, max_group={int(env_stats.max_group_size)}, "
            f"time={float(env_stats.seconds):.2f}s)"
        )
        if gear_points.size == 0:
            return None, [], [], None, [], [], []

    phase_started = time.perf_counter()
    gear_ids = np.zeros((int(gear_codes.shape[0]), 6), dtype=np.int32)
    for idx, gear_code in enumerate(gear_codes.tolist()):
        gear_ids[idx] = _gear_ids_from_code(int(gear_code), pack=ctx.gear_pack, slot_item_ids=ctx.slot_item_ids)

    mini_ids = np.zeros((int(mini_codes.shape[0]), 3), dtype=np.int32)
    for idx, mini_code in enumerate(mini_codes.tolist()):
        mini_ids[idx] = _mini_ids_from_code(int(mini_code), pack=ctx.mini_pack, mini_item_ids=ctx.mini_item_ids)
    _record_phase(phase_seconds, "decode_candidate_ids_cpu", phase_started)
    phase_counts["gear_ids"] = int(gear_ids.shape[0])
    phase_counts["mini_ids"] = int(mini_ids.shape[0])

    status_cb(
        "skyline: build registry + evaluate candidates "
        f"(gear={int(gear_points.shape[0])}, minis={int(mini_points.shape[0])})"
    )

    base_keep_top_k = int(LOADOUTS_PER_SONG_LIMIT)
    keep_top_k = int(base_keep_top_k)
    fg_candidate_mode = _read_skyline_fg_candidate_mode()
    product_total = int(gear_ids.shape[0]) * int(mini_ids.shape[0])

    best_ids: np.ndarray | None = None
    top_codes: list[tuple[int, int, int]] = []
    combined_candidate_count = 0

    status_cb("skyline: combined timing-cell prune")
    phase_started = time.perf_counter()
    pair_g_idx, pair_m_idx = _combined_global_skyline_pairs_6d_lane_base_with_indices(gear_points, mini_points)
    _record_phase(phase_seconds, "combined_skyline_gpu_sparse", phase_started)
    combined_sparse_stats = get_last_combined_skyline_stats()
    sparse_phase_seconds = combined_sparse_stats.get("phase_seconds", {})
    if isinstance(sparse_phase_seconds, dict):
        for name, seconds in sparse_phase_seconds.items():
            phase_seconds[f"combined_sparse.{name}"] = float(seconds or 0.0)
    sparse_counts = combined_sparse_stats.get("counts", {})
    if isinstance(sparse_counts, dict):
        for name, count in sparse_counts.items():
            phase_counts[f"combined_sparse.{name}"] = int(count or 0)
    if pair_g_idx.size > 0:
        status_cb(
            "skyline: evaluate combined frontier "
            f"(pairs={int(pair_g_idx.shape[0])}, product={product_total:,})"
        )
        combined_candidate_count = int(pair_g_idx.shape[0])
        phase_counts["combined_skyline_candidates"] = int(combined_candidate_count)
        phase_counts["combined_product_total"] = int(product_total)
        if envelope_lut is not None:
            status_cb("skyline: combined local envelope prune")
            phase_started = time.perf_counter()
            env_stats, pair_g_idx, pair_m_idx = _reduce_combined_pair_envelope_fast(
                gear_points=gear_points,
                mini_points=mini_points,
                pair_gear_idx=pair_g_idx,
                pair_mini_idx=pair_m_idx,
                dominance_lut=envelope_lut,
            )
            _record_phase(phase_seconds, "combined_local_envelope_cpu", phase_started)
            combined_candidate_count = int(pair_g_idx.shape[0])
            phase_counts["combined_skyline_candidates"] = int(combined_candidate_count)
            phase_counts["combined_local_envelope_in"] = int(env_stats.points_in)
            phase_counts["combined_local_envelope_out"] = int(env_stats.points_out)
            phase_counts["combined_local_envelope_groups"] = int(env_stats.groups)
            status_cb(
                "skyline: combined local envelope kept "
                f"{int(env_stats.points_out):,}/{int(env_stats.points_in):,} "
                f"(groups={int(env_stats.groups_multi):,}, max_group={int(env_stats.max_group_size)}, "
                f"time={float(env_stats.seconds):.2f}s)"
            )
            if pair_g_idx.size == 0:
                return None, [], [], None, [], [], []
        if fg_candidate_mode == "all":
            keep_top_k = int(combined_candidate_count)
        elif fg_candidate_mode == "sample":
            keep_top_k = max(int(base_keep_top_k), 1000)
        pair_ft_caps, pair_ff_caps = _pair_ftff_cap_arrays(
            base_fixed_stats_arr=ctx.base_fixed_stats_arr,
            gear_points=gear_points,
            mini_points=mini_points,
            pair_gear_idx=pair_g_idx,
            pair_mini_idx=pair_m_idx,
        )
        if pair_ft_caps.size > 0:
            phase_counts["base_eval_ft_cap_max"] = int(np.max(pair_ft_caps))
            phase_counts["base_eval_ff_cap_max"] = int(np.max(pair_ff_caps))
            phase_counts["base_eval_ft_cap_p50"] = int(np.percentile(pair_ft_caps, 50))
            phase_counts["base_eval_ff_cap_p50"] = int(np.percentile(pair_ff_caps, 50))
        phase_started = time.perf_counter()
        best_ids, top_codes = _evaluate_pairs_exact(
            gpu_arrays=ctx.gpu_arrays,
            base_fixed_stats_arr=ctx.base_fixed_stats_arr,
            calc_song=ctx.calc_song,
            ref_arrays=ctx.ref_arrays,
            flags=ctx.color_flags,
            song_slot=int(ctx.song_slot),
            gpu_client=ctx.gpu_client,
            gear_ids=gear_ids,
            mini_ids=mini_ids,
            gear_codes=gear_codes,
            mini_codes=mini_codes,
            pair_gear_idx=pair_g_idx,
            pair_mini_idx=pair_m_idx,
            pair_max_ft_gems=pair_ft_caps,
            pair_max_ff_gems=pair_ff_caps,
            keep_top_k=int(keep_top_k),
            status_cb=status_cb,
        )
        _record_phase(phase_seconds, "base_pair_eval_gpu", phase_started)
        phase_counts["base_eval_keep_top_k"] = int(keep_top_k)
        phase_counts["base_eval_top_codes"] = int(len(top_codes))
        sample_source_by_code: dict[tuple[int, int], str] = {
            (int(gear_code), int(mini_code)): "top_base" for _score, gear_code, mini_code in top_codes
        }
        if fg_candidate_mode == "sample" and pair_g_idx.size > 0:
            top_base_codes = list(top_codes[:1000])
            top_base_keys = {(int(gear_code), int(mini_code)) for _score, gear_code, mini_code in top_base_codes}
            top_base_cutoff = int(top_base_codes[-1][0]) if top_base_codes else 0
            sample_idx = _sample_pair_indices(
                int(fg_candidate_count),
                top_limits=(),
                random_after=0,
                random_count=_read_skyline_fg_sample_limit(),
            )
            sampled_codes: list[tuple[int, int, int]] = []
            if sample_idx.size > 0:
                phase_started = time.perf_counter()
                _sample_best_ids, sampled_codes = _evaluate_pairs_exact(
                    gpu_arrays=ctx.gpu_arrays,
                    base_fixed_stats_arr=ctx.base_fixed_stats_arr,
                    calc_song=ctx.calc_song,
                    ref_arrays=ctx.ref_arrays,
                    flags=ctx.color_flags,
                    song_slot=int(ctx.song_slot),
                    gpu_client=ctx.gpu_client,
                    gear_ids=gear_ids,
                    mini_ids=mini_ids,
                    gear_codes=gear_codes,
                    mini_codes=mini_codes,
                    pair_gear_idx=pair_g_idx[sample_idx],
                    pair_mini_idx=pair_m_idx[sample_idx],
                    pair_max_ft_gems=pair_ft_caps[sample_idx] if pair_ft_caps.size else None,
                    pair_max_ff_gems=pair_ff_caps[sample_idx] if pair_ff_caps.size else None,
                    keep_top_k=int(sample_idx.shape[0]),
                    status_cb=status_cb,
                )
                _record_phase(phase_seconds, "sample_pair_eval_gpu", phase_started)
                phase_counts["sample_pair_eval_candidates"] = int(sample_idx.shape[0])
            random_outside: list[tuple[int, int, int]] = []
            for score, gear_code, mini_code in sampled_codes:
                key = (int(gear_code), int(mini_code))
                if key in top_base_keys:
                    continue
                if top_base_cutoff and int(score) >= int(top_base_cutoff):
                    continue
                random_outside.append((int(score), int(gear_code), int(mini_code)))
                sample_source_by_code[key] = "random_outside_top1000"
            top_codes = top_base_codes + random_outside
            top_codes.sort(reverse=True)
            status_cb(
                "skyline: sample FG set "
                f"(top_base={len(top_base_codes)}, random_outside={len(random_outside)}, "
                f"combined={int(combined_candidate_count)})"
            )

    if best_ids is None:
        return None, [], [], None, [], [], []

    override_cfg = build_solver_override_cfg(ctx.cfg_data, p_color=ctx.p_color, selected_color=ctx.selected_color)
    genome_best = ctx.registry.decode_genome(best_ids)
    phase_started = time.perf_counter()
    best_data = _build_candidate_payload(
        cfg=ctx.cfg,
        base_stats_fixed=ctx.base_stats_fixed,
        calc_song=ctx.calc_song,
        ref_arrays=ctx.ref_arrays,
        genome=genome_best,
        override_cfg=override_cfg,
        gpu_client=ctx.gpu_client,
    )
    _record_phase(phase_seconds, "best_payload_build_gpu", phase_started)
    best_data["GenomeIDs"] = [int(x) for x in best_ids.tolist()]

    best_gear = list(best_data.get("Gear") or [])
    best_minis = list(best_data.get("Minis") or [])

    all_evaluated: list[dict[str, Any]] = []

    candidate_records: list[dict[str, Any]] = []
    phase_started = time.perf_counter()
    for score, gear_code, mini_code in top_codes:
        g_ids = _gear_ids_from_code(int(gear_code), pack=ctx.gear_pack, slot_item_ids=ctx.slot_item_ids)
        m_ids = _mini_ids_from_code(int(mini_code), pack=ctx.mini_pack, mini_item_ids=ctx.mini_item_ids)
        ids = np.concatenate((g_ids, m_ids), axis=0).astype(np.int32, copy=False)
        genome = ctx.registry.decode_genome(ids)
        data = _build_candidate_payload(
            cfg=ctx.cfg,
            base_stats_fixed=ctx.base_stats_fixed,
            calc_song=ctx.calc_song,
            ref_arrays=ctx.ref_arrays,
            genome=genome,
            override_cfg=override_cfg,
            gpu_client=ctx.gpu_client,
        )
        data["GenomeIDs"] = [int(x) for x in ids.tolist()]
        base_score = int(data.get("BaseScore") or data.get("Score", 0) or 0)
        post_stats = data.get("Stats") or data.get("Details", {}).get("Stats", {}) or {}
        candidate_records.append(
            {
                "base_score": int(base_score),
                "gear_code": int(gear_code),
                "mini_code": int(mini_code),
                "ids": ids.copy(),
                "genome": genome,
                "data": data,
                "stats": post_stats if isinstance(post_stats, dict) else {},
                "sample_source": sample_source_by_code.get((int(gear_code), int(mini_code)), "top_base"),
            }
        )
    _record_phase(phase_seconds, "candidate_payload_build_gpu", phase_started)
    phase_counts["candidate_payloads"] = int(len(candidate_records))

    fg_search_radius = read_fg_search_radius(ctx.cfg)
    phase_started = time.perf_counter()
    native_fg_summary, _native_fg_best_record = score_retained_skyline_force_greats(
        candidate_records,
        calc_song=ctx.calc_song,
        ref_arrays=ctx.ref_arrays,
        default_selected_color=ctx.selected_color or ctx.p_color,
        search_radius=fg_search_radius,
        use_gpu=True,
        status_cb=status_cb,
    )
    _record_phase(phase_seconds, "native_fg_total", phase_started)
    native_fg_summary["candidate_scope"] = str(fg_candidate_mode)
    native_fg_summary["base_keep_top_k"] = int(base_keep_top_k)
    native_fg_summary["combined_skyline_candidates"] = int(combined_candidate_count)
    native_fg_summary["skyline_certification_status"] = SKYLINE_CERTIFICATION_STATUS
    native_fg_summary["skyline_certification_note"] = SKYLINE_CERTIFICATION_NOTE
    native_fg_summary["skyline_phase_seconds"] = _rounded_phase_seconds(phase_seconds)
    native_fg_summary["skyline_phase_counts"] = dict(phase_counts)
    if fg_candidate_mode == "sample":
        native_fg_summary["sample_random_after_rank"] = 1000
        native_fg_summary["sample_random_count"] = int(_read_skyline_fg_sample_limit())

    best_candidate_record = None
    for rec in candidate_records:
        ids = rec.get("ids")
        if isinstance(ids, np.ndarray) and np.array_equal(ids, best_ids):
            best_candidate_record = rec
            break
    if best_candidate_record is not None:
        rec_data = best_candidate_record.get("data")
        if isinstance(rec_data, dict):
            for key in ("FGScore", "FGDelta", "FGBaseScore", "FGUpperBound", "NativeFGWouldSkipByCeiling"):
                if key in rec_data:
                    best_data[key] = rec_data[key]
            if isinstance(rec_data.get("force"), dict):
                best_data["force"] = rec_data["force"]

    for rec in candidate_records:
        base_score = int(rec.get("base_score", 0) or 0)
        data = rec["data"]
        all_evaluated.append(
            {
                "Score": int(base_score),
                "BaseScore": int(base_score),
                "FGDelta": int(data.get("FGDelta", 0) or 0),
                "FGScore": int(data.get("FGScore", base_score) or base_score),
                "FGBaseScore": int(data.get("FGBaseScore", base_score) or base_score),
                "FGUpperBound": int(data.get("FGUpperBound", data.get("FGScore", base_score)) or base_score),
                "NativeFGWouldSkipByCeiling": bool(data.get("NativeFGWouldSkipByCeiling", False)),
                "Gear": rec["genome"][:6],
                "Minis": rec["genome"][6:9],
                "GenomeIDs": [int(x) for x in rec["ids"].tolist()] if isinstance(rec.get("ids"), np.ndarray) else [],
                "Data": data,
                "fg_score": int(data.get("FGScore", 0) or 0),
                "force": data.get("force"),
            }
        )

    _record_phase(phase_seconds, "solve_total", solve_started)
    native_fg_summary["skyline_phase_seconds"] = _rounded_phase_seconds(phase_seconds)
    native_fg_summary["skyline_phase_counts"] = dict(phase_counts)
    all_evaluated.sort(key=lambda d: int(d.get("Score", 0) or 0), reverse=True)
    if isinstance(best_data, dict):
        best_data["NativeFG"] = dict(native_fg_summary)
    if phase_seconds:
        status_cb(f"skyline: phase telemetry ({_slowest_phase_label(phase_seconds)})")
    status_cb(
        "skyline: native FG "
        f"(mode={native_fg_summary.get('mode')}, candidates={int(len(candidate_records))}, "
        f"exact_calls={int(native_fg_summary.get('exact_calls', 0) or 0)}, "
        f"gains={int(native_fg_summary.get('fg_gains', 0) or 0)}, "
        f"best_fg={int(native_fg_summary.get('best_fg_score', 0) or 0)})"
    )
    status_cb(
        "skyline: done "
        f"(dp_pairs={dp_stats.pairs_6d}, gear_sky={gear_sky_stats.points_out}, "
        f"gear_env={int(gear_points.shape[0])}, mini_sky={int(mini_points.shape[0])})"
    )
    return best_data, best_gear, best_minis, dict(native_fg_summary), _native_fg_best_record, [], all_evaluated


def solve_exact_skyline(
    cfg,
    base_stats_fixed,
    paths,
    calc_song,
    ref_arrays,
    all_gears,
    all_minis,
    gears_by_name,
    minis_by_name,
    optimize_gear=True,
    optimize_minis=True,
    fixed_gear=None,
    fixed_minis=None,
    status_cb=None,
    song_slot: int = 0,
    gpu_client: Any | None = None,
    solver_ctx: SolverContext | None = None,
):
    """Solve through the skyline candidate frontier and exact per-candidate scorers."""
    del paths, gears_by_name, minis_by_name

    if status_cb is None:

        def _noop_status_cb(_m: str) -> None:
            return None

        status_cb = _noop_status_cb

    if solver_ctx is None:
        solver_ctx = prepare_solver_context(
            cfg,
            base_stats_fixed,
            calc_song,
            ref_arrays,
            all_gears,
            all_minis,
            optimize_gear=bool(optimize_gear),
            optimize_minis=bool(optimize_minis),
            fixed_gear=fixed_gear,
            fixed_minis=fixed_minis,
            status_cb=status_cb,
            song_slot=int(song_slot),
            gpu_client=gpu_client,
        )
    if solver_ctx is None:
        return None, [], [], None, [], [], []
    return _solve_exact_skyline_ctx(solver_ctx)
