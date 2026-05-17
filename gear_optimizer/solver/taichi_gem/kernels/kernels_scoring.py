"""
Taichi Kernels - Score Calculation and Greedy Optimization.

This module contains score calculation functions and the critical optimize_core_device:
- _calc_body_score: Body notes score (simple multiply)
- _calc_head_factor: Combo ramp factor
- _calc_head_score_*: Head score with fever masks (3 variants)
- calc_score_device: Main score calculation (work-item masks)
- calc_score_with_grid: Score calculation using grid-stored masks
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
def local_search_from_hint(
    hint_pp: ti.i32,
    hint_cm: ti.i32,
    hint_fm: ti.i32,
    hint_ov: ti.i32,
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
    """
    Local search refinement starting from a warm-start hint.

    Instead of the 90-iteration greedy loop, we start at the hint allocation
    and iteratively try swapping gems (±1) to find a better score.

    Args:
        hint_*: Starting allocation from parent genome
        budget: Total gem budget (hint values should sum to this)
        cur_*: Base stat values before gems
        is_*: Color contribution flags
        head_len, count_*: Song structure parameters
        song_slot, ft_idx, ff_idx: Grid lookup indices

    Returns:
        Vector of [score, gems_pp, gems_cm, gems_fm, gems_ov, p_val, s_val]
    """
    # Import constants from constants.py at compile time
    # Note: These are hardcoded here for GPU kernel compilation
    GEM_SCALE_NORMAL: ti.i32 = 2  # gear_optimizer.core.constants.GEM_SCALE_NORMAL
    GEM_SCALE_FEVER: ti.i32 = 3  # gear_optimizer.core.constants.GEM_SCALE_FEVER
    ELEMENTAL_GEM_SCALE: ti.i32 = 6  # gear_optimizer.core.constants.ELEMENTAL_GEM_SCALE
    GEM_STAT_TO_ELEMENT: ti.i32 = 3  # gear_optimizer.core.constants.GEM_STAT_TO_ELEMENT_SCALE
    MAX_STAT: ti.i32 = 160  # gear_optimizer.core.constants.MAX_STAT_INDEX
    MAX_ITER: ti.i32 = 5  # gear_optimizer.core.constants.LOCAL_SEARCH_MAX_ITERATIONS

    # Load cached bitmasks once
    m0 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 0]
    m1 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 1]
    m2 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 2]
    m3 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 3]

    # Elemental contribution deltas per gem (0/1 is_* flags).
    pp_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_pp
    pp_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_pp
    cm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_cm
    cm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_cm
    fm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_fm
    fm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_fm
    ov_p_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_p_ov
    ov_s_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_s_ov

    # Clamp hint to valid range (defensive)
    gems_pp: ti.i32 = ti.max(0, hint_pp)
    gems_cm: ti.i32 = ti.max(0, hint_cm)
    gems_fm: ti.i32 = ti.max(0, hint_fm)
    gems_ov: ti.i32 = ti.max(0, hint_ov)

    # Ensure hint sums to budget - adjust ov if needed
    hint_sum: ti.i32 = gems_pp + gems_cm + gems_fm + gems_ov
    if hint_sum != budget:
        gems_ov = budget - gems_pp - gems_cm - gems_fm
        if gems_ov < 0:
            # Hint is invalid, fall back to all OV (will improve via local search)
            gems_pp = 0
            gems_cm = 0
            gems_fm = 0
            gems_ov = budget

    # Clamp to stat caps
    max_pp_gems: ti.i32 = (MAX_STAT - cur_pp) // GEM_SCALE_NORMAL
    max_cm_gems: ti.i32 = (MAX_STAT - cur_cm) // GEM_SCALE_NORMAL
    max_fm_gems: ti.i32 = (MAX_STAT - cur_fm) // GEM_SCALE_FEVER
    gems_pp = ti.min(gems_pp, max_pp_gems)
    gems_cm = ti.min(gems_cm, max_cm_gems)
    gems_fm = ti.min(gems_fm, max_fm_gems)
    # Recalculate ov after clamping
    gems_ov = budget - gems_pp - gems_cm - gems_fm

    # Calculate current stats from hint allocation
    pp: ti.i32 = cur_pp + gems_pp * GEM_SCALE_NORMAL
    cm: ti.i32 = cur_cm + gems_cm * GEM_SCALE_NORMAL
    fm: ti.i32 = cur_fm + gems_fm * GEM_SCALE_FEVER
    p_val: ti.i32 = (
        cur_p_val + (gems_pp * pp_p_delta) + (gems_cm * cm_p_delta) + (gems_fm * fm_p_delta) + (gems_ov * ov_p_delta)
    )
    s_val: ti.i32 = (
        cur_s_val + (gems_pp * pp_s_delta) + (gems_cm * cm_s_delta) + (gems_fm * fm_s_delta) + (gems_ov * ov_s_delta)
    )

    # Calculate initial score
    pp_factor = kernels_helpers.lookup_ref_pp(pp)
    c_mul = kernels_helpers.lookup_ref_cm(cm)
    f_mul = kernels_helpers.lookup_ref_fm(fm)
    base_value: ti.f32 = ti.cast((p_val * 2) + s_val, ti.f32) + pp_factor
    best_score: ti.i32 = kernels_helpers.calc_score_with_grid_bits(
        base_value, c_mul, f_mul, m0, m1, m2, m3, head_len, count_fever, count_normal
    )

    # CM plateau escape: due to discrete multiplier breakpoints, moving 1 gem into CM may not
    # improve score even when moving a small streak would. When the hint has CM=0, try shifting
    # up to K OV gems into CM in a single evaluation to cross breakpoints cheaply.
    CM_JUMP_MAX: ti.i32 = 10  # gear_optimizer.core.constants.CM_LOOKAHEAD_MAX
    allow_cm: ti.i32 = ti.cast((cm < MAX_STAT) & ((cm <= 50) | (is_p_cm != 0) | (is_s_cm != 0)), ti.i32)
    if allow_cm != 0 and gems_cm == 0 and gems_ov > 1:
        max_k: ti.i32 = gems_ov
        max_k_by_cap: ti.i32 = (MAX_STAT - cm) // GEM_SCALE_NORMAL
        if max_k > max_k_by_cap:
            max_k = max_k_by_cap
        if max_k > CM_JUMP_MAX:
            max_k = CM_JUMP_MAX

        best_k: ti.i32 = 0
        best_p_val: ti.i32 = p_val
        best_s_val: ti.i32 = s_val
        best_cm_stat: ti.i32 = cm
        best_c_mul: ti.f32 = c_mul

        k: ti.i32 = 2
        while k <= max_k:
            cm_stat_k: ti.i32 = cm + (k * GEM_SCALE_NORMAL)
            p_val_k: ti.i32 = p_val + (k * (cm_p_delta - ov_p_delta))
            s_val_k: ti.i32 = s_val + (k * (cm_s_delta - ov_s_delta))
            c_mul_k: ti.f32 = kernels_helpers.lookup_ref_cm(cm_stat_k)
            base_k: ti.f32 = ti.cast((p_val_k * 2) + s_val_k, ti.f32) + pp_factor
            score_k: ti.i32 = kernels_helpers.calc_score_with_grid_bits(
                base_k, c_mul_k, f_mul, m0, m1, m2, m3, head_len, count_fever, count_normal
            )
            if score_k > best_score:
                best_score = score_k
                best_k = k
                best_p_val = p_val_k
                best_s_val = s_val_k
                best_cm_stat = cm_stat_k
                best_c_mul = c_mul_k
            k += 1

        if best_k > 0:
            gems_cm += best_k
            gems_ov -= best_k
            cm = best_cm_stat
            p_val = best_p_val
            s_val = best_s_val
            c_mul = best_c_mul
            base_value = ti.cast((p_val * 2) + s_val, ti.f32) + pp_factor

    # Delta tables for swap search (index: 0=PP,1=CM,2=FM,3=OV).
    p_delta = ti.Vector([pp_p_delta, cm_p_delta, fm_p_delta, ov_p_delta])
    s_delta = ti.Vector([pp_s_delta, cm_s_delta, fm_s_delta, ov_s_delta])
    pp_stat_delta = ti.Vector([GEM_SCALE_NORMAL, 0, 0, 0])
    cm_stat_delta = ti.Vector([0, GEM_SCALE_NORMAL, 0, 0])
    fm_stat_delta = ti.Vector([0, 0, GEM_SCALE_FEVER, 0])

    # Local search: try swapping 1 gem between types
    # Gem types: 0=PP, 1=CM, 2=FM, 3=OV
    # Each iteration: for each pair (remove, add), try swapping
    iteration: ti.i32 = 0
    improved: ti.i32 = 1

    while improved != 0 and iteration < MAX_ITER:
        improved = 0
        iteration += 1

        # Try all 12 swap combinations (4 remove × 3 add, excluding same type).
        # Unroll the small swap loops to reduce per-combo overhead.
        for remove_type in range(4):
            for add_type in range(4):
                if remove_type == add_type:
                    continue

                # Check if swap is valid.
                if remove_type == 0 and gems_pp <= 0:
                    continue
                if remove_type == 1 and gems_cm <= 0:
                    continue
                if remove_type == 2 and gems_fm <= 0:
                    continue
                if remove_type == 3 and gems_ov <= 0:
                    continue

                if add_type == 0 and pp + GEM_SCALE_NORMAL > MAX_STAT:
                    continue
                if add_type == 1 and cm + GEM_SCALE_NORMAL > MAX_STAT:
                    continue
                if add_type == 2 and fm + GEM_SCALE_FEVER > MAX_STAT:
                    continue

                # Compute new stats incrementally (avoid rebuilding from cur_* each candidate).
                new_pp_stat: ti.i32 = pp + pp_stat_delta[add_type] - pp_stat_delta[remove_type]
                new_cm_stat: ti.i32 = cm + cm_stat_delta[add_type] - cm_stat_delta[remove_type]
                new_fm_stat: ti.i32 = fm + fm_stat_delta[add_type] - fm_stat_delta[remove_type]
                new_p_val: ti.i32 = p_val + p_delta[add_type] - p_delta[remove_type]
                new_s_val: ti.i32 = s_val + s_delta[add_type] - s_delta[remove_type]

                new_pp_factor = pp_factor
                new_c_mul = c_mul
                new_f_mul = f_mul
                if remove_type == 0 or add_type == 0:
                    new_pp_factor = kernels_helpers.lookup_ref_pp(new_pp_stat)
                if remove_type == 1 or add_type == 1:
                    new_c_mul = kernels_helpers.lookup_ref_cm(new_cm_stat)
                if remove_type == 2 or add_type == 2:
                    new_f_mul = kernels_helpers.lookup_ref_fm(new_fm_stat)
                new_base: ti.f32 = ti.cast((new_p_val * 2) + new_s_val, ti.f32) + new_pp_factor
                new_score: ti.i32 = kernels_helpers.calc_score_with_grid_bits(
                    new_base, new_c_mul, new_f_mul, m0, m1, m2, m3, head_len, count_fever, count_normal
                )

                if new_score > best_score:
                    best_score = new_score
                    if remove_type == 0:
                        gems_pp -= 1
                    elif remove_type == 1:
                        gems_cm -= 1
                    elif remove_type == 2:
                        gems_fm -= 1
                    else:
                        gems_ov -= 1

                    if add_type == 0:
                        gems_pp += 1
                    elif add_type == 1:
                        gems_cm += 1
                    elif add_type == 2:
                        gems_fm += 1
                    else:
                        gems_ov += 1
                    pp = new_pp_stat
                    cm = new_cm_stat
                    fm = new_fm_stat
                    p_val = new_p_val
                    s_val = new_s_val
                    pp_factor = new_pp_factor
                    c_mul = new_c_mul
                    f_mul = new_f_mul
                    base_value = new_base
                    improved = 1

    return ti.Vector([best_score, gems_pp, gems_cm, gems_fm, gems_ov, p_val, s_val])


@ti.func
def _optimize_core_device_impl(
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
    pre_m0: ti.u32,
    pre_m1: ti.u32,
    pre_m2: ti.u32,
    pre_m3: ti.u32,
    use_preloaded_bits: ti.i32,
) -> ti.types.vector(7, ti.i32):
    """
    CRITICAL FUNCTION - GPU port of optimize_core_jit (scoring_core.py:99-278).

    Greedy gem allocation: at each iteration, evaluates 4 options:
    - PP gem (Perfect Points): +2 PP stat, +3 to primary/secondary elemental
    - CM gem (Combo Multiplier): +2 CM stat, +3 to primary/secondary elemental
    - FM gem (Fever Multiplier): +3 FM stat, +3 to primary/secondary elemental
    - OV gem (Overflow/Elemental): +6 to primary/secondary elemental only

    Picks the option that maximizes score. Repeats until budget exhausted.

    Special case: PP tie-breaker with lookahead (up to 8 iterations)
    If OV wins a tie but PP would break the tie soon, start investing in PP.

    Args:
        budget: Number of gems to allocate
        cur_pp, cur_cm, cur_fm: Current stat values
        cur_p_val, cur_s_val: Current primary/secondary elemental values
        is_p_*, is_s_*: Color contribution flags (0/1)
        head_len: Number of notes in head
        count_fever, count_normal: Body note counts
        song_slot, ft_idx, ff_idx: Grid indices for bitmask load

    Returns:
        Vector of [score, gems_pp, gems_cm, gems_fm, gems_ov, p_val, s_val]
    """
    # Constants (matching constants.py)
    # Note: These are hardcoded here for GPU kernel compilation
    GEM_SCALE_NORMAL: ti.i32 = 2  # gear_optimizer.core.constants.GEM_SCALE_NORMAL
    GEM_SCALE_FEVER: ti.i32 = 3  # gear_optimizer.core.constants.GEM_SCALE_FEVER
    ELEMENTAL_GEM_SCALE: ti.i32 = 6  # gear_optimizer.core.constants.ELEMENTAL_GEM_SCALE
    GEM_STAT_TO_ELEMENT: ti.i32 = 3  # gear_optimizer.core.constants.GEM_STAT_TO_ELEMENT_SCALE
    MAX_STAT: ti.i32 = 160  # gear_optimizer.core.constants.MAX_STAT_INDEX
    m0: ti.u32 = ti.u32(0)
    m1: ti.u32 = ti.u32(0)
    m2: ti.u32 = ti.u32(0)
    m3: ti.u32 = ti.u32(0)
    if use_preloaded_bits != 0:
        m0 = pre_m0
        m1 = pre_m1
        m2 = pre_m2
        m3 = pre_m3
    else:
        # Cache bitpacked head mask once per evaluation to avoid repeated global loads.
        m0 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 0]
        m1 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 1]
        m2 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 2]
        m3 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 3]

    gems_pp: ti.i32 = 0
    gems_cm: ti.i32 = 0
    gems_fm: ti.i32 = 0
    gems_ov: ti.i32 = 0
    remaining: ti.i32 = budget
    PP_TIE_LOOKAHEAD_MAX: ti.i32 = 8  # gear_optimizer.core.constants.PP_TIE_LOOKAHEAD_MAX
    CM_LOOKAHEAD_MAX: ti.i32 = 10  # gear_optimizer.core.constants.CM_LOOKAHEAD_MAX
    allow_pp: ti.i32 = is_p_pp | is_s_pp

    # Precompute elemental deltas (avoid repeated multiplies in the inner loop).
    pp_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_pp
    pp_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_pp
    cm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_cm
    cm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_cm
    fm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_fm
    fm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_fm
    ov_p_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_p_ov
    ov_s_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_s_ov

    # Mutable state
    pp: ti.i32 = cur_pp
    cm: ti.i32 = cur_cm
    fm: ti.i32 = cur_fm
    p_val: ti.i32 = cur_p_val
    s_val: ti.i32 = cur_s_val

    # Precompute current multipliers once; update incrementally when the corresponding stat changes.
    c_mul_cur: ti.f32 = kernels_helpers.lookup_ref_cm(cm)
    f_mul_cur: ti.f32 = kernels_helpers.lookup_ref_fm(fm)
    pp_factor_cur: ti.f32 = kernels_helpers.lookup_ref_pp(pp)

    best_final_score: ti.i32 = 0

    # Seed with the current stats score so budget=0 returns a correct value.
    base_value0: ti.f32 = ti.cast((p_val * 2) + s_val, ti.f32) + pp_factor_cur
    factor0: ti.f32 = kernels_helpers._calc_head_factor(base_value0, c_mul_cur)
    head0: ti.i32 = ti.cast(
        kernels_helpers._calc_head_score_bits(base_value0, factor0, f_mul_cur, m0, m1, m2, m3, head_len),
        ti.i32,
    )
    best_final_score = _calc_body_score_i32(base_value0, c_mul_cur, f_mul_cur, count_fever, count_normal) + head0

    while remaining > 0:
        # Evaluate each "pick 1 gem now, fill the rest with OV" option.
        # remaining > 0 here, so (remaining - 1) is always non-negative.
        fill_bonus: ti.i32 = (remaining - 1) * ELEMENTAL_GEM_SCALE
        fill_p: ti.i32 = fill_bonus * is_p_ov
        fill_s: ti.i32 = fill_bonus * is_s_ov
        base_p: ti.i32 = p_val + fill_p
        base_s: ti.i32 = s_val + fill_s

        # Defaults: unchanged from current (used by Apply and PP lookahead).
        c_mul_next: ti.f32 = c_mul_cur
        f_mul_next: ti.f32 = f_mul_cur
        pp_factor_next: ti.f32 = pp_factor_cur
        best_score: ti.i32 = 0
        best_opt: ti.i32 = 3
        pp_score: ti.i32 = -1

        # Optimized path: cached grid bitmasks.
        t_p_ov: ti.i32 = base_p + ov_p_delta
        t_s_ov: ti.i32 = base_s + ov_s_delta
        base_ov: ti.f32 = ti.cast((t_p_ov * 2) + t_s_ov, ti.f32) + pp_factor_cur
        factor_ov: ti.f32 = kernels_helpers._calc_head_factor(base_ov, c_mul_cur)

        do_pp: ti.i32 = 0
        do_cm: ti.i32 = 0
        do_fm: ti.i32 = 0

        if allow_pp != 0 or cm < MAX_STAT or fm < MAX_STAT:
            # Always fuse OV/CM/FM head loop; PP stays separate.
            # 4-way fusion (OV/PP/CM/FM) was slower on Vulkan due to register pressure.
            do_pp = 1 if (allow_pp != 0 and pp < MAX_STAT) else 0
            do_cm = 1 if (cm < MAX_STAT and (cm <= 50 or is_p_cm or is_s_cm)) else 0
            do_fm = 1 if (fm < MAX_STAT) else 0

            best_score: ti.i32 = -1
            best_opt = 3

            if do_cm != 0 and do_fm != 0:
                t_p_cm: ti.i32 = base_p + cm_p_delta
                t_s_cm: ti.i32 = base_s + cm_s_delta
                base_cm: ti.f32 = ti.cast((t_p_cm * 2) + t_s_cm, ti.f32) + pp_factor_cur
                c_mul_cm: ti.f32 = kernels_helpers.lookup_ref_cm(cm + GEM_SCALE_NORMAL)
                factor_cm: ti.f32 = kernels_helpers._calc_head_factor(base_cm, c_mul_cm)

                t_p_fm: ti.i32 = base_p + fm_p_delta
                t_s_fm: ti.i32 = base_s + fm_s_delta
                base_fm: ti.f32 = ti.cast((t_p_fm * 2) + t_s_fm, ti.f32) + pp_factor_cur
                factor_fm: ti.f32 = kernels_helpers._calc_head_factor(base_fm, c_mul_cur)
                f_mul_fm: ti.f32 = kernels_helpers.lookup_ref_fm(fm + GEM_SCALE_FEVER)

                score_ov: ti.i32 = 0
                score_cm: ti.i32 = 0
                score_fm: ti.i32 = 0
                if ti.static(GPU_HEAD3_FUSION):
                    head3 = _calc_head_scores_3_bits(
                        head_len,
                        m0,
                        m1,
                        m2,
                        m3,
                        base_ov,
                        factor_ov,
                        f_mul_cur,
                        base_cm,
                        factor_cm,
                        f_mul_cur,
                        base_fm,
                        factor_fm,
                        f_mul_fm,
                    )

                    score_ov = _calc_body_score_i32(base_ov, c_mul_cur, f_mul_cur, count_fever, count_normal) + head3[0]
                    score_cm = _calc_body_score_i32(base_cm, c_mul_cm, f_mul_cur, count_fever, count_normal) + head3[1]
                    score_fm = _calc_body_score_i32(base_fm, c_mul_cur, f_mul_fm, count_fever, count_normal) + head3[2]
                else:
                    # Split evaluation for A/B profiling: lower peak live state, more total ALU work.
                    head_ov = ti.cast(
                        kernels_helpers._calc_head_score_bits(base_ov, factor_ov, f_mul_cur, m0, m1, m2, m3, head_len),
                        ti.i32,
                    )
                    head_cm = ti.cast(
                        kernels_helpers._calc_head_score_bits(base_cm, factor_cm, f_mul_cur, m0, m1, m2, m3, head_len),
                        ti.i32,
                    )
                    head_fm = ti.cast(
                        kernels_helpers._calc_head_score_bits(base_fm, factor_fm, f_mul_fm, m0, m1, m2, m3, head_len),
                        ti.i32,
                    )
                    score_ov = _calc_body_score_i32(base_ov, c_mul_cur, f_mul_cur, count_fever, count_normal) + head_ov
                    score_cm = _calc_body_score_i32(base_cm, c_mul_cm, f_mul_cur, count_fever, count_normal) + head_cm
                    score_fm = _calc_body_score_i32(base_fm, c_mul_cur, f_mul_fm, count_fever, count_normal) + head_fm

                best_score = score_ov
                best_opt = 3
                if score_cm > best_score:
                    best_score = score_cm
                    best_opt = 1
                    c_mul_next = c_mul_cm
                if score_fm > best_score:
                    best_score = score_fm
                    best_opt = 2
                    f_mul_next = f_mul_fm
            elif do_cm != 0:
                t_p_cm = base_p + cm_p_delta
                t_s_cm = base_s + cm_s_delta
                base_cm = ti.cast((t_p_cm * 2) + t_s_cm, ti.f32) + pp_factor_cur
                c_mul_cm = kernels_helpers.lookup_ref_cm(cm + GEM_SCALE_NORMAL)
                factor_cm = kernels_helpers._calc_head_factor(base_cm, c_mul_cm)

                head2 = _calc_head_scores_2_bits(
                    head_len, m0, m1, m2, m3, base_ov, factor_ov, f_mul_cur, base_cm, factor_cm, f_mul_cur
                )
                score_ov = _calc_body_score_i32(base_ov, c_mul_cur, f_mul_cur, count_fever, count_normal) + head2[0]
                score_cm = _calc_body_score_i32(base_cm, c_mul_cm, f_mul_cur, count_fever, count_normal) + head2[1]

                best_score = score_ov
                best_opt = 3
                if score_cm > best_score:
                    best_score = score_cm
                    best_opt = 1
                    c_mul_next = c_mul_cm
            elif do_fm != 0:
                t_p_fm: ti.i32 = base_p + fm_p_delta
                t_s_fm: ti.i32 = base_s + fm_s_delta
                base_fm: ti.f32 = ti.cast((t_p_fm * 2) + t_s_fm, ti.f32) + pp_factor_cur
                factor_fm: ti.f32 = kernels_helpers._calc_head_factor(base_fm, c_mul_cur)
                f_mul_fm: ti.f32 = kernels_helpers.lookup_ref_fm(fm + GEM_SCALE_FEVER)

                head2 = _calc_head_scores_2_bits(
                    head_len, m0, m1, m2, m3, base_ov, factor_ov, f_mul_cur, base_fm, factor_fm, f_mul_fm
                )
                score_ov = _calc_body_score_i32(base_ov, c_mul_cur, f_mul_cur, count_fever, count_normal) + head2[0]
                score_fm = _calc_body_score_i32(base_fm, c_mul_cur, f_mul_fm, count_fever, count_normal) + head2[1]

                best_score = score_ov
                best_opt = 3
                if score_fm > best_score:
                    best_score = score_fm
                    best_opt = 2
                    f_mul_next = f_mul_fm
            else:
                best_score = calc_score_cached_device(
                    base_ov, c_mul_cur, f_mul_cur, head_len, count_fever, count_normal, m0, m1, m2, m3
                )
                best_opt = 3

            if do_pp != 0:
                t_p_pp: ti.i32 = base_p + pp_p_delta
                t_s_pp: ti.i32 = base_s + pp_s_delta
                pp_factor_pp: ti.f32 = kernels_helpers.lookup_ref_pp(pp + GEM_SCALE_NORMAL)
                pp_factor_next = pp_factor_pp
                base_pp: ti.f32 = ti.cast((t_p_pp * 2) + t_s_pp, ti.f32) + pp_factor_pp
                pp_score = calc_score_cached_device(
                    base_pp, c_mul_cur, f_mul_cur, head_len, count_fever, count_normal, m0, m1, m2, m3
                )
                if pp_score > best_score:
                    best_score = pp_score
                    best_opt = 0
        else:
            best_score = calc_score_cached_device(
                base_ov, c_mul_cur, f_mul_cur, head_len, count_fever, count_normal, m0, m1, m2, m3
            )
            best_opt = 3

        # PP lookahead: if OV wins a tie now, but a few PP gems would become a real
        # improvement soon, start investing in PP.
        if allow_pp != 0 and best_opt == 3 and pp_score == best_score and remaining > 1:
            max_k: ti.i32 = remaining
            if max_k > PP_TIE_LOOKAHEAD_MAX:
                max_k = PP_TIE_LOOKAHEAD_MAX
            k: ti.i32 = 2
            while k <= max_k:
                fill_p_k: ti.i32 = (remaining - k) * ov_p_delta
                fill_s_k: ti.i32 = (remaining - k) * ov_s_delta
                t_p = p_val + (k * pp_p_delta) + fill_p_k
                t_s = s_val + (k * pp_s_delta) + fill_s_k
                pp_factor_k: ti.f32 = kernels_helpers.lookup_ref_pp(pp + (k * GEM_SCALE_NORMAL))
                base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor_k
                score_k: ti.i32 = calc_score_cached_device(
                    base, c_mul_cur, f_mul_cur, head_len, count_fever, count_normal, m0, m1, m2, m3
                )
                if score_k > best_score:
                    best_opt = 0
                    # When we commit to PP, the next PP factor should match the +1 PP gem update.
                    # (pp_score was computed using pp + GEM_SCALE_NORMAL when allow_pp != 0.)
                    pp_factor_next = kernels_helpers.lookup_ref_pp(pp + GEM_SCALE_NORMAL)
                    break
                k += 1

        # CM lookahead: discrete CM breakpoints can require multiple CM gems before any
        # improvement is observed. If OV wins now but a short streak of CM gems would
        # strictly improve score, start investing in CM.
        if do_cm != 0 and best_opt == 3 and remaining > 1:
            max_k: ti.i32 = remaining
            if max_k > CM_LOOKAHEAD_MAX:
                max_k = CM_LOOKAHEAD_MAX
            # Cap by CM stat ceiling.
            max_k_by_cap: ti.i32 = (MAX_STAT - cm) // GEM_SCALE_NORMAL
            if max_k > max_k_by_cap:
                max_k = max_k_by_cap
            k: ti.i32 = 2
            while k <= max_k:
                fill_p_k: ti.i32 = (remaining - k) * ov_p_delta
                fill_s_k: ti.i32 = (remaining - k) * ov_s_delta
                t_p = p_val + (k * cm_p_delta) + fill_p_k
                t_s = s_val + (k * cm_s_delta) + fill_s_k
                c_mul_k: ti.f32 = kernels_helpers.lookup_ref_cm(cm + (k * GEM_SCALE_NORMAL))
                base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor_cur
                score_k: ti.i32 = calc_score_cached_device(
                    base, c_mul_k, f_mul_cur, head_len, count_fever, count_normal, m0, m1, m2, m3
                )
                if score_k > best_score:
                    best_opt = 1
                    c_mul_next = kernels_helpers.lookup_ref_cm(cm + GEM_SCALE_NORMAL)
                    break
                k += 1

        # Apply best option
        if best_opt == 0:
            pp += GEM_SCALE_NORMAL
            p_val += pp_p_delta
            s_val += pp_s_delta
            gems_pp += 1
            pp_factor_cur = pp_factor_next
        elif best_opt == 1:
            cm += GEM_SCALE_NORMAL
            p_val += cm_p_delta
            s_val += cm_s_delta
            gems_cm += 1
            c_mul_cur = c_mul_next
        elif best_opt == 2:
            fm += GEM_SCALE_FEVER
            p_val += fm_p_delta
            s_val += fm_s_delta
            gems_fm += 1
            f_mul_cur = f_mul_next
        else:
            p_val += ov_p_delta
            s_val += ov_s_delta
            gems_ov += 1

        remaining -= 1
        best_final_score = best_score

    return ti.Vector([best_final_score, gems_pp, gems_cm, gems_fm, gems_ov, p_val, s_val])


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
    allow_cm_color: ti.i32 = ti.cast((is_p_cm != 0) | (is_s_cm != 0), ti.i32)

    max_pp_gems: ti.i32 = 0
    if allow_pp != 0 and cur_pp < MAX_STAT:
        rem_pp = MAX_STAT - cur_pp
        max_pp_gems = rem_pp // GEM_SCALE_NORMAL
        if rem_pp % GEM_SCALE_NORMAL != 0:
            max_pp_gems += 1

    max_cm_gems: ti.i32 = 0
    if cur_cm < MAX_STAT:
        if allow_cm_color != 0:
            rem_cm = MAX_STAT - cur_cm
            max_cm_gems = rem_cm // GEM_SCALE_NORMAL
            if rem_cm % GEM_SCALE_NORMAL != 0:
                max_cm_gems += 1
        elif cur_cm <= 50:
            max_cm_gems = ((50 - cur_cm) // GEM_SCALE_NORMAL) + 1

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
def optimize_core_device(
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
    return _optimize_core_device_impl(
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
        head_len,
        count_fever,
        count_normal,
        song_slot,
        ft_idx,
        ff_idx,
        ti.u32(0),
        ti.u32(0),
        ti.u32(0),
        ti.u32(0),
        0,
    )


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
def optimize_core_device_preloaded_bits(
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
    return _optimize_core_device_impl(
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
        head_len,
        count_fever,
        count_normal,
        0,
        0,
        0,
        m0,
        m1,
        m2,
        m3,
        1,
    )


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


@ti.func
def _optimize_core_device_refined_from_hint_preloaded_bits_impl(
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
    hint_pp: ti.i32,
    hint_cm: ti.i32,
    hint_fm: ti.i32,
    hint_ov: ti.i32,
) -> ti.types.vector(7, ti.i32):
    """
    Refine a greedy gem allocation hint for a fixed (FT, FF) combo.

    This is used to eliminate false "top-1 misses" where the greedy per-gem allocator
    gets stuck in a local optimum (most commonly CM=0), but a better global allocation
    exists (as observed in historical/root DB records).

    Important: this should remain cheap relative to per-combo evaluation. We only sweep
    over (FM, CM) while keeping PP fixed to the hint, and use a coarse+fine CM scan.
    """
    # Keep constants in sync with optimize_core_jit / _optimize_core_device_impl.
    GEM_SCALE_NORMAL: ti.i32 = 2
    GEM_SCALE_FEVER: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    # Sweep knobs (tuned to catch observed regressions while staying bounded).
    FM_SWEEP: ti.i32 = 12
    CM_STEP: ti.i32 = 4

    max_pp_gems: ti.i32 = (MAX_STAT - cur_pp) // GEM_SCALE_NORMAL
    max_cm_gems: ti.i32 = (MAX_STAT - cur_cm) // GEM_SCALE_NORMAL
    max_fm_gems: ti.i32 = (MAX_STAT - cur_fm) // GEM_SCALE_FEVER
    if max_pp_gems < 0:
        max_pp_gems = 0
    if max_cm_gems < 0:
        max_cm_gems = 0
    if max_fm_gems < 0:
        max_fm_gems = 0

    # Clamp hints defensively (should already be valid).
    pp0: ti.i32 = ti.min(max_pp_gems, ti.max(0, hint_pp))
    cm0: ti.i32 = ti.min(max_cm_gems, ti.max(0, hint_cm))
    fm0: ti.i32 = ti.min(max_fm_gems, ti.max(0, hint_fm))
    ov0: ti.i32 = ti.max(0, hint_ov)
    if pp0 + cm0 + fm0 + ov0 != budget:
        ov0 = budget - pp0 - cm0 - fm0
        if ov0 < 0:
            ov0 = 0

    # Element deltas per gem.
    pp_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_pp
    pp_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_pp
    cm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_cm
    cm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_cm
    fm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_fm
    fm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_fm
    ov_p_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_p_ov
    ov_s_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_s_ov

    allow_cm: ti.i32 = ti.cast((cur_cm <= 50) | (is_p_cm != 0) | (is_s_cm != 0), ti.i32)

    pp_stat0: ti.i32 = ti.min(MAX_STAT, cur_pp + (pp0 * GEM_SCALE_NORMAL))
    pp_factor0: ti.f32 = kernels_helpers.lookup_ref_pp(pp_stat0)

    fm_stat0: ti.i32 = ti.min(MAX_STAT, cur_fm + (fm0 * GEM_SCALE_FEVER))
    f_mul0: ti.f32 = kernels_helpers.lookup_ref_fm(fm_stat0)
    cm_stat0: ti.i32 = ti.min(MAX_STAT, cur_cm + (cm0 * GEM_SCALE_NORMAL))
    c_mul0: ti.f32 = kernels_helpers.lookup_ref_cm(cm_stat0)
    p_val0: ti.i32 = cur_p_val + (pp0 * pp_p_delta) + (cm0 * cm_p_delta) + (fm0 * fm_p_delta) + (ov0 * ov_p_delta)
    s_val0: ti.i32 = cur_s_val + (pp0 * pp_s_delta) + (cm0 * cm_s_delta) + (fm0 * fm_s_delta) + (ov0 * ov_s_delta)
    base_value0: ti.f32 = ti.cast((p_val0 * 2) + s_val0, ti.f32) + pp_factor0
    best_score: ti.i32 = calc_score_cached_device(
        base_value0,
        c_mul0,
        f_mul0,
        head_len,
        count_fever,
        count_normal,
        m0,
        m1,
        m2,
        m3,
    )
    best_pp: ti.i32 = pp0
    best_cm: ti.i32 = cm0
    best_fm: ti.i32 = fm0
    best_ov: ti.i32 = ov0

    do_refine_full: ti.i32 = ti.cast((allow_cm != 0) & (best_cm == 0), ti.i32)
    if do_refine_full != 0:
        fm_lo: ti.i32 = ti.max(0, fm0 - FM_SWEEP)
        fm_hi: ti.i32 = ti.min(max_fm_gems, fm0 + FM_SWEEP)
        fm_g: ti.i32 = fm_lo
        while fm_g <= fm_hi:
            rem0: ti.i32 = budget - pp0 - fm_g
            if rem0 < 0:
                fm_g += 1
                continue

            fm_stat: ti.i32 = ti.min(MAX_STAT, cur_fm + (fm_g * GEM_SCALE_FEVER))
            f_mul: ti.f32 = kernels_helpers.lookup_ref_fm(fm_stat)

            cm_max_here: ti.i32 = rem0
            if cm_max_here > max_cm_gems:
                cm_max_here = max_cm_gems
            if cm_max_here < 0:
                fm_g += 1
                continue

            # Coarse scan CM in steps to avoid large per-genome overhead.
            best_cm_local: ti.i32 = 0
            best_score_local: ti.i32 = -2147483647
            cm_g: ti.i32 = 0
            while cm_g <= cm_max_here:
                ov_g: ti.i32 = rem0 - cm_g
                cm_stat: ti.i32 = ti.min(MAX_STAT, cur_cm + (cm_g * GEM_SCALE_NORMAL))
                c_mul: ti.f32 = kernels_helpers.lookup_ref_cm(cm_stat)
                p_val: ti.i32 = (
                    cur_p_val + (pp0 * pp_p_delta) + (cm_g * cm_p_delta) + (fm_g * fm_p_delta) + (ov_g * ov_p_delta)
                )
                s_val: ti.i32 = (
                    cur_s_val + (pp0 * pp_s_delta) + (cm_g * cm_s_delta) + (fm_g * fm_s_delta) + (ov_g * ov_s_delta)
                )
                base_value: ti.f32 = ti.cast((p_val * 2) + s_val, ti.f32) + pp_factor0
                score: ti.i32 = calc_score_cached_device(
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
                if score > best_score_local:
                    best_score_local = score
                    best_cm_local = cm_g
                if score > best_score:
                    best_score = score
                    best_cm = cm_g
                    best_fm = fm_g
                    best_ov = ov_g
                cm_g += CM_STEP

            # Fine scan around the best coarse CM for this FM.
            cm_lo: ti.i32 = best_cm_local - (CM_STEP - 1)
            if cm_lo < 0:
                cm_lo = 0
            cm_hi: ti.i32 = best_cm_local + (CM_STEP - 1)
            if cm_hi > cm_max_here:
                cm_hi = cm_max_here
            cm_g = cm_lo
            while cm_g <= cm_hi:
                ov_g: ti.i32 = rem0 - cm_g
                cm_stat: ti.i32 = ti.min(MAX_STAT, cur_cm + (cm_g * GEM_SCALE_NORMAL))
                c_mul: ti.f32 = kernels_helpers.lookup_ref_cm(cm_stat)
                p_val: ti.i32 = (
                    cur_p_val + (pp0 * pp_p_delta) + (cm_g * cm_p_delta) + (fm_g * fm_p_delta) + (ov_g * ov_p_delta)
                )
                s_val: ti.i32 = (
                    cur_s_val + (pp0 * pp_s_delta) + (cm_g * cm_s_delta) + (fm_g * fm_s_delta) + (ov_g * ov_s_delta)
                )
                base_value: ti.f32 = ti.cast((p_val * 2) + s_val, ti.f32) + pp_factor0
                score: ti.i32 = calc_score_cached_device(
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
                if score > best_score:
                    best_score = score
                    best_cm = cm_g
                    best_fm = fm_g
                    best_ov = ov_g
                cm_g += 1

            fm_g += 1

    else:
        # Local refinement when CM is already invested:
        # sweep FM and a small CM window around the hint (OV is remainder).
        do_refine_local: ti.i32 = ti.cast((allow_cm != 0) & (best_cm != 0), ti.i32)
        if do_refine_local != 0:
            fm_lo: ti.i32 = ti.max(0, fm0 - FM_SWEEP)
            fm_hi: ti.i32 = ti.min(max_fm_gems, fm0 + FM_SWEEP)
            cm0_i: ti.i32 = cm0
            cm_window: ti.i32 = CM_STEP - 1

            fm_g: ti.i32 = fm_lo
            while fm_g <= fm_hi:
                rem0: ti.i32 = budget - pp0 - fm_g
                if rem0 < 0:
                    fm_g += 1
                    continue

                fm_stat: ti.i32 = ti.min(MAX_STAT, cur_fm + (fm_g * GEM_SCALE_FEVER))
                f_mul: ti.f32 = kernels_helpers.lookup_ref_fm(fm_stat)

                cm_max_here: ti.i32 = rem0
                if cm_max_here > max_cm_gems:
                    cm_max_here = max_cm_gems
                if cm_max_here < 0:
                    fm_g += 1
                    continue

                cm_lo: ti.i32 = cm0_i - cm_window
                if cm_lo < 0:
                    cm_lo = 0
                cm_hi: ti.i32 = cm0_i + cm_window
                if cm_hi > cm_max_here:
                    cm_hi = cm_max_here

                cm_g: ti.i32 = cm_lo
                while cm_g <= cm_hi:
                    ov_g: ti.i32 = rem0 - cm_g
                    cm_stat: ti.i32 = ti.min(MAX_STAT, cur_cm + (cm_g * GEM_SCALE_NORMAL))
                    c_mul: ti.f32 = kernels_helpers.lookup_ref_cm(cm_stat)
                    p_val: ti.i32 = (
                        cur_p_val + (pp0 * pp_p_delta) + (cm_g * cm_p_delta) + (fm_g * fm_p_delta) + (ov_g * ov_p_delta)
                    )
                    s_val: ti.i32 = (
                        cur_s_val + (pp0 * pp_s_delta) + (cm_g * cm_s_delta) + (fm_g * fm_s_delta) + (ov_g * ov_s_delta)
                    )
                    base_value: ti.f32 = ti.cast((p_val * 2) + s_val, ti.f32) + pp_factor0
                    score: ti.i32 = calc_score_cached_device(
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
                    if score > best_score:
                        best_score = score
                        best_cm = cm_g
                        best_fm = fm_g
                        best_ov = ov_g
                    cm_g += 1

                fm_g += 1

    best_p: ti.i32 = (
        cur_p_val + (best_pp * pp_p_delta) + (best_cm * cm_p_delta) + (best_fm * fm_p_delta) + (best_ov * ov_p_delta)
    )
    best_s: ti.i32 = (
        cur_s_val + (best_pp * pp_s_delta) + (best_cm * cm_s_delta) + (best_fm * fm_s_delta) + (best_ov * ov_s_delta)
    )
    return ti.Vector([best_score, best_pp, best_cm, best_fm, best_ov, best_p, best_s])


@ti.func
def optimize_core_device_refined(
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
    """
    Refined gem allocation for a fixed (FT, FF) combo.

    Uses the greedy allocation as a hint and refines it with a bounded CM/FM scan.
    """
    m0 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 0]
    m1 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 1]
    m2 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 2]
    m3 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 3]

    base = optimize_core_device_preloaded_bits(
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
    )
    # Always apply bounded refinement (local scan when CM is nonzero) to avoid top-1 misses.
    return _optimize_core_device_refined_from_hint_preloaded_bits_impl(
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
        base[1],
        base[2],
        base[3],
        base[4],
    )
