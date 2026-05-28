from collections import OrderedDict
import threading
from typing import Any

import numpy as np
import taichi as ti

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    MAX_STAT_INDEX,
    TOTAL_GEM_BUDGET,
    TOTAL_ROWS,
)
from gear_optimizer.core.jit_setup import jit
from gear_optimizer.solver.scoring.fg_policy import is_single_color_song
from gear_optimizer.solver.scoring_core import lookup_reference_jit
from gear_optimizer.solver.taichi_gem import api as gem_api

from .response_types import FgResponseInnerResult, FgResponseSurface
from .response_surface_meta import precompute_response_surface_head_coeffs

_PACKED_FRONTIER_SURFACE_CACHE_MAX = 8
_SURFACE_HEAD_COEFF_CACHE_MAX = 4
_PACKED_FRONTIER_SURFACE_CACHE: OrderedDict[
    tuple[int, tuple[int, ...]], tuple[tuple[Any, ...], np.ndarray, np.ndarray, np.ndarray, np.ndarray]
] = OrderedDict()
_SURFACE_HEAD_COEFF_CACHE: OrderedDict[tuple[int, int, tuple[int, ...], tuple[int, ...]], np.ndarray] = OrderedDict()
_SURFACE_HEAD_COEFF_CACHE_LOCK = threading.RLock()
_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_WORK = 1_000_000_000
_FG_RESPONSE_INNER_GPU_MAX_THREAD_WORK = 100_000
_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_GROUPS = 262_144
_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_ROWS = 262_144
_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_WORK = 512_000_000


def _response_inner_combo_count(
    *,
    residual_budget: int,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    allow_pp: bool,
) -> int:
    residual = max(0, int(residual_budget))
    max_pp_gems = 0
    if bool(allow_pp) and int(cur_pp) < MAX_STAT_INDEX:
        rem_pp = MAX_STAT_INDEX - int(cur_pp)
        max_pp_gems = rem_pp // GEM_SCALE_NORMAL
        if rem_pp % GEM_SCALE_NORMAL != 0:
            max_pp_gems += 1

    max_cm_gems = 0
    if int(cur_cm) < MAX_STAT_INDEX:
        rem_cm = MAX_STAT_INDEX - int(cur_cm)
        max_cm_gems = rem_cm // GEM_SCALE_NORMAL
        if rem_cm % GEM_SCALE_NORMAL != 0:
            max_cm_gems += 1

    max_fm_gems = 0
    if int(cur_fm) < MAX_STAT_INDEX:
        rem_fm = MAX_STAT_INDEX - int(cur_fm)
        max_fm_gems = rem_fm // GEM_SCALE_FEVER
        if rem_fm % GEM_SCALE_FEVER != 0:
            max_fm_gems += 1

    max_pp_gems = min(int(max_pp_gems), int(residual))
    max_cm_gems = min(int(max_cm_gems), int(residual))
    max_fm_gems = min(int(max_fm_gems), int(residual))

    # Exact count of feasible (g_cm, g_fm, g_pp) tuples under:
    # g_cm + g_fm + g_pp <= residual
    # g_cm <= max_cm_gems, g_fm <= max_fm_gems, g_pp <= max_pp_gems
    #
    # We keep a single loop over g_cm and use a closed-form arithmetic sum for
    # the g_fm dimension so planner overhead stays low on large warm batches.
    count = 0
    cm_limit = min(int(max_cm_gems), int(residual))
    pp_cap = int(max_pp_gems)
    fm_cap = int(max_fm_gems)
    for g_cm in range(int(cm_limit) + 1):
        leftover_after_cm = int(residual) - int(g_cm)
        if leftover_after_cm < 0:
            break
        fm_limit = min(int(fm_cap), int(leftover_after_cm))
        if fm_limit < 0:
            continue
        term_count = int(fm_limit) + 1
        if pp_cap >= int(leftover_after_cm):
            # sum_{g_fm=0..fm_limit} (leftover_after_cm - g_fm + 1)
            count += int(term_count) * (int(leftover_after_cm) + 1) - (
                int(fm_limit) * (int(fm_limit) + 1) // 2
            )
            continue

        # g_fm in [0, split-1] saturates at pp_cap, remainder is arithmetic.
        split = int(leftover_after_cm) - int(pp_cap)
        if split < 0:
            split = 0
        if split > int(term_count):
            split = int(term_count)
        count += int(split) * (int(pp_cap) + 1)
        tail_terms = int(term_count) - int(split)
        if tail_terms > 0:
            # sum_{g_fm=split..fm_limit} (leftover_after_cm - g_fm + 1)
            count += int(tail_terms) * (int(leftover_after_cm) + 1) - (
                (int(split) + int(fm_limit)) * int(tail_terms) // 2
            )
    return max(1, int(count))


def _response_inner_combo_counts(group_meta: np.ndarray, *, allow_pp: bool) -> np.ndarray:
    group_meta_arr = np.ascontiguousarray(np.asarray(group_meta, dtype=np.int32))
    if int(group_meta_arr.ndim) != 2 or int(group_meta_arr.shape[1]) < 4:
        raise ValueError("response frontier combo-count estimator requires group metadata columns 0..3")
    row_count = int(group_meta_arr.shape[0])
    if row_count <= 0:
        return np.zeros((0,), dtype=np.int64)
    combo_inputs = np.ascontiguousarray(group_meta_arr[:, :4], dtype=np.int32)
    unique_inputs, inverse = np.unique(combo_inputs, axis=0, return_inverse=True)
    unique_counts = np.asarray(
        [
            _response_inner_combo_count(
                residual_budget=int(row[0]),
                cur_pp=int(row[1]),
                cur_cm=int(row[2]),
                cur_fm=int(row[3]),
                allow_pp=allow_pp,
            )
            for row in unique_inputs
        ],
        dtype=np.int64,
    )
    return np.ascontiguousarray(unique_counts[np.asarray(inverse, dtype=np.intp)], dtype=np.int64)


@jit(nopython=True, cache=True)
def _score_response_surface_jit(
    fever0,
    fever1,
    fever2,
    fever3,
    great0,
    great1,
    great2,
    great3,
    body_fever,
    body_great,
    head_len,
    body_total,
    primary_val,
    secondary_val,
    pp_factor,
    combo_mul,
    fever_mul,
    is_single_color,
):
    base_value64 = float((int(primary_val) * 2) + int(secondary_val)) + float(pp_factor)
    combo64 = float(combo_mul)
    fever64 = float(fever_mul)

    base_f = np.float32(base_value64)
    combo_f = np.float32(combo64)
    fever_f = np.float32(fever64)
    combo_val = int(base_f * combo_f)
    fever_val = int(base_f * combo_f * fever_f)

    body_normal_for_base = int(body_total) - int(body_fever)
    if body_normal_for_base < 0:
        body_normal_for_base = 0
    score = (int(body_fever) * fever_val) + (body_normal_for_base * combo_val)

    factor = (combo_f - np.float32(1.0)) * base_f / np.float32(100.0)
    for i in range(int(head_len)):
        word = fever0
        great_word = great0
        bit = i
        if i >= 32 and i < 64:
            word = fever1
            great_word = great1
            bit = i - 32
        elif i >= 64 and i < 96:
            word = fever2
            great_word = great2
            bit = i - 64
        elif i >= 96:
            word = fever3
            great_word = great3
            bit = i - 96

        ramp = base_f + (np.float32(i + 1) * factor)
        if ((word >> bit) & 1) != 0:
            score += int(ramp * fever_f)
        else:
            score += int(ramp)

    if int(is_single_color) != 0:
        great_penalty_base_head = (int(primary_val) * 2) + 150
        great_penalty_base_raw = float(great_penalty_base_head)
    else:
        great_penalty_base_head = int(np.floor(float(int(primary_val)) * (4.0 / 3.0))) + int(
            np.floor(float(int(secondary_val)) * (2.0 / 3.0))
        ) + 150
        great_penalty_base_raw = (float(int(primary_val)) * (4.0 / 3.0)) + (
            float(int(secondary_val)) * (2.0 / 3.0)
        ) + 150.0
    penalty_combo_value = int(np.floor(base_value64 * combo64))
    great_combo_value = int(np.floor(great_penalty_base_raw * combo64))
    body_penalty = penalty_combo_value - great_combo_value
    if body_penalty < 0:
        body_penalty = 0
    score -= int(body_great) * int(body_penalty)

    combo_span = combo64 - 1.0
    for i in range(int(head_len)):
        great_word = great0
        bit = i
        if i >= 32 and i < 64:
            great_word = great1
            bit = i - 32
        elif i >= 64 and i < 96:
            great_word = great2
            bit = i - 64
        elif i >= 96:
            great_word = great3
            bit = i - 96
        if ((great_word >> bit) & 1) == 0:
            continue
        scaling = 1.0 + combo_span * float(i + 1) / 100.0
        perfect_val = int(np.floor(base_value64 * scaling))
        great_val = int(np.floor(float(great_penalty_base_head) * scaling))
        penalty = perfect_val - great_val
        if penalty > 0:
            score -= penalty
    return int(score)


