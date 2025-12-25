"""
ForceGreatsFinder GPU kernels (Taichi).

This module contains ONLY the FG finder kernels and their helper @ti.func's.
It reuses the shared scoring helpers from `gear_optimizer.solver.taichi_gem.kernels`
(reference lookups + score calculation).

Fields are bound at runtime via `force_greats.fields.bind_fields()`.
"""

import taichi as ti

from ..kernels import kernels_helpers
from .fields import FG_MAX_SECTIONS


# ============================================================================
# FIELD PLACEHOLDERS (bound by force_greats.fields.bind_fields)
# ============================================================================

song_timestamps = None
song_timestamps_great_candidate = None
fg_forced_counts = None
fg_pair_caps = None
fg_ft_list = None
fg_ff_list = None

fg_best_final_score = None
fg_best_base_score = None
fg_best_cfg_idx = None
fg_best_ft = None
fg_best_ff = None
fg_best_g_pp = None
fg_best_g_cm = None
fg_best_g_fm = None
fg_best_g_ov = None
fg_best_score_penalty = None
fg_best_fill_penalty = None

fg_stage1_final_score = None
fg_stage1_base_score = None
fg_stage1_cfg_idx = None
fg_stage1_g_pp = None
fg_stage1_g_cm = None
fg_stage1_g_fm = None
fg_stage1_g_ov = None
fg_stage1_score_penalty = None
fg_stage1_fill_penalty = None

# Flat work items (GPU-friendly parallelization)
fg_flat_work_genome = None
fg_flat_work_ftff = None

# Packed 64-bit field for atomic (score, cfg_idx) updates
fg_stage1_packed = None

# Global best fields for GPU-resident accumulation (persist across group calls)
fg_global_best_final_score = None
fg_global_best_base_score = None
fg_global_best_cfg_idx = None
fg_global_best_ft = None
fg_global_best_ff = None
fg_global_best_g_pp = None
fg_global_best_g_cm = None
fg_global_best_g_fm = None
fg_global_best_g_ov = None
fg_global_best_score_penalty = None
fg_global_best_fill_penalty = None

# Warm-start hint allocation (bound from fields.py)
fg_genome_hint_allocation = None


# ============================================================================
# HELPERS
# ============================================================================

