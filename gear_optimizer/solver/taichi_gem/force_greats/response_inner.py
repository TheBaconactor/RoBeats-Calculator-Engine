from typing import Any

import numpy as np
import taichi as ti

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    MAX_STAT_INDEX,
    TOTAL_ROWS,
)
from gear_optimizer.core.jit_setup import jit
from gear_optimizer.solver.scoring_core import lookup_reference_jit
from gear_optimizer.solver.taichi_gem import api as gem_api

from .response_types import FgResponseInnerResult, FgResponseSurface


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

    great_penalty_base_head = int(np.floor(float(int(primary_val) * 2) * (2.0 / 3.0))) + int(
        np.floor(float(int(secondary_val)) * (2.0 / 3.0))
    ) + 150
    great_penalty_base_raw = (float(int(primary_val) * 2) * (2.0 / 3.0)) + (
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
    ref_pp,
    ref_cm,
    ref_fm,
):
    allow_pp = (int(is_p_pp) != 0) or (int(is_s_pp) != 0)
    allow_cm_color = (int(is_p_cm) != 0) or (int(is_s_cm) != 0)

    max_pp_gems = 0
    if allow_pp and int(cur_pp) < MAX_STAT_INDEX:
        rem_pp = MAX_STAT_INDEX - int(cur_pp)
        max_pp_gems = rem_pp // GEM_SCALE_NORMAL
        if rem_pp % GEM_SCALE_NORMAL != 0:
            max_pp_gems += 1

    max_cm_gems = 0
    if int(cur_cm) < MAX_STAT_INDEX:
        if allow_cm_color:
            rem_cm = MAX_STAT_INDEX - int(cur_cm)
            max_cm_gems = rem_cm // GEM_SCALE_NORMAL
            if rem_cm % GEM_SCALE_NORMAL != 0:
                max_cm_gems += 1
        elif int(cur_cm) <= 50:
            max_cm_gems = ((50 - int(cur_cm)) // GEM_SCALE_NORMAL) + 1

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
) -> ti.i32:
    base_value: ti.f32 = ti.cast((primary_val * 2) + secondary_val, ti.f32) + pp_factor
    combo_val: ti.i32 = ti.cast(ti.floor(base_value * combo_mul), ti.i32)
    fever_val: ti.i32 = ti.cast(ti.floor(base_value * combo_mul * fever_mul), ti.i32)
    body_normal: ti.i32 = body_total - body_fever
    if body_normal < 0:
        body_normal = 0
    score: ti.i32 = body_fever * fever_val + body_normal * combo_val

    factor: ti.f32 = (combo_mul - ti.f32(1.0)) * base_value / ti.f32(100.0)
    for i in range(100):
        if i < head_len:
            fever_word: ti.u32 = fever0
            great_word: ti.u32 = great0
            bit_idx: ti.i32 = i
            if i >= 32 and i < 64:
                fever_word = fever1
                great_word = great1
                bit_idx = i - 32
            elif i >= 64 and i < 96:
                fever_word = fever2
                great_word = great2
                bit_idx = i - 64
            elif i >= 96:
                fever_word = fever3
                great_word = great3
                bit_idx = i - 96
            ramp: ti.f32 = base_value + ti.cast(i + 1, ti.f32) * factor
            if _fg_response_bit(fever_word, bit_idx) != 0:
                score += ti.cast(ti.floor(ramp * fever_mul), ti.i32)
            else:
                score += ti.cast(ti.floor(ramp), ti.i32)

    great_head_base: ti.i32 = (
        ti.cast(ti.floor(ti.cast(primary_val * 2, ti.f32) * ti.f32(2.0 / 3.0)), ti.i32)
        + ti.cast(ti.floor(ti.cast(secondary_val, ti.f32) * ti.f32(2.0 / 3.0)), ti.i32)
        + 150
    )
    great_raw: ti.f32 = (
        ti.cast(primary_val * 2, ti.f32) * ti.f32(2.0 / 3.0)
        + ti.cast(secondary_val, ti.f32) * ti.f32(2.0 / 3.0)
        + ti.f32(150.0)
    )
    body_penalty: ti.i32 = combo_val - ti.cast(ti.floor(great_raw * combo_mul), ti.i32)
    if body_penalty < 0:
        body_penalty = 0
    score -= body_great * body_penalty

    combo_span: ti.f32 = combo_mul - ti.f32(1.0)
    for i in range(100):
        if i < head_len:
            great_word: ti.u32 = great0
            bit_idx: ti.i32 = i
            if i >= 32 and i < 64:
                great_word = great1
                bit_idx = i - 32
            elif i >= 64 and i < 96:
                great_word = great2
                bit_idx = i - 64
            elif i >= 96:
                great_word = great3
                bit_idx = i - 96
            if _fg_response_bit(great_word, bit_idx) != 0:
                scaling: ti.f32 = ti.f32(1.0) + combo_span * ti.cast(i + 1, ti.f32) / ti.f32(100.0)
                perfect_val: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
                great_val: ti.i32 = ti.cast(ti.floor(ti.cast(great_head_base, ti.f32) * scaling), ti.i32)
                penalty: ti.i32 = perfect_val - great_val
                if penalty > 0:
                    score -= penalty
    return score