@jit(nopython=True, cache=True)
def _optimize_response_surface_inner_jit(
    fever0,
    fever1,
    fever2,
    fever3,
    great0,
    great1,
    great2,
    great3,
    body_fever,
    body_great,
    head_len,
    body_total,
    residual_budget,
    cur_pp,
    cur_cm,
    cur_fm,
    cur_primary,
    cur_secondary,
    is_p_pp,
    is_s_pp,
    is_p_cm,
    is_s_cm,
    is_p_fm,
    is_s_fm,
    is_p_ov,
    is_s_ov,
    is_single_color,
    ref_pp,
    ref_cm,
    ref_fm,
):
    allow_pp = (int(is_p_pp) != 0) or (int(is_s_pp) != 0)

    max_pp_gems = 0
    if allow_pp and int(cur_pp) < MAX_STAT_INDEX:
        rem_pp = MAX_STAT_INDEX - int(cur_pp)
        max_pp_gems = rem_pp // GEM_SCALE_NORMAL
        if rem_pp % GEM_SCALE_NORMAL != 0:
            max_pp_gems += 1

    max_cm_gems = 0
    if int(cur_cm) < MAX_STAT_INDEX:
        rem_cm = MAX_STAT_INDEX - int(cur_cm)
        max_cm_gems = rem_cm // GEM_SCALE_NORMAL
        if rem_cm % GEM_SCALE_NORMAL != 0:
            max_cm_gems += 1

    max_fm_gems = 0
    if int(cur_fm) < MAX_STAT_INDEX:
        rem_fm = MAX_STAT_INDEX - int(cur_fm)
        max_fm_gems = rem_fm // GEM_SCALE_FEVER
        if rem_fm % GEM_SCALE_FEVER != 0:
            max_fm_gems += 1

    if max_pp_gems > int(residual_budget):
        max_pp_gems = int(residual_budget)
    if max_cm_gems > int(residual_budget):
        max_cm_gems = int(residual_budget)
    if max_fm_gems > int(residual_budget):
        max_fm_gems = int(residual_budget)

    pp_p_delta = GEM_STAT_TO_ELEMENT_SCALE * int(is_p_pp)
    pp_s_delta = GEM_STAT_TO_ELEMENT_SCALE * int(is_s_pp)
    cm_p_delta = GEM_STAT_TO_ELEMENT_SCALE * int(is_p_cm)
    cm_s_delta = GEM_STAT_TO_ELEMENT_SCALE * int(is_s_cm)
    fm_p_delta = GEM_STAT_TO_ELEMENT_SCALE * int(is_p_fm)
    fm_s_delta = GEM_STAT_TO_ELEMENT_SCALE * int(is_s_fm)
    ov_p_delta = ELEMENTAL_GEM_SCALE * int(is_p_ov)
    ov_s_delta = ELEMENTAL_GEM_SCALE * int(is_s_ov)

    best_score = -1
    best_pp = 0
    best_cm = 0
    best_fm = 0
    best_ov = int(residual_budget)
    best_final_pp = int(cur_pp)
    best_final_cm = int(cur_cm)
    best_final_fm = int(cur_fm)
    best_final_primary = int(cur_primary) + best_ov * ov_p_delta
    best_final_secondary = int(cur_secondary) + best_ov * ov_s_delta

    g_cm = 0
    while g_cm <= max_cm_gems:
        leftover_after_cm = int(residual_budget) - g_cm
        if leftover_after_cm < 0:
            break
        g_fm_max = max_fm_gems
        if g_fm_max > leftover_after_cm:
            g_fm_max = leftover_after_cm

        g_fm = 0
        while g_fm <= g_fm_max:
            leftover_after_fm = leftover_after_cm - g_fm
            g_pp_max = max_pp_gems
            if g_pp_max > leftover_after_fm:
                g_pp_max = leftover_after_fm

            g_pp = 0
            while g_pp <= g_pp_max:
                g_ov = leftover_after_fm - g_pp
                pp_stat = int(cur_pp) + g_pp * GEM_SCALE_NORMAL
                cm_stat = int(cur_cm) + g_cm * GEM_SCALE_NORMAL
                fm_stat = int(cur_fm) + g_fm * GEM_SCALE_FEVER
                primary_val = (
                    int(cur_primary)
                    + g_pp * pp_p_delta
                    + g_cm * cm_p_delta
                    + g_fm * fm_p_delta
                    + g_ov * ov_p_delta
                )
                secondary_val = (
                    int(cur_secondary)
                    + g_pp * pp_s_delta
                    + g_cm * cm_s_delta
                    + g_fm * fm_s_delta
                    + g_ov * ov_s_delta
                )
                score = _score_response_surface_jit(
                    fever0,
                    fever1,
                    fever2,
                    fever3,
                    great0,
                    great1,
                    great2,
                    great3,
                    body_fever,
                    body_great,
                    head_len,
                    body_total,
                    primary_val,
                    secondary_val,
                    lookup_reference_jit(pp_stat, ref_pp, TOTAL_ROWS),
                    lookup_reference_jit(cm_stat, ref_cm, TOTAL_ROWS),
                    lookup_reference_jit(fm_stat, ref_fm, TOTAL_ROWS),
                    int(is_single_color),
                )
                if score > best_score or (
                    score == best_score
                    and (
                        g_cm < best_cm
                        or (g_cm == best_cm and (g_fm < best_fm or (g_fm == best_fm and g_pp < best_pp)))
                    )
                ):
                    best_score = score
                    best_pp = g_pp
                    best_cm = g_cm
                    best_fm = g_fm
                    best_ov = g_ov
                    best_final_pp = pp_stat
                    best_final_cm = cm_stat
                    best_final_fm = fm_stat
                    best_final_primary = primary_val
                    best_final_secondary = secondary_val
                g_pp += 1
            g_fm += 1
        g_cm += 1

    return (
        int(best_score),
        int(best_pp),
        int(best_cm),
        int(best_fm),
        int(best_ov),
        int(best_final_pp),
        int(best_final_cm),
        int(best_final_fm),
        int(best_final_primary),
        int(best_final_secondary),
    )


def _color_flags(primary_color: str, secondary_color: str, selected_color: str) -> tuple[int, ...]:
    primary = str(primary_color or "")
    secondary = str(secondary_color or "")
    selected = str(selected_color or "")
    return (
        int(primary == "Chill"),
        int(secondary == "Chill"),
        int(primary == "Flow"),
        int(secondary == "Flow"),
        int(primary == "Rush"),
        int(secondary == "Rush"),
        int(primary == selected and bool(selected)),
        int(secondary == selected and bool(selected)),
        int(is_single_color_song(primary, secondary)),
    )


def _validate_surface(surface: FgResponseSurface, *, body_total: int) -> None:
    if int(surface.body_fever) < 0 or int(surface.body_great) < 0:
        raise ValueError("FG response surface body counts must be nonnegative")
    if int(surface.body_fever) > int(body_total) or int(surface.body_great) > int(body_total):
        raise ValueError("FG response surface body count exceeds song body note count")


def score_response_surface_exact(
    surface: FgResponseSurface,
    *,
    total_notes: int,
    primary_val: int,
    secondary_val: int,
    pp_factor: float,
    combo_mul: float,
    fever_mul: float,
    single_color: bool,
) -> int:
    head_len = min(int(total_notes), 100)
    body_total = max(0, int(total_notes) - 100)
    _validate_surface(surface, body_total=int(body_total))
    return int(
        _score_response_surface_jit(
            int(surface.fever0),
            int(surface.fever1),
            int(surface.fever2),
            int(surface.fever3),
            int(surface.great0),
            int(surface.great1),
            int(surface.great2),
            int(surface.great3),
            int(surface.body_fever),
            int(surface.body_great),
            int(head_len),
            int(body_total),
            int(primary_val),
            int(secondary_val),
            float(pp_factor),
            float(combo_mul),
            float(fever_mul),
            int(bool(single_color)),
        )
    )


def optimize_response_frontier_inner_exact(
    surfaces: tuple[FgResponseSurface, ...] | list[FgResponseSurface],
    *,
    total_notes: int,
    residual_budget: int,
    stats_after_ftff: dict[str, Any],
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    ref_arrays: dict[str, Any],
) -> FgResponseInnerResult:
    head_len = min(int(total_notes), 100)
    body_total = max(0, int(total_notes) - 100)
    ref_pp = np.ascontiguousarray(np.asarray(ref_arrays["Perfect Points"], dtype=np.float32))
    ref_cm = np.ascontiguousarray(np.asarray(ref_arrays["Combo Multiplier"], dtype=np.float32))
    ref_fm = np.ascontiguousarray(np.asarray(ref_arrays["Fever Multiplier"], dtype=np.float32))
    flags = _color_flags(str(primary_color or ""), str(secondary_color or ""), str(selected_color or ""))

    cur_pp = int(stats_after_ftff.get("Perfect Points", 0) or 0)
    cur_cm = int(stats_after_ftff.get("Combo Multiplier", 0) or 0)
    cur_fm = int(stats_after_ftff.get("Fever Multiplier", 0) or 0)
    cur_primary = int(stats_after_ftff.get(str(primary_color or ""), 0) or 0)
    cur_secondary = int(stats_after_ftff.get(str(secondary_color or ""), 0) or 0)
    residual = max(0, int(residual_budget))

    best: FgResponseInnerResult | None = None
    for idx, surface in enumerate(tuple(surfaces or ())):
        _validate_surface(surface, body_total=int(body_total))
        row = _optimize_response_surface_inner_jit(
            int(surface.fever0),
            int(surface.fever1),
            int(surface.fever2),
            int(surface.fever3),
            int(surface.great0),
            int(surface.great1),
            int(surface.great2),
            int(surface.great3),
            int(surface.body_fever),
            int(surface.body_great),
            int(head_len),
            int(body_total),
            int(residual),
            int(cur_pp),
            int(cur_cm),
            int(cur_fm),
            int(cur_primary),
            int(cur_secondary),
            *flags,
            ref_pp,
            ref_cm,
            ref_fm,
        )
        candidate = FgResponseInnerResult(
            best_score=int(row[0]),
            surface_index=int(idx),
            g_pp=int(row[1]),
            g_cm=int(row[2]),
            g_fm=int(row[3]),
            g_ov=int(row[4]),
            final_pp=int(row[5]),
            final_cm=int(row[6]),
            final_fm=int(row[7]),
            final_primary=int(row[8]),
            final_secondary=int(row[9]),
        )
        if best is None or int(candidate.best_score) > int(best.best_score):
            best = candidate
    if best is None:
        raise ValueError("response frontier inner solve requires at least one surface")
    return best


@ti.func
def _fg_response_lookup_ref(ref: ti.template(), idx: ti.i32) -> ti.f32:
    safe_idx: ti.i32 = idx
    if safe_idx < 0:
        safe_idx = 0
    if safe_idx > TOTAL_ROWS:
        safe_idx = TOTAL_ROWS
    return ref[safe_idx]


@ti.func
def _fg_response_bit(word: ti.u32, bit_idx: ti.i32) -> ti.i32:
    return ti.cast((word >> ti.cast(bit_idx, ti.u32)) & ti.u32(1), ti.i32)


