from typing import Any

import numpy as np

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    MAX_STAT_INDEX,
    TOTAL_ROWS,
)
from gear_optimizer.core.jit_setup import jit
from gear_optimizer.solver.scoring.fg_policy import is_single_color_song
from gear_optimizer.solver.scoring_core import lookup_reference_jit

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
