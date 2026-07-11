import sys

import numpy as np
import taichi as ti

from gear_optimizer.core.constants import TOTAL_ROWS

# Hardware-gated solver fp for the FG response-inner gem search. The RX 7900 XTX (and any
# Vulkan device with shaderFloat64) runs the search in f64 -- its native mixed-precision
# form, bit-identical to today. MoltenVK/Metal (macOS) has no shaderFloat64, so the same
# kernel compiles at f32 there. This is a required-hardware-safety-boundary split (the only
# branch the canonical-path rule permits), mirroring the IS_METAL gate in runtime.py. The
# search only selects the argmax gem allocation; the served score is CPU-f64 exact-rescored,
# so the final score is lossless regardless of which fp the search ran at.
FP = ti.f32 if sys.platform == "darwin" else ti.f64
# The numpy dtype the host must feed the GPU kernel's ref arrays, kept in lockstep with FP
# (one gate). The CPU exact-rescore path stays float64 regardless.
SOLVER_NP_FP = np.float32 if sys.platform == "darwin" else np.float64


@ti.func
def _fg_response_lookup_ref(ref: ti.template(), idx: ti.i32) -> FP:
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
def _fg_response_head_score(
    base_value: FP,
    combo_slope: FP,
    fever_mul: FP,
    note_idx: ti.i32,
    is_fever: ti.i32,
) -> ti.i32:
    scaling: FP = combo_slope * ti.cast(note_idx + 1, FP) + FP(1.0)
    score: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
    if is_fever != 0:
        score = ti.cast(ti.floor(base_value * scaling * fever_mul), ti.i32)
    return score


@ti.func
def _fg_response_body_score_device(
    body_fever: ti.i32,
    body_great: ti.i32,
    body_fever_great: ti.i32,
    body_total: ti.i32,
    primary_val: ti.i32,
    secondary_val: ti.i32,
    pp_factor: FP,
    combo_mul: FP,
    fever_mul: FP,
    is_single_color: ti.i32,
) -> ti.i32:
    base_value: FP = ti.cast((primary_val * 2) + secondary_val, FP) + pp_factor
    combo_val: ti.i32 = ti.cast(ti.floor(base_value * combo_mul), ti.i32)
    fever_val: ti.i32 = ti.cast(ti.floor(base_value * combo_mul * fever_mul), ti.i32)
    body_normal: ti.i32 = ti.max(0, body_total - body_fever)
    score: ti.i32 = body_fever * fever_val + body_normal * combo_val
    if body_great > 0:
        great_head_base: ti.i32 = 0
        if is_single_color != 0:
            great_head_base = (primary_val * 2) + 150
        else:
            great_head_base = (
                ti.cast(ti.floor(ti.cast(primary_val, FP) * FP(4.0 / 3.0)), ti.i32)
                + ti.cast(ti.floor(ti.cast(secondary_val, FP) * FP(2.0 / 3.0)), ti.i32)
                + 150
            )
        great_base: FP = ti.cast(great_head_base, FP)
        great_combo_val: ti.i32 = ti.cast(ti.floor(great_base * combo_mul), ti.i32)
        great_fever_val: ti.i32 = ti.cast(ti.floor(great_base * combo_mul * fever_mul), ti.i32)
        body_normal_great: ti.i32 = ti.max(0, body_great - body_fever_great)
        body_normal_penalty: ti.i32 = ti.max(0, combo_val - great_combo_val)
        body_fever_penalty: ti.i32 = ti.max(0, fever_val - great_fever_val)
        score -= body_normal_great * body_normal_penalty
        score -= body_fever_great * body_fever_penalty
    return score