@ti.func
def _fg_response_score_device(
    fever0: ti.u32,
    fever1: ti.u32,
    fever2: ti.u32,
    fever3: ti.u32,
    great0: ti.u32,
    great1: ti.u32,
    great2: ti.u32,
    great3: ti.u32,
    body_fever: ti.i32,
    body_great: ti.i32,
    head_len: ti.i32,
    body_total: ti.i32,
    primary_val: ti.i32,
    secondary_val: ti.i32,
    pp_factor: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    is_single_color: ti.i32,
) -> ti.i32:
    base_value: ti.f32 = ti.cast((primary_val * 2) + secondary_val, ti.f32) + pp_factor
    combo_val: ti.i32 = ti.cast(ti.floor(base_value * combo_mul), ti.i32)
    fever_val: ti.i32 = ti.cast(ti.floor(base_value * combo_mul * fever_mul), ti.i32)
    body_normal: ti.i32 = body_total - body_fever
    if body_normal < 0:
        body_normal = 0
    score: ti.i32 = body_fever * fever_val + body_normal * combo_val

    factor: ti.f32 = (combo_mul - ti.f32(1.0)) * base_value / ti.f32(100.0)
    n0 = ti.min(head_len, 32)
    for i in range(n0):
        ramp: ti.f32 = base_value + ti.cast(i + 1, ti.f32) * factor
        if _fg_response_bit(fever0, i) != 0:
            score += ti.cast(ti.floor(ramp * fever_mul), ti.i32)
        else:
            score += ti.cast(ti.floor(ramp), ti.i32)
    if head_len > 32:
        n1 = ti.min(head_len, 64)
        for i in range(32, n1):
            ramp: ti.f32 = base_value + ti.cast(i + 1, ti.f32) * factor
            if _fg_response_bit(fever1, i - 32) != 0:
                score += ti.cast(ti.floor(ramp * fever_mul), ti.i32)
            else:
                score += ti.cast(ti.floor(ramp), ti.i32)
    if head_len > 64:
        n2 = ti.min(head_len, 96)
        for i in range(64, n2):
            ramp: ti.f32 = base_value + ti.cast(i + 1, ti.f32) * factor
            if _fg_response_bit(fever2, i - 64) != 0:
                score += ti.cast(ti.floor(ramp * fever_mul), ti.i32)
            else:
                score += ti.cast(ti.floor(ramp), ti.i32)
    if head_len > 96:
        for i in range(96, head_len):
            ramp: ti.f32 = base_value + ti.cast(i + 1, ti.f32) * factor
            if _fg_response_bit(fever3, i - 96) != 0:
                score += ti.cast(ti.floor(ramp * fever_mul), ti.i32)
            else:
                score += ti.cast(ti.floor(ramp), ti.i32)

    great_bits: ti.u32 = great0 | great1 | great2 | great3
    if body_great > 0 or great_bits != ti.u32(0):
        great_head_base: ti.i32 = 0
        great_raw: ti.f32 = ti.f32(0.0)
        if is_single_color != 0:
            great_head_base = (primary_val * 2) + 150
            great_raw = ti.cast(great_head_base, ti.f32)
        else:
            great_head_base = (
                ti.cast(ti.floor(ti.cast(primary_val, ti.f32) * ti.f32(4.0 / 3.0)), ti.i32)
                + ti.cast(ti.floor(ti.cast(secondary_val, ti.f32) * ti.f32(2.0 / 3.0)), ti.i32)
                + 150
            )
            great_raw = (
                ti.cast(primary_val, ti.f32) * ti.f32(4.0 / 3.0)
                + ti.cast(secondary_val, ti.f32) * ti.f32(2.0 / 3.0)
                + ti.f32(150.0)
            )
        if body_great > 0:
            body_penalty: ti.i32 = combo_val - ti.cast(ti.floor(great_raw * combo_mul), ti.i32)
            if body_penalty < 0:
                body_penalty = 0
            score -= body_great * body_penalty

        if great_bits != ti.u32(0):
            combo_span: ti.f32 = combo_mul - ti.f32(1.0)
            for i in range(n0):
                if _fg_response_bit(great0, i) != 0:
                    scaling: ti.f32 = ti.f32(1.0) + combo_span * ti.cast(i + 1, ti.f32) / ti.f32(100.0)
                    perfect_val: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
                    great_val: ti.i32 = ti.cast(ti.floor(ti.cast(great_head_base, ti.f32) * scaling), ti.i32)
                    penalty: ti.i32 = perfect_val - great_val
                    if penalty > 0:
                        score -= penalty
            if head_len > 32:
                for i in range(32, ti.min(head_len, 64)):
                    if _fg_response_bit(great1, i - 32) != 0:
                        scaling: ti.f32 = ti.f32(1.0) + combo_span * ti.cast(i + 1, ti.f32) / ti.f32(100.0)
                        perfect_val: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
                        great_val: ti.i32 = ti.cast(ti.floor(ti.cast(great_head_base, ti.f32) * scaling), ti.i32)
                        penalty: ti.i32 = perfect_val - great_val
                        if penalty > 0:
                            score -= penalty
            if head_len > 64:
                for i in range(64, ti.min(head_len, 96)):
                    if _fg_response_bit(great2, i - 64) != 0:
                        scaling: ti.f32 = ti.f32(1.0) + combo_span * ti.cast(i + 1, ti.f32) / ti.f32(100.0)
                        perfect_val: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
                        great_val: ti.i32 = ti.cast(ti.floor(ti.cast(great_head_base, ti.f32) * scaling), ti.i32)
                        penalty: ti.i32 = perfect_val - great_val
                        if penalty > 0:
                            score -= penalty
            if head_len > 96:
                for i in range(96, head_len):
                    if _fg_response_bit(great3, i - 96) != 0:
                        scaling: ti.f32 = ti.f32(1.0) + combo_span * ti.cast(i + 1, ti.f32) / ti.f32(100.0)
                        perfect_val: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
                        great_val: ti.i32 = ti.cast(ti.floor(ti.cast(great_head_base, ti.f32) * scaling), ti.i32)
                        penalty: ti.i32 = perfect_val - great_val
                        if penalty > 0:
                            score -= penalty
    return score


@ti.func
def _fg_response_head_coefficients(
    fever0: ti.u32,
    fever1: ti.u32,
    fever2: ti.u32,
    fever3: ti.u32,
    head_len: ti.i32,
) -> ti.types.vector(4, ti.i32):
    n_hn = ti.i32(0)
    n_hf = ti.i32(0)
    sigma_hn = ti.i32(0)
    sigma_hf = ti.i32(0)
    head_len_c = ti.max(0, ti.min(head_len, 100))
    for i in range(100):
        if i < head_len_c:
            word = ti.u32(0)
            bit_idx = i
            if i < 32:
                word = fever0
            elif i < 64:
                word = fever1
                bit_idx = i - 32
            elif i < 96:
                word = fever2
                bit_idx = i - 64
            else:
                word = fever3
                bit_idx = i - 96
            pos = i + 1
            if _fg_response_bit(word, bit_idx) != 0:
                n_hf += 1
                sigma_hf += pos
            else:
                n_hn += 1
                sigma_hn += pos
    return ti.Vector([n_hn, n_hf, sigma_hn, sigma_hf])


@ti.func
def _fg_response_surface_upper_bound(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    body_fever: ti.i32,
    body_normal: ti.i32,
    n_hn: ti.i32,
    n_hf: ti.i32,
    sigma_hn: ti.i32,
    sigma_hf: ti.i32,
) -> ti.f32:
    ub_eps = ti.f32(1024.0)
    combo_val = ti.cast(ti.floor(base_value * combo_mul), ti.i32)
    fever_val = ti.cast(ti.floor(base_value * combo_mul * fever_mul), ti.i32)
    body_score = body_fever * fever_val + body_normal * combo_val
    factor = (combo_mul - ti.f32(1.0)) * base_value / ti.f32(100.0)
    head_upper = base_value * (ti.cast(n_hn, ti.f32) + fever_mul * ti.cast(n_hf, ti.f32)) + factor * (
        ti.cast(sigma_hn, ti.f32) + fever_mul * ti.cast(sigma_hf, ti.f32)
    )
    return ti.cast(body_score, ti.f32) + head_upper + ub_eps