@ti.func
def _optimize_core_bits(
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
) -> ti.types.vector(10, ti.i32):
    """
    Greedy gem allocation optimizer (bitmask head scoring).

    Returns vector:
      [score, pp, cm, fm, p_val, s_val, g_pp, g_cm, g_fm, g_ov]
    """
    GEM_SCALE_NORMAL: ti.i32 = 2
    GEM_SCALE_FEVER: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    PP_TIE_LOOKAHEAD_MAX: ti.i32 = 8

    gems_pp: ti.i32 = 0
    gems_cm: ti.i32 = 0
    gems_fm: ti.i32 = 0
    gems_ov: ti.i32 = 0
    remaining: ti.i32 = budget

    pp: ti.i32 = cur_pp
    cm: ti.i32 = cur_cm
    fm: ti.i32 = cur_fm
    p_val: ti.i32 = cur_p_val
    s_val: ti.i32 = cur_s_val

    best_final_score: ti.i32 = 0

    while remaining > 0:
        fill_budget: ti.i32 = remaining - 1
        fill_bonus: ti.i32 = fill_budget * ELEMENTAL_GEM_SCALE if fill_budget > 0 else 0

        c_mul_cur: ti.f32 = kernels_helpers.lookup_ref_cm(cm)
        f_mul_cur: ti.f32 = kernels_helpers.lookup_ref_fm(fm)

        # OV wins exact ties by default
        t_p: ti.i32 = p_val + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
        t_s: ti.i32 = s_val + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
        pp_factor: ti.f32 = kernels_helpers.lookup_ref_pp(pp)
        base: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
        best_score: ti.i32 = kernels_helpers.calc_score_with_grid_bits(
            base, c_mul_cur, f_mul_cur, m0, m1, m2, m3, head_len, count_fever, count_normal
        )
        best_opt: ti.i32 = 3

        pp_score: ti.i32 = -1

        # PP gem
        if pp < MAX_STAT:
            t_pp: ti.i32 = pp + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus * is_s_ov)
            pp_factor = kernels_helpers.lookup_ref_pp(t_pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            pp_score = kernels_helpers.calc_score_with_grid_bits(
                base, c_mul_cur, f_mul_cur, m0, m1, m2, m3, head_len, count_fever, count_normal
            )
            if pp_score > best_score:
                best_score = pp_score
                best_opt = 0

        # CM gem
        if cm < MAX_STAT:
            t_cm: ti.i32 = cm + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_cm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_cm) + (fill_bonus * is_s_ov)
            pp_factor = kernels_helpers.lookup_ref_pp(pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            c_mul: ti.f32 = kernels_helpers.lookup_ref_cm(t_cm)
            score: ti.i32 = kernels_helpers.calc_score_with_grid_bits(
                base, c_mul, f_mul_cur, m0, m1, m2, m3, head_len, count_fever, count_normal
            )
            if score > best_score:
                best_score = score
                best_opt = 1

        # FM gem
        if fm < MAX_STAT:
            t_fm: ti.i32 = fm + GEM_SCALE_FEVER
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_fm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_fm) + (fill_bonus * is_s_ov)
            pp_factor = kernels_helpers.lookup_ref_pp(pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            f_mul: ti.f32 = kernels_helpers.lookup_ref_fm(t_fm)
            score = kernels_helpers.calc_score_with_grid_bits(
                base, c_mul_cur, f_mul, m0, m1, m2, m3, head_len, count_fever, count_normal
            )
            if score > best_score:
                best_score = score
                best_opt = 2

        # PP lookahead (optional)
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
                score_k: ti.i32 = kernels_helpers.calc_score_with_grid_bits(
                    base, c_mul_cur, f_mul_cur, m0, m1, m2, m3, head_len, count_fever, count_normal
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

    return ti.Vector(
        [
            best_final_score,
            pp,
            cm,
            fm,
            p_val,
            s_val,
            gems_pp,
            gems_cm,
            gems_fm,
            gems_ov,
        ]
    )


@ti.func
def _forced_from_fp_target(
    raw_fill: ti.f32,
    base_ceil: ti.i32,
    fp_target: ti.i32,
    non_fever_base: ti.i32,
) -> ti.i32:
    """
    Convert a fill-penalty target into the minimal forced great count.

    Uses: ceil(raw_fill + 0.5*k) - ceil(raw_fill) >= fp_target
    """
    forced_val: ti.i32 = 0
    if fp_target > 0:
        delta: ti.f32 = (ti.cast(base_ceil, ti.f32) + ti.cast(fp_target, ti.f32) - 1.0) - raw_fill
        if delta >= 0.0:
            forced_val = ti.cast(ti.floor(delta * 2.0), ti.i32) + 1
    if forced_val > non_fever_base:
        forced_val = non_fever_base
    return forced_val


@ti.func
def _get_fill_penalty_analytical(
    forced_count: ti.i32,
    raw_fever_fill: ti.f32,
    is_section_1: ti.i32,
) -> ti.i32:
    """
    Calculate fill penalty in notes using analytical formula.
    
    EXACTLY matches CPU analytical_fg.get_fill_penalty().
    Direct formula: fill_penalty = ceil(raw_base + forced*0.5) - ceil(raw_base)
    
    This function provides CPU/GPU parity and fixes off-by-one errors
    in section 1 that occur with the inverse _forced_from_fp_target() approach.
    
    Args:
        forced_count: Number of forced greats in this section
        raw_fever_fill: Raw fever fill value (non_fever_cas * ff_factor)
        is_section_1: 1 if section 1, 0 otherwise (applies -1 offset)
    
    Returns:
        Fill penalty in notes (extra notes needed to reach fever)
    """
    if forced_count <= 0:
        return 0
    
    # Calculate raw penalty and total notes needed
    penalty_raw: ti.f32 = ti.cast(forced_count, ti.f32) * 0.5
    notes_with_penalty: ti.f32 = raw_fever_fill + penalty_raw
    
    # Apply ceiling to both values
    ceiled_with_penalty: ti.i32 = ti.cast(ti.ceil(notes_with_penalty), ti.i32)
    ceiled_base: ti.i32 = ti.cast(ti.ceil(raw_fever_fill), ti.i32)
    
    # Section 1 adjustment (indexing offset)
    # This handles the "first section uses base-1" rule
    if is_section_1 == 1:
        ceiled_with_penalty -= 1
        ceiled_base -= 1
    
    # Fill penalty is the delta between adjusted values
    fill_penalty: ti.i32 = ti.max(0, ceiled_with_penalty - ceiled_base)
    return fill_penalty


@ti.func
def _local_search_bits_from_hint(
    hint_pp: ti.i32, hint_cm: ti.i32, hint_fm: ti.i32, hint_ov: ti.i32,
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
) -> ti.types.vector(10, ti.i32):
    """
    Local search gem allocation from warm-start hint.
    
    Instead of 90 iterations of greedy allocation, starts from hint and
    tries ±1 gem swaps until no improvement found (typically <20 iterations).
    
    Returns same vector as _optimize_core_bits:
      [score, pp, cm, fm, p_val, s_val, g_pp, g_cm, g_fm, g_ov]
    """
    GEM_SCALE_NORMAL: ti.i32 = 2
    GEM_SCALE_FEVER: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    MAX_ITER: ti.i32 = 20
    
    # Clamp hints to valid ranges
    gems_pp: ti.i32 = ti.max(0, hint_pp)
    gems_cm: ti.i32 = ti.max(0, hint_cm)
    gems_fm: ti.i32 = ti.max(0, hint_fm)
    gems_ov: ti.i32 = ti.max(0, hint_ov)
    
    # Clamp total to budget
    total: ti.i32 = gems_pp + gems_cm + gems_fm + gems_ov
    if total > budget:
        # Scale down proportionally
        scale: ti.f32 = ti.cast(budget, ti.f32) / ti.cast(total, ti.f32)
        gems_pp = ti.cast(ti.floor(ti.cast(gems_pp, ti.f32) * scale), ti.i32)
        gems_cm = ti.cast(ti.floor(ti.cast(gems_cm, ti.f32) * scale), ti.i32)
        gems_fm = ti.cast(ti.floor(ti.cast(gems_fm, ti.f32) * scale), ti.i32)
        gems_ov = budget - gems_pp - gems_cm - gems_fm
        if gems_ov < 0:
            gems_ov = 0
            if gems_fm > 0:
                gems_fm = ti.max(0, gems_fm + (budget - gems_pp - gems_cm - gems_fm))
            elif gems_cm > 0:
                gems_cm = ti.max(0, budget - gems_pp)
                gems_fm = 0
            else:
                gems_pp = budget
                gems_cm = 0
                gems_fm = 0
    elif total < budget:
        # Fill remainder with overflow gems
        gems_ov += (budget - total)
    
    # Clamp stats to MAX_STAT
    max_pp_gems: ti.i32 = (MAX_STAT - cur_pp) // GEM_SCALE_NORMAL
    max_cm_gems: ti.i32 = (MAX_STAT - cur_cm) // GEM_SCALE_NORMAL
    max_fm_gems: ti.i32 = (MAX_STAT - cur_fm) // GEM_SCALE_FEVER
    if gems_pp > max_pp_gems:
        excess: ti.i32 = gems_pp - max_pp_gems
        gems_pp = max_pp_gems
        gems_ov += excess
    if gems_cm > max_cm_gems:
        excess = gems_cm - max_cm_gems
        gems_cm = max_cm_gems
        gems_ov += excess
    if gems_fm > max_fm_gems:
        excess = gems_fm - max_fm_gems
        gems_fm = max_fm_gems
        gems_ov += excess
    
    # Compute initial stats from allocation
    pp: ti.i32 = cur_pp + gems_pp * GEM_SCALE_NORMAL
    cm: ti.i32 = cur_cm + gems_cm * GEM_SCALE_NORMAL
    fm: ti.i32 = cur_fm + gems_fm * GEM_SCALE_FEVER
    p_val: ti.i32 = cur_p_val + (gems_pp * GEM_STAT_TO_ELEMENT * is_p_pp) + \
                     (gems_cm * GEM_STAT_TO_ELEMENT * is_p_cm) + \
                     (gems_fm * GEM_STAT_TO_ELEMENT * is_p_fm) + \
                     (gems_ov * ELEMENTAL_GEM_SCALE * is_p_ov)
    s_val: ti.i32 = cur_s_val + (gems_pp * GEM_STAT_TO_ELEMENT * is_s_pp) + \
                     (gems_cm * GEM_STAT_TO_ELEMENT * is_s_cm) + \
                     (gems_fm * GEM_STAT_TO_ELEMENT * is_s_fm) + \
                     (gems_ov * ELEMENTAL_GEM_SCALE * is_s_ov)
    
    # Calculate initial score
    c_mul: ti.f32 = kernels_helpers.lookup_ref_cm(cm)
    f_mul: ti.f32 = kernels_helpers.lookup_ref_fm(fm)
    pp_factor: ti.f32 = kernels_helpers.lookup_ref_pp(pp)
    base: ti.f32 = ti.cast((p_val * 2) + s_val, ti.f32) + pp_factor
    best_score: ti.i32 = kernels_helpers.calc_score_with_grid_bits(
        base, c_mul, f_mul, m0, m1, m2, m3, head_len, count_fever, count_normal
    )
    
    # Local search: try swapping gems
    improved: ti.i32 = 1
    iteration: ti.i32 = 0
    
    while improved != 0 and iteration < MAX_ITER:
        improved = 0
        iteration += 1
        
        # Try all 12 swap combinations (4 remove × 3 add)
        for remove_type in range(4):
            for add_type in range(4):
                if remove_type == add_type:
                    continue
                
                # Check if swap is valid
                can_remove: ti.i32 = 0
                can_add: ti.i32 = 0
                
                if remove_type == 0 and gems_pp > 0:
                    can_remove = 1
                elif remove_type == 1 and gems_cm > 0:
                    can_remove = 1
                elif remove_type == 2 and gems_fm > 0:
                    can_remove = 1
                elif remove_type == 3 and gems_ov > 0:
                    can_remove = 1
                
                if add_type == 0 and pp + GEM_SCALE_NORMAL <= MAX_STAT:
                    can_add = 1
                elif add_type == 1 and cm + GEM_SCALE_NORMAL <= MAX_STAT:
                    can_add = 1
                elif add_type == 2 and fm + GEM_SCALE_FEVER <= MAX_STAT:
                    can_add = 1
                elif add_type == 3:
                    can_add = 1  # OV has no cap
                
                if can_remove == 0 or can_add == 0:
                    continue
                
                # Calculate new stats
                new_pp: ti.i32 = pp
                new_cm: ti.i32 = cm
                new_fm: ti.i32 = fm
                new_p: ti.i32 = p_val
                new_s: ti.i32 = s_val
                
                # Remove gem
                if remove_type == 0:
                    new_pp -= GEM_SCALE_NORMAL
                    new_p -= GEM_STAT_TO_ELEMENT * is_p_pp
                    new_s -= GEM_STAT_TO_ELEMENT * is_s_pp
                elif remove_type == 1:
                    new_cm -= GEM_SCALE_NORMAL
                    new_p -= GEM_STAT_TO_ELEMENT * is_p_cm
                    new_s -= GEM_STAT_TO_ELEMENT * is_s_cm
                elif remove_type == 2:
                    new_fm -= GEM_SCALE_FEVER
                    new_p -= GEM_STAT_TO_ELEMENT * is_p_fm
                    new_s -= GEM_STAT_TO_ELEMENT * is_s_fm
                else:
                    new_p -= ELEMENTAL_GEM_SCALE * is_p_ov
                    new_s -= ELEMENTAL_GEM_SCALE * is_s_ov
                
                # Add gem
                if add_type == 0:
                    new_pp += GEM_SCALE_NORMAL
                    new_p += GEM_STAT_TO_ELEMENT * is_p_pp
                    new_s += GEM_STAT_TO_ELEMENT * is_s_pp
                elif add_type == 1:
                    new_cm += GEM_SCALE_NORMAL
                    new_p += GEM_STAT_TO_ELEMENT * is_p_cm
                    new_s += GEM_STAT_TO_ELEMENT * is_s_cm
                elif add_type == 2:
                    new_fm += GEM_SCALE_FEVER
                    new_p += GEM_STAT_TO_ELEMENT * is_p_fm
                    new_s += GEM_STAT_TO_ELEMENT * is_s_fm
                else:
                    new_p += ELEMENTAL_GEM_SCALE * is_p_ov
                    new_s += ELEMENTAL_GEM_SCALE * is_s_ov
                
                # Calculate new score
                new_c_mul: ti.f32 = kernels_helpers.lookup_ref_cm(new_cm)
                new_f_mul: ti.f32 = kernels_helpers.lookup_ref_fm(new_fm)
                new_pp_factor: ti.f32 = kernels_helpers.lookup_ref_pp(new_pp)
                new_base: ti.f32 = ti.cast((new_p * 2) + new_s, ti.f32) + new_pp_factor
                new_score: ti.i32 = kernels_helpers.calc_score_with_grid_bits(
                    new_base, new_c_mul, new_f_mul, m0, m1, m2, m3, head_len, count_fever, count_normal
                )
                
                if new_score > best_score:
                    best_score = new_score
                    pp = new_pp
                    cm = new_cm
                    fm = new_fm
                    p_val = new_p
                    s_val = new_s
                    
                    # Update gem counts
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
                    
                    improved = 1
    
    return ti.Vector([
        best_score,
        pp,
        cm,
        fm,
        p_val,
        s_val,
        gems_pp,
        gems_cm,
        gems_fm,
        gems_ov,
    ])


# ============================================================================
# KERNELS
# ============================================================================

@ti.kernel
def fg_upload_forced_counts_kernel(n_cfg: ti.i32, data: ti.types.ndarray(dtype=ti.i32, ndim=2)):
    """
    Upload the per-config forced-count grid from a small external array.

    This avoids `field.from_numpy()` on the huge `(FG_MAX_CONFIGS, FG_MAX_SECTIONS)` field.
    `data` must be shaped `(n_cfg, FG_MAX_SECTIONS)` and contain zeros for unused sections.
    """
    for i, j in ti.ndrange(n_cfg, FG_MAX_SECTIONS):
        fg_forced_counts[i, j] = data[i, j]


@ti.kernel
def fg_build_flat_work_kernel(n_genomes: ti.i32, n_ftff: ti.i32):
    """
    Build the flat work-item arrays on GPU.

    Each work item is (genome_id, ftff_id). This avoids uploading two 4M-element
    arrays from CPU on every FG call.
    """
    for g, f in ti.ndrange(n_genomes, n_ftff):
        idx: ti.i32 = g * n_ftff + f
        fg_flat_work_genome[idx] = g
        fg_flat_work_ftff[idx] = f


@ti.kernel
def fg_reset_best_kernel(n_genomes: ti.i32):
    for i in range(n_genomes):
        fg_best_final_score[i] = -1
        fg_best_base_score[i] = 0
        fg_best_cfg_idx[i] = -1
        fg_best_ft[i] = 0
        fg_best_ff[i] = 0
        fg_best_g_pp[i] = 0
        fg_best_g_cm[i] = 0
        fg_best_g_fm[i] = 0
        fg_best_g_ov[i] = 0
        fg_best_score_penalty[i] = 0
        fg_best_fill_penalty[i] = 0


@ti.kernel
def fg_stage1_init_kernel(n_genomes: ti.i32, n_ftff: ti.i32):
    """Initialize Stage 1 fields before reduction (supports cfg-chunk accumulation)."""
    for g, f in ti.ndrange(n_genomes, n_ftff):
        fg_stage1_final_score[g, f] = -1
        fg_stage1_base_score[g, f] = 0
        fg_stage1_cfg_idx[g, f] = -1
        fg_stage1_g_pp[g, f] = 0
        fg_stage1_g_cm[g, f] = 0
        fg_stage1_g_fm[g, f] = 0
        fg_stage1_g_ov[g, f] = 0
        fg_stage1_score_penalty[g, f] = 0
        fg_stage1_fill_penalty[g, f] = 0
        # Initialize packed field to sentinel value (very negative score, cfg=-1)
        # Use -2^62 in upper bits for sentinel (so any real score wins)
        fg_stage1_packed[g, f] = ti.cast(-1, ti.i64) << 32


@ti.kernel
def fg_stage1_kernel(
    n_genomes: ti.i32,
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    n_cfg: ti.i32,
    n_sections: ti.i32,
    n_ftff: ti.i32,
    cfg_offset: ti.i32,
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
):
    """
    Stage 1: Find best cfg for each (genome, ftff) pair.

    Parallelizes over (genome, ftff), loops cfg sequentially inside.
    NO ATOMICS - each (g, f) pair has its own output slot.
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    MAX_STAT: ti.i32 = 160

    head_len: ti.i32 = ti.min(total_notes, 100)

    non_fever_cas: ti.f32 = ti.max(0.0, (ti.cast(total_notes - long_notes, ti.f32) * 0.333))
    fever_time_cas: ti.f32 = last_note_time * 0.15 + 0.15

    for g, ftff_idx in ti.ndrange(n_genomes, n_ftff):
        ft_gems: ti.i32 = fg_ft_list[ftff_idx]
        ff_gems: ti.i32 = fg_ff_list[ftff_idx]
        if ft_gems + ff_gems > total_budget:
            continue

        # Load genome base stats (hoisted out of cfg loop)
        # Load genome base stats (hoisted out of cfg loop)
        # [pp, cm, fm, p_val, s_val, ft, ff]
        base_stats = kernels_helpers.genome_base_stats[g]
        base_pp: ti.i32 = base_stats[0]
        base_cm: ti.i32 = base_stats[1]
        base_fm: ti.i32 = base_stats[2]
        base_p_val: ti.i32 = base_stats[3]
        base_s_val: ti.i32 = base_stats[4]
        base_ft_stat: ti.i32 = base_stats[5]
        base_ff_stat: ti.i32 = base_stats[6]

        # Fever multipliers for this FT/FF (hoisted)
        ft_stat_val: ti.i32 = base_ft_stat + (ft_gems * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff_gems * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
        ft_factor: ti.f32 = kernels_helpers.lookup_ref_ft(ft_idx)
        ff_factor: ti.f32 = kernels_helpers.lookup_ref_ff(ff_idx)

        non_fever_base_f: ti.f32 = non_fever_cas * ff_factor
        non_fever_base: ti.i32 = ti.cast(ti.ceil(non_fever_base_f), ti.i32)
        non_fever_great_to_fill: ti.i32 = ti.cast(
            ti.ceil(ti.max(1.0, non_fever_cas * ff_factor * 2.0)), ti.i32
        )
        real_fever_time: ti.f32 = fever_time_cas * ft_factor

        # Accumulate across cfg-chunks: seed from existing stage1 result
        best_final: ti.i32 = fg_stage1_final_score[g, ftff_idx]
        best_base: ti.i32 = 0
        best_cfg: ti.i32 = 0
        best_pp: ti.i32 = 0
        best_cm: ti.i32 = 0
        best_fm: ti.i32 = 0
        best_ov: ti.i32 = 0
        best_sp: ti.i32 = 0
        best_fp: ti.i32 = 0
        if best_final >= 0:
            best_base = fg_stage1_base_score[g, ftff_idx]
            best_cfg = fg_stage1_cfg_idx[g, ftff_idx]
            best_pp = fg_stage1_g_pp[g, ftff_idx]
            best_cm = fg_stage1_g_cm[g, ftff_idx]
            best_fm = fg_stage1_g_fm[g, ftff_idx]
            best_ov = fg_stage1_g_ov[g, ftff_idx]
            best_sp = fg_stage1_score_penalty[g, ftff_idx]
            best_fp = fg_stage1_fill_penalty[g, ftff_idx]

        # Sequential loop over configs (no atomics needed!)
        for cfg_idx in range(n_cfg):
            # Timeline simulation -> head mask bits + body fever count
            m0 = ti.cast(0, ti.u32)
            m1 = ti.cast(0, ti.u32)
            m2 = ti.cast(0, ti.u32)
            m3 = ti.cast(0, ti.u32)
            body_fever: ti.i32 = 0

            start_idx = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
            forced_applied = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
            fill_notes = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
            skip_wasted = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)

            current_idx: ti.i32 = 0
            sec: ti.i32 = 0
            carry_time: ti.f32 = 0.0
            while current_idx < total_notes:
                base_notes_s: ti.i32 = non_fever_base - 1 if sec == 0 else non_fever_base
                if base_notes_s < 0:
                    base_notes_s = 0

                fp_target: ti.i32 = 0
                if sec < n_sections:
                    fp_target = fg_forced_counts[cfg_idx, sec]
                    if fp_target < 0:
                        fp_target = 0
                    if sec < FG_MAX_SECTIONS:
                        pair_cap_forced: ti.i32 = fg_pair_caps[ft_idx, ff_idx, sec]
                        if pair_cap_forced < 0:
                            pair_cap_forced = 0
                        # Convert forced-count cap to an FP-target cap:
                        # fp_cap = ceil(raw_fill + 0.5*cap) - ceil(raw_fill)
                        notes_with_cap = ti.ceil(non_fever_base_f + ti.cast(pair_cap_forced, ti.f32) * 0.5)
                        non_fever_base_ceiled = ti.ceil(non_fever_base_f)
                        fp_cap: ti.i32 = ti.cast(notes_with_cap, ti.i32) - ti.cast(non_fever_base_ceiled, ti.i32)
                        fp_target = ti.min(fp_target, fp_cap)

                # Derive forced_val from fp_target using raw_fill-based inverse.
                forced_val: ti.i32 = _forced_from_fp_target(
                    non_fever_base_f, non_fever_base, fp_target, non_fever_base
                )

                fp_calc: ti.i32 = fp_target

                notes_to_fill: ti.i32 = base_notes_s + fp_calc
                section_start: ti.i32 = current_idx
                end_normal: ti.i32 = ti.min(total_notes, section_start + notes_to_fill)
                actual_notes: ti.i32 = ti.max(0, end_normal - section_start)
                forced_app: ti.i32 = ti.min(forced_val, actual_notes)

                if forced_app > 0:
                    forced_start: ti.i32 = section_start + (1 - ti.cast(sec == 0, ti.i32))
                    forced_end: ti.i32 = forced_start + forced_app - 1
                    forced_end = ti.min(forced_end, end_normal - 1)
                    if forced_end >= forced_start and forced_end < total_notes:
                        carry_time = ti.max(carry_time, song_timestamps_great_candidate[forced_end])

                if sec < n_sections and sec < FG_MAX_SECTIONS:
                    start_idx[sec] = section_start
                    forced_applied[sec] = forced_app
                    fill_notes[sec] = fp_calc
                    skip_wasted[sec] = ti.cast(sec == 0, ti.i32)

                current_idx = end_normal
                if current_idx >= total_notes:
                    break

                # Fever section
                start_time: ti.f32 = ti.max(song_timestamps[current_idx], carry_time)
                end_time: ti.f32 = start_time + real_fever_time
                fever_end_idx: ti.i32 = kernels_helpers.binary_search_left_from(song_timestamps, total_notes, end_time, current_idx)
                if fever_end_idx <= current_idx:
                    fever_end_idx = ti.min(total_notes, current_idx + 1)

                # Mark head fever notes (bitset)
                if current_idx < head_len:
                    head_end = ti.min(head_len, fever_end_idx)
                    for i in range(current_idx, head_end):
                        word = i >> 5
                        bit = ti.cast(1, ti.u32) << ti.cast(i & 31, ti.u32)
                        if word == 0:
                            m0 |= bit
                        elif word == 1:
                            m1 |= bit
                        elif word == 2:
                            m2 |= bit
                        else:
                            m3 |= bit

                # Count body fever notes
                if fever_end_idx > head_len:
                    body_start = head_len if current_idx < head_len else current_idx
                    if fever_end_idx > body_start:
                        body_fever += (fever_end_idx - body_start)

                current_idx = fever_end_idx
                sec += 1

            body_len = ti.max(total_notes - head_len, 0)
            body_normal: ti.i32 = ti.max(body_len - body_fever, 0)

            budget: ti.i32 = total_budget - ft_gems - ff_gems
            if budget < 0:
                continue

            p_val: ti.i32 = base_p_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_p_ft) + (
                ff_gems * GEM_STAT_TO_ELEMENT * is_p_ff
            )
            s_val: ti.i32 = base_s_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_s_ft) + (
                ff_gems * GEM_STAT_TO_ELEMENT * is_s_ff
            )

            opt = _optimize_core_bits(
                budget,
                base_pp,
                base_cm,
                base_fm,
                p_val,
                s_val,
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
                body_fever,
                body_normal,
            )

            base_score: ti.i32 = opt[0]
            final_pp: ti.i32 = opt[1]
            final_cm: ti.i32 = opt[2]
            final_fm: ti.i32 = opt[3]
            final_p_val: ti.i32 = opt[4]
            final_s_val: ti.i32 = opt[5]
            gems_pp: ti.i32 = opt[6]
            gems_cm: ti.i32 = opt[7]
            gems_fm: ti.i32 = opt[8]
            gems_ov: ti.i32 = opt[9]

            # Penalty math
            pp_factor: ti.f32 = kernels_helpers.lookup_ref_pp(final_pp)
            combo_mul: ti.f32 = kernels_helpers.lookup_ref_cm(final_cm)
            combo_span: ti.f32 = combo_mul - 1.0

            base_value: ti.f32 = ti.cast((final_p_val * 2) + final_s_val, ti.f32) + pp_factor
            combo_value: ti.i32 = ti.cast(ti.floor(base_value * combo_mul), ti.i32)

            # Match the game's floor-sensitive split for Great color bonus on 2-color charts:
            # floor((4/3)*primary) + floor((2/3)*secondary) + 150
            great_penalty_base: ti.i32 = (
                ti.cast(
                    ti.floor(ti.cast(final_p_val * 2, ti.f32) * (2.0 / 3.0)),
                    ti.i32,
                )
                + ti.cast(
                    ti.floor(ti.cast(final_s_val, ti.f32) * (2.0 / 3.0)),
                    ti.i32,
                )
                + 150
            )
            great_combo_value: ti.i32 = ti.cast(ti.floor(ti.cast(great_penalty_base, ti.f32) * combo_mul), ti.i32)
            body_penalty: ti.i32 = ti.max(0, combo_value - great_combo_value)

            score_penalty_total: ti.i32 = 0
            fill_penalty_total: ti.i32 = 0

            for s in range(ti.min(n_sections, FG_MAX_SECTIONS)):
                fp_notes: ti.i32 = fill_notes[s]
                fill_penalty_total += fp_notes * combo_value

                forced_n: ti.i32 = forced_applied[s]
                if forced_n > 0:
                    # For sections 2+, the first non-fever note is the transition note (no fill).
                    # Forced Greats should apply to fill-contributing notes, so offset by +1.
                    start = start_idx[s] + (1 - skip_wasted[s])
                    for k in range(forced_n):
                        note_idx = start + k
                        if note_idx < 100:
                            scaling: ti.f32 = 1.0 + combo_span * (ti.cast(note_idx + 1, ti.f32) / 100.0)
                            perfect_val: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
                            great_val: ti.i32 = ti.cast(ti.floor(ti.cast(great_penalty_base, ti.f32) * scaling), ti.i32)
                            pen: ti.i32 = ti.max(0, perfect_val - great_val)
                            score_penalty_total += pen
                        else:
                            score_penalty_total += body_penalty

            final_score: ti.i32 = base_score - score_penalty_total
            if final_score < 0:
                final_score = 0

            if final_score > best_final:
                best_final = final_score
                best_base = base_score
                best_cfg = cfg_offset + cfg_idx
                best_pp = gems_pp
                best_cm = gems_cm
                best_fm = gems_fm
                best_ov = gems_ov
                best_sp = score_penalty_total
                best_fp = fill_penalty_total

        fg_stage1_final_score[g, ftff_idx] = best_final
        fg_stage1_base_score[g, ftff_idx] = best_base
        fg_stage1_cfg_idx[g, ftff_idx] = best_cfg
        fg_stage1_g_pp[g, ftff_idx] = best_pp
        fg_stage1_g_cm[g, ftff_idx] = best_cm
        fg_stage1_g_fm[g, ftff_idx] = best_fm
        fg_stage1_g_ov[g, ftff_idx] = best_ov
        fg_stage1_score_penalty[g, ftff_idx] = best_sp
        fg_stage1_fill_penalty[g, ftff_idx] = best_fp


@ti.kernel
def fg_stage2_kernel(n_genomes: ti.i32, n_ftff: ti.i32):
    """
    Stage 2: Reduce across ftff to find best per genome.

    Each thread handles one genome, loops over ftff sequentially.
    Uses the packed field to get atomically-consistent (score, cfg_idx) pairs.
    """
    for g in range(n_genomes):
        best_packed: ti.i64 = ti.cast(-1, ti.i64) << 32  # Sentinel
        best_ftff: ti.i32 = 0

        for f in range(n_ftff):
            packed = fg_stage1_packed[g, f]
            if packed > best_packed:
                best_packed = packed
                best_ftff = f

        # Extract score and DECODE inverted cfg_idx
        best_final: ti.i32 = ti.cast(best_packed >> 32, ti.i32)
        inverted_cfg: ti.i32 = ti.cast(best_packed & 0x7FFFFFFF, ti.i32)
        best_cfg: ti.i32 = 0x7FFFFFFF - inverted_cfg  # Decode: invert back

        if best_final >= 0:
            fg_best_final_score[g] = best_final
            fg_best_base_score[g] = fg_stage1_base_score[g, best_ftff]
            fg_best_cfg_idx[g] = best_cfg  # Use decoded cfg from packed field
            fg_best_ft[g] = fg_ft_list[best_ftff]
            fg_best_ff[g] = fg_ff_list[best_ftff]
            fg_best_g_pp[g] = fg_stage1_g_pp[g, best_ftff]
            fg_best_g_cm[g] = fg_stage1_g_cm[g, best_ftff]
            fg_best_g_fm[g] = fg_stage1_g_fm[g, best_ftff]
            fg_best_g_ov[g] = fg_stage1_g_ov[g, best_ftff]
            fg_best_score_penalty[g] = fg_stage1_score_penalty[g, best_ftff]
            fg_best_fill_penalty[g] = fg_stage1_fill_penalty[g, best_ftff]


@ti.kernel
def fg_pack_results_kernel(n_genomes: ti.i32):
    """
    Pack all 11 best result fields into a single contiguous array for efficient CPU download.
    
    This eliminates 11 separate to_numpy() calls (11 CPU waits) into 1 single download.
    MASSIVE speedup on weak CPUs that bottleneck on GPU synchronization.
    
    Column order: [final_score, base_score, cfg_idx, ft, ff, g_pp, g_cm, g_fm, g_ov, score_penalty, fill_penalty]
    """
    for g in range(n_genomes):
        fg_best_packed[g, 0] = fg_best_final_score[g]
        fg_best_packed[g, 1] = fg_best_base_score[g]
        fg_best_packed[g, 2] = fg_best_cfg_idx[g]
        fg_best_packed[g, 3] = fg_best_ft[g]
        fg_best_packed[g, 4] = fg_best_ff[g]
        fg_best_packed[g, 5] = fg_best_g_pp[g]
        fg_best_packed[g, 6] = fg_best_g_cm[g]
        fg_best_packed[g, 7] = fg_best_g_fm[g]
        fg_best_packed[g, 8] = fg_best_g_ov[g]
        fg_best_packed[g, 9] = fg_best_score_penalty[g]
        fg_best_packed[g, 10] =fg_best_fill_penalty[g]

@ti.kernel
def fg_stage1_flat_kernel(
    n_work_items: ti.i32,
    n_cfg: ti.i32,
    cfg_offset: ti.i32,
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    n_sections: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
):
    """
    GPU-friendly Stage 1: One thread per (work_item, cfg) pair.
    
    Parallelizes over (work_item * n_cfg), where work_item is (genome, ftff).
    Uses atomic_max for reduction within each (genome, ftff) slot.
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    MAX_STAT: ti.i32 = 160

    head_len: ti.i32 = ti.min(total_notes, 100)
    non_fever_cas: ti.f32 = ti.max(0.0, (ti.cast(total_notes - long_notes, ti.f32) * 0.333))
    fever_time_cas: ti.f32 = last_note_time * 0.15 + 0.15

    # Flatten: each thread handles one (work_item, cfg) pair
    for flat_idx in range(n_work_items * n_cfg):
        work_idx: ti.i32 = flat_idx // n_cfg
        cfg_idx: ti.i32 = flat_idx % n_cfg

        # Decode work item -> (genome, ftff)
        g: ti.i32 = fg_flat_work_genome[work_idx]
        ftff_idx: ti.i32 = fg_flat_work_ftff[work_idx]

        ft_gems: ti.i32 = fg_ft_list[ftff_idx]
        ff_gems: ti.i32 = fg_ff_list[ftff_idx]
        if ft_gems + ff_gems > total_budget:
            continue

        # Load genome base stats
        base_stats = kernels_helpers.genome_base_stats[g]
        base_pp: ti.i32 = base_stats[0]
        base_cm: ti.i32 = base_stats[1]
        base_fm: ti.i32 = base_stats[2]
        base_p_val: ti.i32 = base_stats[3]
        base_s_val: ti.i32 = base_stats[4]
        base_ft_stat: ti.i32 = base_stats[5]
        base_ff_stat: ti.i32 = base_stats[6]

        # Fever multipliers
        ft_stat_val: ti.i32 = base_ft_stat + (ft_gems * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff_gems * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
        ft_factor: ti.f32 = kernels_helpers.lookup_ref_ft(ft_idx)
        ff_factor: ti.f32 = kernels_helpers.lookup_ref_ff(ff_idx)

        non_fever_base_f: ti.f32 = non_fever_cas * ff_factor
        non_fever_base: ti.i32 = ti.cast(ti.ceil(non_fever_base_f), ti.i32)
        non_fever_great_to_fill: ti.i32 = ti.cast(
            ti.ceil(ti.max(1.0, non_fever_cas * ff_factor * 2.0)), ti.i32
        )
        real_fever_time: ti.f32 = fever_time_cas * ft_factor

        # Timeline simulation for this ONE config
        m0 = ti.cast(0, ti.u32)
        m1 = ti.cast(0, ti.u32)
        m2 = ti.cast(0, ti.u32)
        m3 = ti.cast(0, ti.u32)
        body_fever: ti.i32 = 0

        start_idx_vec = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
        forced_applied = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
        fill_notes = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
        skip_wasted = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)

        current_idx: ti.i32 = 0
        sec: ti.i32 = 0
        carry_time: ti.f32 = 0.0
        while current_idx < total_notes:
            base_notes_s: ti.i32 = non_fever_base - 1 if sec == 0 else non_fever_base
            if base_notes_s < 0:
                base_notes_s = 0

            fp_target: ti.i32 = 0
            if sec < n_sections:
                fp_target = fg_forced_counts[cfg_idx, sec]
                if fp_target < 0:
                    fp_target = 0

                # Clamp by per-pair dynamic cap (stored as forced-count caps)
                    if sec < FG_MAX_SECTIONS:
                        pair_cap_forced: ti.i32 = fg_pair_caps[ft_idx, ff_idx, sec]
                        if pair_cap_forced < 0:
                            pair_cap_forced = 0
                        notes_with_cap = ti.ceil(non_fever_base_f + ti.cast(pair_cap_forced, ti.f32) * 0.5)
                        non_fever_base_ceiled = ti.ceil(non_fever_base_f)
                        fp_cap: ti.i32 = ti.cast(notes_with_cap, ti.i32) - ti.cast(non_fever_base_ceiled, ti.i32)
                        fp_target = ti.min(fp_target, fp_cap)

            # Derive forced_val from fp_target using raw_fill-based inverse.
            forced_val: ti.i32 = _forced_from_fp_target(
                non_fever_base_f, non_fever_base, fp_target, non_fever_base
            )

            fp_calc: ti.i32 = fp_target

            notes_to_fill: ti.i32 = base_notes_s + fp_calc
            section_start: ti.i32 = current_idx
            end_normal: ti.i32 = ti.min(total_notes, section_start + notes_to_fill)
            actual_notes: ti.i32 = ti.max(0, end_normal - section_start)
            forced_app: ti.i32 = ti.min(forced_val, actual_notes)

            if forced_app > 0:
                forced_start: ti.i32 = section_start + (1 - ti.cast(sec == 0, ti.i32))
                forced_end: ti.i32 = forced_start + forced_app - 1
                forced_end = ti.min(forced_end, end_normal - 1)
                if forced_end >= forced_start and forced_end < total_notes:
                    carry_time = ti.max(carry_time, song_timestamps_great_candidate[forced_end])

            if sec < n_sections and sec < FG_MAX_SECTIONS:
                start_idx_vec[sec] = section_start
                forced_applied[sec] = forced_app
                fill_notes[sec] = fp_calc
                skip_wasted[sec] = ti.cast(sec == 0, ti.i32)

            current_idx = end_normal
            if current_idx >= total_notes:
                break

            # Fever section
            start_time: ti.f32 = ti.max(song_timestamps[current_idx], carry_time)
            end_time: ti.f32 = start_time + real_fever_time
            fever_end_idx: ti.i32 = kernels_helpers.binary_search_left_from(song_timestamps, total_notes, end_time, current_idx)
            if fever_end_idx <= current_idx:
                fever_end_idx = ti.min(total_notes, current_idx + 1)

            # Mark head fever notes (bitset)
            if current_idx < head_len:
                head_end = ti.min(head_len, fever_end_idx)
                for i in range(current_idx, head_end):
                    word = i >> 5
                    bit = ti.cast(1, ti.u32) << ti.cast(i & 31, ti.u32)
                    if word == 0:
                        m0 |= bit
                    elif word == 1:
                        m1 |= bit
                    elif word == 2:
                        m2 |= bit
                    else:
                        m3 |= bit

            # Count body fever notes
            if fever_end_idx > head_len:
                body_start = head_len if current_idx < head_len else current_idx
                if fever_end_idx > body_start:
                    body_fever += (fever_end_idx - body_start)

            current_idx = fever_end_idx
            sec += 1

        body_len = ti.max(total_notes - head_len, 0)
        body_normal: ti.i32 = ti.max(body_len - body_fever, 0)

        budget: ti.i32 = total_budget - ft_gems - ff_gems
        if budget < 0:
            continue

        p_val: ti.i32 = base_p_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_p_ft) + (
            ff_gems * GEM_STAT_TO_ELEMENT * is_p_ff
        )
        s_val: ti.i32 = base_s_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_s_ft) + (
            ff_gems * GEM_STAT_TO_ELEMENT * is_s_ff
        )

        opt = _optimize_core_bits(
            budget,
            base_pp, base_cm, base_fm,
            p_val, s_val,
            is_p_pp, is_s_pp,
            is_p_cm, is_s_cm,
            is_p_fm, is_s_fm,
            is_p_ov, is_s_ov,
            m0, m1, m2, m3,
            head_len,
            body_fever, body_normal,
        )

        base_score: ti.i32 = opt[0]
        final_pp: ti.i32 = opt[1]
        final_cm: ti.i32 = opt[2]
        final_fm: ti.i32 = opt[3]
        final_p_val: ti.i32 = opt[4]
        final_s_val: ti.i32 = opt[5]
        gems_pp: ti.i32 = opt[6]
        gems_cm: ti.i32 = opt[7]
        gems_fm: ti.i32 = opt[8]
        gems_ov: ti.i32 = opt[9]

        # Penalty calculation
        pp_factor: ti.f32 = kernels_helpers.lookup_ref_pp(final_pp)
        combo_mul: ti.f32 = kernels_helpers.lookup_ref_cm(final_cm)
        combo_span: ti.f32 = combo_mul - 1.0

        base_value: ti.f32 = ti.cast((final_p_val * 2) + final_s_val, ti.f32) + pp_factor
        combo_value: ti.i32 = ti.cast(ti.floor(base_value * combo_mul), ti.i32)

        great_penalty_base: ti.i32 = (
            ti.cast(
                ti.floor(ti.cast(final_p_val * 2, ti.f32) * (2.0 / 3.0)),
                ti.i32,
            )
            + ti.cast(
                ti.floor(ti.cast(final_s_val, ti.f32) * (2.0 / 3.0)),
                ti.i32,
            )
            + 150
        )
        great_combo_value: ti.i32 = ti.cast(ti.floor(ti.cast(great_penalty_base, ti.f32) * combo_mul), ti.i32)
        body_penalty: ti.i32 = ti.max(0, combo_value - great_combo_value)

        score_penalty_total: ti.i32 = 0
        fill_penalty_total: ti.i32 = 0

        for s in range(ti.min(n_sections, FG_MAX_SECTIONS)):
            fp_notes: ti.i32 = fill_notes[s]
            fill_penalty_total += fp_notes * combo_value

            forced_n: ti.i32 = forced_applied[s]
            if forced_n > 0:
                # For sections 2+, the first non-fever note is the transition note (no fill).
                # Forced Greats should apply to fill-contributing notes, so offset by +1.
                start = start_idx_vec[s] + (1 - skip_wasted[s])
                for k in range(forced_n):
                    note_idx = start + k
                    if note_idx < 100:
                        scaling: ti.f32 = 1.0 + combo_span * (ti.cast(note_idx + 1, ti.f32) / 100.0)
                        perfect_val: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
                        great_val: ti.i32 = ti.cast(ti.floor(ti.cast(great_penalty_base, ti.f32) * scaling), ti.i32)
                        pen: ti.i32 = ti.max(0, perfect_val - great_val)
                        score_penalty_total += pen
                    else:
                        score_penalty_total += body_penalty

        final_score: ti.i32 = base_score - score_penalty_total
        if final_score < 0:
            final_score = 0

        # Pack score and cfg_idx into a single 64-bit value for atomic update
        # Format: (score << 32) | inverted_cfg_idx
        # Score in upper 32 bits ensures atomic_max picks highest score
        # INVERTED cfg_idx in lower 32 bits ensures lower cfg_idx wins ties
        # (atomic_max picks larger value, so invert to prefer smaller idx)
        global_cfg_idx: ti.i32 = cfg_offset + cfg_idx
        inverted_idx: ti.i32 = 0x7FFFFFFF - global_cfg_idx  # Invert: 0 -> 0x7FFFFFFF, 1 -> 0x7FFFFFFE, etc.
        packed_val: ti.i64 = (ti.cast(final_score, ti.i64) << 32) | ti.cast(inverted_idx, ti.i64)
        
        # Atomic update - score and cfg_idx updated TOGETHER atomically
        old_packed = ti.atomic_max(fg_stage1_packed[g, ftff_idx], packed_val)
        old_score: ti.i32 = ti.cast(old_packed >> 32, ti.i32)
        
        # Only update metadata if WE won the atomic race
        # Strict < check ensures exactly ONE winner writes metadata
        if old_score < final_score:
            # We won - safe to update all metadata fields (no race)
            fg_stage1_final_score[g, ftff_idx] = final_score
            fg_stage1_base_score[g, ftff_idx] = base_score
            fg_stage1_cfg_idx[g, ftff_idx] = global_cfg_idx
            fg_stage1_g_pp[g, ftff_idx] = gems_pp
            fg_stage1_g_cm[g, ftff_idx] = gems_cm
            fg_stage1_g_fm[g, ftff_idx] = gems_fm
            fg_stage1_g_ov[g, ftff_idx] = gems_ov
            fg_stage1_score_penalty[g, ftff_idx] = score_penalty_total
            fg_stage1_fill_penalty[g, ftff_idx] = fill_penalty_total


