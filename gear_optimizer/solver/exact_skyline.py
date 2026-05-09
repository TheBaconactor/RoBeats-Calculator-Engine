from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

import numpy as np

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    FG_CANDIDATE_LIMIT,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    LOADOUTS_PER_SONG_LIMIT,
    MAX_STAT_INDEX,
    TOTAL_GEM_BUDGET,
)
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.combined_skyline_gpu import combined_global_skyline_pairs_6d_gpu
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
from gear_optimizer.solver.registry_solve_request import RegistrySolveRequest, dispatch_registry_solve

LaneAwareMiniSkylineStats = _LaneAwareMiniSkylineStats_common
_SLOTS = GEAR_SLOTS
_BitPack = _BitPack_common
_make_pack = _make_pack_common
_build_cfg_data = _build_cfg_data_common
_gear_ids_from_code = _gear_ids_from_code_common
_mini_ids_from_code = _mini_ids_from_code_common
_build_candidate_payload = _build_candidate_payload_common
_mini_combo_skyline_points_6d_lane_base_with_codes = _mini_combo_skyline_common


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
class Theorem5ResponsePruneStats:
    gear_in: int
    gear_out: int
    lambda_classes: int
    eval_pairs: int
    seconds: float
    skipped_reason: str | None = None


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

    groups: dict[tuple[int, int, int, int], list[int]] = {}
    for idx, row in enumerate(pts):
        key = (int(row[1]), int(row[2]), int(row[3]), int(row[4]))
        groups.setdefault(key, []).append(int(idx))

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

    for idxs in groups.values():
        g = int(len(idxs))
        if g <= 1:
            continue
        groups_multi += 1
        if g > max_group_size:
            max_group_size = g

        idx_arr = np.asarray(idxs, dtype=np.int64)
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
        groups=int(len(groups)),
        groups_multi=int(groups_multi),
        max_group_size=int(max_group_size),
        seconds=float(time.perf_counter() - t0),
    )
    return stats, reduced_points, reduced_codes


def _frontier_insert_ff_base_code(frontier: list[tuple[int, int, int]], ff: int, base: int, code: int) -> None:
    ff = int(ff)
    base = int(base)
    code = int(code)

    n = len(frontier)
    i = 0
    while i < n and frontier[i][0] < ff:
        i += 1

    if i < n and frontier[i][0] == ff:
        if base <= frontier[i][1]:
            return
        frontier[i] = (ff, base, code)
    else:
        if i < n and frontier[i][1] >= base:
            return
        frontier.insert(i, (ff, base, code))
        n += 1

    j = i - 1
    while j >= 0 and frontier[j][1] <= base:
        del frontier[j]
        i -= 1
        j -= 1

    if i + 1 < len(frontier) and frontier[i + 1][1] >= frontier[i][1]:
        del frontier[i]


