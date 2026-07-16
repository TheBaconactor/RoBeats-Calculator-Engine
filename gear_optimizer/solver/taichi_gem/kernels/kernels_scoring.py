"""
Taichi Kernels - Score Calculation and Greedy Optimization.

This module contains score calculation functions and the exact-bound optimizer:
- _calc_body_score: Body notes score (simple multiply)
- _calc_head_factor: Combo ramp factor
- calc_score_device: Main score calculation (work-item masks)
- calc_score_with_grid_bits: Score calculation using bitpacked masks
- calc_score_cached_device: Cached score calculation
- optimize_core_device_exact_bound: exact bounded gem allocation

The exact-bound optimizer is the core of GPU gem evaluation. It enumerates exact
CM/FM surfaces, uses a PP/OV prefix table, and prunes with admissible bounds.
"""

import taichi as ti

from . import kernels_helpers


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
def score_timeline_frontier_cached_device(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    song_slot: ti.i32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
    head_len: ti.i32,
) -> ti.i32:
    """Score every retained physical Base surface and return the exact maximum."""
    frontier_count = ti.cast(kernels_helpers.grid_frontier_count[song_slot, ft_idx, ff_idx], ti.i32)
    best_score = ti.i32(-1)
    variant_idx = ti.i32(0)
    while variant_idx < frontier_count:
        frontier = kernels_helpers.read_timeline_frontier_variant(
            song_slot, ft_idx, ff_idx, variant_idx
        )
        score = calc_score_cached_device(
            base_value,
            combo_mul,
            fever_mul,
            head_len,
            frontier.body_fever,
            frontier.body_normal,
            frontier.m0,
            frontier.m1,
            frontier.m2,
            frontier.m3,
        )
        best_score = ti.max(best_score, score)
        variant_idx += 1
    return best_score


