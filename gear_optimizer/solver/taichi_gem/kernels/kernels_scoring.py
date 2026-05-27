"""
Taichi Kernels - Score Calculation and Greedy Optimization.

This module contains score calculation functions and the critical optimize_core_device:
- _calc_body_score: Body notes score (simple multiply)
- _calc_head_factor: Combo ramp factor
- _calc_head_score_*: Head score with fever masks (3 variants)
- calc_score_device: Main score calculation (work-item masks)
- calc_score_with_grid_bits: Score calculation using bitpacked masks
- calc_score_cached_device: Cached score calculation
- optimize_core_device: CRITICAL greedy gem allocation (179 lines)

The optimize_core_device function is the core of the gem optimizer - it evaluates
4 gem options (PP, CM, FM, OV) at each iteration and greedily picks the best.
"""

import taichi as ti

from gear_optimizer.core.parsing import env_flag

from . import kernels_helpers


# Diagnostic toggle: allow A/B between fused and split OV/CM/FM scoring paths.
# Default preserves existing fused behavior.
GPU_HEAD3_FUSION = env_flag("GPU_HEAD3_FUSION", "1")


@ti.func
def _calc_body_score_i32(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    # Match kernels_helpers._calc_body_score semantics exactly (integer truncation per term).
    combo_val = ti.cast(base_value * combo_mul, ti.i32)
    fever_val = ti.cast(base_value * combo_mul * fever_mul, ti.i32)
    return (count_fever * fever_val) + (count_normal * combo_val)


@ti.func
def _calc_head_scores_2_bits(
    head_len: ti.i32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
    base_a: ti.f32,
    factor_a: ti.f32,
    fever_mul_a: ti.f32,
    base_b: ti.f32,
    factor_b: ti.f32,
    fever_mul_b: ti.f32,
) -> ti.types.vector(2, ti.i32):
    s_a: ti.i32 = 0
    s_b: ti.i32 = 0
    fever_delta_a = fever_mul_a - 1.0
    fever_delta_b = fever_mul_b - 1.0

    n0 = ti.min(head_len, 32)
    t: ti.f32 = 1.0
    for i in range(n0):
        is_fever_f = ti.cast((m0 >> ti.u32(i)) & ti.u32(1), ti.f32)

        ramp_a = base_a + (t * factor_a)
        mul_a = 1.0 + fever_delta_a * is_fever_f
        s_a += ti.cast(ramp_a * mul_a, ti.i32)

        ramp_b = base_b + (t * factor_b)
        mul_b = 1.0 + fever_delta_b * is_fever_f
        s_b += ti.cast(ramp_b * mul_b, ti.i32)
        t += 1.0

    if head_len > 32:
        n1 = ti.min(head_len, 64)
        t = 33.0
        for i in range(32, n1):
            is_fever_f = ti.cast((m1 >> ti.u32(i - 32)) & ti.u32(1), ti.f32)

            ramp_a = base_a + (t * factor_a)
            mul_a = 1.0 + fever_delta_a * is_fever_f
            s_a += ti.cast(ramp_a * mul_a, ti.i32)

            ramp_b = base_b + (t * factor_b)
            mul_b = 1.0 + fever_delta_b * is_fever_f
            s_b += ti.cast(ramp_b * mul_b, ti.i32)
            t += 1.0

    if head_len > 64:
        n2 = ti.min(head_len, 96)
        t = 65.0
        for i in range(64, n2):
            is_fever_f = ti.cast((m2 >> ti.u32(i - 64)) & ti.u32(1), ti.f32)

            ramp_a = base_a + (t * factor_a)
            mul_a = 1.0 + fever_delta_a * is_fever_f
            s_a += ti.cast(ramp_a * mul_a, ti.i32)

            ramp_b = base_b + (t * factor_b)
            mul_b = 1.0 + fever_delta_b * is_fever_f
            s_b += ti.cast(ramp_b * mul_b, ti.i32)
            t += 1.0

    if head_len > 96:
        t = 97.0
        for i in range(96, head_len):
            is_fever_f = ti.cast((m3 >> ti.u32(i - 96)) & ti.u32(1), ti.f32)

            ramp_a = base_a + (t * factor_a)
            mul_a = 1.0 + fever_delta_a * is_fever_f
            s_a += ti.cast(ramp_a * mul_a, ti.i32)

            ramp_b = base_b + (t * factor_b)
            mul_b = 1.0 + fever_delta_b * is_fever_f
            s_b += ti.cast(ramp_b * mul_b, ti.i32)
            t += 1.0

    return ti.Vector([s_a, s_b])


@ti.func
def _calc_head_scores_3_bits(
    head_len: ti.i32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
    base_ov: ti.f32,
    factor_ov: ti.f32,
    fever_mul_ov: ti.f32,
    base_cm: ti.f32,
    factor_cm: ti.f32,
    fever_mul_cm: ti.f32,
    base_fm: ti.f32,
    factor_fm: ti.f32,
    fever_mul_fm: ti.f32,
) -> ti.types.vector(3, ti.i32):
    s_ov: ti.i32 = 0
    s_cm: ti.i32 = 0
    s_fm: ti.i32 = 0
    fever_delta_ov = fever_mul_ov - 1.0
    fever_delta_cm = fever_mul_cm - 1.0
    fever_delta_fm = fever_mul_fm - 1.0

    n0 = ti.min(head_len, 32)
    t: ti.f32 = 1.0
    for i in range(n0):
        is_fever_f = ti.cast((m0 >> ti.u32(i)) & ti.u32(1), ti.f32)

        ramp_ov = base_ov + (t * factor_ov)
        mul_ov = 1.0 + fever_delta_ov * is_fever_f
        s_ov += ti.cast(ramp_ov * mul_ov, ti.i32)

        ramp_cm = base_cm + (t * factor_cm)
        mul_cm = 1.0 + fever_delta_cm * is_fever_f
        s_cm += ti.cast(ramp_cm * mul_cm, ti.i32)

        ramp_fm = base_fm + (t * factor_fm)
        mul_fm = 1.0 + fever_delta_fm * is_fever_f
        s_fm += ti.cast(ramp_fm * mul_fm, ti.i32)
        t += 1.0

    if head_len > 32:
        n1 = ti.min(head_len, 64)
        t = 33.0
        for i in range(32, n1):
            is_fever_f = ti.cast((m1 >> ti.u32(i - 32)) & ti.u32(1), ti.f32)

            ramp_ov = base_ov + (t * factor_ov)
            mul_ov = 1.0 + fever_delta_ov * is_fever_f
            s_ov += ti.cast(ramp_ov * mul_ov, ti.i32)

            ramp_cm = base_cm + (t * factor_cm)
            mul_cm = 1.0 + fever_delta_cm * is_fever_f
            s_cm += ti.cast(ramp_cm * mul_cm, ti.i32)

            ramp_fm = base_fm + (t * factor_fm)
            mul_fm = 1.0 + fever_delta_fm * is_fever_f
            s_fm += ti.cast(ramp_fm * mul_fm, ti.i32)
            t += 1.0

    if head_len > 64:
        n2 = ti.min(head_len, 96)
        t = 65.0
        for i in range(64, n2):
            is_fever_f = ti.cast((m2 >> ti.u32(i - 64)) & ti.u32(1), ti.f32)

            ramp_ov = base_ov + (t * factor_ov)
            mul_ov = 1.0 + fever_delta_ov * is_fever_f
            s_ov += ti.cast(ramp_ov * mul_ov, ti.i32)

            ramp_cm = base_cm + (t * factor_cm)
            mul_cm = 1.0 + fever_delta_cm * is_fever_f
            s_cm += ti.cast(ramp_cm * mul_cm, ti.i32)

            ramp_fm = base_fm + (t * factor_fm)
            mul_fm = 1.0 + fever_delta_fm * is_fever_f
            s_fm += ti.cast(ramp_fm * mul_fm, ti.i32)
            t += 1.0

    if head_len > 96:
        t = 97.0
        for i in range(96, head_len):
            is_fever_f = ti.cast((m3 >> ti.u32(i - 96)) & ti.u32(1), ti.f32)

            ramp_ov = base_ov + (t * factor_ov)
            mul_ov = 1.0 + fever_delta_ov * is_fever_f
            s_ov += ti.cast(ramp_ov * mul_ov, ti.i32)

            ramp_cm = base_cm + (t * factor_cm)
            mul_cm = 1.0 + fever_delta_cm * is_fever_f
            s_cm += ti.cast(ramp_cm * mul_cm, ti.i32)

            ramp_fm = base_fm + (t * factor_fm)
            mul_fm = 1.0 + fever_delta_fm * is_fever_f
            s_fm += ti.cast(ramp_fm * mul_fm, ti.i32)
            t += 1.0

    return ti.Vector([s_ov, s_cm, s_fm])


@ti.func
def _calc_head_score_grid(
    base_value: ti.f32,
    factor: ti.f32,
    fever_mul: ti.f32,
    song_slot: ti.i32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
    head_len: ti.i32,
) -> ti.f32:
    """
    Calculate head score using grid-stored fever masks.

    Uses precomputed timeline grid for O(1) mask lookup.

    Args:
        base_value: Base score value
        factor: Combo ramp factor
        fever_mul: Fever multiplier
        song_slot: Song slot in grid (for batch coalescing)
        ft_idx: FT stat index
        ff_idx: FF stat index
        head_len: Number of notes in head

    Returns:
        Head score as float
    """
    m0 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 0]
    m1 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 1]
    m2 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 2]
    m3 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 3]
    scores = _calc_head_scores_2_bits(
        head_len,
        m0,
        m1,
        m2,
        m3,
        base_value,
        factor,
        fever_mul,
        base_value,
        factor,
        fever_mul,
    )
    return ti.cast(scores[0], ti.f32)