@ti.kernel
def _fg_response_inner_batch_kernel(
    row_count: ti.i32,
    surface_words: ti.types.ndarray(dtype=ti.u32, ndim=2),
    surface_counts: ti.types.ndarray(dtype=ti.i32, ndim=2),
    surface_head_coeffs: ti.types.ndarray(dtype=ti.i32, ndim=2),
    row_meta: ti.types.ndarray(dtype=ti.i32, ndim=2),
    color_flags: ti.types.ndarray(dtype=ti.i32, ndim=1),
    ref_pp: ti.types.ndarray(dtype=ti.f32, ndim=1),
    ref_cm: ti.types.ndarray(dtype=ti.f32, ndim=1),
    ref_fm: ti.types.ndarray(dtype=ti.f32, ndim=1),
    out_rows: ti.types.ndarray(dtype=ti.i32, ndim=2),
    allow_pp_template: ti.template(),
):
    for row in range(row_count):
        residual_budget: ti.i32 = row_meta[row, 0]
        cur_pp: ti.i32 = row_meta[row, 1]
        cur_cm: ti.i32 = row_meta[row, 2]
        cur_fm: ti.i32 = row_meta[row, 3]
        cur_primary: ti.i32 = row_meta[row, 4]
        cur_secondary: ti.i32 = row_meta[row, 5]
        head_len: ti.i32 = row_meta[row, 6]
        body_total: ti.i32 = row_meta[row, 7]

        is_p_pp: ti.i32 = color_flags[0]
        is_s_pp: ti.i32 = color_flags[1]
        is_p_cm: ti.i32 = color_flags[2]
        is_s_cm: ti.i32 = color_flags[3]
        is_p_fm: ti.i32 = color_flags[4]
        is_s_fm: ti.i32 = color_flags[5]
        is_p_ov: ti.i32 = color_flags[6]
        is_s_ov: ti.i32 = color_flags[7]
        is_single_color: ti.i32 = color_flags[8]

        pp_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
        pp_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
        cm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
        cm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
        fm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
        fm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
        ov_p_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_p_ov
        ov_s_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_s_ov

        max_pp_gems: ti.i32 = 0
        if ti.static(allow_pp_template):
            if cur_pp < MAX_STAT_INDEX:
                rem_pp: ti.i32 = MAX_STAT_INDEX - cur_pp
                max_pp_gems = rem_pp // GEM_SCALE_NORMAL
                if rem_pp % GEM_SCALE_NORMAL != 0:
                    max_pp_gems += 1

        max_cm_gems: ti.i32 = 0
        if cur_cm < MAX_STAT_INDEX:
            rem_cm: ti.i32 = MAX_STAT_INDEX - cur_cm
            max_cm_gems = rem_cm // GEM_SCALE_NORMAL
            if rem_cm % GEM_SCALE_NORMAL != 0:
                max_cm_gems += 1

        max_fm_gems: ti.i32 = 0
        if cur_fm < MAX_STAT_INDEX:
            rem_fm: ti.i32 = MAX_STAT_INDEX - cur_fm
            max_fm_gems = rem_fm // GEM_SCALE_FEVER
            if rem_fm % GEM_SCALE_FEVER != 0:
                max_fm_gems += 1

        if max_pp_gems > residual_budget:
            max_pp_gems = residual_budget
        if max_cm_gems > residual_budget:
            max_cm_gems = residual_budget
        if max_fm_gems > residual_budget:
            max_fm_gems = residual_budget

        w_pp: ti.i32 = (pp_p_delta << 1) + pp_s_delta
        w_cm: ti.i32 = (cm_p_delta << 1) + cm_s_delta
        w_fm: ti.i32 = (fm_p_delta << 1) + fm_s_delta
        w_ov: ti.i32 = (ov_p_delta << 1) + ov_s_delta
        delta_pp_vs_ov: ti.i32 = w_pp - w_ov
        pp_primary_delta: ti.i32 = pp_p_delta - ov_p_delta
        pp_secondary_delta: ti.i32 = pp_s_delta - ov_s_delta
        base_init: ti.i32 = (cur_primary << 1) + cur_secondary
        pp_ref_base = _fg_response_lookup_ref(ref_pp, cur_pp)
        cm_ref_cache = ti.Vector.zero(ti.f32, TOTAL_GEM_BUDGET + 1)
        fm_ref_cache = ti.Vector.zero(ti.f32, TOTAL_GEM_BUDGET + 1)
        pp_ref_cache = ti.Vector.zero(ti.f32, TOTAL_GEM_BUDGET + 1)
        pp_bound_prefix_max = ti.Vector.zero(ti.f32, TOTAL_GEM_BUDGET + 1)
        if ti.static(allow_pp_template):
            g_pp_cache: ti.i32 = 0
            running_pp_bound_max: ti.f32 = ti.f32(-1e30)
            while g_pp_cache <= max_pp_gems:
                pp_stat_cache: ti.i32 = cur_pp + g_pp_cache * GEM_SCALE_NORMAL
                pp_ref_val: ti.f32 = _fg_response_lookup_ref(ref_pp, pp_stat_cache)
                pp_ref_cache[g_pp_cache] = pp_ref_val
                pp_bound_val: ti.f32 = ti.cast(g_pp_cache * delta_pp_vs_ov, ti.f32) + pp_ref_val
                if pp_bound_val > running_pp_bound_max:
                    running_pp_bound_max = pp_bound_val
                pp_bound_prefix_max[g_pp_cache] = running_pp_bound_max
                g_pp_cache += 1
        g_cm_cache: ti.i32 = 0
        while g_cm_cache <= max_cm_gems:
            cm_ref_cache[g_cm_cache] = _fg_response_lookup_ref(ref_cm, cur_cm + g_cm_cache * GEM_SCALE_NORMAL)
            g_cm_cache += 1
        g_fm_cache: ti.i32 = 0
        while g_fm_cache <= max_fm_gems:
            fm_ref_cache[g_fm_cache] = _fg_response_lookup_ref(ref_fm, cur_fm + g_fm_cache * GEM_SCALE_FEVER)
            g_fm_cache += 1

        fever0: ti.u32 = surface_words[row, 0]
        fever1: ti.u32 = surface_words[row, 1]
        fever2: ti.u32 = surface_words[row, 2]
        fever3: ti.u32 = surface_words[row, 3]
        great0: ti.u32 = surface_words[row, 4]
        great1: ti.u32 = surface_words[row, 5]
        great2: ti.u32 = surface_words[row, 6]
        great3: ti.u32 = surface_words[row, 7]
        body_fever: ti.i32 = surface_counts[row, 0]
        body_great: ti.i32 = surface_counts[row, 1]

        best_score: ti.i32 = -1
        best_pp: ti.i32 = 0
        best_cm: ti.i32 = 0
        best_fm: ti.i32 = 0
        best_ov: ti.i32 = residual_budget
        best_final_pp: ti.i32 = cur_pp
        best_final_cm: ti.i32 = cur_cm
        best_final_fm: ti.i32 = cur_fm
        best_final_primary: ti.i32 = cur_primary + best_ov * ov_p_delta
        best_final_secondary: ti.i32 = cur_secondary + best_ov * ov_s_delta

        body_normal: ti.i32 = body_total - body_fever
        if body_normal < 0:
            body_normal = 0
        n_hn = surface_head_coeffs[row, 0]
        n_hf = surface_head_coeffs[row, 1]
        sigma_hn = surface_head_coeffs[row, 2]
        sigma_hf = surface_head_coeffs[row, 3]

        g_cm: ti.i32 = 0
        while g_cm <= max_cm_gems:
            leftover_after_cm: ti.i32 = residual_budget - g_cm
            if leftover_after_cm < 0:
                break
            cm_stat: ti.i32 = cur_cm + g_cm * GEM_SCALE_NORMAL
            cm_mul = cm_ref_cache[g_cm]
            g_fm_max: ti.i32 = max_fm_gems
            if g_fm_max > leftover_after_cm:
                g_fm_max = leftover_after_cm
            g_fm: ti.i32 = 0
            while g_fm <= g_fm_max:
                leftover_after_fm: ti.i32 = leftover_after_cm - g_fm
                fm_stat: ti.i32 = cur_fm + g_fm * GEM_SCALE_FEVER
                fm_mul = fm_ref_cache[g_fm]
                g_pp_max: ti.i32 = max_pp_gems
                if g_pp_max > leftover_after_fm:
                    g_pp_max = leftover_after_fm

                base_linear_common: ti.i32 = base_init + (g_cm * w_cm) + (g_fm * w_fm) + (leftover_after_fm * w_ov)
                max_base_value: ti.f32 = ti.cast(base_linear_common, ti.f32) + pp_ref_base
                if ti.static(allow_pp_template):
                    max_base_value = ti.cast(base_linear_common, ti.f32) + pp_bound_prefix_max[g_pp_max]
                ub = _fg_response_surface_upper_bound(
                    max_base_value,
                    cm_mul,
                    fm_mul,
                    body_fever,
                    body_normal,
                    n_hn,
                    n_hf,
                    sigma_hn,
                    sigma_hf,
                )

                if ub > ti.cast(best_score, ti.f32):
                    primary_base: ti.i32 = (
                        cur_primary + g_cm * cm_p_delta + g_fm * fm_p_delta + leftover_after_fm * ov_p_delta
                    )
                    secondary_base: ti.i32 = (
                        cur_secondary + g_cm * cm_s_delta + g_fm * fm_s_delta + leftover_after_fm * ov_s_delta
                    )
                    if ti.static(allow_pp_template):
                        if max_pp_gems <= 0:
                            score: ti.i32 = _fg_response_score_device(
                                fever0,
                                fever1,
                                fever2,
                                fever3,
                                great0,
                                great1,
                                great2,
                                great3,
                                body_fever,
                                body_great,
                                head_len,
                                body_total,
                                primary_base,
                                secondary_base,
                                pp_ref_cache[0],
                                cm_mul,
                                fm_mul,
                                is_single_color,
                            )
                            if score > best_score or (
                                score == best_score
                                and (
                                    g_cm < best_cm
                                    or (g_cm == best_cm and (g_fm < best_fm or (g_fm == best_fm and 0 < best_pp)))
                                )
                            ):
                                best_score = score
                                best_pp = 0
                                best_cm = g_cm
                                best_fm = g_fm
                                best_ov = leftover_after_fm
                                best_final_pp = cur_pp
                                best_final_cm = cm_stat
                                best_final_fm = fm_stat
                                best_final_primary = primary_base
                                best_final_secondary = secondary_base
                        else:
                            g_pp: ti.i32 = 0
                            while g_pp <= g_pp_max:
                                g_ov: ti.i32 = leftover_after_fm - g_pp
                                pp_stat: ti.i32 = cur_pp + g_pp * GEM_SCALE_NORMAL
                                primary_val: ti.i32 = primary_base + g_pp * pp_primary_delta
                                secondary_val: ti.i32 = secondary_base + g_pp * pp_secondary_delta
                                pp_base_value: ti.f32 = ti.cast(
                                    base_linear_common + g_pp * delta_pp_vs_ov,
                                    ti.f32,
                                ) + pp_ref_cache[g_pp]
                                pp_ub = _fg_response_surface_upper_bound(
                                    pp_base_value,
                                    cm_mul,
                                    fm_mul,
                                    body_fever,
                                    body_normal,
                                    n_hn,
                                    n_hf,
                                    sigma_hn,
                                    sigma_hf,
                                )
                                should_score: ti.i32 = 1
                                if pp_ub < ti.cast(best_score, ti.f32):
                                    should_score = 0
                                if should_score != 0:
                                    score = _fg_response_score_device(
                                        fever0,
                                        fever1,
                                        fever2,
                                        fever3,
                                        great0,
                                        great1,
                                        great2,
                                        great3,
                                        body_fever,
                                        body_great,
                                        head_len,
                                        body_total,
                                        primary_val,
                                        secondary_val,
                                        pp_ref_cache[g_pp],
                                        cm_mul,
                                        fm_mul,
                                        is_single_color,
                                    )
                                    if score > best_score or (
                                        score == best_score
                                        and (
                                            g_cm < best_cm
                                            or (
                                                g_cm == best_cm
                                                and (g_fm < best_fm or (g_fm == best_fm and g_pp < best_pp))
                                            )
                                        )
                                    ):
                                        best_score = score
                                        best_pp = g_pp
                                        best_cm = g_cm
                                        best_fm = g_fm
                                        best_ov = g_ov
                                        best_final_pp = pp_stat
                                        best_final_cm = cm_stat
                                        best_final_fm = fm_stat
                                        best_final_primary = primary_val
                                        best_final_secondary = secondary_val
                                g_pp += 1
                    else:
                        score: ti.i32 = _fg_response_score_device(
                            fever0,
                            fever1,
                            fever2,
                            fever3,
                            great0,
                            great1,
                            great2,
                            great3,
                            body_fever,
                            body_great,
                            head_len,
                            body_total,
                            primary_base,
                            secondary_base,
                            pp_ref_base,
                            cm_mul,
                            fm_mul,
                            is_single_color,
                        )
                        if score > best_score or (
                            score == best_score
                            and (
                                g_cm < best_cm
                                or (g_cm == best_cm and (g_fm < best_fm or (g_fm == best_fm and 0 < best_pp)))
                            )
                        ):
                            best_score = score
                            best_pp = 0
                            best_cm = g_cm
                            best_fm = g_fm
                            best_ov = leftover_after_fm
                            best_final_pp = cur_pp
                            best_final_cm = cm_stat
                            best_final_fm = fm_stat
                            best_final_primary = primary_base
                            best_final_secondary = secondary_base
                g_fm += 1
            g_cm += 1

        out_rows[row, 0] = best_score
        out_rows[row, 1] = best_pp
        out_rows[row, 2] = best_cm
        out_rows[row, 3] = best_fm
        out_rows[row, 4] = best_ov
        out_rows[row, 5] = best_final_pp
        out_rows[row, 6] = best_final_cm
        out_rows[row, 7] = best_final_fm
        out_rows[row, 8] = best_final_primary
        out_rows[row, 9] = best_final_secondary