# ============================================================================
# GLOBAL BEST KERNELS (GPU-resident accumulation across groups)
# ============================================================================

@ti.kernel
def fg_reset_global_best_kernel(n_genomes: ti.i32):
    """
    Reset global best fields to sentinel values before multi-group processing.
    
    Call this once at the start of a batch of FG groups, before the loop.
    """
    for i in range(n_genomes):
        fg_global_best_final_score[i] = -1
        fg_global_best_base_score[i] = 0
        fg_global_best_cfg_idx[i] = -1
        fg_global_best_ft[i] = 0
        fg_global_best_ff[i] = 0
        fg_global_best_g_pp[i] = 0
        fg_global_best_g_cm[i] = 0
        fg_global_best_g_fm[i] = 0
        fg_global_best_g_ov[i] = 0
        fg_global_best_score_penalty[i] = 0
        fg_global_best_fill_penalty[i] = 0


@ti.kernel
def fg_update_global_best_kernel(n_genomes: ti.i32):
    """
    Compare current fg_best_* results with fg_global_best_*, update if better.
    
    Call this after each solve_force_greats_finder_gpu() call to accumulate
    the best results across all groups without downloading to CPU.
    """
    for gid in range(n_genomes):
        new_score = fg_best_final_score[gid]
        old_score = fg_global_best_final_score[gid]
        
        if new_score > old_score:
            fg_global_best_final_score[gid] = new_score
            fg_global_best_base_score[gid] = fg_best_base_score[gid]
            fg_global_best_cfg_idx[gid] = fg_best_cfg_idx[gid]
            fg_global_best_ft[gid] = fg_best_ft[gid]
            fg_global_best_ff[gid] = fg_best_ff[gid]
            fg_global_best_g_pp[gid] = fg_best_g_pp[gid]
            fg_global_best_g_cm[gid] = fg_best_g_cm[gid]
            fg_global_best_g_fm[gid] = fg_best_g_fm[gid]
            fg_global_best_g_ov[gid] = fg_best_g_ov[gid]
            fg_global_best_score_penalty[gid] = fg_best_score_penalty[gid]
            fg_global_best_fill_penalty[gid] = fg_best_fill_penalty[gid]




