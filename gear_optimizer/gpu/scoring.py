"""Taichi scoring: the score of a gem allocation on a surface of the song's timeline frontier, and exact_gem_search, the
GA's per-cell gem search: every (CM, FM) pair whose admissible bound can beat the best so far, bounded by rows and runs of
_FM_RUN pairs first (PP from the PP/element prefix-argmax table).

A surface's shape (A, E, F, G) gives its notes' sum before the score's floors: base value x (combo x (A x fever + E) + F x
fever + G). Each note's score is at most its share of that, so a bound is that sum, with _BOUND_MARGIN over the float order."""

from collections.abc import Mapping

from gear_optimizer.core.color_flags import COLOR_FLAG_KEYS
from gear_optimizer.rules import ELEMENT_GEM_GAIN, MAX_STAT, STAT_GEM_ELEMENT_GAIN, STAT_GEM_GAIN_FEVER, STAT_GEM_GAIN_NORMAL

from . import fields
from .runtime import ti

# FM gem counts per run bound in the exact search's pair loop.
_FM_RUN = 8
_BOUND_MARGIN = 1024.0

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
def _surface_score(base_value: ti.f32, combo_mul: ti.f32, fever_mul: ti.f32, pool_idx: ti.i32) -> ti.i32:
    """Notes past the head at full combo, then the head's combo ramp: score[i] = base_value + i * factor (the first 100
    notes). All values are non-negative: truncation matches the game's floor."""
    head_len: ti.i32 = fields.song_head_len[0]
    combo_val = ti.cast(base_value * combo_mul, ti.i32)
    fever_val = ti.cast(base_value * combo_mul * fever_mul, ti.i32)
    score = (fields.grid_frontier_body_fever_pool[pool_idx] * fever_val) + (
        fields.grid_frontier_body_normal_pool[pool_idx] * combo_val
    )
    factor: ti.f32 = (combo_mul - 1.0) * base_value / 100.0
    fever_delta: ti.f32 = fever_mul - 1.0
    for word in ti.static(range(4)):
        mask = fields.grid_frontier_masks_bits_pool[pool_idx, word]
        score += _head_word_score(base_value, factor, fever_delta, mask, word * 32, ti.min(head_len, (word + 1) * 32))
    return score


@ti.func
def shape_value(shape: ti.types.vector(4, ti.f32), combo_mul: ti.f32, fever_mul: ti.f32) -> ti.f32:
    return combo_mul * ((shape[0] * fever_mul) + shape[1]) + (shape[2] * fever_mul) + shape[3]


@ti.func
def gem_weights(flags: GpuColorFlags) -> ti.types.vector(4, ti.i32):
    """What one PP, CM, FM or element gem adds to 2 x primary + secondary."""
    return ti.Vector([
        STAT_GEM_ELEMENT_GAIN * ((flags.is_p_pp << 1) + flags.is_s_pp),
        STAT_GEM_ELEMENT_GAIN * ((flags.is_p_cm << 1) + flags.is_s_cm),
        STAT_GEM_ELEMENT_GAIN * ((flags.is_p_fm << 1) + flags.is_s_fm),
        ELEMENT_GEM_GAIN * ((flags.is_p_ov << 1) + flags.is_s_ov),
    ])


# What one surface's search needs of the genome, the budget and the surface.
SearchContext = ti.types.struct(
    budget=ti.i32,
    max_pp_gems=ti.i32,
    max_cm_gems=ti.i32,
    max_fm_gems=ti.i32,
    cur_pp=ti.i32,
    cur_cm=ti.i32,
    cur_fm=ti.i32,
    base_init=ti.i32,
    w_cm=ti.i32,
    w_fm=ti.i32,
    w_ov=ti.i32,
    flags_idx=ti.i32,
    delta_pp_vs_ov=ti.i32,
    pool_idx=ti.i32,
    shape=ti.types.vector(4, ti.f32),
)