@ti.kernel
def _fg_response_inner_group_kernel(
    group_count: ti.i32,
    surface_words: ti.types.ndarray(dtype=ti.u32, ndim=2),
    surface_counts: ti.types.ndarray(dtype=ti.i32, ndim=2),
    surface_head_coeffs: ti.types.ndarray(dtype=ti.i32, ndim=2),
    group_offsets: ti.types.ndarray(dtype=ti.i32, ndim=1),
    group_lengths: ti.types.ndarray(dtype=ti.i32, ndim=1),
    row_meta: ti.types.ndarray(dtype=ti.i32, ndim=2),
    color_flags: ti.types.ndarray(dtype=ti.i32, ndim=1),
    ref_pp: ti.types.ndarray(dtype=ti.f32, ndim=1),
    ref_cm: ti.types.ndarray(dtype=ti.f32, ndim=1),
    ref_fm: ti.types.ndarray(dtype=ti.f32, ndim=1),
    out_rows: ti.types.ndarray(dtype=ti.i32, ndim=2),
    allow_pp_template: ti.template(),
):
    for group in range(group_count):
        residual_budget: ti.i32 = row_meta[group, 0]
        cur_pp: ti.i32 = row_meta[group, 1]
        cur_cm: ti.i32 = row_meta[group, 2]
        cur_fm: ti.i32 = row_meta[group, 3]
        cur_primary: ti.i32 = row_meta[group, 4]
        cur_secondary: ti.i32 = row_meta[group, 5]
        head_len: ti.i32 = row_meta[group, 6]
        body_total: ti.i32 = row_meta[group, 7]

        is_p_pp: ti.i32 = color_flags[0]
        is_s_pp: ti.i32 = color_flags[1]
        is_p_cm: ti.i32 = color_flags[2]
        is_s_cm: ti.i32 = color_flags[3]
        is_p_fm: ti.i32 = color_flags[4]
        is_s_fm: ti.i32 = color_flags[5]
        is_p_ov: ti.i32 = color_flags[6]
        is_s_ov: ti.i32 = color_flags[7]
        is_single_color: ti.i32 = color_flags[8]

        pp_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
        pp_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
        cm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
        cm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
        fm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
        fm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
        ov_p_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_p_ov
        ov_s_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_s_ov

        max_pp_gems: ti.i32 = 0
        if ti.static(allow_pp_template):
            if cur_pp < MAX_STAT_INDEX:
                rem_pp: ti.i32 = MAX_STAT_INDEX - cur_pp
                max_pp_gems = rem_pp // GEM_SCALE_NORMAL
                if rem_pp % GEM_SCALE_NORMAL != 0:
                    max_pp_gems += 1

        max_cm_gems: ti.i32 = 0
        if cur_cm < MAX_STAT_INDEX:
            rem_cm: ti.i32 = MAX_STAT_INDEX - cur_cm
            max_cm_gems = rem_cm // GEM_SCALE_NORMAL
            if rem_cm % GEM_SCALE_NORMAL != 0:
                max_cm_gems += 1

        max_fm_gems: ti.i32 = 0
        if cur_fm < MAX_STAT_INDEX:
            rem_fm: ti.i32 = MAX_STAT_INDEX - cur_fm
            max_fm_gems = rem_fm // GEM_SCALE_FEVER
            if rem_fm % GEM_SCALE_FEVER != 0:
                max_fm_gems += 1

        if max_pp_gems > residual_budget:
            max_pp_gems = residual_budget
        if max_cm_gems > residual_budget:
            max_cm_gems = residual_budget
        if max_fm_gems > residual_budget:
            max_fm_gems = residual_budget

        w_pp: ti.i32 = (pp_p_delta << 1) + pp_s_delta
        w_cm: ti.i32 = (cm_p_delta << 1) + cm_s_delta
        w_fm: ti.i32 = (fm_p_delta << 1) + fm_s_delta
        w_ov: ti.i32 = (ov_p_delta << 1) + ov_s_delta
        delta_pp_vs_ov: ti.i32 = w_pp - w_ov
        pp_primary_delta: ti.i32 = pp_p_delta - ov_p_delta
        pp_secondary_delta: ti.i32 = pp_s_delta - ov_s_delta
        base_init: ti.i32 = (cur_primary << 1) + cur_secondary
        pp_ref_base = _fg_response_lookup_ref(ref_pp, cur_pp)
        cm_ref_cache = ti.Vector.zero(ti.f32, TOTAL_GEM_BUDGET + 1)
        fm_ref_cache = ti.Vector.zero(ti.f32, TOTAL_GEM_BUDGET + 1)
        pp_ref_cache = ti.Vector.zero(ti.f32, TOTAL_GEM_BUDGET + 1)
        pp_bound_prefix_max = ti.Vector.zero(ti.f32, TOTAL_GEM_BUDGET + 1)
        if ti.static(allow_pp_template):
            g_pp_cache: ti.i32 = 0
            running_pp_bound_max: ti.f32 = ti.f32(-1e30)
            while g_pp_cache <= max_pp_gems:
                pp_stat_cache: ti.i32 = cur_pp + g_pp_cache * GEM_SCALE_NORMAL
                pp_ref_val: ti.f32 = _fg_response_lookup_ref(ref_pp, pp_stat_cache)
                pp_ref_cache[g_pp_cache] = pp_ref_val
                pp_bound_val: ti.f32 = ti.cast(g_pp_cache * delta_pp_vs_ov, ti.f32) + pp_ref_val
                if pp_bound_val > running_pp_bound_max:
                    running_pp_bound_max = pp_bound_val
                pp_bound_prefix_max[g_pp_cache] = running_pp_bound_max
                g_pp_cache += 1
        g_cm_cache: ti.i32 = 0
        while g_cm_cache <= max_cm_gems:
            cm_ref_cache[g_cm_cache] = _fg_response_lookup_ref(ref_cm, cur_cm + g_cm_cache * GEM_SCALE_NORMAL)
            g_cm_cache += 1
        g_fm_cache: ti.i32 = 0
        while g_fm_cache <= max_fm_gems:
            fm_ref_cache[g_fm_cache] = _fg_response_lookup_ref(ref_fm, cur_fm + g_fm_cache * GEM_SCALE_FEVER)
            g_fm_cache += 1

        group_best_score: ti.i32 = -1
        group_best_surface: ti.i32 = 0
        group_best_pp: ti.i32 = 0
        group_best_cm: ti.i32 = 0
        group_best_fm: ti.i32 = 0
        group_best_ov: ti.i32 = residual_budget
        group_best_final_pp: ti.i32 = cur_pp
        group_best_final_cm: ti.i32 = cur_cm
        group_best_final_fm: ti.i32 = cur_fm
        group_best_final_primary: ti.i32 = cur_primary + group_best_ov * ov_p_delta
        group_best_final_secondary: ti.i32 = cur_secondary + group_best_ov * ov_s_delta

        start: ti.i32 = group_offsets[group]
        length: ti.i32 = group_lengths[group]
        local_surface: ti.i32 = 0
        while local_surface < length:
            surface_row: ti.i32 = start + local_surface
            fever0: ti.u32 = surface_words[surface_row, 0]
            fever1: ti.u32 = surface_words[surface_row, 1]
            fever2: ti.u32 = surface_words[surface_row, 2]
            fever3: ti.u32 = surface_words[surface_row, 3]
            great0: ti.u32 = surface_words[surface_row, 4]
            great1: ti.u32 = surface_words[surface_row, 5]
            great2: ti.u32 = surface_words[surface_row, 6]
            great3: ti.u32 = surface_words[surface_row, 7]
            body_fever: ti.i32 = surface_counts[surface_row, 0]
            body_great: ti.i32 = surface_counts[surface_row, 1]

            best_score: ti.i32 = group_best_score
            best_pp: ti.i32 = group_best_pp
            best_cm: ti.i32 = group_best_cm
            best_fm: ti.i32 = group_best_fm
            best_ov: ti.i32 = group_best_ov
            best_final_pp: ti.i32 = group_best_final_pp
            best_final_cm: ti.i32 = group_best_final_cm
            best_final_fm: ti.i32 = group_best_final_fm
            best_final_primary: ti.i32 = group_best_final_primary
            best_final_secondary: ti.i32 = group_best_final_secondary

            body_normal: ti.i32 = body_total - body_fever
            if body_normal < 0:
                body_normal = 0
            n_hn = surface_head_coeffs[surface_row, 0]
            n_hf = surface_head_coeffs[surface_row, 1]
            sigma_hn = surface_head_coeffs[surface_row, 2]
            sigma_hf = surface_head_coeffs[surface_row, 3]

            g_cm: ti.i32 = 0
            while g_cm <= max_cm_gems:
                leftover_after_cm: ti.i32 = residual_budget - g_cm
                if leftover_after_cm < 0:
                    break
                cm_stat: ti.i32 = cur_cm + g_cm * GEM_SCALE_NORMAL
                cm_mul = cm_ref_cache[g_cm]
                g_fm_max: ti.i32 = max_fm_gems
                if g_fm_max > leftover_after_cm:
                    g_fm_max = leftover_after_cm
                g_fm: ti.i32 = 0
                while g_fm <= g_fm_max:
                    leftover_after_fm: ti.i32 = leftover_after_cm - g_fm
                    fm_stat: ti.i32 = cur_fm + g_fm * GEM_SCALE_FEVER
                    fm_mul = fm_ref_cache[g_fm]
                    g_pp_max: ti.i32 = max_pp_gems
                    if g_pp_max > leftover_after_fm:
                        g_pp_max = leftover_after_fm

                    base_linear_common: ti.i32 = base_init + (g_cm * w_cm) + (g_fm * w_fm) + (leftover_after_fm * w_ov)
                    max_base_value: ti.f32 = ti.cast(base_linear_common, ti.f32) + pp_ref_base
                    if ti.static(allow_pp_template):
                        max_base_value = ti.cast(base_linear_common, ti.f32) + pp_bound_prefix_max[g_pp_max]
                    ub = _fg_response_surface_upper_bound(
                        max_base_value,
                        cm_mul,
                        fm_mul,
                        body_fever,
                        body_normal,
                        n_hn,
                        n_hf,
                        sigma_hn,
                        sigma_hf,
                    )

                    if ub > ti.cast(best_score, ti.f32):
                        primary_base: ti.i32 = (
                            cur_primary + g_cm * cm_p_delta + g_fm * fm_p_delta + leftover_after_fm * ov_p_delta
                        )
                        secondary_base: ti.i32 = (
                            cur_secondary + g_cm * cm_s_delta + g_fm * fm_s_delta + leftover_after_fm * ov_s_delta
                        )
                        if ti.static(allow_pp_template):
                            if max_pp_gems <= 0:
                                score: ti.i32 = _fg_response_score_device(
                                    fever0,
                                    fever1,
                                    fever2,
                                    fever3,
                                    great0,
                                    great1,
                                    great2,
                                    great3,
                                    body_fever,
                                    body_great,
                                    head_len,
                                    body_total,
                                    primary_base,
                                    secondary_base,
                                    pp_ref_cache[0],
                                    cm_mul,
                                    fm_mul,
                                    is_single_color,
                                )
                                if score > best_score or (
                                    score == best_score
                                    and (
                                        g_cm < best_cm
                                        or (g_cm == best_cm and (g_fm < best_fm or (g_fm == best_fm and 0 < best_pp)))
                                    )
                                ):
                                    best_score = score
                                    best_pp = 0
                                    best_cm = g_cm
                                    best_fm = g_fm
                                    best_ov = leftover_after_fm
                                    best_final_pp = cur_pp
                                    best_final_cm = cm_stat
                                    best_final_fm = fm_stat
                                    best_final_primary = primary_base
                                    best_final_secondary = secondary_base
                            else:
                                g_pp: ti.i32 = 0
                                while g_pp <= g_pp_max:
                                    g_ov: ti.i32 = leftover_after_fm - g_pp
                                    pp_stat: ti.i32 = cur_pp + g_pp * GEM_SCALE_NORMAL
                                    primary_val: ti.i32 = primary_base + g_pp * pp_primary_delta
                                    secondary_val: ti.i32 = secondary_base + g_pp * pp_secondary_delta
                                    pp_base_value: ti.f32 = ti.cast(
                                        base_linear_common + g_pp * delta_pp_vs_ov,
                                        ti.f32,
                                    ) + pp_ref_cache[g_pp]
                                    pp_ub = _fg_response_surface_upper_bound(
                                        pp_base_value,
                                        cm_mul,
                                        fm_mul,
                                        body_fever,
                                        body_normal,
                                        n_hn,
                                        n_hf,
                                        sigma_hn,
                                        sigma_hf,
                                    )
                                    should_score: ti.i32 = 1
                                    if pp_ub < ti.cast(best_score, ti.f32):
                                        should_score = 0
                                    if should_score != 0:
                                        score = _fg_response_score_device(
                                            fever0,
                                            fever1,
                                            fever2,
                                            fever3,
                                            great0,
                                            great1,
                                            great2,
                                            great3,
                                            body_fever,
                                            body_great,
                                            head_len,
                                            body_total,
                                            primary_val,
                                            secondary_val,
                                            pp_ref_cache[g_pp],
                                            cm_mul,
                                            fm_mul,
                                            is_single_color,
                                        )
                                        if score > best_score or (
                                            score == best_score
                                            and (
                                                g_cm < best_cm
                                                or (
                                                    g_cm == best_cm
                                                    and (g_fm < best_fm or (g_fm == best_fm and g_pp < best_pp))
                                                )
                                            )
                                        ):
                                            best_score = score
                                            best_pp = g_pp
                                            best_cm = g_cm
                                            best_fm = g_fm
                                            best_ov = g_ov
                                            best_final_pp = pp_stat
                                            best_final_cm = cm_stat
                                            best_final_fm = fm_stat
                                            best_final_primary = primary_val
                                            best_final_secondary = secondary_val
                                    g_pp += 1
                        else:
                            score: ti.i32 = _fg_response_score_device(
                                fever0,
                                fever1,
                                fever2,
                                fever3,
                                great0,
                                great1,
                                great2,
                                great3,
                                body_fever,
                                body_great,
                                head_len,
                                body_total,
                                primary_base,
                                secondary_base,
                                pp_ref_base,
                                cm_mul,
                                fm_mul,
                                is_single_color,
                            )
                            if score > best_score or (
                                score == best_score
                                and (
                                    g_cm < best_cm
                                    or (g_cm == best_cm and (g_fm < best_fm or (g_fm == best_fm and 0 < best_pp)))
                                )
                            ):
                                best_score = score
                                best_pp = 0
                                best_cm = g_cm
                                best_fm = g_fm
                                best_ov = leftover_after_fm
                                best_final_pp = cur_pp
                                best_final_cm = cm_stat
                                best_final_fm = fm_stat
                                best_final_primary = primary_base
                                best_final_secondary = secondary_base
                    g_fm += 1
                g_cm += 1

            if best_score > group_best_score:
                group_best_score = best_score
                group_best_surface = local_surface
                group_best_pp = best_pp
                group_best_cm = best_cm
                group_best_fm = best_fm
                group_best_ov = best_ov
                group_best_final_pp = best_final_pp
                group_best_final_cm = best_final_cm
                group_best_final_fm = best_final_fm
                group_best_final_primary = best_final_primary
                group_best_final_secondary = best_final_secondary
            local_surface += 1

        out_rows[group, 0] = group_best_score
        out_rows[group, 1] = group_best_surface
        out_rows[group, 2] = group_best_pp
        out_rows[group, 3] = group_best_cm
        out_rows[group, 4] = group_best_fm
        out_rows[group, 5] = group_best_ov
        out_rows[group, 6] = group_best_final_pp
        out_rows[group, 7] = group_best_final_cm
        out_rows[group, 8] = group_best_final_fm
        out_rows[group, 9] = group_best_final_primary
        out_rows[group, 10] = group_best_final_secondary


