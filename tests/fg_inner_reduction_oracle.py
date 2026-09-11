"""Pre-reduction two-pass scorers, frozen as test-only parity oracles.

The floor primitives are deliberately shared: the reduction must not alter them.
"""

import numpy as np
import taichi as ti

from gear_optimizer.core.jit_setup import jit
from gear_optimizer.solver.taichi_gem.force_greats.response_inner_kernels import (
    FP,
    _fg_response_bit,
    _fg_response_head_score,
)


@ti.func
def legacy_fg_score_device(
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
        great_head_base: ti.i32 = (
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


@jit(nopython=True, cache=True)
def legacy_fg_score_native_f64(
    surface_words,
    sr,
    body_fever,
    body_great,
    body_fever_great,
    head_len,
    body_total,
    primary_val,
    secondary_val,
    pp_factor,
    combo_mul,
    fever_mul,
):
    """f64 CPU port of ``_fg_response_score_device``: exact score of one surface for a fixed
    (gem-allocated) stat line. Same op order / per-term ``floor`` / i32 accumulation as the
    GPU device function, run in CPU doubles (no MoltenVK shaderFloat64 needed)."""
    base_value = float((primary_val * 2) + secondary_val) + pp_factor
    combo_val = int(np.floor(base_value * combo_mul))
    fever_val = int(np.floor(base_value * combo_mul * fever_mul))
    body_normal = body_total - body_fever
    if body_normal < 0:
        body_normal = 0
    score = body_fever * fever_val + body_normal * combo_val
    combo_slope = (combo_mul - 1.0) / 100.0

    for i in range(head_len):
        wi = i >> 5
        b = i & 31
        is_fever = (int(surface_words[sr, wi]) >> b) & 1
        scaling = combo_slope * float(i + 1) + 1.0
        if is_fever != 0:
            score += int(np.floor(base_value * scaling * fever_mul))
        else:
            score += int(np.floor(base_value * scaling))

    great_or = (
        int(surface_words[sr, 4]) | int(surface_words[sr, 5]) | int(surface_words[sr, 6]) | int(surface_words[sr, 7])
    )
    if body_great > 0 or great_or != 0:
        great_head_base = (
            int(np.floor(float(primary_val) * (4.0 / 3.0))) + int(np.floor(float(secondary_val) * (2.0 / 3.0))) + 150
        )
        great_base = float(great_head_base)
        great_combo_val = int(np.floor(great_base * combo_mul))
        great_fever_val = int(np.floor(great_base * combo_mul * fever_mul))
        if body_great > 0:
            body_normal_great = body_great - body_fever_great
            if body_normal_great < 0:
                body_normal_great = 0
            body_normal_penalty = combo_val - great_combo_val
            if body_normal_penalty < 0:
                body_normal_penalty = 0
            body_fever_penalty = fever_val - great_fever_val
            if body_fever_penalty < 0:
                body_fever_penalty = 0
            score -= body_normal_great * body_normal_penalty
            score -= body_fever_great * body_fever_penalty
        if great_or != 0:
            for i in range(head_len):
                wi = i >> 5
                b = i & 31
                if ((int(surface_words[sr, 4 + wi]) >> b) & 1) != 0:
                    is_fever = (int(surface_words[sr, wi]) >> b) & 1
                    scaling = combo_slope * float(i + 1) + 1.0
                    if is_fever != 0:
                        perfect_val = int(np.floor(base_value * scaling * fever_mul))
                        great_val = int(np.floor(great_base * scaling * fever_mul))
                    else:
                        perfect_val = int(np.floor(base_value * scaling))
                        great_val = int(np.floor(great_base * scaling))
                    penalty = perfect_val - great_val
                    if penalty > 0:
                        score -= penalty
    return score
