"""Taichi scoring: the score of a gem allocation on a surface of the song's timeline frontier, and exact_gem_search, the
GA's per-cell gem search: a greedy seed, then every (CM, FM) pair whose admissible bound can beat the best so far, bounded by
rows and runs of _FM_RUN pairs first (PP from the PP/element prefix-argmax table)."""

from collections.abc import Mapping

from gear_optimizer.core.color_flags import COLOR_FLAG_KEYS
from gear_optimizer.rules import ELEMENT_GEM_GAIN, MAX_STAT, STAT_GEM_ELEMENT_GAIN, STAT_GEM_GAIN_FEVER, STAT_GEM_GAIN_NORMAL

from . import fields
from .runtime import ti

# FM gem counts per run bound in the exact search's pair loop.
_FM_RUN = 8

# The song's color flags as one kernel argument (core.color_flags).
GpuColorFlags = ti.types.struct(**dict.fromkeys(COLOR_FLAG_KEYS, ti.i32))


def gpu_color_flags(flags: Mapping[str, int]) -> GpuColorFlags:
    return GpuColorFlags(**{key: flags[key] for key in COLOR_FLAG_KEYS})


@ti.func
def _stat_index(value: ti.i32) -> ti.i32:
    return ti.max(0, ti.min(MAX_STAT, value))


@ti.func
def lookup_ref_pp(value: ti.i32) -> ti.f32:
    return ti.cast(fields.ref_pp_field[_stat_index(value)], ti.f32)


@ti.func
def lookup_ref_cm(value: ti.i32) -> ti.f32:
    return fields.ref_cm_field[_stat_index(value)]


@ti.func
def lookup_ref_fm(value: ti.i32) -> ti.f32:
    return fields.ref_fm_field[_stat_index(value)]


FrontierSurface = ti.types.struct(
    m0=ti.u32,
    m1=ti.u32,
    m2=ti.u32,
    m3=ti.u32,
    body_fever=ti.i32,
    body_normal=ti.i32,
    n_hn=ti.i32,
    n_hf=ti.i32,
    sigma_hn=ti.i32,
    sigma_hf=ti.i32,
)


@ti.func
def _read_surface(ft_idx: ti.i32, ff_idx: ti.i32, variant_idx: ti.i32) -> FrontierSurface:
    pool_idx = fields.grid_frontier_offset[ft_idx, ff_idx] + variant_idx
    return FrontierSurface(
        m0=fields.grid_frontier_masks_bits_pool[pool_idx, 0],
        m1=fields.grid_frontier_masks_bits_pool[pool_idx, 1],
        m2=fields.grid_frontier_masks_bits_pool[pool_idx, 2],
        m3=fields.grid_frontier_masks_bits_pool[pool_idx, 3],
        body_fever=fields.grid_frontier_body_fever_pool[pool_idx],
        body_normal=fields.grid_frontier_body_normal_pool[pool_idx],
        n_hn=ti.cast(fields.grid_frontier_head_coeffs_pool[pool_idx, 0], ti.i32),
        n_hf=ti.cast(fields.grid_frontier_head_coeffs_pool[pool_idx, 1], ti.i32),
        sigma_hn=ti.cast(fields.grid_frontier_head_coeffs_pool[pool_idx, 2], ti.i32),
        sigma_hf=ti.cast(fields.grid_frontier_head_coeffs_pool[pool_idx, 3], ti.i32),
    )


@ti.func
def _body_score(base_value: ti.f32, combo_mul: ti.f32, fever_mul: ti.f32, count_fever: ti.i32, count_normal: ti.i32) -> ti.i32:
    """Notes past the head, at full combo. All values are non-negative: truncation matches the game's floor."""
    combo_val = ti.cast(base_value * combo_mul, ti.i32)
    fever_val = ti.cast(base_value * combo_mul * fever_mul, ti.i32)
    return (count_fever * fever_val) + (count_normal * combo_val)


@ti.func
def _head_factor(base_value: ti.f32, combo_mul: ti.f32) -> ti.f32:
    """The combo ramp per note of the head (the first 100 notes): score[i] = base_value + i * factor."""
    return (combo_mul - 1.0) * base_value / 100.0