def optimize_response_frontier_inner_exact_gpu(
    surfaces: tuple[FgResponseSurface, ...] | list[FgResponseSurface],
    *,
    total_notes: int,
    residual_budget: int,
    stats_after_ftff: dict[str, Any],
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    ref_arrays: dict[str, Any],
) -> FgResponseInnerResult:
    result, _rows = _optimize_response_surfaces_gpu(
        [(int(residual_budget), stats_after_ftff, tuple(surfaces or ()))],
        total_notes=int(total_notes),
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        selected_color=str(selected_color or ""),
        ref_arrays=ref_arrays,
    )
    if not result:
        raise ValueError("response frontier GPU inner solve requires at least one surface")
    row = result[0]
    return FgResponseInnerResult(
        best_score=int(row[0]),
        surface_index=int(row[1]),
        g_pp=int(row[2]),
        g_cm=int(row[3]),
        g_fm=int(row[4]),
        g_ov=int(row[5]),
        final_pp=int(row[6]),
        final_cm=int(row[7]),
        final_fm=int(row[8]),
        final_primary=int(row[9]),
        final_secondary=int(row[10]),
    )


def _inner_stat_values_for_colors(
    stats_after_ftff: dict[str, Any] | tuple[int, ...],
    *,
    primary_color: str,
    secondary_color: str,
) -> tuple[int, int, int, int, int]:
    if isinstance(stats_after_ftff, tuple):
        return (
            int(stats_after_ftff[0]),
            int(stats_after_ftff[1]),
            int(stats_after_ftff[2]),
            int(stats_after_ftff[3]),
            int(stats_after_ftff[4]),
        )
    return (
        int(stats_after_ftff.get("Perfect Points", 0) or 0),
        int(stats_after_ftff.get("Combo Multiplier", 0) or 0),
        int(stats_after_ftff.get("Fever Multiplier", 0) or 0),
        int(stats_after_ftff.get(str(primary_color or ""), 0) or 0),
        int(stats_after_ftff.get(str(secondary_color or ""), 0) or 0),
    )