@ti.func
def score_solution_from_gems_frontier(
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

    return score_timeline_frontier_cached_device(
        base_value,
        combo_mul,
        fever_mul,
        song_slot,
        ft_idx,
        ff_idx,
        head_len,
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
def _eval_coupled_fm(
    base0: ti.f32,
    m_f: ti.f32,
    cur_fm_f: ti.f32,
    slope: ti.f32,
    intercept: ti.f32,
    inner_fm: ti.f32,
    s: ti.f32,
) -> ti.f32:
    # Folded relaxation Psi = B * F * (C*a2 + a1), with C pinned at C* (inner_fm = C*a2 + a1),
    # B = base0 - Delta_f * f  (f = (s - cur_fm)/3 folded into m_f = Delta_f/3), F = envelope(s).
    # Association follows design section 3.3 exactly; do NOT reassociate this folded product.
    b: ti.f32 = base0 - m_f * (s - cur_fm_f)
    f: ti.f32 = slope * s + intercept
    return b * f * inner_fm


@ti.func
def _coupled_ub_fm(
    base0: ti.f32,
    inner_fm: ti.f32,
    delta_f: ti.i32,
    cur_fm: ti.i32,
    budget: ti.i32,
) -> ti.f32:
    # UB_fm = max over reachable FM stat of the folded relaxation, couples FM <-> base lane.
    GEM_SCALE_FEVER: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    budget_nn: ti.i32 = ti.max(0, budget)
    s_lo: ti.f32 = ti.cast(ti.max(0, ti.min(MAX_STAT, cur_fm)), ti.f32)
    s_hi: ti.f32 = ti.cast(ti.max(0, ti.min(MAX_STAT, cur_fm + budget_nn * GEM_SCALE_FEVER)), ti.f32)
    cur_fm_f: ti.f32 = ti.cast(cur_fm, ti.f32)
    m_f: ti.f32 = ti.cast(delta_f, ti.f32) / ti.cast(GEM_SCALE_FEVER, ti.f32)
    best: ti.f32 = ti.f32(-1.0e30)
    n_seg: ti.i32 = kernels_helpers.hull_fm_count[0]
    seg: ti.i32 = 0
    while seg < n_seg:
        lo: ti.f32 = kernels_helpers.hull_fm_seg[seg, 0]
        hi: ti.f32 = kernels_helpers.hull_fm_seg[seg, 1]
        slope: ti.f32 = kernels_helpers.hull_fm_seg[seg, 2]
        intercept: ti.f32 = kernels_helpers.hull_fm_seg[seg, 3]
        a: ti.f32 = ti.max(lo, s_lo)
        b: ti.f32 = ti.min(hi, s_hi)
        if a <= b:
            cand: ti.f32 = ti.max(
                _eval_coupled_fm(base0, m_f, cur_fm_f, slope, intercept, inner_fm, a),
                _eval_coupled_fm(base0, m_f, cur_fm_f, slope, intercept, inner_fm, b),
            )
            # Concave quadratic q(s) = (base0 + m_f*cur_fm - m_f*s) * (slope*s + intercept).
            # Interior vertex maximises it; clamp to the segment and evaluate. Leading coeff
            # -m_f*slope <= 0. Only search the vertex when strictly concave (m_f*slope > 0).
            lead: ti.f32 = m_f * slope
            if lead > ti.f32(0.0):
                bhat: ti.f32 = base0 + m_f * cur_fm_f
                sv: ti.f32 = (bhat * slope - m_f * intercept) / (ti.f32(2.0) * lead)
                if sv > a and sv < b:
                    cand = ti.max(
                        cand,
                        _eval_coupled_fm(base0, m_f, cur_fm_f, slope, intercept, inner_fm, sv),
                    )
            best = ti.max(best, cand)
        seg += 1
    return best


@ti.func
def _eval_coupled_cm(
    base0: ti.f32,
    m_c: ti.f32,
    cur_cm_f: ti.f32,
    slope: ti.f32,
    intercept: ti.f32,
    fstar: ti.f32,
    a2: ti.f32,
    a1: ti.f32,
    s: ti.f32,
) -> ti.f32:
    # Folded relaxation Psi = B * F * (C*a2 + a1), with F pinned at F* (fstar), C = envelope(s).
    # B = base0 - Delta_c * c (c = (s - cur_cm)/2 folded into m_c = Delta_c/2).
    b: ti.f32 = base0 - m_c * (s - cur_cm_f)
    cval: ti.f32 = slope * s + intercept
    inner: ti.f32 = cval * a2 + a1
    return b * fstar * inner


@ti.func
def _coupled_ub_cm(
    base0: ti.f32,
    fstar: ti.f32,
    a2: ti.f32,
    a1: ti.f32,
    delta_c: ti.i32,
    cur_cm: ti.i32,
    budget: ti.i32,
) -> ti.f32:
    # UB_cm = max over reachable CM stat of the folded relaxation, couples CM <-> base lane.
    GEM_SCALE_NORMAL: ti.i32 = 2
    MAX_STAT: ti.i32 = 160
    budget_nn: ti.i32 = ti.max(0, budget)
    s_lo: ti.f32 = ti.cast(ti.max(0, ti.min(MAX_STAT, cur_cm)), ti.f32)
    s_hi: ti.f32 = ti.cast(ti.max(0, ti.min(MAX_STAT, cur_cm + budget_nn * GEM_SCALE_NORMAL)), ti.f32)
    cur_cm_f: ti.f32 = ti.cast(cur_cm, ti.f32)
    m_c: ti.f32 = ti.cast(delta_c, ti.f32) / ti.cast(GEM_SCALE_NORMAL, ti.f32)
    best: ti.f32 = ti.f32(-1.0e30)
    n_seg: ti.i32 = kernels_helpers.hull_cm_count[0]
    seg: ti.i32 = 0
    while seg < n_seg:
        lo: ti.f32 = kernels_helpers.hull_cm_seg[seg, 0]
        hi: ti.f32 = kernels_helpers.hull_cm_seg[seg, 1]
        slope: ti.f32 = kernels_helpers.hull_cm_seg[seg, 2]
        intercept: ti.f32 = kernels_helpers.hull_cm_seg[seg, 3]
        a: ti.f32 = ti.max(lo, s_lo)
        b: ti.f32 = ti.min(hi, s_hi)
        if a <= b:
            cand: ti.f32 = ti.max(
                _eval_coupled_cm(base0, m_c, cur_cm_f, slope, intercept, fstar, a2, a1, a),
                _eval_coupled_cm(base0, m_c, cur_cm_f, slope, intercept, fstar, a2, a1, b),
            )
            # inner(s) = a2*slope*s + (a2*intercept + a1) = amp*s + dee. Concave quadratic
            # q(s) = (base0 + m_c*cur_cm - m_c*s)*(amp*s + dee); leading coeff -m_c*amp <= 0.
            amp: ti.f32 = a2 * slope
            lead: ti.f32 = m_c * amp
            if lead > ti.f32(0.0):
                dee: ti.f32 = a2 * intercept + a1
                bhat: ti.f32 = base0 + m_c * cur_cm_f
                sv: ti.f32 = (bhat * amp - m_c * dee) / (ti.f32(2.0) * lead)
                if sv > a and sv < b:
                    cand = ti.max(
                        cand,
                        _eval_coupled_cm(base0, m_c, cur_cm_f, slope, intercept, fstar, a2, a1, sv),
                    )
            best = ti.max(best, cand)
        seg += 1
    return best


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
    body_total: ti.i32,
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
    body_total_c: ti.i32 = ti.max(0, body_total)

    current_ub: ti.f32 = _semi_exact_upper_bound(
        base_value,
        combo_mul,
        fever_mul,
        body_total_c,
        0,
        0,
        head_len_c,
        0,
        sigma_hf,
    )

    # Coupled Lagrangian-exchange sub-bounds (design UB_CULL_BOUND_DESIGN.md, Design 1).
    # Both fold the exact score to Psi = B*F*(C*a2 + a1) (body/head floors dropped upward),
    # then couple the base lane against one multiplier axis while pinning the other at its
    # current-corner value (C* = combo_mul, F* = fever_mul). Each maximises a concave quadratic
    # over the reachable stat range using the precomputed concave envelopes of refcm/reffm.
    # UB_gate = min(current, UB_fm, UB_cm) is >= current always, so the cull only ever tightens.
    UB_EPS: ti.f32 = 1024.0
    n_f: ti.f32 = ti.cast(body_total_c, ti.f32)
    l_f: ti.f32 = ti.cast(head_len_c, ti.f32)
    sigma_f: ti.f32 = ti.cast(sigma_hf, ti.f32)
    a2: ti.f32 = n_f + sigma_f / ti.f32(100.0)
    a1: ti.f32 = l_f - sigma_f / ti.f32(100.0)
    delta_c: ti.i32 = w_max - w_cm
    delta_f: ti.i32 = w_max - w_fm
    inner_fm: ti.f32 = combo_mul * a2 + a1
    ub_fm: ti.f32 = _coupled_ub_fm(base_value, inner_fm, delta_f, cur_fm, budget) + UB_EPS
    ub_cm: ti.f32 = _coupled_ub_cm(base_value, fever_mul, a2, a1, delta_c, cur_cm, budget) + UB_EPS

    return ti.min(current_ub, ti.min(ub_fm, ub_cm))


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
    n_hn: ti.i32,
    n_hf: ti.i32,
    sigma_hn: ti.i32,
    sigma_hf: ti.i32,
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

    # Head coefficients (n_hn, n_hf, sigma_hn, sigma_hf) arrive precomputed per
    # frontier variant (grid_frontier_head_coeffs_pool, filled at timeline build):
    # they are genome-invariant, so deriving them in-kernel per (genome, combo,
    # variant) was pure recompute.

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
            frontier.n_hn,
            frontier.n_hf,
            frontier.sigma_hn,
            frontier.sigma_hf,
        )
        if cand_vec[0] > result_vec[0]:
            result_vec = cand_vec
        variant_idx += 1
    return result_vec