@ti.kernel
def _fg_response_inner_batch_kernel(
    row_count: ti.i32,
    surface_words: ti.types.ndarray(dtype=ti.u32, ndim=2),
    surface_counts: ti.types.ndarray(dtype=ti.i32, ndim=2),
    row_meta: ti.types.ndarray(dtype=ti.i32, ndim=2),
    color_flags: ti.types.ndarray(dtype=ti.i32, ndim=1),
    ref_pp: ti.types.ndarray(dtype=ti.f32, ndim=1),
    ref_cm: ti.types.ndarray(dtype=ti.f32, ndim=1),
    ref_fm: ti.types.ndarray(dtype=ti.f32, ndim=1),
    out_rows: ti.types.ndarray(dtype=ti.i32, ndim=2),
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

        pp_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
        pp_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
        cm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
        cm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
        fm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
        fm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
        ov_p_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_p_ov
        ov_s_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_s_ov

        allow_pp: ti.i32 = ti.cast((is_p_pp != 0) | (is_s_pp != 0), ti.i32)
        allow_cm_color: ti.i32 = ti.cast((is_p_cm != 0) | (is_s_cm != 0), ti.i32)

        max_pp_gems: ti.i32 = 0
        if allow_pp != 0 and cur_pp < MAX_STAT_INDEX:
            rem_pp: ti.i32 = MAX_STAT_INDEX - cur_pp
            max_pp_gems = rem_pp // GEM_SCALE_NORMAL
            if rem_pp % GEM_SCALE_NORMAL != 0:
                max_pp_gems += 1

        max_cm_gems: ti.i32 = 0
        if cur_cm < MAX_STAT_INDEX:
            if allow_cm_color != 0:
                rem_cm: ti.i32 = MAX_STAT_INDEX - cur_cm
                max_cm_gems = rem_cm // GEM_SCALE_NORMAL
                if rem_cm % GEM_SCALE_NORMAL != 0:
                    max_cm_gems += 1
            elif cur_cm <= 50:
                max_cm_gems = ((50 - cur_cm) // GEM_SCALE_NORMAL) + 1

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

        g_cm: ti.i32 = 0
        while g_cm <= max_cm_gems:
            leftover_after_cm: ti.i32 = residual_budget - g_cm
            if leftover_after_cm < 0:
                break
            g_fm_max: ti.i32 = max_fm_gems
            if g_fm_max > leftover_after_cm:
                g_fm_max = leftover_after_cm
            g_fm: ti.i32 = 0
            while g_fm <= g_fm_max:
                leftover_after_fm: ti.i32 = leftover_after_cm - g_fm
                g_pp_max: ti.i32 = max_pp_gems
                if g_pp_max > leftover_after_fm:
                    g_pp_max = leftover_after_fm
                g_pp: ti.i32 = 0
                while g_pp <= g_pp_max:
                    g_ov: ti.i32 = leftover_after_fm - g_pp
                    pp_stat: ti.i32 = cur_pp + g_pp * GEM_SCALE_NORMAL
                    cm_stat: ti.i32 = cur_cm + g_cm * GEM_SCALE_NORMAL
                    fm_stat: ti.i32 = cur_fm + g_fm * GEM_SCALE_FEVER
                    primary_val: ti.i32 = (
                        cur_primary
                        + g_pp * pp_p_delta
                        + g_cm * cm_p_delta
                        + g_fm * fm_p_delta
                        + g_ov * ov_p_delta
                    )
                    secondary_val: ti.i32 = (
                        cur_secondary
                        + g_pp * pp_s_delta
                        + g_cm * cm_s_delta
                        + g_fm * fm_s_delta
                        + g_ov * ov_s_delta
                    )
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
                        primary_val,
                        secondary_val,
                        _fg_response_lookup_ref(ref_pp, pp_stat),
                        _fg_response_lookup_ref(ref_cm, cm_stat),
                        _fg_response_lookup_ref(ref_fm, fm_stat),
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


def _optimize_response_surfaces_gpu(
    groups: list[tuple[int, dict[str, Any], tuple[FgResponseSurface, ...]]],
    *,
    total_notes: int,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    ref_arrays: dict[str, Any],
) -> tuple[list[tuple[int, int, int, int, int, int, int, int, int, int, int]], int]:
    rows: list[tuple[int, int, FgResponseSurface]] = []
    meta: list[list[int]] = []
    head_len = min(int(total_notes), 100)
    body_total = max(0, int(total_notes) - 100)
    for group_idx, (residual_budget, stats_after_ftff, surfaces) in enumerate(groups):
        cur_pp = int(stats_after_ftff.get("Perfect Points", 0) or 0)
        cur_cm = int(stats_after_ftff.get("Combo Multiplier", 0) or 0)
        cur_fm = int(stats_after_ftff.get("Fever Multiplier", 0) or 0)
        cur_primary = int(stats_after_ftff.get(str(primary_color or ""), 0) or 0)
        cur_secondary = int(stats_after_ftff.get(str(secondary_color or ""), 0) or 0)
        for surface_idx, surface in enumerate(tuple(surfaces or ())):
            _validate_surface(surface, body_total=int(body_total))
            rows.append((int(group_idx), int(surface_idx), surface))
            meta.append(
                [
                    max(0, int(residual_budget)),
                    int(cur_pp),
                    int(cur_cm),
                    int(cur_fm),
                    int(cur_primary),
                    int(cur_secondary),
                    int(head_len),
                    int(body_total),
                ]
            )
    if not rows:
        return [], 0

    gem_api.ensure_ready()
    surface_words = np.zeros((len(rows), 8), dtype=np.uint32)
    surface_counts = np.zeros((len(rows), 2), dtype=np.int32)
    for idx, (_group_idx, _surface_idx, surface) in enumerate(rows):
        surface_words[idx] = np.asarray(
            [
                int(surface.fever0),
                int(surface.fever1),
                int(surface.fever2),
                int(surface.fever3),
                int(surface.great0),
                int(surface.great1),
                int(surface.great2),
                int(surface.great3),
            ],
            dtype=np.uint32,
        )
        surface_counts[idx] = np.asarray([int(surface.body_fever), int(surface.body_great)], dtype=np.int32)

    row_meta = np.ascontiguousarray(np.asarray(meta, dtype=np.int32))
    flags = np.ascontiguousarray(np.asarray(_color_flags(primary_color, secondary_color, selected_color), dtype=np.int32))
    ref_pp = np.ascontiguousarray(np.asarray(ref_arrays["Perfect Points"], dtype=np.float32))
    ref_cm = np.ascontiguousarray(np.asarray(ref_arrays["Combo Multiplier"], dtype=np.float32))
    ref_fm = np.ascontiguousarray(np.asarray(ref_arrays["Fever Multiplier"], dtype=np.float32))
    out_rows = np.zeros((len(rows), 10), dtype=np.int32)
    _fg_response_inner_batch_kernel(
        int(len(rows)),
        surface_words,
        surface_counts,
        row_meta,
        flags,
        ref_pp,
        ref_cm,
        ref_fm,
        out_rows,
    )
    ti.sync()

    best_by_group: list[tuple[int, int, int, int, int, int, int, int, int, int, int] | None] = [None] * len(groups)
    for row_idx, (group_idx, surface_idx, _surface) in enumerate(rows):
        raw = out_rows[row_idx]
        candidate = (
            int(raw[0]),
            int(surface_idx),
            int(raw[1]),
            int(raw[2]),
            int(raw[3]),
            int(raw[4]),
            int(raw[5]),
            int(raw[6]),
            int(raw[7]),
            int(raw[8]),
            int(raw[9]),
        )
        current = best_by_group[int(group_idx)]
        if current is None or candidate[0] > current[0]:
            best_by_group[int(group_idx)] = candidate
    return [row for row in best_by_group if row is not None], int(len(rows))