def _dp_gear_ff_base_frontier_with_codes(
    gear_pool: dict[str, list[dict]],
    *,
    p_color: str,
    s_color: str,
    pack: _BitPack,
) -> tuple[dict[tuple[int, int, int, int], list[tuple[int, int, int]]], LaneAwareGearDPStats]:
    t0 = time.perf_counter()

    states: dict[tuple[int, int, int, int], list[tuple[int, int, int]]] = {(0, 0, 0, 0): [(0, 0, 0)]}

    slot_items: list[list[tuple[int, int, int, int, int, int, int]]] = []
    for slot_idx, slot in enumerate(_SLOTS):
        items = gear_pool.get(slot, [])
        if not items:
            return {}, LaneAwareGearDPStats(0, 0, 0.0, 0.0, 0, float(time.perf_counter() - t0))
        v: list[tuple[int, int, int, int, int, int, int]] = []
        shift = pack.shifts[slot_idx]
        for item_idx, it in enumerate(items):
            dpp, dcm, dfm, dft, dff = _item_vec_5(it)
            dbase = _lane_base_init(it, p_color, s_color)
            v.append((dpp, dcm, dfm, dft, dff, dbase, int(item_idx) << int(shift)))
        slot_items.append(v)

    for slot_idx, items in enumerate(slot_items):
        new_states: dict[tuple[int, int, int, int], list[tuple[int, int, int]]] = {}
        new_get = new_states.get
        for (pp, cm, fm, ft), frontier in states.items():
            for ff0, base0, code0 in frontier:
                for dpp, dcm, dfm, dft, dff, dbase, code_delta in items:
                    pp2 = pp + dpp
                    cm2 = cm + dcm
                    fm2 = fm + dfm
                    ft2 = ft + dft
                    ff2 = ff0 + dff

                    # Clamp gem-indexed stats to the scorer's MAX_STAT_INDEX.
                    # Any value above this is score-equivalent and only increases state space.
                    if pp2 < 0:
                        pp2 = 0
                    elif pp2 > MAX_STAT_INDEX:
                        pp2 = MAX_STAT_INDEX
                    if cm2 < 0:
                        cm2 = 0
                    elif cm2 > MAX_STAT_INDEX:
                        cm2 = MAX_STAT_INDEX
                    if fm2 < 0:
                        fm2 = 0
                    elif fm2 > MAX_STAT_INDEX:
                        fm2 = MAX_STAT_INDEX
                    if ft2 < 0:
                        ft2 = 0
                    elif ft2 > MAX_STAT_INDEX:
                        ft2 = MAX_STAT_INDEX
                    if ff2 < 0:
                        ff2 = 0
                    elif ff2 > MAX_STAT_INDEX:
                        ff2 = MAX_STAT_INDEX

                    key = (int(pp2), int(cm2), int(fm2), int(ft2))
                    base2 = base0 + dbase
                    code2 = code0 | code_delta
                    fr = new_get(key)
                    if fr is None:
                        new_states[key] = [(int(ff2), int(base2), int(code2))]
                    else:
                        _frontier_insert_ff_base_code(fr, int(ff2), int(base2), int(code2))
        states = new_states

    sizes = np.fromiter((len(fr) for fr in states.values()), dtype=np.int32)
    pairs = int(sizes.sum())
    stats = LaneAwareGearDPStats(
        keys_4d=int(len(states)),
        pairs_6d=pairs,
        frontier_mean=float(sizes.mean()) if sizes.size else 0.0,
        frontier_p95=float(np.percentile(sizes, 95)) if sizes.size else 0.0,
        frontier_max=int(sizes.max()) if sizes.size else 0,
        seconds=float(time.perf_counter() - t0),
    )
    return states, stats


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


_PAIR_CODE_MASK = np.uint64(0xFFFF_FFFF)