@ti.func
def _fg_response_pattern_result_is_better(
    score: ti.i32,
    local_surface: ti.i32,
    g_cm: ti.i32,
    g_fm: ti.i32,
    g_pp: ti.i32,
    best_score: ti.i32,
    best_surface: ti.i32,
    best_cm: ti.i32,
    best_fm: ti.i32,
    best_pp: ti.i32,
) -> ti.i32:
    better: ti.i32 = 0
    if score > best_score:
        better = 1
    elif score == best_score:
        if local_surface < best_surface:
            better = 1
        elif local_surface == best_surface:
            if g_cm < best_cm or (
                g_cm == best_cm and (g_fm < best_fm or (g_fm == best_fm and g_pp < best_pp))
            ):
                better = 1
    return better


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
    body_fever_great: ti.i32,
    head_len: ti.i32,
    body_total: ti.i32,
    primary_val: ti.i32,
    secondary_val: ti.i32,
    pp_factor: FP,
    combo_mul: FP,
    fever_mul: FP,
    is_single_color: ti.i32,
) -> ti.i32:
    base_value: FP = ti.cast((primary_val * 2) + secondary_val, FP) + pp_factor
    combo_val: ti.i32 = ti.cast(ti.floor(base_value * combo_mul), ti.i32)
    fever_val: ti.i32 = ti.cast(ti.floor(base_value * combo_mul * fever_mul), ti.i32)
    body_normal: ti.i32 = body_total - body_fever
    if body_normal < 0:
        body_normal = 0
    score: ti.i32 = body_fever * fever_val + body_normal * combo_val

    combo_span: FP = combo_mul - FP(1.0)
    combo_slope: FP = combo_span / FP(100.0)
    n0 = ti.min(head_len, 32)
    for i in range(n0):
        score += _fg_response_head_score(
            base_value,
            combo_slope,
            fever_mul,
            i,
            _fg_response_bit(fever0, i),
        )
    if head_len > 32:
        n1 = ti.min(head_len, 64)
        for i in range(32, n1):
            score += _fg_response_head_score(
                base_value,
                combo_slope,
                fever_mul,
                i,
                _fg_response_bit(fever1, i - 32),
            )
    if head_len > 64:
        n2 = ti.min(head_len, 96)
        for i in range(64, n2):
            score += _fg_response_head_score(
                base_value,
                combo_slope,
                fever_mul,
                i,
                _fg_response_bit(fever2, i - 64),
            )
    if head_len > 96:
        for i in range(96, head_len):
            score += _fg_response_head_score(
                base_value,
                combo_slope,
                fever_mul,
                i,
                _fg_response_bit(fever3, i - 96),
            )

    great_bits: ti.u32 = great0 | great1 | great2 | great3
    if body_great > 0 or great_bits != ti.u32(0):
        great_head_base: ti.i32 = 0
        if is_single_color != 0:
            great_head_base = (primary_val * 2) + 150
        else:
            great_head_base = (
                ti.cast(ti.floor(ti.cast(primary_val, FP) * FP(4.0 / 3.0)), ti.i32)
                + ti.cast(ti.floor(ti.cast(secondary_val, FP) * FP(2.0 / 3.0)), ti.i32)
                + 150
            )
        great_base: FP = ti.cast(great_head_base, FP)
        great_combo_val: ti.i32 = ti.cast(ti.floor(great_base * combo_mul), ti.i32)
        great_fever_val: ti.i32 = ti.cast(ti.floor(great_base * combo_mul * fever_mul), ti.i32)
        if body_great > 0:
            body_normal_great: ti.i32 = body_great - body_fever_great
            if body_normal_great < 0:
                body_normal_great = 0
            body_normal_penalty: ti.i32 = combo_val - great_combo_val
            if body_normal_penalty < 0:
                body_normal_penalty = 0
            body_fever_penalty: ti.i32 = fever_val - great_fever_val
            if body_fever_penalty < 0:
                body_fever_penalty = 0
            score -= body_normal_great * body_normal_penalty
            score -= body_fever_great * body_fever_penalty

        if great_bits != ti.u32(0):
            for i in range(n0):
                if _fg_response_bit(great0, i) != 0:
                    is_fever: ti.i32 = _fg_response_bit(fever0, i)
                    perfect_val: ti.i32 = _fg_response_head_score(
                        base_value,
                        combo_slope,
                        fever_mul,
                        i,
                        is_fever,
                    )
                    great_val: ti.i32 = _fg_response_head_score(
                        great_base,
                        combo_slope,
                        fever_mul,
                        i,
                        is_fever,
                    )
                    penalty: ti.i32 = perfect_val - great_val
                    if penalty > 0:
                        score -= penalty
            if head_len > 32:
                for i in range(32, ti.min(head_len, 64)):
                    if _fg_response_bit(great1, i - 32) != 0:
                        is_fever: ti.i32 = _fg_response_bit(fever1, i - 32)
                        perfect_val: ti.i32 = _fg_response_head_score(
                            base_value,
                            combo_slope,
                            fever_mul,
                            i,
                            is_fever,
                        )
                        great_val: ti.i32 = _fg_response_head_score(
                            great_base,
                            combo_slope,
                            fever_mul,
                            i,
                            is_fever,
                        )
                        penalty: ti.i32 = perfect_val - great_val
                        if penalty > 0:
                            score -= penalty
            if head_len > 64:
                for i in range(64, ti.min(head_len, 96)):
                    if _fg_response_bit(great2, i - 64) != 0:
                        is_fever: ti.i32 = _fg_response_bit(fever2, i - 64)
                        perfect_val: ti.i32 = _fg_response_head_score(
                            base_value,
                            combo_slope,
                            fever_mul,
                            i,
                            is_fever,
                        )
                        great_val: ti.i32 = _fg_response_head_score(
                            great_base,
                            combo_slope,
                            fever_mul,
                            i,
                            is_fever,
                        )
                        penalty: ti.i32 = perfect_val - great_val
                        if penalty > 0:
                            score -= penalty
            if head_len > 96:
                for i in range(96, head_len):
                    if _fg_response_bit(great3, i - 96) != 0:
                        is_fever: ti.i32 = _fg_response_bit(fever3, i - 96)
                        perfect_val: ti.i32 = _fg_response_head_score(
                            base_value,
                            combo_slope,
                            fever_mul,
                            i,
                            is_fever,
                        )
                        great_val: ti.i32 = _fg_response_head_score(
                            great_base,
                            combo_slope,
                            fever_mul,
                            i,
                            is_fever,
                        )
                        penalty: ti.i32 = perfect_val - great_val
                        if penalty > 0:
                            score -= penalty
    return score


@ti.func
def _fg_response_surface_upper_bound(
    base_value: FP,
    combo_mul: FP,
    fever_mul: FP,
    body_fever: ti.i32,
    body_normal: ti.i32,
    n_hn: ti.i32,
    n_hf: ti.i32,
    sigma_hn: ti.i32,
    sigma_hf: ti.i32,
) -> FP:
    ub_eps = FP(1024.0)
    combo_val = ti.cast(ti.floor(base_value * combo_mul), ti.i32)
    fever_val = ti.cast(ti.floor(base_value * combo_mul * fever_mul), ti.i32)
    body_score = body_fever * fever_val + body_normal * combo_val
    factor = (combo_mul - FP(1.0)) * base_value / FP(100.0)
    head_upper = base_value * (ti.cast(n_hn, FP) + fever_mul * ti.cast(n_hf, FP)) + factor * (
        ti.cast(sigma_hn, FP) + fever_mul * ti.cast(sigma_hf, FP)
    )
    return ti.cast(body_score, FP) + head_upper + ub_eps
