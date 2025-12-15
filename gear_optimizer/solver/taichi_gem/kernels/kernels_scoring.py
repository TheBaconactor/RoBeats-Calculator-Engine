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
def _calc_body_score(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.f32:
    """
    Calculate score for body notes (notes past the head).

    Body notes are at full combo, so no ramping. Just multiply base score
    by combo and fever multipliers.

    Args:
        base_value: (primary*2) + secondary + pp_factor
        combo_mul: Combo multiplier
        fever_mul: Fever multiplier
        count_fever: Number of fever notes in body
        count_normal: Number of normal notes in body

    Returns:
        Body score as float
    """
    combo_val = ti.floor(base_value * combo_mul)
    fever_val = ti.floor(base_value * combo_mul * fever_mul)
    return (ti.cast(count_fever, ti.f32) * fever_val) + (
        ti.cast(count_normal, ti.f32) * combo_val
    )


@ti.func
def _calc_head_factor(base_value: ti.f32, combo_mul: ti.f32) -> ti.f32:
    """
    Calculate combo ramp factor for head notes.

    The head (first 100 notes) has ramping combo multiplier.
    Factor is added per note: score[i] = base_value + (i * factor)

    Args:
        base_value: Base score value
        combo_mul: Combo multiplier at full combo

    Returns:
        Ramp factor per note
    """
    return (combo_mul - 1.0) * base_value / 100.0


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
    head_score = 0.0
    for i in range(head_len):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        if kernels_helpers.fever_masks[work_idx, i] != 0:
            head_score += ti.floor(ramp_val * fever_mul)
        else:
            head_score += ti.floor(ramp_val)
    return head_score


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
    head_score = 0.0
    for i in range(head_len):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        if kernels_helpers.grid_fever_masks[song_slot, ft_idx, ff_idx, i] != 0:
            head_score += ti.floor(ramp_val * fever_mul)
        else:
            head_score += ti.floor(ramp_val)
    return head_score


@ti.func
def _calc_head_score_bits(
    base_value: ti.f32,
    factor: ti.f32,
    fever_mul: ti.f32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
    head_len: ti.i32,
) -> ti.f32:
    """
    Calculate head score using bitpacked fever masks.

    More efficient than grid lookup - masks passed as 4×u32 = 128 bits.
    Bit i corresponds to head note i being a fever note.

    Args:
        base_value: Base score value
        factor: Combo ramp factor
        fever_mul: Fever multiplier
        m0: Bits 0-31 (notes 0-31)
        m1: Bits 32-63 (notes 32-63)
        m2: Bits 64-95 (notes 64-95)
        m3: Bits 96-127 (notes 96-99 used)
        head_len: Number of notes in head

    Returns:
        Head score as float
    """
    head_score = 0.0
    for i in range(head_len):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        word = ti.u32(0)
        shift = ti.u32(i & 31)

        if i < 32:
            word = m0
        elif i < 64:
            word = m1
        elif i < 96:
            word = m2
        else:
            word = m3

        is_fever = (word >> shift) & ti.u32(1)
        if is_fever != 0:
            head_score += ti.floor(ramp_val * fever_mul)
        else:
            head_score += ti.floor(ramp_val)
    return head_score


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
    body_score = _calc_body_score(
        base_value, combo_mul, fever_mul, count_fever, count_normal
    )
    factor = _calc_head_factor(base_value, combo_mul)
    head_score = _calc_head_score_masks(base_value, factor, fever_mul, work_idx, head_len)
    return ti.cast(body_score + head_score, ti.i32)


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
    body_score = _calc_body_score(
        base_value, combo_mul, fever_mul, count_fever, count_normal
    )
    factor = _calc_head_factor(base_value, combo_mul)
    head_score = _calc_head_score_grid(
        base_value, factor, fever_mul, song_slot, ft_idx, ff_idx, head_len
    )
    return ti.cast(body_score + head_score, ti.i32)


@ti.func
def calc_score_with_grid_bits(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    """
    Score calculation using bitpacked fever masks (4x u32 = 128 bits).
    Bit i corresponds to head note i being a fever note.

    More efficient than grid lookup for repeated score calculations
    in optimize_core_device.

    Args:
        base_value: (primary*2) + secondary + pp_factor
        combo_mul: Combo multiplier
        fever_mul: Fever multiplier
        m0-m3: Bitpacked fever masks (4×32 bits)
        head_len: Number of notes in head
        count_fever: Fever notes in body
        count_normal: Normal notes in body

    Returns:
        Total score as int32
    """
    body_score = _calc_body_score(
        base_value, combo_mul, fever_mul, count_fever, count_normal
    )
    factor = _calc_head_factor(base_value, combo_mul)
    head_score = _calc_head_score_bits(base_value, factor, fever_mul, m0, m1, m2, m3, head_len)
    return ti.cast(body_score + head_score, ti.i32)


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
        score = calc_score_device(
            base_value, combo_mul, fever_mul, work_idx, head_len, count_fever, count_normal
        )
    else:
        score = calc_score_with_grid_bits(
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
def optimize_core_device(
    work_idx: ti.i32,
    budget: ti.i32,
    cur_pp: ti.i32,
    cur_cm: ti.i32,
    cur_fm: ti.i32,
    cur_p_val: ti.i32,
    cur_s_val: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
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
    GEM_SCALE_NORMAL: ti.i32 = 2
    GEM_SCALE_FEVER: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
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
    PP_TIE_LOOKAHEAD_MAX: ti.i32 = 8

    # Mutable state
    pp: ti.i32 = cur_pp
    cm: ti.i32 = cur_cm
    fm: ti.i32 = cur_fm
    p_val: ti.i32 = cur_p_val
    s_val: ti.i32 = cur_s_val

    best_final_score: ti.i32 = 0

    while remaining > 0:
        fill_budget: ti.i32 = remaining - 1
        fill_bonus: ti.i32 = fill_budget * ELEMENTAL_GEM_SCALE if fill_budget > 0 else 0

        # Precompute current multipliers (unchanged for PP/OV checks)
        c_mul_cur: ti.f32 = kernels_helpers.lookup_ref_cm(cm)
        f_mul_cur: ti.f32 = kernels_helpers.lookup_ref_fm(fm)

        # Start with OV as default so OV wins exact ties.
        t_p: ti.i32 = p_val + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
        t_s: ti.i32 = s_val + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
        pp_factor: ti.f32 = kernels_helpers.lookup_ref_pp(pp)
        base: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
        best_score: ti.i32 = calc_score_cached_device(
            mode, base, c_mul_cur, f_mul_cur, work_idx, head_len, count_fever, count_normal, m0, m1, m2, m3
        )
        best_opt: ti.i32 = 3

        pp_score: ti.i32 = -1

        # Option 0: PP gem
        if pp < MAX_STAT:
            t_pp: ti.i32 = pp + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus * is_s_ov)
            pp_factor = kernels_helpers.lookup_ref_pp(t_pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            pp_score = calc_score_cached_device(
                mode, base, c_mul_cur, f_mul_cur, work_idx, head_len, count_fever, count_normal, m0, m1, m2, m3
            )
            if pp_score > best_score:
                best_score = pp_score
                best_opt = 0

        # Option 1: CM gem
        if cm < MAX_STAT:
            t_cm: ti.i32 = cm + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_cm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_cm) + (fill_bonus * is_s_ov)
            pp_factor = kernels_helpers.lookup_ref_pp(pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            c_mul: ti.f32 = kernels_helpers.lookup_ref_cm(t_cm)
            score: ti.i32 = calc_score_cached_device(
                mode, base, c_mul, f_mul_cur, work_idx, head_len, count_fever, count_normal, m0, m1, m2, m3
            )
            if score > best_score:
                best_score = score
                best_opt = 1

        # Option 2: FM gem
        if fm < MAX_STAT:
            t_fm: ti.i32 = fm + GEM_SCALE_FEVER
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_fm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_fm) + (fill_bonus * is_s_ov)
            pp_factor = kernels_helpers.lookup_ref_pp(pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            f_mul: ti.f32 = kernels_helpers.lookup_ref_fm(t_fm)
            score = calc_score_cached_device(
                mode, base, c_mul_cur, f_mul, work_idx, head_len, count_fever, count_normal, m0, m1, m2, m3
            )
            if score > best_score:
                best_score = score
                best_opt = 2

        # PP lookahead: if OV wins a tie now, but a few PP gems would become a real
        # improvement soon, start investing in PP.
        if best_opt == 3 and pp_score == best_score and remaining > 1:
            max_k: ti.i32 = remaining
            if max_k > PP_TIE_LOOKAHEAD_MAX:
                max_k = PP_TIE_LOOKAHEAD_MAX
            k: ti.i32 = 2
            while k <= max_k:
                fill_bonus_k: ti.i32 = (remaining - k) * ELEMENTAL_GEM_SCALE
                t_pp: ti.i32 = pp + (k * GEM_SCALE_NORMAL)
                t_p = p_val + (k * GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus_k * is_p_ov)
                t_s = s_val + (k * GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus_k * is_s_ov)
                pp_factor = kernels_helpers.lookup_ref_pp(t_pp)
                base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                score_k: ti.i32 = calc_score_cached_device(
                    mode, base, c_mul_cur, f_mul_cur, work_idx, head_len, count_fever, count_normal, m0, m1, m2, m3
                )
                if score_k > best_score:
                    best_opt = 0
                    break
                k += 1

        # Apply best option
        if best_opt == 0:
            pp += GEM_SCALE_NORMAL
            p_val += GEM_STAT_TO_ELEMENT * is_p_pp
            s_val += GEM_STAT_TO_ELEMENT * is_s_pp
            gems_pp += 1
        elif best_opt == 1:
            cm += GEM_SCALE_NORMAL
            p_val += GEM_STAT_TO_ELEMENT * is_p_cm
            s_val += GEM_STAT_TO_ELEMENT * is_s_cm
            gems_cm += 1
        elif best_opt == 2:
            fm += GEM_SCALE_FEVER
            p_val += GEM_STAT_TO_ELEMENT * is_p_fm
            s_val += GEM_STAT_TO_ELEMENT * is_s_fm
            gems_fm += 1
        else:
            p_val += ELEMENTAL_GEM_SCALE * is_p_ov
            s_val += ELEMENTAL_GEM_SCALE * is_s_ov
            gems_ov += 1

        remaining -= 1
        best_final_score = best_score

    return ti.Vector([best_final_score, gems_pp, gems_cm, gems_fm, gems_ov, p_val, s_val])