@ti.func
def calc_score_cached_device(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
) -> ti.i32:
    """Score calculation using cached grid bitmasks (m0..m3)."""
    return kernels_helpers.calc_score_with_grid_bits(
        base_value,
        combo_mul,
        fever_mul,
        m0,
        m1,
        m2,
        m3,
        head_len,
        count_fever,
        count_normal,
    )


@ti.func
def score_solution_from_gems_preloaded(
    ft: ti.i32,
    ff: ti.i32,
    pp_gems: ti.i32,
    cm_gems: ti.i32,
    fm_gems: ti.i32,
    ov_gems: ti.i32,
    base_pp: ti.i32,
    base_cm: ti.i32,
    base_fm: ti.i32,
    base_p_val: ti.i32,
    base_s_val: ti.i32,
    base_ft_stat: ti.i32,
    base_ff_stat: ti.i32,
    gem_scale_fever: ti.i32,
    is_p_ft: ti.i32,
    is_s_ft: ti.i32,
    is_p_ff: ti.i32,
    is_s_ff: ti.i32,
    is_p_pp: ti.i32,
    is_s_pp: ti.i32,
    is_p_cm: ti.i32,
    is_s_cm: ti.i32,
    is_p_fm: ti.i32,
    is_s_fm: ti.i32,
    is_p_ov: ti.i32,
    is_s_ov: ti.i32,
    song_slot: ti.i32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    GEM_SCALE_NORMAL: ti.i32 = 2
    GEM_SCALE_FEVER: ti.i32 = 3
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    MAX_STAT: ti.i32 = 160

    pp_stat: ti.i32 = ti.min(MAX_STAT, base_pp + (pp_gems * GEM_SCALE_NORMAL))
    cm_stat: ti.i32 = ti.min(MAX_STAT, base_cm + (cm_gems * GEM_SCALE_NORMAL))
    fm_stat: ti.i32 = ti.min(MAX_STAT, base_fm + (fm_gems * GEM_SCALE_FEVER))

    p_val: ti.i32 = (
        base_p_val
        + (ft * GEM_STAT_TO_ELEMENT * is_p_ft)
        + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
        + (pp_gems * GEM_STAT_TO_ELEMENT * is_p_pp)
        + (cm_gems * GEM_STAT_TO_ELEMENT * is_p_cm)
        + (fm_gems * GEM_STAT_TO_ELEMENT * is_p_fm)
        + (ov_gems * ELEMENTAL_GEM_SCALE * is_p_ov)
    )
    s_val: ti.i32 = (
        base_s_val
        + (ft * GEM_STAT_TO_ELEMENT * is_s_ft)
        + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
        + (pp_gems * GEM_STAT_TO_ELEMENT * is_s_pp)
        + (cm_gems * GEM_STAT_TO_ELEMENT * is_s_cm)
        + (fm_gems * GEM_STAT_TO_ELEMENT * is_s_fm)
        + (ov_gems * ELEMENTAL_GEM_SCALE * is_s_ov)
    )

    pp_factor = kernels_helpers.lookup_ref_pp(pp_stat)
    combo_mul = kernels_helpers.lookup_ref_cm(cm_stat)
    fever_mul = kernels_helpers.lookup_ref_fm(fm_stat)
    base_value = ti.cast((p_val * 2) + s_val, ti.f32) + pp_factor

    m0 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 0]
    m1 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 1]
    m2 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 2]
    m3 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 3]

    return calc_score_cached_device(
        base_value,
        combo_mul,
        fever_mul,
        head_len,
        count_fever,
        count_normal,
        m0,
        m1,
        m2,
        m3,
    )