@ti.func
def _head_word_score(
    base_value: ti.f32, factor: ti.f32, fever_delta: ti.f32, mask: ti.u32, first: ti.i32, last: ti.i32
) -> ti.i32:
    """Head notes first..last - 1, at most one mask word of them: bit i - first says whether note i is in fever."""
    score = ti.i32(0)
    t: ti.f32 = ti.cast(first + 1, ti.f32)
    for i in range(first, last):
        ramp_val = base_value + (t * factor)
        is_fever = (mask >> ti.u32(i - first)) & ti.u32(1)
        # Branchless select: mul is either 1.0 or fever_mul.
        mul = 1.0 + fever_delta * ti.cast(is_fever, ti.f32)
        score += ti.cast(ramp_val * mul, ti.i32)
        t += 1.0
    return score


@ti.func
def _surface_score(
    base_value: ti.f32, combo_mul: ti.f32, fever_mul: ti.f32, head_len: ti.i32, surface: FrontierSurface
) -> ti.i32:
    body = _body_score(base_value, combo_mul, fever_mul, surface.body_fever, surface.body_normal)
    factor, fever_delta = _head_factor(base_value, combo_mul), fever_mul - 1.0
    return (
        body
        + _head_word_score(base_value, factor, fever_delta, surface.m0, 0, ti.min(head_len, 32))
        + _head_word_score(base_value, factor, fever_delta, surface.m1, 32, ti.min(head_len, 64))
        + _head_word_score(base_value, factor, fever_delta, surface.m2, 64, ti.min(head_len, 96))
        + _head_word_score(base_value, factor, fever_delta, surface.m3, 96, head_len)
    )