def _pack_response_frontier_surface_pool(
    frontiers: tuple[Any, ...],
    *,
    total_notes: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    body_total = max(0, int(total_notes) - 100)
    key = (int(body_total), tuple(id(frontier) for frontier in frontiers))
    cached = _PACKED_FRONTIER_SURFACE_CACHE.get(key)
    if cached is not None and cached[0] == frontiers:
        _PACKED_FRONTIER_SURFACE_CACHE.move_to_end(key)
        return cached[1], cached[2], cached[3], cached[4]

    offsets = np.zeros(len(frontiers), dtype=np.int32)
    lengths = np.zeros(len(frontiers), dtype=np.int32)
    word_blocks: list[np.ndarray] = []
    count_blocks: list[np.ndarray] = []
    row_offset = 0
    for frontier_idx, frontier in enumerate(frontiers):
        surfaces = tuple(getattr(frontier, "first_frontier"))
        offsets[frontier_idx] = int(row_offset)
        lengths[frontier_idx] = int(len(surfaces))
        if not surfaces:
            continue
        words = np.empty((len(surfaces), 8), dtype=np.uint32)
        counts = np.empty((len(surfaces), 2), dtype=np.int32)
        for surface_idx, surface in enumerate(surfaces):
            _validate_surface(surface, body_total=int(body_total))
            words[surface_idx, 0] = int(surface.fever0)
            words[surface_idx, 1] = int(surface.fever1)
            words[surface_idx, 2] = int(surface.fever2)
            words[surface_idx, 3] = int(surface.fever3)
            words[surface_idx, 4] = int(surface.great0)
            words[surface_idx, 5] = int(surface.great1)
            words[surface_idx, 6] = int(surface.great2)
            words[surface_idx, 7] = int(surface.great3)
            counts[surface_idx, 0] = int(surface.body_fever)
            counts[surface_idx, 1] = int(surface.body_great)
        word_blocks.append(words)
        count_blocks.append(counts)
        row_offset += int(len(surfaces))

    if row_offset > 0:
        surface_words = np.ascontiguousarray(np.concatenate(word_blocks, axis=0))
        surface_counts = np.ascontiguousarray(np.concatenate(count_blocks, axis=0))
    else:
        surface_words = np.zeros((0, 8), dtype=np.uint32)
        surface_counts = np.zeros((0, 2), dtype=np.int32)
    packed = (tuple(frontiers), surface_words, surface_counts, offsets, lengths)
    _PACKED_FRONTIER_SURFACE_CACHE[key] = packed
    _PACKED_FRONTIER_SURFACE_CACHE.move_to_end(key)
    while len(_PACKED_FRONTIER_SURFACE_CACHE) > _PACKED_FRONTIER_SURFACE_CACHE_MAX:
        _PACKED_FRONTIER_SURFACE_CACHE.popitem(last=False)
    return surface_words, surface_counts, offsets, lengths


def _precompute_surface_head_coeffs(
    surface_words: np.ndarray,
    *,
    head_len: int,
) -> np.ndarray:
    source = np.asarray(surface_words)
    cacheable = bool(source.dtype == np.uint32 and source.flags.c_contiguous)
    words = source if cacheable else np.ascontiguousarray(source, dtype=np.uint32)
    key = (int(id(words)), int(head_len), tuple(int(v) for v in words.shape), tuple(int(v) for v in words.strides))
    if cacheable:
        with _SURFACE_HEAD_COEFF_CACHE_LOCK:
            cached = _SURFACE_HEAD_COEFF_CACHE.get(key)
            if cached is not None:
                _SURFACE_HEAD_COEFF_CACHE.move_to_end(key)
                return cached
    coeffs = precompute_response_surface_head_coeffs(words, head_len=int(head_len))
    if cacheable:
        with _SURFACE_HEAD_COEFF_CACHE_LOCK:
            _SURFACE_HEAD_COEFF_CACHE[key] = coeffs
            _SURFACE_HEAD_COEFF_CACHE.move_to_end(key)
            while len(_SURFACE_HEAD_COEFF_CACHE) > int(_SURFACE_HEAD_COEFF_CACHE_MAX):
                _SURFACE_HEAD_COEFF_CACHE.popitem(last=False)
    return coeffs


def _score_response_group_meta_gpu(
    *,
    group_meta: np.ndarray,
    group_offsets: np.ndarray,
    group_lengths: np.ndarray,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    ref_arrays: dict[str, Any],
    surface_words: np.ndarray,
    surface_counts: np.ndarray,
    surface_head_coeffs: np.ndarray | None = None,
) -> tuple[np.ndarray, int]:
    group_count = int(group_meta.shape[0])
    if group_count != int(group_offsets.shape[0]) or group_count != int(group_lengths.shape[0]):
        raise ValueError("response frontier GPU group metadata arrays have inconsistent lengths")
    logical_surface_rows = int(np.sum(group_lengths, dtype=np.int64))
    if logical_surface_rows <= 0:
        return np.zeros((0, 11), dtype=np.int32), 0

    gem_api.ensure_ready()
    flags = np.ascontiguousarray(np.asarray(_color_flags(primary_color, secondary_color, selected_color), dtype=np.int32))
    ref_pp = np.ascontiguousarray(np.asarray(ref_arrays["Perfect Points"], dtype=np.float32))
    ref_cm = np.ascontiguousarray(np.asarray(ref_arrays["Combo Multiplier"], dtype=np.float32))
    ref_fm = np.ascontiguousarray(np.asarray(ref_arrays["Fever Multiplier"], dtype=np.float32))
    surface_words_all = np.ascontiguousarray(surface_words, dtype=np.uint32)
    surface_counts_all = np.ascontiguousarray(surface_counts, dtype=np.int32)
    group_meta_all = np.ascontiguousarray(group_meta, dtype=np.int32)
    group_offsets_all = np.ascontiguousarray(group_offsets, dtype=np.int32)
    group_lengths_all = np.ascontiguousarray(group_lengths, dtype=np.int32)

    if int(surface_words_all.shape[0]) != int(surface_counts_all.shape[0]):
        raise ValueError("response frontier GPU surface arrays have inconsistent lengths")
    if int(surface_words_all.shape[1]) != 8 or int(surface_counts_all.shape[1]) != 2:
        raise ValueError("response frontier GPU surface arrays have invalid shape")
    if int(group_meta_all.shape[1]) < 8:
        raise ValueError("response frontier GPU group metadata requires head/body columns")
    head_lengths = np.unique(np.ascontiguousarray(group_meta_all[:, 6], dtype=np.int32))
    if int(head_lengths.shape[0]) != 1:
        raise ValueError("response frontier GPU group metadata has inconsistent head length")
    if surface_head_coeffs is None:
        surface_head_coeffs_all = _precompute_surface_head_coeffs(surface_words_all, head_len=int(head_lengths[0]))
    else:
        surface_head_coeffs_all = np.ascontiguousarray(np.asarray(surface_head_coeffs, dtype=np.int32))
        if (
            int(surface_head_coeffs_all.ndim) != 2
            or int(surface_head_coeffs_all.shape[0]) != int(surface_words_all.shape[0])
            or int(surface_head_coeffs_all.shape[1]) != 4
        ):
            raise ValueError("response frontier GPU surface head coefficients have invalid shape")

    flags_tuple = _color_flags(primary_color, secondary_color, selected_color)
    allow_pp = bool(int(flags_tuple[0]) != 0 or int(flags_tuple[1]) != 0)
    combo_counts = _response_inner_combo_counts(group_meta_all, allow_pp=allow_pp)
    work_by_group = np.asarray(group_lengths_all, dtype=np.int64) * combo_counts
    total_work = int(np.sum(work_by_group, dtype=np.int64))
    max_group_work = int(np.max(work_by_group)) if group_count > 0 else 0
    max_dispatch_work = max(1, int(_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_WORK))
    max_thread_work = max(1, int(_FG_RESPONSE_INNER_GPU_MAX_THREAD_WORK))
    max_dispatch_groups = max(1, int(_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_GROUPS))
    max_surface_dispatch_rows = max(1, int(_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_ROWS))
    max_surface_dispatch_work = max(1, int(_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_WORK))
    out_rows = np.zeros((group_count, 11), dtype=np.int32)
    if (
        group_count <= max_dispatch_groups
        and total_work <= max_dispatch_work
        and max_group_work <= max_thread_work
    ):
        _fg_response_inner_group_kernel(
            int(group_count),
            surface_words_all,
            surface_counts_all,
            surface_head_coeffs_all,
            group_offsets_all,
            group_lengths_all,
            group_meta_all,
            flags,
            ref_pp,
            ref_cm,
            ref_fm,
            out_rows,
            bool(allow_pp),
        )
        ti.sync()
        return out_rows, int(logical_surface_rows)

    valid_mask = np.asarray(group_lengths_all > 0, dtype=np.bool_)
    standard_group_mask = np.asarray(
        valid_mask & (work_by_group <= int(max_thread_work)),
        dtype=np.bool_,
    )
    direct_group_indices = np.flatnonzero(standard_group_mask).astype(np.int32, copy=False)
    oversized_group_indices = np.flatnonzero(valid_mask & ~standard_group_mask).astype(
        np.int32,
        copy=False,
    )

    def run_group_dispatch(group_indices: np.ndarray) -> None:
        dispatch_count = int(group_indices.shape[0])
        if dispatch_count <= 0:
            return
        dispatch_out = np.zeros((dispatch_count, 11), dtype=np.int32)
        _fg_response_inner_group_kernel(
            int(dispatch_count),
            surface_words_all,
            surface_counts_all,
            surface_head_coeffs_all,
            np.ascontiguousarray(group_offsets_all[group_indices], dtype=np.int32),
            np.ascontiguousarray(group_lengths_all[group_indices], dtype=np.int32),
            np.ascontiguousarray(group_meta_all[group_indices], dtype=np.int32),
            flags,
            ref_pp,
            ref_cm,
            ref_fm,
            dispatch_out,
            bool(allow_pp),
        )
        ti.sync()
        out_rows[group_indices, :] = dispatch_out

    if int(direct_group_indices.shape[0]) > 0:
        dispatch_indices: list[int] = []
        dispatch_work = 0
        for group_idx in direct_group_indices.tolist():
            group_work = int(work_by_group[int(group_idx)])
            if dispatch_indices and (
                len(dispatch_indices) >= int(max_dispatch_groups)
                or (int(dispatch_work) + int(group_work)) > int(max_dispatch_work)
            ):
                run_group_dispatch(np.asarray(dispatch_indices, dtype=np.int32))
                dispatch_indices.clear()
                dispatch_work = 0
            dispatch_indices.append(int(group_idx))
            dispatch_work += int(group_work)
        if dispatch_indices:
            run_group_dispatch(np.asarray(dispatch_indices, dtype=np.int32))

    if int(oversized_group_indices.shape[0]) <= 0:
        return out_rows, int(logical_surface_rows)

    best_scores = np.full((group_count,), np.iinfo(np.int32).min, dtype=np.int32)
    chunk_row_meta_blocks: list[np.ndarray] = []
    chunk_word_blocks: list[np.ndarray] = []
    chunk_count_blocks: list[np.ndarray] = []
    chunk_head_coeff_blocks: list[np.ndarray] = []
    chunk_owner_blocks: list[np.ndarray] = []
    chunk_local_surface_blocks: list[np.ndarray] = []
    chunk_surface_rows = 0
    chunk_work = 0

    def flush_chunk() -> None:
        nonlocal chunk_surface_rows, chunk_work
        if chunk_surface_rows <= 0:
            return
        chunk_surface_words = np.ascontiguousarray(np.concatenate(chunk_word_blocks, axis=0), dtype=np.uint32)
        chunk_surface_counts = np.ascontiguousarray(np.concatenate(chunk_count_blocks, axis=0), dtype=np.int32)
        chunk_surface_head_coeffs = np.ascontiguousarray(np.concatenate(chunk_head_coeff_blocks, axis=0), dtype=np.int32)
        chunk_row_meta = np.ascontiguousarray(np.concatenate(chunk_row_meta_blocks, axis=0), dtype=np.int32)
        chunk_owners = np.ascontiguousarray(np.concatenate(chunk_owner_blocks, axis=0), dtype=np.int32)
        chunk_local_surfaces = np.ascontiguousarray(np.concatenate(chunk_local_surface_blocks, axis=0), dtype=np.int32)
        chunk_out = np.zeros((chunk_surface_rows, 10), dtype=np.int32)
        _fg_response_inner_batch_kernel(
            int(chunk_surface_rows),
            chunk_surface_words,
            chunk_surface_counts,
            chunk_surface_head_coeffs,
            chunk_row_meta,
            flags,
            ref_pp,
            ref_cm,
            ref_fm,
            chunk_out,
            bool(allow_pp),
        )
        ti.sync()

        chunk_scores = np.ascontiguousarray(chunk_out[:, 0], dtype=np.int32)
        run_starts = np.concatenate(
            (
                np.asarray([0], dtype=np.intp),
                np.flatnonzero(chunk_owners[1:] != chunk_owners[:-1]).astype(np.intp, copy=False) + 1,
            )
        )
        run_stops = np.concatenate((run_starts[1:], np.asarray([int(chunk_scores.shape[0])], dtype=np.intp)))
        run_owners = np.asarray(chunk_owners[run_starts], dtype=np.intp)
        run_scores = np.maximum.reduceat(chunk_scores, run_starts)
        run_lengths = np.asarray(run_stops - run_starts, dtype=np.intp)
        row_indices = np.arange(int(chunk_scores.shape[0]), dtype=np.intp)
        best_candidates = np.where(
            chunk_scores == np.repeat(run_scores, run_lengths),
            row_indices,
            int(chunk_scores.shape[0]),
        )
        best_row_indices = np.minimum.reduceat(best_candidates, run_starts)
        improved = run_scores > best_scores[run_owners]
        if bool(np.any(improved)):
            improved_owners = run_owners[improved]
            improved_rows = best_row_indices[improved]
            best_scores[improved_owners] = run_scores[improved]
            out_rows[improved_owners, 0] = run_scores[improved]
            out_rows[improved_owners, 1] = chunk_local_surfaces[improved_rows]
            out_rows[improved_owners, 2:] = chunk_out[improved_rows, 1:]

        chunk_row_meta_blocks.clear()
        chunk_word_blocks.clear()
        chunk_count_blocks.clear()
        chunk_head_coeff_blocks.clear()
        chunk_owner_blocks.clear()
        chunk_local_surface_blocks.clear()
        chunk_surface_rows = 0
        chunk_work = 0

    for group_idx in oversized_group_indices.tolist():
        offset = int(group_offsets_all[int(group_idx)])
        length = int(group_lengths_all[int(group_idx)])
        if length <= 0:
            continue
        if offset < 0 or offset + length > int(surface_words_all.shape[0]):
            raise ValueError("response frontier GPU group references surfaces outside the packed pool")

        consumed = 0
        combo_count = max(1, int(combo_counts[int(group_idx)]))
        while consumed < length:
            if chunk_surface_rows >= int(max_surface_dispatch_rows) or chunk_work >= int(max_surface_dispatch_work):
                flush_chunk()

            row_budget = int(max_surface_dispatch_rows) - int(chunk_surface_rows)
            work_budget = int(max_surface_dispatch_work) - int(chunk_work)
            max_take_by_work = max(1, int(work_budget) // int(combo_count))
            take = min(int(length - consumed), int(row_budget), int(max_take_by_work))
            if take <= 0:
                flush_chunk()
                continue
            item_work = int(take) * int(combo_count)

            surface_start = int(offset + consumed)
            surface_stop = int(surface_start + take)
            chunk_row_meta_blocks.append(np.repeat(group_meta_all[int(group_idx) : int(group_idx) + 1], int(take), axis=0))
            chunk_word_blocks.append(surface_words_all[surface_start:surface_stop])
            chunk_count_blocks.append(surface_counts_all[surface_start:surface_stop])
            chunk_head_coeff_blocks.append(surface_head_coeffs_all[surface_start:surface_stop])
            chunk_owner_blocks.append(np.full((int(take),), int(group_idx), dtype=np.int32))
            chunk_local_surface_blocks.append(np.arange(int(consumed), int(consumed + take), dtype=np.int32))
            chunk_surface_rows += int(take)
            chunk_work += int(item_work)
            consumed += int(take)

    flush_chunk()
    return out_rows, int(logical_surface_rows)


def _optimize_response_groups_gpu(
    groups: list[tuple[int, dict[str, Any] | tuple[int, ...], int]],
    *,
    total_notes: int,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    ref_arrays: dict[str, Any],
    surface_words: np.ndarray,
    surface_counts: np.ndarray,
    frontier_offsets: np.ndarray,
    frontier_lengths: np.ndarray,
) -> tuple[list[tuple[int, int, int, int, int, int, int, int, int, int, int]], int]:
    head_len = min(int(total_notes), 100)
    body_total = max(0, int(total_notes) - 100)
    group_meta = np.zeros((len(groups), 8), dtype=np.int32)
    group_offsets = np.zeros(len(groups), dtype=np.int32)
    group_lengths = np.zeros(len(groups), dtype=np.int32)
    logical_surface_rows = 0

    for group_idx, (residual_budget, stats_after_ftff, frontier_idx) in enumerate(groups):
        idx = int(frontier_idx)
        if idx < 0 or idx >= int(frontier_offsets.shape[0]):
            raise ValueError(f"response frontier group references unknown packed frontier index: {idx}")
        length = int(frontier_lengths[idx])
        if length <= 0:
            continue
        if isinstance(stats_after_ftff, tuple):
            cur_pp = int(stats_after_ftff[0])
            cur_cm = int(stats_after_ftff[1])
            cur_fm = int(stats_after_ftff[2])
            cur_primary = int(stats_after_ftff[3])
            cur_secondary = int(stats_after_ftff[4])
        else:
            cur_pp, cur_cm, cur_fm, cur_primary, cur_secondary = _inner_stat_values_for_colors(
                stats_after_ftff,
                primary_color=primary_color,
                secondary_color=secondary_color,
            )
        logical_surface_rows += int(length)
        group_offsets[group_idx] = int(frontier_offsets[idx])
        group_lengths[group_idx] = int(length)
        residual = int(residual_budget)
        if residual < 0:
            residual = 0
        group_meta[group_idx] = (
            int(residual),
            int(cur_pp),
            int(cur_cm),
            int(cur_fm),
            int(cur_primary),
            int(cur_secondary),
            int(head_len),
            int(body_total),
        )
    if logical_surface_rows <= 0:
        return [], 0

    out_rows, _surface_rows = _score_response_group_meta_gpu(
        group_meta=group_meta,
        group_offsets=group_offsets,
        group_lengths=group_lengths,
        primary_color=primary_color,
        secondary_color=secondary_color,
        selected_color=selected_color,
        ref_arrays=ref_arrays,
        surface_words=surface_words,
        surface_counts=surface_counts,
    )

    best_by_group: list[tuple[int, int, int, int, int, int, int, int, int, int, int] | None] = [None] * len(groups)
    for group_idx in range(len(groups)):
        if int(group_lengths[group_idx]) <= 0:
            continue
        raw = out_rows[group_idx]
        best_by_group[int(group_idx)] = (
            int(raw[0]),
            int(raw[1]),
            int(raw[2]),
            int(raw[3]),
            int(raw[4]),
            int(raw[5]),
            int(raw[6]),
            int(raw[7]),
            int(raw[8]),
            int(raw[9]),
            int(raw[10]),
        )
    return [row for row in best_by_group if row is not None], int(_surface_rows)


def _optimize_response_surfaces_gpu(
    groups: list[tuple[int, dict[str, Any] | tuple[int, ...], tuple[FgResponseSurface, ...]]],
    *,
    total_notes: int,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    ref_arrays: dict[str, Any],
) -> tuple[list[tuple[int, int, int, int, int, int, int, int, int, int, int]], int]:
    head_len = min(int(total_notes), 100)
    body_total = max(0, int(total_notes) - 100)
    surface_cache: dict[int, tuple[int, int]] = {}
    surface_word_blocks: list[np.ndarray] = []
    surface_count_blocks: list[np.ndarray] = []
    group_meta = np.zeros((len(groups), 8), dtype=np.int32)
    group_offsets = np.zeros(len(groups), dtype=np.int32)
    group_lengths = np.zeros(len(groups), dtype=np.int32)
    logical_surface_rows = 0
    unique_surface_rows = 0

    def _surface_block(surfaces: tuple[FgResponseSurface, ...]) -> tuple[int, int]:
        nonlocal unique_surface_rows
        key = id(surfaces)
        cached = surface_cache.get(key)
        if cached is not None:
            return cached
        words = np.empty((len(surfaces), 8), dtype=np.uint32)
        counts = np.empty((len(surfaces), 2), dtype=np.int32)
        for idx, surface in enumerate(surfaces):
            _validate_surface(surface, body_total=int(body_total))
            words[idx, 0] = int(surface.fever0)
            words[idx, 1] = int(surface.fever1)
            words[idx, 2] = int(surface.fever2)
            words[idx, 3] = int(surface.fever3)
            words[idx, 4] = int(surface.great0)
            words[idx, 5] = int(surface.great1)
            words[idx, 6] = int(surface.great2)
            words[idx, 7] = int(surface.great3)
            counts[idx, 0] = int(surface.body_fever)
            counts[idx, 1] = int(surface.body_great)
        cached = (int(unique_surface_rows), int(words.shape[0]))
        surface_cache[key] = cached
        surface_word_blocks.append(words)
        surface_count_blocks.append(counts)
        unique_surface_rows += int(words.shape[0])
        return cached

    for group_idx, (residual_budget, stats_after_ftff, surfaces) in enumerate(groups):
        cur_pp, cur_cm, cur_fm, cur_primary, cur_secondary = _inner_stat_values_for_colors(
            stats_after_ftff,
            primary_color=str(primary_color or ""),
            secondary_color=str(secondary_color or ""),
        )
        surfaces_tuple = tuple(surfaces or ())
        if not surfaces_tuple:
            continue
        offset, length = _surface_block(surfaces_tuple)
        logical_surface_rows += int(length)
        group_offsets[group_idx] = int(offset)
        group_lengths[group_idx] = int(length)
        group_meta[group_idx] = (
            max(0, int(residual_budget)),
            int(cur_pp),
            int(cur_cm),
            int(cur_fm),
            int(cur_primary),
            int(cur_secondary),
            int(head_len),
            int(body_total),
        )
    if logical_surface_rows <= 0:
        return [], 0

    gem_api.ensure_ready()
    if unique_surface_rows <= 0:
        raise ValueError("response frontier GPU inner solve has groups but no packed surfaces")
    surface_words = np.ascontiguousarray(np.concatenate(surface_word_blocks, axis=0))
    surface_counts = np.ascontiguousarray(np.concatenate(surface_count_blocks, axis=0))
    surface_head_coeffs = _precompute_surface_head_coeffs(surface_words, head_len=int(head_len))

    flags_tuple = _color_flags(primary_color, secondary_color, selected_color)
    allow_pp = bool(int(flags_tuple[0]) != 0 or int(flags_tuple[1]) != 0)
    flags = np.ascontiguousarray(np.asarray(flags_tuple, dtype=np.int32))
    ref_pp = np.ascontiguousarray(np.asarray(ref_arrays["Perfect Points"], dtype=np.float32))
    ref_cm = np.ascontiguousarray(np.asarray(ref_arrays["Combo Multiplier"], dtype=np.float32))
    ref_fm = np.ascontiguousarray(np.asarray(ref_arrays["Fever Multiplier"], dtype=np.float32))
    out_rows = np.zeros((len(groups), 11), dtype=np.int32)
    _fg_response_inner_group_kernel(
        int(len(groups)),
        surface_words,
        surface_counts,
        surface_head_coeffs,
        group_offsets,
        group_lengths,
        group_meta,
        flags,
        ref_pp,
        ref_cm,
        ref_fm,
        out_rows,
        bool(allow_pp),
    )
    ti.sync()

    best_by_group: list[tuple[int, int, int, int, int, int, int, int, int, int, int] | None] = [None] * len(groups)
    for group_idx in range(len(groups)):
        if int(group_lengths[group_idx]) <= 0:
            continue
        raw = out_rows[group_idx]
        candidate = (
            int(raw[0]),
            int(raw[1]),
            int(raw[2]),
            int(raw[3]),
            int(raw[4]),
            int(raw[5]),
            int(raw[6]),
            int(raw[7]),
            int(raw[8]),
            int(raw[9]),
            int(raw[10]),
        )
        best_by_group[int(group_idx)] = candidate
    return [row for row in best_by_group if row is not None], int(logical_surface_rows)