def _collapse_mini_response_classes_with_codes(
    mini_points: np.ndarray,
    mini_codes: np.ndarray,
    mini_ids: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Collapse minis by lambda=(CM,FM,FT,FF), keeping max-base representative per class."""

    if mini_points.size == 0 or mini_codes.size == 0 or mini_ids.size == 0:
        return (
            np.zeros((0, 5), dtype=np.int32),
            np.zeros(0, dtype=np.uint64),
            np.zeros((0, 3), dtype=np.int32),
        )

    pts = np.asarray(mini_points, dtype=np.int32)
    codes = np.asarray(mini_codes, dtype=np.uint64)
    ids = np.asarray(mini_ids, dtype=np.int32)

    n = int(pts.shape[0])
    if int(codes.shape[0]) != n or int(ids.shape[0]) != n:
        raise ValueError("mini response class inputs must have matching lengths")

    best_idx_by_key: dict[tuple[int, int, int, int], int] = {}
    best_base_by_key: dict[tuple[int, int, int, int], int] = {}

    for idx, row in enumerate(pts):
        key = (int(row[0]), int(row[1]), int(row[2]), int(row[3]))
        base = int(row[4])
        prev = best_base_by_key.get(key)
        if prev is None or base > int(prev):
            best_base_by_key[key] = int(base)
            best_idx_by_key[key] = int(idx)

    chosen = sorted(int(v) for v in best_idx_by_key.values())
    if not chosen:
        return (
            np.zeros((0, 5), dtype=np.int32),
            np.zeros(0, dtype=np.uint64),
            np.zeros((0, 3), dtype=np.int32),
        )

    idx_arr = np.asarray(chosen, dtype=np.int64)
    return (
        pts[idx_arr].astype(np.int32, copy=False),
        codes[idx_arr].astype(np.uint64, copy=False),
        ids[idx_arr].astype(np.int32, copy=False),
    )


def _response_dominance_keep_mask(scores: np.ndarray) -> np.ndarray:
    """Row-wise skyline mask over theorem-5 response vectors (maximize each lambda axis)."""

    arr = np.asarray(scores, dtype=np.int32)
    if arr.ndim != 2:
        raise ValueError("scores must be 2D")

    rows = int(arr.shape[0])
    if rows == 0:
        return np.zeros(0, dtype=np.bool_)

    keep = np.ones(rows, dtype=np.bool_)
    for i in range(rows):
        row_i = arr[i]
        ge = np.all(arr >= row_i, axis=1)
        strict = np.any(arr > row_i, axis=1)
        ge[i] = False
        if bool(np.any(ge & strict)):
            keep[i] = False
    return keep


def _evaluate_response_matrix_exact(
    *,
    gpu_arrays: dict[str, np.ndarray],
    base_fixed_stats_arr: np.ndarray,
    calc_song: dict,
    ref_arrays: dict,
    flags: dict[str, int],
    song_slot: int,
    gpu_client: Any | None,
    gear_ids: np.ndarray,
    mini_ids: np.ndarray,
    status_cb: Callable[[str], None] | None,
    status_label: str,
    status_every: int = 65_536,
) -> np.ndarray:
    g_n = int(gear_ids.shape[0])
    m_n = int(mini_ids.shape[0])
    out = np.zeros((g_n, m_n), dtype=np.int32)
    if g_n == 0 or m_n == 0:
        return out

    max_batch = 4096
    batch = np.zeros((max_batch, 9), dtype=np.int32)
    batch_g_idx = np.zeros(max_batch, dtype=np.int32)
    batch_m_idx = np.zeros(max_batch, dtype=np.int32)
    batch_len = 0

    total = int(g_n) * int(m_n)
    done = 0

    def _flush(n_rows: int) -> None:
        nonlocal done
        if n_rows <= 0:
            return
        req = RegistrySolveRequest(
            population_indices=batch[:n_rows].copy(),
            item_stats=gpu_arrays["item_stats"],
            slot_start=gpu_arrays["slot_start"],
            slot_count=gpu_arrays["slot_count"],
            base_fixed_stats=base_fixed_stats_arr,
            timeline_grid=calc_song,
            ref_arrays=ref_arrays,
            flags=flags,
            total_budget=TOTAL_GEM_BUDGET,
            gem_scale_fever=GEM_SCALE_FEVER,
            song_slot=int(song_slot),
        )
        results = dispatch_registry_solve(req, gpu_client=gpu_client)
        for local_idx, result in enumerate(results):
            gi = int(batch_g_idx[local_idx])
            mi = int(batch_m_idx[local_idx])
            try:
                score = int(result[0] or 0)
            except Exception:
                score = 0
            out[gi, mi] = int(score)

        done += int(n_rows)
        if status_cb is not None and (done == int(total) or done % int(status_every) == 0):
            status_cb(f"{status_label}: scored {done}/{int(total)} response points")

    for gi in range(g_n):
        g_row = gear_ids[gi]
        for mi in range(m_n):
            batch[batch_len, :6] = g_row
            batch[batch_len, 6:] = mini_ids[mi]
            batch_g_idx[batch_len] = int(gi)
            batch_m_idx[batch_len] = int(mi)
            batch_len += 1
            if batch_len == max_batch:
                _flush(batch_len)
                batch_len = 0

    if batch_len:
        _flush(batch_len)

    return out


def _theorem5_response_prune_gears_exact(
    *,
    gear_points: np.ndarray,
    gear_codes: np.ndarray,
    gear_ids: np.ndarray,
    mini_points: np.ndarray,
    mini_codes: np.ndarray,
    mini_ids: np.ndarray,
    gpu_arrays: dict[str, np.ndarray],
    base_fixed_stats_arr: np.ndarray,
    calc_song: dict,
    ref_arrays: dict,
    flags: dict[str, int],
    song_slot: int,
    gpu_client: Any | None,
    status_cb: Callable[[str], None] | None,
) -> tuple[Theorem5ResponsePruneStats, np.ndarray, np.ndarray, np.ndarray]:
    t0 = time.perf_counter()
    g_n = int(gear_points.shape[0])

    lambda_points, _lambda_codes, lambda_ids = _collapse_mini_response_classes_with_codes(
        mini_points,
        mini_codes,
        mini_ids,
    )
    lambda_n = int(lambda_points.shape[0])
    eval_pairs = int(g_n) * int(lambda_n)

    if g_n <= 1:
        stats = Theorem5ResponsePruneStats(
            gear_in=int(g_n), gear_out=int(g_n),
            lambda_classes=int(lambda_n), eval_pairs=int(eval_pairs),
            seconds=float(time.perf_counter() - t0),
            skipped_reason="insufficient_gears",
        )
        return stats, gear_points, gear_codes, gear_ids

    if lambda_n <= 0:
        stats = Theorem5ResponsePruneStats(
            gear_in=int(g_n), gear_out=int(g_n),
            lambda_classes=0, eval_pairs=0,
            seconds=float(time.perf_counter() - t0),
            skipped_reason="no_lambda_classes",
        )
        return stats, gear_points, gear_codes, gear_ids

    matrix = _evaluate_response_matrix_exact(
        gpu_arrays=gpu_arrays,
        base_fixed_stats_arr=base_fixed_stats_arr,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        flags=flags,
        song_slot=int(song_slot),
        gpu_client=gpu_client,
        gear_ids=gear_ids,
        mini_ids=lambda_ids,
        status_cb=status_cb,
        status_label="exact_skyline theorem5",
    )
    keep = _response_dominance_keep_mask(matrix)
    if not np.any(keep):
        keep[:] = True

    out_points = gear_points[keep].astype(np.int32, copy=False)
    out_codes = gear_codes[keep].astype(np.uint64, copy=False)
    out_ids = gear_ids[keep].astype(np.int32, copy=False)
    stats = Theorem5ResponsePruneStats(
        gear_in=int(g_n),
        gear_out=int(out_points.shape[0]),
        lambda_classes=int(lambda_n),
        eval_pairs=int(eval_pairs),
        seconds=float(time.perf_counter() - t0),
        skipped_reason=None,
    )
    return stats, out_points, out_codes, out_ids


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


def _global_gear_skyline_points_6d_lane_base_with_codes(
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
        raise MemoryError(f"Gear skyline grid too large: {shape} ({grid_elems:,} elems). Try reducing pools or use GA.")

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

    max_batch = 4096
    total = int(gear_ids.shape[0]) * int(mini_ids.shape[0])

    def _candidate_batches() -> Iterable[tuple[np.ndarray, np.ndarray, np.ndarray]]:
        batch = np.zeros((max_batch, 9), dtype=np.int32)
        batch_gc = np.zeros(max_batch, dtype=np.uint64)
        batch_mc = np.zeros(max_batch, dtype=np.uint64)
        batch_len = 0
        for gi in range(int(gear_ids.shape[0])):
            g_row = gear_ids[gi]
            g_code = int(gear_codes[gi])
            for mi in range(int(mini_ids.shape[0])):
                batch[batch_len, :6] = g_row
                batch[batch_len, 6:] = mini_ids[mi]
                batch_gc[batch_len] = np.uint64(g_code)
                batch_mc[batch_len] = np.uint64(int(mini_codes[mi]))
                batch_len += 1
                if batch_len == max_batch:
                    yield batch[:batch_len].copy(), batch_gc[:batch_len].copy(), batch_mc[:batch_len].copy()
                    batch_len = 0
        if batch_len:
            yield batch[:batch_len].copy(), batch_gc[:batch_len].copy(), batch_mc[:batch_len].copy()

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
        status_label="exact_skyline",
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
    if grid_elems > 250_000_000:
        raise MemoryError(f"Combined skyline grid too large: {shape} ({grid_elems:,} elems)")
    approx_bytes = int(grid_elems) * int(np.dtype(base_dtype).itemsize) * 3
    if approx_bytes > 2_100_000_000:
        gib = float(approx_bytes) / float(1024**3)
        raise MemoryError(f"Combined skyline grid too large: {shape} ({grid_elems:,} elems, ~{gib:.2f} GiB)")

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
        _suffix_max_4d_inplace(layer_grid)

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
        m2 = (ft_u + 1) < ft_size
        if np.any(m2):
            strict[m2] = np.maximum(strict[m2], layer_grid[cm_u[m2], fm_u[m2], ft_u[m2] + 1, ff_u[m2]])
        m3 = (ff_u + 1) < ff_size
        if np.any(m3):
            strict[m3] = np.maximum(strict[m3], layer_grid[cm_u[m3], fm_u[m3], ft_u[m3], ff_u[m3] + 1])

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
        _suffix_max_4d(higher_grid, higher_suffix)
        higher_valid = True

    if not kept_g_idx:
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32)

    return np.concatenate(kept_g_idx, axis=0), np.concatenate(kept_m_idx, axis=0)


def _combined_global_skyline_pairs_6d_lane_base_with_indices(
    gear_points: np.ndarray,
    mini_points: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """GPU-resident exact combined skyline over gear ⊕ mini stat products."""

    return combined_global_skyline_pairs_6d_gpu(gear_points, mini_points)


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
    keep_top_k: int,
    status_cb: Callable[[str], None] | None,
) -> tuple[np.ndarray | None, list[tuple[int, int, int]]]:
    if pair_gear_idx.size == 0 or pair_mini_idx.size == 0:
        return None, []

    max_batch = 4096
    total = int(pair_gear_idx.shape[0])

    def _candidate_batches() -> Iterable[tuple[np.ndarray, np.ndarray, np.ndarray]]:
        batch = np.zeros((max_batch, 9), dtype=np.int32)
        batch_gc = np.zeros(max_batch, dtype=np.uint64)
        batch_mc = np.zeros(max_batch, dtype=np.uint64)
        batch_len = 0
        for idx in range(total):
            gi = int(pair_gear_idx[idx])
            mi = int(pair_mini_idx[idx])
            batch[batch_len, :6] = gear_ids[gi]
            batch[batch_len, 6:] = mini_ids[mi]
            batch_gc[batch_len] = np.uint64(int(gear_codes[gi]))
            batch_mc[batch_len] = np.uint64(int(mini_codes[mi]))
            batch_len += 1
            if batch_len == max_batch:
                yield batch[:batch_len].copy(), batch_gc[:batch_len].copy(), batch_mc[:batch_len].copy()
                batch_len = 0
        if batch_len:
            yield batch[:batch_len].copy(), batch_gc[:batch_len].copy(), batch_mc[:batch_len].copy()

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
    status_cb = ctx.status_cb
    if status_cb is None:

        def _noop_status_cb(_message: str) -> None:
            return None

        status_cb = _noop_status_cb

    if ctx.mini_points.size == 0:
        return None, [], [], None, [], [], []

    status_cb("exact_skyline: gear DP")
    dp_states, dp_stats = _dp_gear_ff_base_frontier_with_codes(
        ctx.gear_pool,
        p_color=ctx.p_color,
        s_color=ctx.s_color,
        pack=ctx.gear_pack,
    )
    if not dp_states:
        return None, [], [], None, [], [], []

    status_cb("exact_skyline: gear global skyline")
    gear_sky_stats, gear_points, gear_codes = _global_gear_skyline_points_6d_lane_base_with_codes(dp_states)
    if gear_points.size == 0:
        return None, [], [], None, [], [], []

    ref_pp_raw = ctx.ref_arrays.get("Perfect Points") if isinstance(ctx.ref_arrays, dict) else None
    ref_pp = np.asarray(ref_pp_raw, dtype=np.float32) if ref_pp_raw is not None else np.zeros(0, dtype=np.float32)
    envelope_lut: EnvelopeDominanceLUT | None = None
    if ref_pp.ndim == 1 and ref_pp.shape[0] > 0:
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
        status_cb("exact_skyline: local envelope prune")
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
        status_cb(
            "exact_skyline: local envelope kept "
            f"{int(env_stats.points_out):,}/{int(env_stats.points_in):,} "
            f"(groups={int(env_stats.groups_multi):,}, max_group={int(env_stats.max_group_size)}, "
            f"time={float(env_stats.seconds):.2f}s)"
        )
        if gear_points.size == 0:
            return None, [], [], None, [], [], []

    gear_ids = np.zeros((int(gear_codes.shape[0]), 6), dtype=np.int32)
    for idx, gear_code in enumerate(gear_codes.tolist()):
        gear_ids[idx] = _gear_ids_from_code(int(gear_code), pack=ctx.gear_pack, slot_item_ids=ctx.slot_item_ids)

    mini_ids = np.zeros((int(ctx.mini_codes.shape[0]), 3), dtype=np.int32)
    for idx, mini_code in enumerate(ctx.mini_codes.tolist()):
        mini_ids[idx] = _mini_ids_from_code(int(mini_code), pack=ctx.mini_pack, mini_item_ids=ctx.mini_item_ids)

    status_cb("exact_skyline: theorem5 response prune")
    theorem5_stats, gear_points, gear_codes, gear_ids = _theorem5_response_prune_gears_exact(
        gear_points=gear_points,
        gear_codes=gear_codes,
        gear_ids=gear_ids,
        mini_points=ctx.mini_points,
        mini_codes=ctx.mini_codes,
        mini_ids=mini_ids,
        gpu_arrays=ctx.gpu_arrays,
        base_fixed_stats_arr=ctx.base_fixed_stats_arr,
        calc_song=ctx.calc_song,
        ref_arrays=ctx.ref_arrays,
        flags=ctx.color_flags,
        song_slot=int(ctx.song_slot),
        gpu_client=ctx.gpu_client,
        status_cb=status_cb,
    )
    if theorem5_stats.skipped_reason is None:
        status_cb(
            "exact_skyline: theorem5 kept "
            f"{int(theorem5_stats.gear_out):,}/{int(theorem5_stats.gear_in):,} gears "
            f"(lambda={int(theorem5_stats.lambda_classes):,}, eval_pairs={int(theorem5_stats.eval_pairs):,}, "
            f"time={float(theorem5_stats.seconds):.2f}s)"
        )
    else:
        status_cb(
            f"exact_skyline: theorem5 skipped ({theorem5_stats.skipped_reason})"
        )
    if gear_points.size == 0:
        return None, [], [], None, [], [], []

    status_cb(
        "exact_skyline: build registry + evaluate candidates "
        f"(gear={int(gear_points.shape[0])}, minis={int(ctx.mini_points.shape[0])})"
    )

    keep_top_k = max(int(LOADOUTS_PER_SONG_LIMIT), int(FG_CANDIDATE_LIMIT))
    product_total = int(gear_ids.shape[0]) * int(mini_ids.shape[0])

    best_ids: np.ndarray | None = None
    top_codes: list[tuple[int, int, int]] = []

    try:
        status_cb("exact_skyline: combined skyline prune")
        pair_g_idx, pair_m_idx = _combined_global_skyline_pairs_6d_lane_base_with_indices(gear_points, ctx.mini_points)
        if pair_g_idx.size > 0:
            if ref_pp.ndim == 1 and ref_pp.shape[0] > 0:
                status_cb("exact_skyline: combined envelope prune")
                g_pts = gear_points[pair_g_idx].astype(np.int32, copy=False)
                m_pts = ctx.mini_points[pair_m_idx].astype(np.int32, copy=False)

                pair_points = np.empty((int(pair_g_idx.shape[0]), 6), dtype=np.int32)
                pair_points[:, 0] = g_pts[:, 0]

                pair_points[:, 1] = g_pts[:, 1]
                pair_points[:, 1] += m_pts[:, 0]
                np.minimum(pair_points[:, 1], int(MAX_STAT_INDEX), out=pair_points[:, 1])

                pair_points[:, 2] = g_pts[:, 2]
                pair_points[:, 2] += m_pts[:, 1]
                np.minimum(pair_points[:, 2], int(MAX_STAT_INDEX), out=pair_points[:, 2])

                pair_points[:, 3] = g_pts[:, 3]
                pair_points[:, 3] += m_pts[:, 2]
                np.minimum(pair_points[:, 3], int(MAX_STAT_INDEX), out=pair_points[:, 3])

                pair_points[:, 4] = g_pts[:, 4]
                pair_points[:, 4] += m_pts[:, 3]
                np.minimum(pair_points[:, 4], int(MAX_STAT_INDEX), out=pair_points[:, 4])

                pair_points[:, 5] = g_pts[:, 5]
                pair_points[:, 5] += m_pts[:, 4]

                pair_codes = _pack_pair_indices(pair_g_idx, pair_m_idx)
                pair_env_stats, _, reduced_codes = _reduce_same_stat_envelope_frontier_with_codes(
                    pair_points,
                    pair_codes,
                    p_color=ctx.p_color,
                    s_color=ctx.s_color,
                    selected_color=ctx.selected_color,
                    ref_pp=ref_pp,
                    budget_max=int(TOTAL_GEM_BUDGET),
                    dominance_lut=envelope_lut,
                )
                status_cb(
                    "exact_skyline: combined envelope kept "
                    f"{int(pair_env_stats.points_out):,}/{int(pair_env_stats.points_in):,} "
                    f"(groups={int(pair_env_stats.groups_multi):,}, max_group={int(pair_env_stats.max_group_size)}, "
                    f"time={float(pair_env_stats.seconds):.2f}s)"
                )

                # Safety: only replace the candidate list when the reduction kept at least one.
                if reduced_codes.size > 0:
                    pair_g_idx, pair_m_idx = _unpack_pair_codes(reduced_codes)

            status_cb(
                "exact_skyline: evaluate combined skyline "
                f"(pairs={int(pair_g_idx.shape[0])}, product={product_total:,})"
            )
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
                mini_codes=ctx.mini_codes,
                pair_gear_idx=pair_g_idx,
                pair_mini_idx=pair_m_idx,
                keep_top_k=int(keep_top_k),
                status_cb=status_cb,
            )
    except MemoryError:
        status_cb("exact_skyline: combined skyline too large; falling back to cartesian")
    except Exception as exc:
        status_cb(f"exact_skyline: combined skyline failed ({type(exc).__name__}); falling back to cartesian")

    if best_ids is None:
        status_cb(f"exact_skyline: evaluate product (candidates={product_total:,})")
        best_ids, top_codes = _evaluate_product_exact(
            registry=ctx.registry,
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
            mini_codes=ctx.mini_codes,
            keep_top_k=int(keep_top_k),
            status_cb=status_cb,
        )

    if best_ids is None:
        return None, [], [], None, [], [], []

    override_cfg = build_solver_override_cfg(ctx.cfg_data, p_color=ctx.p_color, selected_color=ctx.selected_color)
    genome_best = ctx.registry.decode_genome(best_ids)
    best_data = _build_candidate_payload(
        cfg=ctx.cfg,
        base_stats_fixed=ctx.base_stats_fixed,
        calc_song=ctx.calc_song,
        ref_arrays=ctx.ref_arrays,
        genome=genome_best,
        override_cfg=override_cfg,
        gpu_client=ctx.gpu_client,
    )

    best_gear = list(best_data.get("Gear") or [])
    best_minis = list(best_data.get("Minis") or [])

    all_evaluated: list[dict[str, Any]] = []
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
        base_score = int(data.get("BaseScore") or data.get("Score", 0) or 0)
        all_evaluated.append(
            {"Score": base_score, "BaseScore": base_score, "Gear": genome[:6], "Minis": genome[6:9], "Data": data}
        )

    all_evaluated.sort(key=lambda data: int(data.get("Score", 0) or 0), reverse=True)
    status_cb(
        "exact_skyline: done "
        f"(dp_pairs={dp_stats.pairs_6d}, gear_sky={gear_sky_stats.points_out}, "
        f"gear_env={int(gear_points.shape[0])}, mini_sky={int(ctx.mini_points.shape[0])})"
    )
    return best_data, best_gear, best_minis, None, [], [], all_evaluated


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
    ga_depth=75,
    db_seed=None,
    ga_settings=None,
    status_cb=None,
    executor=None,
    known_loadouts=None,
    song_slot: int = 0,
    ga_seed: int | None = None,
    gpu_client: Any | None = None,
    pre_prune_mode: str = "none",
    solver_ctx: SolverContext | None = None,
):
    del paths, gears_by_name, minis_by_name, ga_depth, db_seed, ga_settings, executor, known_loadouts, ga_seed

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
            pre_prune_mode=pre_prune_mode,
            status_cb=status_cb,
            song_slot=int(song_slot),
            gpu_client=gpu_client,
        )
    if solver_ctx is None:
        return None, [], [], None, [], [], []
    return _solve_exact_skyline_ctx(solver_ctx)