@ti.func
def _upper_bound(
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
    body_score = _body_score(base_value, combo_mul, fever_mul, count_fever, count_normal)
    factor = _head_factor(base_value, combo_mul)
    head_upper = base_value * (ti.cast(n_hn, ti.f32) + (fever_mul * ti.cast(n_hf, ti.f32))) + factor * (
        ti.cast(sigma_hn, ti.f32) + (fever_mul * ti.cast(sigma_hf, ti.f32))
    )
    return ti.cast(body_score, ti.f32) + head_upper + UB_EPS


@ti.func
def _gem_weights(flags: GpuColorFlags) -> ti.types.vector(4, ti.i32):
    """What one PP, CM, FM or element gem adds to 2 x primary + secondary."""
    return ti.Vector([
        STAT_GEM_ELEMENT_GAIN * ((flags.is_p_pp << 1) + flags.is_s_pp),
        STAT_GEM_ELEMENT_GAIN * ((flags.is_p_cm << 1) + flags.is_s_cm),
        STAT_GEM_ELEMENT_GAIN * ((flags.is_p_fm << 1) + flags.is_s_fm),
        ELEMENT_GEM_GAIN * ((flags.is_p_ov << 1) + flags.is_s_ov),
    ])


@ti.func
def combo_upper_bound(
    budget: ti.i32,
    cur_pp: ti.i32,
    cur_cm: ti.i32,
    cur_fm: ti.i32,
    cur_p_val: ti.i32,
    cur_s_val: ti.i32,
    flags: GpuColorFlags,
    head_len: ti.i32,
    body_total: ti.i32,
) -> ti.f32:
    """A bound on every gem split of a cell: each stat as if it took the whole budget, every note in fever."""
    weights = _gem_weights(flags)
    pp_stat: ti.i32 = _stat_index(cur_pp + (budget * STAT_GEM_GAIN_NORMAL))
    cm_stat: ti.i32 = _stat_index(cur_cm + (budget * STAT_GEM_GAIN_NORMAL))
    fm_stat: ti.i32 = _stat_index(cur_fm + (budget * STAT_GEM_GAIN_FEVER))
    base_lane: ti.i32 = (cur_p_val << 1) + cur_s_val + (budget * weights.max())
    base_value: ti.f32 = ti.cast(base_lane, ti.f32) + lookup_ref_pp(pp_stat)
    head_len_c: ti.i32 = ti.max(0, ti.min(head_len, 100))
    sigma_hf: ti.i32 = (head_len_c * (head_len_c + 1)) // 2
    return _upper_bound(
        base_value, lookup_ref_cm(cm_stat), lookup_ref_fm(fm_stat), ti.max(0, body_total), 0, 0, head_len_c, 0, sigma_hf
    )


# The (CM, FM)-invariant inputs of one surface's search.
SearchContext = ti.types.struct(
    budget=ti.i32,
    max_pp_gems=ti.i32,
    cur_pp=ti.i32,
    cur_cm=ti.i32,
    cur_fm=ti.i32,
    base_init=ti.i32,
    w_cm=ti.i32,
    w_fm=ti.i32,
    w_ov=ti.i32,
    flags_idx=ti.i32,
    cur_pp_idx=ti.i32,
    delta_pp_vs_ov=ti.i32,
    surface=FrontierSurface,
)


@ti.func
def _best_pp_gems(ctx: SearchContext, leftover: ti.i32) -> ti.i32:
    """The prefix table's PP gems of `leftover` gems split between PP and element gems: O(1) per (CM, FM) pair instead of
    a scan of the splits."""
    return ti.cast(fields.exact_pp_best_gems_prefix[ctx.flags_idx, ctx.cur_pp_idx, ti.min(ctx.max_pp_gems, leftover)], ti.i32)


@ti.func
def _split_base_value(ctx: SearchContext, g_cm: ti.i32, g_fm: ti.i32, g_pp: ti.i32) -> ti.f32:
    leftover: ti.i32 = ctx.budget - g_cm - g_fm
    pp_extra: ti.f32 = ti.cast(g_pp * ctx.delta_pp_vs_ov, ti.f32) + lookup_ref_pp(ctx.cur_pp + (g_pp * STAT_GEM_GAIN_NORMAL))
    base_linear: ti.i32 = ctx.base_init + (g_cm * ctx.w_cm) + (g_fm * ctx.w_fm) + (leftover * ctx.w_ov)
    return ti.cast(base_linear, ti.f32) + pp_extra


@ti.func
def _surface_bound(ctx: SearchContext, base_value: ti.f32, combo_mul: ti.f32, fever_mul: ti.f32) -> ti.f32:
    surface = ctx.surface
    return _upper_bound(
        base_value, combo_mul, fever_mul, surface.body_fever, surface.body_normal, surface.n_hn, surface.n_hf,
        surface.sigma_hn, surface.sigma_hf,
    )


@ti.func
def _pair_bound(ctx: SearchContext, g_cm: ti.i32, g_fm: ti.i32) -> ti.f32:
    base_value = _split_base_value(ctx, g_cm, g_fm, _best_pp_gems(ctx, ctx.budget - g_cm - g_fm))
    combo_mul = lookup_ref_cm(ctx.cur_cm + (g_cm * STAT_GEM_GAIN_NORMAL))
    fever_mul = lookup_ref_fm(ctx.cur_fm + (g_fm * STAT_GEM_GAIN_FEVER))
    return _surface_bound(ctx, base_value, combo_mul, fever_mul)


@ti.func
def _fm_run_bound(ctx: SearchContext, g_cm: ti.i32, fm_lo: ti.i32, fm_hi: ti.i32) -> ti.f32:
    """At least _pair_bound(ctx, g_cm, g_fm) for every g_fm in [fm_lo, fm_hi]: the bound is non-decreasing in the base
    value and both multipliers, so it is taken at the run's largest of each (the fever multiplier at fm_hi, the base's
    linear part at the better end, its PP part at the largest leftover, as the prefix-argmax table's best never falls
    with more gems)."""
    g_pp: ti.i32 = _best_pp_gems(ctx, ctx.budget - g_cm - fm_lo)
    fm_gain: ti.i32 = ctx.w_fm - ctx.w_ov
    base_linear: ti.i32 = (
        ctx.base_init + (g_cm * ctx.w_cm) + ((ctx.budget - g_cm) * ctx.w_ov) + ti.max(fm_lo * fm_gain, fm_hi * fm_gain)
    )
    pp_extra: ti.f32 = ti.cast(g_pp * ctx.delta_pp_vs_ov, ti.f32) + lookup_ref_pp(ctx.cur_pp + (g_pp * STAT_GEM_GAIN_NORMAL))
    return _surface_bound(
        ctx,
        ti.cast(base_linear, ti.f32) + pp_extra,
        lookup_ref_cm(ctx.cur_cm + (g_cm * STAT_GEM_GAIN_NORMAL)),
        lookup_ref_fm(ctx.cur_fm + (fm_hi * STAT_GEM_GAIN_FEVER)),
    )


@ti.func
def _improves(
    score: ti.i32, g_cm: ti.i32, g_fm: ti.i32, g_pp: ti.i32, best: ti.types.vector(5, ti.i32)
) -> ti.i32:
    """Whether a split beats best [score, PP, CM, FM, element]: a higher score, then fewer CM, FM, PP gems."""
    return (
        score > best[0]
        or (score == best[0] and ((g_cm < best[2]) or (g_cm == best[2] and ((g_fm < best[3]) or (g_fm == best[3] and g_pp < best[1])))))
    )


@ti.func
def _gems_to_cap(stat: ti.i32, gain: ti.i32) -> ti.i32:
    return ti.max(0, (MAX_STAT - stat + gain - 1) // gain)


@ti.func
def _surface_search(
    budget: ti.i32,
    cur_pp: ti.i32,
    cur_cm: ti.i32,
    cur_fm: ti.i32,
    cur_p_val: ti.i32,
    cur_s_val: ti.i32,
    flags: GpuColorFlags,
    surface: FrontierSurface,
    head_len: ti.i32,
    floor: ti.i32,
) -> ti.types.vector(5, ti.i32):
    """The best [score, PP, CM, FM, element gems] on one surface; a pair whose bound is below `floor` (the caller's
    incumbent: a result under it cannot win) is not scored."""
    weights = _gem_weights(flags)
    allow_pp: ti.i32 = ti.cast((flags.is_p_pp != 0) | (flags.is_s_pp != 0), ti.i32)
    max_pp_gems: ti.i32 = ti.min(budget, _gems_to_cap(cur_pp, STAT_GEM_GAIN_NORMAL) * allow_pp)
    max_cm_gems: ti.i32 = ti.min(budget, _gems_to_cap(cur_cm, STAT_GEM_GAIN_NORMAL))
    max_fm_gems: ti.i32 = ti.min(budget, _gems_to_cap(cur_fm, STAT_GEM_GAIN_FEVER))
    ctx = SearchContext(
        budget=budget,
        max_pp_gems=max_pp_gems,
        cur_pp=cur_pp,
        cur_cm=cur_cm,
        cur_fm=cur_fm,
        base_init=(cur_p_val << 1) + cur_s_val,
        w_cm=weights[1],
        w_fm=weights[2],
        w_ov=weights[3],
        # The prefix table's key: its 16 flag combinations.
        flags_idx=(
            ti.cast(flags.is_p_pp != 0, ti.i32) | (ti.cast(flags.is_s_pp != 0, ti.i32) << 1)
            | (ti.cast(flags.is_p_ov != 0, ti.i32) << 2) | (ti.cast(flags.is_s_ov != 0, ti.i32) << 3)
        ),
        cur_pp_idx=_stat_index(cur_pp),
        delta_pp_vs_ov=weights[0] - weights[3],
        surface=surface,
    )

    # The incumbent seed: two greedy walks over (CM, FM) by bound that differ only in the tie rule (walk 0 prefers CM,
    # walk 1 FM); each keeps the highest-bound point it passes, which is then scored.
    seed_ub_init: ti.f32 = _pair_bound(ctx, 0, 0)
    seed_best_cm = ti.Vector([0, 0], dt=ti.i32)
    seed_best_fm = ti.Vector([0, 0], dt=ti.i32)
    for walk in ti.static(range(2)):
        seed_best_ub: ti.f32 = seed_ub_init
        seed_cm: ti.i32 = 0
        seed_fm: ti.i32 = 0
        step: ti.i32 = 0
        while step < budget:
            can_add_cm = ti.cast((seed_cm < max_cm_gems) & ((seed_cm + seed_fm + 1) <= budget), ti.i32)
            can_add_fm = ti.cast((seed_fm < max_fm_gems) & ((seed_cm + seed_fm + 1) <= budget), ti.i32)
            if can_add_cm == 0 and can_add_fm == 0:
                break
            ub_cm = ti.f32(-1.0e30)
            ub_fm = ti.f32(-1.0e30)
            if can_add_cm != 0:
                ub_cm = _pair_bound(ctx, seed_cm + 1, seed_fm)
            if can_add_fm != 0:
                ub_fm = _pair_bound(ctx, seed_cm, seed_fm + 1)
            cur_ub = ub_fm
            if ti.static(walk == 0):
                if ub_cm >= ub_fm:
                    seed_cm += 1
                    cur_ub = ub_cm
                else:
                    seed_fm += 1
            else:
                cur_ub = ub_cm
                if ub_fm >= ub_cm:
                    seed_fm += 1
                    cur_ub = ub_fm
                else:
                    seed_cm += 1
            if cur_ub > seed_best_ub:
                seed_best_ub = cur_ub
                seed_best_cm[walk] = seed_cm
                seed_best_fm[walk] = seed_fm
            step += 1

    best = ti.Vector([-1, 0, 0, 0, 0], dt=ti.i32)
    for walk in ti.static(range(2)):
        g_cm: ti.i32 = seed_best_cm[walk]
        g_fm: ti.i32 = seed_best_fm[walk]
        # Identical walks choose the same PP split as well as the same CM/FM pair.
        if walk == 0 or g_cm != seed_best_cm[0] or g_fm != seed_best_fm[0]:
            leftover: ti.i32 = budget - g_cm - g_fm
            g_pp: ti.i32 = _best_pp_gems(ctx, leftover)
            combo_mul: ti.f32 = lookup_ref_cm(cur_cm + (g_cm * STAT_GEM_GAIN_NORMAL))
            fever_mul: ti.f32 = lookup_ref_fm(cur_fm + (g_fm * STAT_GEM_GAIN_FEVER))
            score = _surface_score(_split_base_value(ctx, g_cm, g_fm, g_pp), combo_mul, fever_mul, head_len, surface)
            if _improves(score, g_cm, g_fm, g_pp, best):
                best = ti.Vector([score, g_pp, g_cm, g_fm, leftover - g_pp])

    g_cm_row: ti.i32 = 0
    while g_cm_row <= max_cm_gems:
        leftover_after_cm: ti.i32 = budget - g_cm_row
        if leftover_after_cm < 0:
            break
        combo_mul: ti.f32 = lookup_ref_cm(cur_cm + (g_cm_row * STAT_GEM_GAIN_NORMAL))
        max_fm_here: ti.i32 = ti.min(max_fm_gems, leftover_after_cm)
        # The row is bounded whole, then in runs of _FM_RUN pairs: a run whose bound cannot beat the best so far or
        # reach the floor holds no pair the loop would score.
        g_fm_pair: ti.i32 = 0
        run_end: ti.i32 = max_fm_here
        while g_fm_pair <= max_fm_here:
            run_ub = _fm_run_bound(ctx, g_cm_row, g_fm_pair, run_end)
            open_run = run_ub > ti.cast(best[0], ti.f32) and run_ub >= ti.cast(floor, ti.f32)
            if open_run and run_end - g_fm_pair >= _FM_RUN:
                run_end = g_fm_pair + _FM_RUN - 1
                continue
            while open_run and g_fm_pair <= run_end:
                # Both seeds were already scored and compared with the same tie ordering.
                if (g_cm_row == seed_best_cm[0] and g_fm_pair == seed_best_fm[0]) or (
                    g_cm_row == seed_best_cm[1] and g_fm_pair == seed_best_fm[1]
                ):
                    g_fm_pair += 1
                    continue
                leftover: ti.i32 = budget - g_cm_row - g_fm_pair
                g_pp: ti.i32 = _best_pp_gems(ctx, leftover)
                fever_mul: ti.f32 = lookup_ref_fm(cur_fm + (g_fm_pair * STAT_GEM_GAIN_FEVER))
                base_value: ti.f32 = _split_base_value(ctx, g_cm_row, g_fm_pair, g_pp)
                if _surface_bound(ctx, base_value, combo_mul, fever_mul) > ti.cast(best[0], ti.f32):
                    score = _surface_score(base_value, combo_mul, fever_mul, head_len, surface)
                    if _improves(score, g_cm_row, g_fm_pair, g_pp, best):
                        best = ti.Vector([score, g_pp, g_cm_row, g_fm_pair, leftover - g_pp])
                g_fm_pair += 1
            g_fm_pair = run_end + 1
            run_end = ti.min(g_fm_pair + _FM_RUN - 1, max_fm_here)
        g_cm_row += 1
    return best


@ti.func
def exact_gem_search(
    budget: ti.i32,
    cur_pp: ti.i32,
    cur_cm: ti.i32,
    cur_fm: ti.i32,
    cur_p_val: ti.i32,
    cur_s_val: ti.i32,
    flags: GpuColorFlags,
    head_len: ti.i32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
    floor: ti.i32,
) -> ti.types.vector(5, ti.i32):
    """The best gem allocation over the cell's surfaces (the first surface wins a tie); `floor`: as in _surface_search."""
    result = ti.Vector([-1, 0, 0, 0, 0], dt=ti.i32)
    variant_idx = ti.i32(0)
    while variant_idx < fields.grid_frontier_count[ft_idx, ff_idx]:
        surface = _read_surface(ft_idx, ff_idx, variant_idx)
        candidate = _surface_search(budget, cur_pp, cur_cm, cur_fm, cur_p_val, cur_s_val, flags, surface, head_len, floor)
        if candidate[0] > result[0]:
            result = candidate
        variant_idx += 1
    return result