@ti.func
def gems_to_cap(stat: ti.i32, gain: ti.i32) -> ti.i32:
    return ti.max(0, (MAX_STAT - stat + gain - 1) // gain)


@ti.func
def search_context(
    budget: ti.i32, stats: ti.types.vector(7, ti.i32), base_init: ti.i32, flags: GpuColorFlags, pool_idx: ti.i32
) -> SearchContext:
    """The search of surface pool_idx with `budget` gems, for pre-gem stats and base_init: their 2 x primary + secondary."""
    weights = gem_weights(flags)
    allow_pp: ti.i32 = ti.cast((flags.is_p_pp != 0) | (flags.is_s_pp != 0), ti.i32)
    return SearchContext(
        budget=budget,
        max_pp_gems=ti.min(budget, gems_to_cap(stats[0], STAT_GEM_GAIN_NORMAL) * allow_pp),
        max_cm_gems=ti.min(budget, gems_to_cap(stats[1], STAT_GEM_GAIN_NORMAL)),
        max_fm_gems=ti.min(budget, gems_to_cap(stats[2], STAT_GEM_GAIN_FEVER)),
        cur_pp=stats[0],
        cur_cm=stats[1],
        cur_fm=stats[2],
        base_init=base_init,
        w_cm=weights[1],
        w_fm=weights[2],
        w_ov=weights[3],
        # The prefix table's key: its 16 flag combinations.
        flags_idx=(
            ti.cast(flags.is_p_pp != 0, ti.i32) | (ti.cast(flags.is_s_pp != 0, ti.i32) << 1)
            | (ti.cast(flags.is_p_ov != 0, ti.i32) << 2) | (ti.cast(flags.is_s_ov != 0, ti.i32) << 3)
        ),
        delta_pp_vs_ov=weights[0] - weights[3],
        pool_idx=pool_idx,
        shape=fields.grid_frontier_shape_pool[pool_idx],
    )


@ti.func
def _best_pp_gems(ctx: SearchContext, leftover: ti.i32) -> ti.i32:
    """The prefix table's PP gems of `leftover` gems split between PP and element gems: O(1) per (CM, FM) pair instead of
    a scan of the splits."""
    return ti.cast(fields.exact_pp_best_gems_prefix[ctx.flags_idx, _stat_index(ctx.cur_pp), ti.min(ctx.max_pp_gems, leftover)], ti.i32)


@ti.func
def _split_base_value(ctx: SearchContext, g_cm: ti.i32, g_fm: ti.i32, g_pp: ti.i32) -> ti.f32:
    leftover: ti.i32 = ctx.budget - g_cm - g_fm
    pp_extra: ti.f32 = ti.cast(g_pp * ctx.delta_pp_vs_ov, ti.f32) + lookup_ref_pp(ctx.cur_pp + (g_pp * STAT_GEM_GAIN_NORMAL))
    base_linear: ti.i32 = ctx.base_init + (g_cm * ctx.w_cm) + (g_fm * ctx.w_fm) + (leftover * ctx.w_ov)
    return ti.cast(base_linear, ti.f32) + pp_extra


@ti.func
def _pair_base(ctx: SearchContext, g_cm: ti.i32, g_fm: ti.i32) -> ti.f32:
    """A pair's base value, its PP gems from the prefix table."""
    return _split_base_value(ctx, g_cm, g_fm, _best_pp_gems(ctx, ctx.budget - g_cm - g_fm))


@ti.func
def pair_bound(ctx: SearchContext, g_cm: ti.i32, g_fm: ti.i32) -> ti.f32:
    return _pair_base(ctx, g_cm, g_fm) * shape_value(
        ctx.shape, lookup_ref_cm(ctx.cur_cm + (g_cm * STAT_GEM_GAIN_NORMAL)),
        lookup_ref_fm(ctx.cur_fm + (g_fm * STAT_GEM_GAIN_FEVER)),
    ) + _BOUND_MARGIN


@ti.func
def pair_score(ctx: SearchContext, g_cm: ti.i32, g_fm: ti.i32) -> ti.i32:
    """The exact score of a (CM, FM) pair, its PP gems from the prefix table."""
    return _surface_score(
        _pair_base(ctx, g_cm, g_fm), lookup_ref_cm(ctx.cur_cm + (g_cm * STAT_GEM_GAIN_NORMAL)),
        lookup_ref_fm(ctx.cur_fm + (g_fm * STAT_GEM_GAIN_FEVER)), ctx.pool_idx,
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
def _seed_pair(ctx: SearchContext) -> ti.types.vector(2, ti.i32):
    """A (CM, FM) pair near the bound's peak, to start a search from: along a row or column it rises, then falls."""
    seed = ti.Vector([0, 0], dt=ti.i32)
    for axis in ti.static((0, 1, 0, 1)):
        lo = ti.i32(0)
        hi: ti.i32 = ti.min(ctx.max_cm_gems if axis == 0 else ctx.max_fm_gems, ctx.budget - seed[1 - axis])
        while lo < hi:
            seed[axis] = (lo + hi) // 2
            here = pair_bound(ctx, seed[0], seed[1])
            seed[axis] += 1
            if pair_bound(ctx, seed[0], seed[1]) > here:
                lo = seed[axis]
            else:
                hi = seed[axis] - 1
        seed[axis] = lo
    return seed


@ti.func
def surface_search(ctx: SearchContext, floor: ti.i32) -> ti.types.vector(5, ti.i32):
    """The best [score, PP, CM, FM, element gems] on one surface; a pair whose bound is below `floor` (the caller's
    incumbent: a result under it cannot win) is not scored. Without one, a seed pair's score starts the pruning.

    Along a row, an FM gem replaces an element gem and gains less base value (a song's element gem is worth the most), so
    a run's best base value is at its fewest FM gems (PP's share never falls with more leftover) and its highest fever
    multiplier at the most."""
    best = ti.Vector([-1, 0, 0, 0, 0], dt=ti.i32)
    seed = ti.Vector([-1, -1], dt=ti.i32)
    if floor <= 0:
        seed = _seed_pair(ctx)
        g_pp: ti.i32 = _best_pp_gems(ctx, ctx.budget - seed[0] - seed[1])
        best = ti.Vector([pair_score(ctx, seed[0], seed[1]), g_pp, seed[0], seed[1], ctx.budget - seed[0] - seed[1] - g_pp])
    floor_value: ti.f32 = ti.cast(floor, ti.f32)
    g_cm: ti.i32 = 0
    while g_cm <= ctx.max_cm_gems:
        combo_mul: ti.f32 = lookup_ref_cm(ctx.cur_cm + (g_cm * STAT_GEM_GAIN_NORMAL))
        alpha: ti.f32 = (combo_mul * ctx.shape[0]) + ctx.shape[2]
        beta: ti.f32 = (combo_mul * ctx.shape[1]) + ctx.shape[3]
        fm_top: ti.i32 = ti.min(ctx.max_fm_gems, ctx.budget - g_cm)
        # The row is bounded whole, then in runs of _FM_RUN pairs: a run whose bound cannot beat the best so far or
        # reach the floor holds no pair the loop would score.
        g_fm: ti.i32 = 0
        run_end: ti.i32 = fm_top
        while g_fm <= fm_top:
            run_fever: ti.f32 = lookup_ref_fm(ctx.cur_fm + (run_end * STAT_GEM_GAIN_FEVER))
            run_bound: ti.f32 = _pair_base(ctx, g_cm, g_fm) * ((alpha * run_fever) + beta) + _BOUND_MARGIN
            open_run = run_bound > ti.cast(best[0], ti.f32) and run_bound >= floor_value
            if open_run and run_end - g_fm >= _FM_RUN:
                run_end = g_fm + _FM_RUN - 1
                continue
            while open_run and g_fm <= run_end:
                base_value: ti.f32 = _pair_base(ctx, g_cm, g_fm)
                fever_mul: ti.f32 = lookup_ref_fm(ctx.cur_fm + (g_fm * STAT_GEM_GAIN_FEVER))
                bound: ti.f32 = base_value * ((alpha * fever_mul) + beta) + _BOUND_MARGIN
                # The seed was already scored.
                if bound > ti.cast(best[0], ti.f32) and bound >= floor_value and (g_cm != seed[0] or g_fm != seed[1]):
                    score = _surface_score(base_value, combo_mul, fever_mul, ctx.pool_idx)
                    g_pp: ti.i32 = _best_pp_gems(ctx, ctx.budget - g_cm - g_fm)
                    if _improves(score, g_cm, g_fm, g_pp, best):
                        best = ti.Vector([score, g_pp, g_cm, g_fm, ctx.budget - g_cm - g_fm - g_pp])
                g_fm += 1
            g_fm = run_end + 1
            run_end = ti.min(g_fm + _FM_RUN - 1, fm_top)
        g_cm += 1
    return best


@ti.func
def gem_reference(ctx: SearchContext, base: ti.i32, best_score: ti.i32) -> fields.GemReference:
    """The reference of a search over the largest budget of a genome's combos, its best score best_score; `base`: its base
    value without (CM, FM) or PP gems. A pair's value is at most best_score plus the notes' floors, with a margin over the
    float order. A base value that may reach zero bounds nothing: every combo stays."""
    cm_cost: ti.i32 = ctx.w_ov - ctx.w_cm
    fm_cost: ti.i32 = ctx.w_ov - ctx.w_fm
    pp_base: ti.f32 = lookup_ref_pp(ctx.cur_pp)
    # The most PP adds is at the largest leftover (the table's best never falls).
    base_hi: ti.f32 = _split_base_value(ctx, 0, 0, _best_pp_gems(ctx, ctx.budget))
    lowest: ti.i32 = ti.max(base - (ctx.max_cm_gems * cm_cost) - (ctx.max_fm_gems * fm_cost), ctx.base_init)
    base_lo: ti.f32 = ti.cast(lowest, ti.f32) + pp_base
    notes: ti.i32 = (
        fields.grid_frontier_body_fever_pool[ctx.pool_idx] + fields.grid_frontier_body_normal_pool[ctx.pool_idx]
        + fields.song_head_len[0]
    )
    top: ti.f32 = ti.cast(best_score + notes + 64, ti.f32) * 1.00001 if base_lo > 0.0 else 1.0e20
    combo_lo: ti.f32 = lookup_ref_cm(ctx.cur_cm)
    combo_hi: ti.f32 = lookup_ref_cm(ctx.cur_cm + (ctx.max_cm_gems * STAT_GEM_GAIN_NORMAL))
    fever_lo: ti.f32 = lookup_ref_fm(ctx.cur_fm)
    fever_hi: ti.f32 = lookup_ref_fm(ctx.cur_fm + (ctx.max_fm_gems * STAT_GEM_GAIN_FEVER))
    return fields.GemReference(
        base=ti.cast(base, ti.f32),
        scale=top / ti.Vector([
            shape_value(ctx.shape, combo_lo, fever_lo), shape_value(ctx.shape, combo_lo, fever_hi),
            shape_value(ctx.shape, combo_hi, fever_lo), shape_value(ctx.shape, combo_hi, fever_hi),
        ]),
        combo_lo=combo_lo,
        combo_hi=combo_hi,
        fever_lo=fever_lo,
        fever_hi=fever_hi,
        inverse_base_lo=1.0 / ti.max(base_lo, 1.0),
        inverse_base_hi=1.0 / base_hi,
    )


@ti.func
def reference_bound(reference, base: ti.f32, shape: ti.types.vector(4, ti.f32)) -> ti.f32:
    """At least every score of a surface of `shape` on a combo of the genome whose base value without (CM, FM) gems is
    `base`: at any pair its value is the reference's times the ratio of the base values, monotone in the base value, and
    the ratio of the shapes, monotone in each multiplier."""
    offset: ti.f32 = base - reference.base
    return ti.Vector([
        shape_value(shape, reference.combo_lo, reference.fever_lo) * reference.scale[0],
        shape_value(shape, reference.combo_lo, reference.fever_hi) * reference.scale[1],
        shape_value(shape, reference.combo_hi, reference.fever_lo) * reference.scale[2],
        shape_value(shape, reference.combo_hi, reference.fever_hi) * reference.scale[3],
    ]).max() * ti.max(1.0 + (offset * reference.inverse_base_lo), 1.0 + (offset * reference.inverse_base_hi))


@ti.func
def exact_gem_search(
    option: ti.types.vector(4, ti.i32),
    stats: ti.types.vector(7, ti.i32),
    flags: GpuColorFlags,
    floor: ti.i32,
    reference,
) -> ti.types.vector(5, ti.i32):
    """The best gem allocation over the surfaces of a combo (`option`: kernels._combo_option; the first surface wins a
    tie), skipping a surface whose bound by the genome's reference is below `floor`: a result under it cannot win."""
    result = ti.Vector([-1, 0, 0, 0, 0], dt=ti.i32)
    budget, base_init = option[2], option[3]
    base: ti.f32 = ti.cast(base_init + (budget * gem_weights(flags)[3]), ti.f32)
    for pool_idx in range(option[0], option[0] + option[1]):
        if reference_bound(reference, base, fields.grid_frontier_shape_pool[pool_idx]) >= ti.cast(floor, ti.f32):
            candidate = surface_search(search_context(budget, stats, base_init, flags, pool_idx), floor)
            if candidate[0] > result[0]:
                result = candidate
    return result
