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

from . import kernels_helpers


@ti.func
def _calc_head_score_masks(
    base_value: ti.f32,
    factor: ti.f32,
    fever_mul: ti.f32,
    work_idx: ti.i32,
    head_len: ti.i32,
) -> ti.f32:
    """
    Calculate head score using per-work-item fever masks.

    Iterates through first head_len notes, applying combo ramp and
    fever multiplier where applicable.

    Args:
        base_value: Base score value
        factor: Combo ramp factor
        fever_mul: Fever multiplier
        work_idx: Work item index (for fever_masks lookup)
        head_len: Number of notes in head (<= 100)

    Returns:
        Head score as float
    """
    head_score = ti.i32(0)
    for i in range(head_len):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        if kernels_helpers.fever_masks[work_idx, i] != 0:
            # All values are non-negative; truncation toward zero matches floor and is faster.
            head_score += ti.cast(ramp_val * fever_mul, ti.i32)
        else:
            head_score += ti.cast(ramp_val, ti.i32)
    return ti.cast(head_score, ti.f32)


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
    head_score = ti.i32(0)
    for i in range(head_len):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        if kernels_helpers.grid_fever_masks[song_slot, ft_idx, ff_idx, i] != 0:
            # All values are non-negative; truncation toward zero matches floor and is faster.
            head_score += ti.cast(ramp_val * fever_mul, ti.i32)
        else:
            head_score += ti.cast(ramp_val, ti.i32)
    return ti.cast(head_score, ti.f32)