@ti.func
def _semi_exact_upper_bound(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    count_fever: ti.i32,
    count_normal: ti.i32,
    n_hn: ti.i32,
    n_hf: ti.i32,
    sigma_hn: ti.i32,
    sigma_hf: ti.i32,
) -> ti.f32:
    UB_EPS: ti.f32 = 1024.0
    body_score = _calc_body_score_i32(base_value, combo_mul, fever_mul, count_fever, count_normal)
    factor = kernels_helpers._calc_head_factor(base_value, combo_mul)
    head_upper = base_value * (ti.cast(n_hn, ti.f32) + (fever_mul * ti.cast(n_hf, ti.f32))) + factor * (
        ti.cast(sigma_hn, ti.f32) + (fever_mul * ti.cast(sigma_hf, ti.f32))
    )
    return ti.cast(body_score, ti.f32) + head_upper + UB_EPS


@ti.func
def response_score_upper_bound_relaxed(
    budget: ti.i32,
    cur_pp: ti.i32,
    cur_cm: ti.i32,
    cur_fm: ti.i32,
    cur_p_val: ti.i32,
    cur_s_val: ti.i32,
    is_p_pp: ti.i32,
    is_s_pp: ti.i32,
    is_p_cm: ti.i32,
    is_s_cm: ti.i32,
    is_p_fm: ti.i32,
    is_s_fm: ti.i32,
    is_p_ov: ti.i32,
    is_s_ov: ti.i32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.f32:
    GEM_SCALE_NORMAL: ti.i32 = 2
    GEM_SCALE_FEVER: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    pp_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_pp
    pp_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_pp
    cm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_cm
    cm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_cm
    fm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_fm
    fm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_fm
    ov_p_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_p_ov
    ov_s_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_s_ov

    w_pp: ti.i32 = (pp_p_delta << 1) + pp_s_delta
    w_cm: ti.i32 = (cm_p_delta << 1) + cm_s_delta
    w_fm: ti.i32 = (fm_p_delta << 1) + fm_s_delta
    w_ov: ti.i32 = (ov_p_delta << 1) + ov_s_delta
    w_max: ti.i32 = ti.max(ti.max(w_pp, w_cm), ti.max(w_fm, w_ov))

    pp_stat: ti.i32 = ti.min(MAX_STAT, ti.max(0, cur_pp + (budget * GEM_SCALE_NORMAL)))
    cm_stat: ti.i32 = ti.min(MAX_STAT, ti.max(0, cur_cm + (budget * GEM_SCALE_NORMAL)))
    fm_stat: ti.i32 = ti.min(MAX_STAT, ti.max(0, cur_fm + (budget * GEM_SCALE_FEVER)))

    base_lane: ti.i32 = (cur_p_val << 1) + cur_s_val + (budget * w_max)
    base_value: ti.f32 = ti.cast(base_lane, ti.f32) + kernels_helpers.lookup_ref_pp(pp_stat)
    combo_mul: ti.f32 = kernels_helpers.lookup_ref_cm(cm_stat)
    fever_mul: ti.f32 = kernels_helpers.lookup_ref_fm(fm_stat)

    head_len_c: ti.i32 = ti.max(0, ti.min(head_len, 100))
    sigma_hf: ti.i32 = (head_len_c * (head_len_c + 1)) // 2
    body_total: ti.i32 = ti.max(0, count_fever + count_normal)

    return _semi_exact_upper_bound(
        base_value,
        combo_mul,
        fever_mul,
        body_total,
        0,
        0,
        head_len_c,
        0,
        sigma_hf,
    )


@ti.func
def _exact_bound_ub_for_cm_fm(
    budget: ti.i32,
    g_cm: ti.i32,
    g_fm: ti.i32,
    max_pp_gems: ti.i32,
    cur_pp: ti.i32,
    cur_cm: ti.i32,
    cur_fm: ti.i32,
    base_init: ti.i32,
    w_cm: ti.i32,
    w_fm: ti.i32,
    w_ov: ti.i32,
    flags_idx: ti.i32,
    cur_pp_idx: ti.i32,
    delta_pp_vs_ov: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
    n_hn: ti.i32,
    n_hf: ti.i32,
    sigma_hn: ti.i32,
    sigma_hf: ti.i32,
) -> ti.f32:
    """
    Cheap semi-exact upper bound for a fixed (CM gems, FM gems) choice.

    Leaves PP/OV distribution to the precomputed prefix argmax table.
    Used to seed the bounded exact solver without running the 90-step greedy loop.
    """
    GEM_SCALE_NORMAL: ti.i32 = 2
    GEM_SCALE_FEVER: ti.i32 = 3

    ub: ti.f32 = ti.f32(-1.0e30)
    leftover: ti.i32 = budget - g_cm - g_fm
    if leftover >= 0:
        cm_stat: ti.i32 = cur_cm + (g_cm * GEM_SCALE_NORMAL)
        c_mul: ti.f32 = kernels_helpers.lookup_ref_cm(cm_stat)

        fm_stat: ti.i32 = cur_fm + (g_fm * GEM_SCALE_FEVER)
        f_mul: ti.f32 = kernels_helpers.lookup_ref_fm(fm_stat)

        max_pp_here: ti.i32 = max_pp_gems
        if max_pp_here > leftover:
            max_pp_here = leftover

        g_pp_best: ti.i32 = ti.cast(
            kernels_helpers.exact_pp_best_gems_prefix[flags_idx, cur_pp_idx, max_pp_here], ti.i32
        )
        pp_stat: ti.i32 = cur_pp + (g_pp_best * GEM_SCALE_NORMAL)
        best_pp_extra: ti.f32 = ti.cast(g_pp_best * delta_pp_vs_ov, ti.f32) + kernels_helpers.lookup_ref_pp(pp_stat)

        base_linear: ti.i32 = base_init + (g_cm * w_cm) + (g_fm * w_fm) + (leftover * w_ov)
        base_value: ti.f32 = ti.cast(base_linear, ti.f32) + best_pp_extra

        ub = _semi_exact_upper_bound(
            base_value,
            c_mul,
            f_mul,
            count_fever,
            count_normal,
            n_hn,
            n_hf,
            sigma_hn,
            sigma_hf,
        )

    return ub


@ti.func
def _head_mask_coefficients_bits(
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
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
                word = m0
            elif i < 64:
                word = m1
                bit_idx = i - 32
            elif i < 96:
                word = m2
                bit_idx = i - 64
            else:
                word = m3
                bit_idx = i - 96

            is_fever = ti.cast((word >> ti.u32(bit_idx)) & ti.u32(1), ti.i32)
            pos = i + 1
            if is_fever != 0:
                n_hf += 1
                sigma_hf += pos
            else:
                n_hn += 1
                sigma_hn += pos

    return ti.Vector([n_hn, n_hf, sigma_hn, sigma_hf])


@ti.func
def _optimize_core_device_exact_bound_preloaded_bits_impl(
    budget: ti.i32,
    cur_pp: ti.i32,
    cur_cm: ti.i32,
    cur_fm: ti.i32,
    cur_p_val: ti.i32,
    cur_s_val: ti.i32,
    is_p_pp: ti.i32,
    is_s_pp: ti.i32,
    is_p_cm: ti.i32,
    is_s_cm: ti.i32,
    is_p_fm: ti.i32,
    is_s_fm: ti.i32,
    is_p_ov: ti.i32,
    is_s_ov: ti.i32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
    song_slot: ti.i32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
) -> ti.types.vector(7, ti.i32):
    GEM_SCALE_NORMAL: ti.i32 = 2
    GEM_SCALE_FEVER: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    pp_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_pp
    pp_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_pp
    cm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_cm
    cm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_cm
    fm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_fm
    fm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_fm
    ov_p_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_p_ov
    ov_s_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_s_ov

    w_pp: ti.i32 = (pp_p_delta << 1) + pp_s_delta
    w_cm: ti.i32 = (cm_p_delta << 1) + cm_s_delta
    w_fm: ti.i32 = (fm_p_delta << 1) + fm_s_delta
    w_ov: ti.i32 = (ov_p_delta << 1) + ov_s_delta
    base_init: ti.i32 = (cur_p_val << 1) + cur_s_val

    # PP-vs-OV prefix argmax table lookup key (16 flag combos).
    # This makes PP selection O(1) per (CM,FM) pair instead of an inner O(B) scan.
    f_p_pp: ti.i32 = ti.cast(is_p_pp != 0, ti.i32)
    f_s_pp: ti.i32 = ti.cast(is_s_pp != 0, ti.i32)
    f_p_ov: ti.i32 = ti.cast(is_p_ov != 0, ti.i32)
    f_s_ov: ti.i32 = ti.cast(is_s_ov != 0, ti.i32)
    flags_idx: ti.i32 = f_p_pp | (f_s_pp << 1) | (f_p_ov << 2) | (f_s_ov << 3)
    cur_pp_idx: ti.i32 = ti.max(0, ti.min(MAX_STAT, cur_pp))
    delta_pp_vs_ov: ti.i32 = w_pp - w_ov

    allow_pp: ti.i32 = ti.cast((is_p_pp != 0) | (is_s_pp != 0), ti.i32)

    max_pp_gems: ti.i32 = 0
    if allow_pp != 0 and cur_pp < MAX_STAT:
        rem_pp = MAX_STAT - cur_pp
        max_pp_gems = rem_pp // GEM_SCALE_NORMAL
        if rem_pp % GEM_SCALE_NORMAL != 0:
            max_pp_gems += 1

    max_cm_gems: ti.i32 = 0
    if cur_cm < MAX_STAT:
        rem_cm = MAX_STAT - cur_cm
        max_cm_gems = rem_cm // GEM_SCALE_NORMAL
        if rem_cm % GEM_SCALE_NORMAL != 0:
            max_cm_gems += 1

    max_fm_gems: ti.i32 = 0
    if cur_fm < MAX_STAT:
        rem_fm = MAX_STAT - cur_fm
        max_fm_gems = rem_fm // GEM_SCALE_FEVER
        if rem_fm % GEM_SCALE_FEVER != 0:
            max_fm_gems += 1

    if max_pp_gems > budget:
        max_pp_gems = budget
    if max_cm_gems > budget:
        max_cm_gems = budget
    if max_fm_gems > budget:
        max_fm_gems = budget

    n_hn: ti.i32 = 0
    n_hf: ti.i32 = 0
    sigma_hn: ti.i32 = 0
    sigma_hf: ti.i32 = 0
    if song_slot >= 0:
        n_hn = kernels_helpers.grid_N_hn[song_slot, ft_idx, ff_idx]
        n_hf = kernels_helpers.grid_N_hf[song_slot, ft_idx, ff_idx]
        sigma_hn = kernels_helpers.grid_Sigma_hn[song_slot, ft_idx, ff_idx]
        sigma_hf = kernels_helpers.grid_Sigma_hf[song_slot, ft_idx, ff_idx]
    else:
        coeffs = _head_mask_coefficients_bits(m0, m1, m2, m3, head_len)
        n_hn = coeffs[0]
        n_hf = coeffs[1]
        sigma_hn = coeffs[2]
        sigma_hf = coeffs[3]

    # ---------------------------------------------------------------------
    # Incumbent seed (no hints): cheap UB-guided greedy over (CM, FM) counts.
    #
    # The bounded solver's prune effectiveness depends heavily on the starting
    # incumbent score. Historically we ran the full 90-step greedy solver here,
    # which dominates cold exact runtime in the warmstart kernel.
    #
    # Instead, do a tiny greedy walk using the semi-exact upper bound to pick
    # a promising (CM, FM) point, then evaluate that point exactly once to
    # initialize best_score.
    # ---------------------------------------------------------------------
    best_score: ti.i32 = -1
    best_pp: ti.i32 = 0
    best_cm: ti.i32 = 0
    best_fm: ti.i32 = 0
    best_ov: ti.i32 = 0
    best_p: ti.i32 = cur_p_val
    best_s: ti.i32 = cur_s_val

    # Two tie-break variants (prefer CM vs prefer FM) to mitigate UB ties.
    seed_best_cm0: ti.i32 = 0
    seed_best_fm0: ti.i32 = 0
    seed_best_ub0: ti.f32 = _exact_bound_ub_for_cm_fm(
        budget,
        0,
        0,
        max_pp_gems,
        cur_pp,
        cur_cm,
        cur_fm,
        base_init,
        w_cm,
        w_fm,
        w_ov,
        flags_idx,
        cur_pp_idx,
        delta_pp_vs_ov,
        count_fever,
        count_normal,
        n_hn,
        n_hf,
        sigma_hn,
        sigma_hf,
    )
    seed_ub_init: ti.f32 = seed_best_ub0
    seed_cm0: ti.i32 = 0
    seed_fm0: ti.i32 = 0
    step0: ti.i32 = 0
    while step0 < budget:
        can_add_cm = ti.cast((seed_cm0 < max_cm_gems) & ((seed_cm0 + seed_fm0 + 1) <= budget), ti.i32)
        can_add_fm = ti.cast((seed_fm0 < max_fm_gems) & ((seed_cm0 + seed_fm0 + 1) <= budget), ti.i32)
        if can_add_cm == 0 and can_add_fm == 0:
            break

        ub_cm = ti.f32(-1.0e30)
        ub_fm = ti.f32(-1.0e30)
        if can_add_cm != 0:
            ub_cm = _exact_bound_ub_for_cm_fm(
                budget,
                seed_cm0 + 1,
                seed_fm0,
                max_pp_gems,
                cur_pp,
                cur_cm,
                cur_fm,
                base_init,
                w_cm,
                w_fm,
                w_ov,
                flags_idx,
                cur_pp_idx,
                delta_pp_vs_ov,
                count_fever,
                count_normal,
                n_hn,
                n_hf,
                sigma_hn,
                sigma_hf,
            )
        if can_add_fm != 0:
            ub_fm = _exact_bound_ub_for_cm_fm(
                budget,
                seed_cm0,
                seed_fm0 + 1,
                max_pp_gems,
                cur_pp,
                cur_cm,
                cur_fm,
                base_init,
                w_cm,
                w_fm,
                w_ov,
                flags_idx,
                cur_pp_idx,
                delta_pp_vs_ov,
                count_fever,
                count_normal,
                n_hn,
                n_hf,
                sigma_hn,
                sigma_hf,
            )

        # Prefer CM when tied.
        cur_ub = ub_fm
        if ub_cm >= ub_fm:
            seed_cm0 += 1
            cur_ub = ub_cm
        else:
            seed_fm0 += 1

        if cur_ub > seed_best_ub0:
            seed_best_ub0 = cur_ub
            seed_best_cm0 = seed_cm0
            seed_best_fm0 = seed_fm0

        step0 += 1

    seed_best_cm1: ti.i32 = 0
    seed_best_fm1: ti.i32 = 0
    seed_best_ub1: ti.f32 = seed_ub_init
    seed_cm1: ti.i32 = 0
    seed_fm1: ti.i32 = 0
    step1: ti.i32 = 0
    while step1 < budget:
        can_add_cm = ti.cast((seed_cm1 < max_cm_gems) & ((seed_cm1 + seed_fm1 + 1) <= budget), ti.i32)
        can_add_fm = ti.cast((seed_fm1 < max_fm_gems) & ((seed_cm1 + seed_fm1 + 1) <= budget), ti.i32)
        if can_add_cm == 0 and can_add_fm == 0:
            break

        ub_cm = ti.f32(-1.0e30)
        ub_fm = ti.f32(-1.0e30)
        if can_add_cm != 0:
            ub_cm = _exact_bound_ub_for_cm_fm(
                budget,
                seed_cm1 + 1,
                seed_fm1,
                max_pp_gems,
                cur_pp,
                cur_cm,
                cur_fm,
                base_init,
                w_cm,
                w_fm,
                w_ov,
                flags_idx,
                cur_pp_idx,
                delta_pp_vs_ov,
                count_fever,
                count_normal,
                n_hn,
                n_hf,
                sigma_hn,
                sigma_hf,
            )
        if can_add_fm != 0:
            ub_fm = _exact_bound_ub_for_cm_fm(
                budget,
                seed_cm1,
                seed_fm1 + 1,
                max_pp_gems,
                cur_pp,
                cur_cm,
                cur_fm,
                base_init,
                w_cm,
                w_fm,
                w_ov,
                flags_idx,
                cur_pp_idx,
                delta_pp_vs_ov,
                count_fever,
                count_normal,
                n_hn,
                n_hf,
                sigma_hn,
                sigma_hf,
            )

        # Prefer FM when tied.
        cur_ub = ub_cm
        if ub_fm >= ub_cm:
            seed_fm1 += 1
            cur_ub = ub_fm
        else:
            seed_cm1 += 1

        if cur_ub > seed_best_ub1:
            seed_best_ub1 = cur_ub
            seed_best_cm1 = seed_cm1
            seed_best_fm1 = seed_fm1

        step1 += 1

    # Evaluate both seed candidates exactly to initialize best_score.
    # Candidate 0 (prefer CM ties)
    seed_cm = seed_best_cm0
    seed_fm = seed_best_fm0
    for _seed_pass in ti.static(range(2)):
        leftover: ti.i32 = budget - seed_cm - seed_fm
        max_pp_here: ti.i32 = max_pp_gems
        if max_pp_here > leftover:
            max_pp_here = leftover

        g_pp_best: ti.i32 = ti.cast(
            kernels_helpers.exact_pp_best_gems_prefix[flags_idx, cur_pp_idx, max_pp_here],
            ti.i32,
        )
        g_ov: ti.i32 = leftover - g_pp_best

        cm_stat: ti.i32 = cur_cm + (seed_cm * GEM_SCALE_NORMAL)
        fm_stat: ti.i32 = cur_fm + (seed_fm * GEM_SCALE_FEVER)
        c_mul: ti.f32 = kernels_helpers.lookup_ref_cm(cm_stat)
        f_mul: ti.f32 = kernels_helpers.lookup_ref_fm(fm_stat)

        pp_stat: ti.i32 = cur_pp + (g_pp_best * GEM_SCALE_NORMAL)
        best_pp_extra: ti.f32 = ti.cast(g_pp_best * delta_pp_vs_ov, ti.f32) + kernels_helpers.lookup_ref_pp(pp_stat)

        base_linear: ti.i32 = base_init + (seed_cm * w_cm) + (seed_fm * w_fm) + (leftover * w_ov)
        base_value: ti.f32 = ti.cast(base_linear, ti.f32) + best_pp_extra
        score = calc_score_cached_device(
            base_value,
            c_mul,
            f_mul,
            head_len,
            count_fever,
            count_normal,
            m0,
            m1,
            m2,
            m3,
        )

        better = 0
        if score > best_score:
            better = 1
        elif score == best_score:
            if seed_cm < best_cm:
                better = 1
            elif seed_cm == best_cm:
                if seed_fm < best_fm:
                    better = 1
                elif seed_fm == best_fm:
                    if g_pp_best < best_pp:
                        better = 1

        if better != 0:
            best_score = score
            best_pp = g_pp_best
            best_cm = seed_cm
            best_fm = seed_fm
            best_ov = g_ov
            best_p = (
                cur_p_val
                + (g_pp_best * pp_p_delta)
                + (seed_cm * cm_p_delta)
                + (seed_fm * fm_p_delta)
                + (g_ov * ov_p_delta)
            )
            best_s = (
                cur_s_val
                + (g_pp_best * pp_s_delta)
                + (seed_cm * cm_s_delta)
                + (seed_fm * fm_s_delta)
                + (g_ov * ov_s_delta)
            )

        # Candidate 1 (prefer FM ties)
        seed_cm = seed_best_cm1
        seed_fm = seed_best_fm1

    g_cm: ti.i32 = 0
    while g_cm <= max_cm_gems:
        leftover_after_cm: ti.i32 = budget - g_cm
        if leftover_after_cm < 0:
            break

        cm_stat: ti.i32 = cur_cm + (g_cm * GEM_SCALE_NORMAL)
        c_mul: ti.f32 = kernels_helpers.lookup_ref_cm(cm_stat)

        max_fm_here: ti.i32 = max_fm_gems
        if max_fm_here > leftover_after_cm:
            max_fm_here = leftover_after_cm

        g_fm: ti.i32 = 0
        while g_fm <= max_fm_here:
            leftover: ti.i32 = budget - g_cm - g_fm
            if leftover < 0:
                break

            fm_stat: ti.i32 = cur_fm + (g_fm * GEM_SCALE_FEVER)
            f_mul: ti.f32 = kernels_helpers.lookup_ref_fm(fm_stat)

            max_pp_here: ti.i32 = max_pp_gems
            if max_pp_here > leftover:
                max_pp_here = leftover

            g_pp_best: ti.i32 = ti.cast(
                kernels_helpers.exact_pp_best_gems_prefix[flags_idx, cur_pp_idx, max_pp_here],
                ti.i32,
            )
            pp_stat: ti.i32 = cur_pp + (g_pp_best * GEM_SCALE_NORMAL)
            best_pp_extra: ti.f32 = ti.cast(g_pp_best * delta_pp_vs_ov, ti.f32) + kernels_helpers.lookup_ref_pp(pp_stat)

            g_ov: ti.i32 = leftover - g_pp_best
            base_linear: ti.i32 = base_init + (g_cm * w_cm) + (g_fm * w_fm) + (leftover * w_ov)
            base_value: ti.f32 = ti.cast(base_linear, ti.f32) + best_pp_extra
            ub = _semi_exact_upper_bound(
                base_value,
                c_mul,
                f_mul,
                count_fever,
                count_normal,
                n_hn,
                n_hf,
                sigma_hn,
                sigma_hf,
            )
            if ub > ti.cast(best_score, ti.f32):
                score = calc_score_cached_device(
                    base_value,
                    c_mul,
                    f_mul,
                    head_len,
                    count_fever,
                    count_normal,
                    m0,
                    m1,
                    m2,
                    m3,
                )
                if score > best_score or (
                    score == best_score
                    and (
                        (g_cm < best_cm)
                        or (g_cm == best_cm and ((g_fm < best_fm) or (g_fm == best_fm and g_pp_best < best_pp)))
                    )
                ):
                    best_score = score
                    best_pp = g_pp_best
                    best_cm = g_cm
                    best_fm = g_fm
                    best_ov = g_ov
                    best_p = (
                        cur_p_val
                        + (g_pp_best * pp_p_delta)
                        + (g_cm * cm_p_delta)
                        + (g_fm * fm_p_delta)
                        + (g_ov * ov_p_delta)
                    )
                    best_s = (
                        cur_s_val
                        + (g_pp_best * pp_s_delta)
                        + (g_cm * cm_s_delta)
                        + (g_fm * fm_s_delta)
                        + (g_ov * ov_s_delta)
                    )

            g_fm += 1
        g_cm += 1

    return ti.Vector([best_score, best_pp, best_cm, best_fm, best_ov, best_p, best_s])


@ti.func
def optimize_core_device_exact_bound(
    budget: ti.i32,
    cur_pp: ti.i32,
    cur_cm: ti.i32,
    cur_fm: ti.i32,
    cur_p_val: ti.i32,
    cur_s_val: ti.i32,
    is_p_pp: ti.i32,
    is_s_pp: ti.i32,
    is_p_cm: ti.i32,
    is_s_cm: ti.i32,
    is_p_fm: ti.i32,
    is_s_fm: ti.i32,
    is_p_ov: ti.i32,
    is_s_ov: ti.i32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
    song_slot: ti.i32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
) -> ti.types.vector(7, ti.i32):
    frontier_count = ti.cast(kernels_helpers.grid_frontier_count[song_slot, ft_idx, ff_idx], ti.i32)
    result_vec = ti.Vector([ti.i32(-1), ti.i32(0), ti.i32(0), ti.i32(0), ti.i32(0), ti.i32(0), ti.i32(0)])
    variant_idx = ti.i32(0)
    while variant_idx < frontier_count:
        frontier = kernels_helpers.read_timeline_frontier_variant(song_slot, ft_idx, ff_idx, variant_idx)
        cand_vec = _optimize_core_device_exact_bound_preloaded_bits_impl(
            budget,
            cur_pp,
            cur_cm,
            cur_fm,
            cur_p_val,
            cur_s_val,
            is_p_pp,
            is_s_pp,
            is_p_cm,
            is_s_cm,
            is_p_fm,
            is_s_fm,
            is_p_ov,
            is_s_ov,
            frontier.m0,
            frontier.m1,
            frontier.m2,
            frontier.m3,
            head_len,
            frontier.body_fever,
            frontier.body_normal,
            -1,
            0,
            0,
        )
        if cand_vec[0] > result_vec[0]:
            result_vec = cand_vec
        variant_idx += 1
    return result_vec


@ti.func
def optimize_core_device_exact_bound_preloaded_bits(
    budget: ti.i32,
    cur_pp: ti.i32,
    cur_cm: ti.i32,
    cur_fm: ti.i32,
    cur_p_val: ti.i32,
    cur_s_val: ti.i32,
    is_p_pp: ti.i32,
    is_s_pp: ti.i32,
    is_p_cm: ti.i32,
    is_s_cm: ti.i32,
    is_p_fm: ti.i32,
    is_s_fm: ti.i32,
    is_p_ov: ti.i32,
    is_s_ov: ti.i32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.types.vector(7, ti.i32):
    return _optimize_core_device_exact_bound_preloaded_bits_impl(
        budget,
        cur_pp,
        cur_cm,
        cur_fm,
        cur_p_val,
        cur_s_val,
        is_p_pp,
        is_s_pp,
        is_p_cm,
        is_s_cm,
        is_p_fm,
        is_s_fm,
        is_p_ov,
        is_s_ov,
        m0,
        m1,
        m2,
        m3,
        head_len,
        count_fever,
        count_normal,
        -1,
        0,
        0,
    )