@ti.func
def calc_score_device(
    base_value: ti.f32,  # Changed to f32 for performance
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    work_idx: ti.i32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    """
    GPU port of fast_calculate_score (scoring_core.py:48-96).

    Calculates total score by:
    1. Body score: simple multiply (all notes past head at full combo)
    2. Head score: ramped combo scaling for first head_len notes

    Args:
        base_value: (primary*2) + secondary + pp_factor
        combo_mul: Combo multiplier from lookup
        fever_mul: Fever multiplier from lookup
        work_idx: Index into fever_masks for this work item
        head_len: Number of notes in the head (<=100)
        count_fever: Fever notes in body
        count_normal: Normal notes in body

    Returns:
        Total score as int32
    """
    body_score = kernels_helpers._calc_body_score(base_value, combo_mul, fever_mul, count_fever, count_normal)
    factor = kernels_helpers._calc_head_factor(base_value, combo_mul)
    head_score = _calc_head_score_masks(base_value, factor, fever_mul, work_idx, head_len)
    # Cast each component to i32 first, then add as integers for exact result
    return ti.cast(body_score, ti.i32) + ti.cast(head_score, ti.i32)


@ti.func
def calc_score_with_grid(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    song_slot: ti.i32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    """
    Score calculation using grid-stored fever masks.
    Reads fever mask from grid_fever_masks[ft_idx, ff_idx, :].

    Args:
        base_value: (primary*2) + secondary + pp_factor
        combo_mul: Combo multiplier
        fever_mul: Fever multiplier
        song_slot: Song slot in grid
        ft_idx: FT stat index
        ff_idx: FF stat index
        head_len: Number of notes in head
        count_fever: Fever notes in body
        count_normal: Normal notes in body

    Returns:
        Total score as int32
    """
    body_score = kernels_helpers._calc_body_score(base_value, combo_mul, fever_mul, count_fever, count_normal)
    factor = kernels_helpers._calc_head_factor(base_value, combo_mul)
    head_score = _calc_head_score_grid(base_value, factor, fever_mul, song_slot, ft_idx, ff_idx, head_len)
    # Cast each component to i32 first, then add as integers for exact result
    return ti.cast(body_score, ti.i32) + ti.cast(head_score, ti.i32)


@ti.func
def calc_score_cached_device(
    mode: ti.i32,
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    work_idx: ti.i32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
) -> ti.i32:
    """
    Score calculation with cached bitmasks.

    For mode=1, callers pass the preloaded grid bitmasks (m0..m3) so we don't
    re-read grid_fever_masks_bits from global memory for every option check.

    This is a critical optimization for optimize_core_device which evaluates
    4 gem options per iteration (16 score calculations for lookahead).

    Args:
        mode: 0=work-item masks, 1=cached grid bitmasks
        base_value: (primary*2) + secondary + pp_factor
        combo_mul: Combo multiplier
        fever_mul: Fever multiplier
        work_idx: Work item index (mode=0 only)
        head_len: Number of notes in head
        count_fever: Fever notes in body
        count_normal: Normal notes in body
        m0-m3: Cached bitpacked masks (mode=1 only)

    Returns:
        Total score as int32
    """
    score: ti.i32 = 0
    if mode == 0:
        score = calc_score_device(base_value, combo_mul, fever_mul, work_idx, head_len, count_fever, count_normal)
    else:
        score = kernels_helpers.calc_score_with_grid_bits(
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
    return score


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
    MAX_ITER: ti.i32 = 20  # gear_optimizer.core.constants.LOCAL_SEARCH_MAX_ITERATIONS

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
def optimize_core_device(
    work_idx: ti.i32,
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
    mode: ti.i32,
    song_slot: ti.i32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
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
        work_idx: Work item index (for mode=0 fever mask lookup)
        budget: Number of gems to allocate
        cur_pp, cur_cm, cur_fm: Current stat values
        cur_p_val, cur_s_val: Current primary/secondary elemental values
        is_p_*, is_s_*: Color contribution flags (0/1)
        head_len: Number of notes in head
        count_fever, count_normal: Body note counts
        mode: 0=work-item masks, 1=grid bitmasks
        song_slot, ft_idx, ff_idx: Grid indices (mode=1 only)

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
    if mode != 0:
        # Cache bitpacked head mask once per work item to avoid repeated global loads.
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

    while remaining > 0:
        # Evaluate each "pick 1 gem now, fill the rest with OV" option.
        # remaining > 0 here, so (remaining - 1) is always non-negative.
        fill_bonus: ti.i32 = (remaining - 1) * ELEMENTAL_GEM_SCALE
        fill_p: ti.i32 = fill_bonus * is_p_ov
        fill_s: ti.i32 = fill_bonus * is_s_ov
        base_p: ti.i32 = p_val + fill_p
        base_s: ti.i32 = s_val + fill_s

        # Track "next" multipliers for the option we actually apply.
        # Defaults: unchanged from current.
        c_mul_next: ti.f32 = c_mul_cur
        f_mul_next: ti.f32 = f_mul_cur
        pp_factor_next: ti.f32 = pp_factor_cur

        # Start with OV as default so OV wins exact ties.
        t_p: ti.i32 = base_p + ov_p_delta
        t_s: ti.i32 = base_s + ov_s_delta
        base: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor_cur
        best_score: ti.i32 = calc_score_cached_device(
            mode, base, c_mul_cur, f_mul_cur, work_idx, head_len, count_fever, count_normal, m0, m1, m2, m3
        )
        best_opt: ti.i32 = 3

        pp_score: ti.i32 = -1

        # Option 0: PP gem
        # Optimization: Skip PP if Chill is not in Primary/Secondary
        if allow_pp != 0 and pp < MAX_STAT:
            t_p = base_p + pp_p_delta
            t_s = base_s + pp_s_delta
            pp_factor_pp: ti.f32 = kernels_helpers.lookup_ref_pp(pp + GEM_SCALE_NORMAL)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor_pp
            pp_score = calc_score_cached_device(
                mode, base, c_mul_cur, f_mul_cur, work_idx, head_len, count_fever, count_normal, m0, m1, m2, m3
            )
            if pp_score > best_score:
                best_score = pp_score
                best_opt = 0
                pp_factor_next = pp_factor_pp

        # Option 1: CM gem
        if cm < MAX_STAT and (cm <= 50 or is_p_cm or is_s_cm):
            t_p = base_p + cm_p_delta
            t_s = base_s + cm_s_delta
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor_cur
            c_mul: ti.f32 = kernels_helpers.lookup_ref_cm(cm + GEM_SCALE_NORMAL)
            score: ti.i32 = calc_score_cached_device(
                mode, base, c_mul, f_mul_cur, work_idx, head_len, count_fever, count_normal, m0, m1, m2, m3
            )
            if score > best_score:
                best_score = score
                best_opt = 1
                c_mul_next = c_mul

        # Option 2: FM gem
        if fm < MAX_STAT:
            t_p = base_p + fm_p_delta
            t_s = base_s + fm_s_delta
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor_cur
            f_mul: ti.f32 = kernels_helpers.lookup_ref_fm(fm + GEM_SCALE_FEVER)
            score = calc_score_cached_device(
                mode, base, c_mul_cur, f_mul, work_idx, head_len, count_fever, count_normal, m0, m1, m2, m3
            )
            if score > best_score:
                best_score = score
                best_opt = 2
                f_mul_next = f_mul

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
                    mode, base, c_mul_cur, f_mul_cur, work_idx, head_len, count_fever, count_normal, m0, m1, m2, m3
                )
                if score_k > best_score:
                    best_opt = 0
                    # When we commit to PP, the next PP factor should match the +1 PP gem update.
                    # (pp_score was computed using pp + GEM_SCALE_NORMAL when allow_pp != 0.)
                    pp_factor_next = kernels_helpers.lookup_ref_pp(pp + GEM_SCALE_NORMAL)
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
