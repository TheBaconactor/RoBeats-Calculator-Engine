"""
Taichi Kernels - GPU kernel implementations for gem optimization.

This module contains all @ti.func and @ti.kernel definitions.
Fields are bound at runtime via fields.bind_fields() after allocation.

IMPORTANT: Do NOT import fields directly at module load time.
The field variables below are placeholders that get populated by bind_fields().
"""
import taichi as ti

from .runtime import get_block_dim

# Resolve once at import time so Taichi sees a plain constant in `ti.loop_config`.
# (Calling Python functions inside kernels triggers Taichi AST warnings.)
_KERNEL_BLOCK_DIM = get_block_dim()

# ============================================================================
# FIELD PLACEHOLDERS (bound by fields.bind_fields() after allocation)
# ============================================================================

# Reference tables
ref_pp_field = None
ref_cm_field = None
ref_fm_field = None
ref_ft_field = None
ref_ff_field = None

# Grid fields
grid_count_body_fever = None
grid_count_body_normal = None
grid_head_len = None
grid_fever_masks = None
grid_fever_masks_bits = None

# Work item data
fever_masks = None
work_budgets = None
work_count_fever = None
work_count_normal = None
work_ft_gems = None
work_ff_gems = None
work_head_len = None
work_genome_id = None

# Genome base stats
genome_base_pp = None
genome_base_cm = None
genome_base_fm = None
genome_base_p_val = None
genome_base_s_val = None
genome_base_ft = None
genome_base_ff = None

# GPU-native GA / stat aggregation fields
population_indices = None
population_next_indices = None
item_stats = None
base_fixed_stats = None
ga_scores = None
ga_rng_state = None
ga_parent_a = None
ga_parent_b = None

# Results
result_scores = None
result_pp = None
result_cm = None
result_fm = None
result_ov = None
result_p_val = None
result_s_val = None

# Genome results
genome_result_scores = None
genome_result_ft = None
genome_result_ff = None
genome_result_pp = None
genome_result_cm = None
genome_result_fm = None
genome_result_ov = None


# ============================================================================
# @ti.func IMPLEMENTATIONS (Ported from scoring_core.py)
# ============================================================================

@ti.func
def lookup_ref_pp(value: ti.i32) -> ti.f32:
    """O(1) lookup from Perfect Points reference table. Clamps to [0, 160]."""
    idx = ti.max(0, ti.min(160, value))
    return ref_pp_field[idx]


@ti.func
def lookup_ref_cm(value: ti.i32) -> ti.f32:
    """O(1) lookup from Combo Multiplier reference table. Clamps to [0, 160]."""
    idx = ti.max(0, ti.min(160, value))
    return ref_cm_field[idx]


@ti.func
def lookup_ref_fm(value: ti.i32) -> ti.f32:
    """O(1) lookup from Fever Multiplier reference table. Clamps to [0, 160]."""
    idx = ti.max(0, ti.min(160, value))
    return ref_fm_field[idx]


@ti.func
def _xorshift32(x: ti.u32) -> ti.u32:
    # Deterministic per-thread RNG (fast, good enough for GA operators).
    x ^= x << ti.u32(13)
    x ^= x >> ti.u32(17)
    x ^= x << ti.u32(5)
    return x


@ti.kernel
def ga_seed_rng_kernel(n_genomes: ti.i32, seed: ti.u32):
    """
    Initialize per-genome RNG state deterministically.
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        # Mix seed with genome index (avoid all-zero states).
        s = seed ^ (ti.cast(g, ti.u32) * ti.u32(747796405)) ^ ti.u32(2891336453)
        if s == ti.u32(0):
            s = ti.u32(1)
        ga_rng_state[g] = s


@ti.kernel
def ga_select_parents_tournament_kernel(n_genomes: ti.i32, tournament_k: ti.i32):
    """
    Tournament selection on GPU.

    Produces two parent indices per output genome (ga_parent_a/b).
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        state = ga_rng_state[g]

        # Pick parent A
        best_a = 0
        best_a_score = ti.cast(-2147483648, ti.i32)
        for _ in range(tournament_k):
            state = _xorshift32(state)
            idx = ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
            sc = ga_scores[idx]
            if sc > best_a_score:
                best_a_score = sc
                best_a = idx

        # Pick parent B
        best_b = 0
        best_b_score = ti.cast(-2147483648, ti.i32)
        for _ in range(tournament_k):
            state = _xorshift32(state)
            idx = ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
            sc = ga_scores[idx]
            if sc > best_b_score:
                best_b_score = sc
                best_b = idx

        pa = best_a
        pb = best_b

        ga_parent_a[g] = pa
        ga_parent_b[g] = pb
        ga_rng_state[g] = state


@ti.kernel
def ga_crossover_mutate_kernel(
    n_genomes: ti.i32,
    n_slots: ti.i32,
    mutation_rate_fp: ti.u32,  # [0..2^32-1]
    elite_count: ti.i32,
):
    """
    Create next generation in population_next_indices (race-free, deterministic).

    - Parent selection is provided via ga_parent_a/ga_parent_b (tournament selection kernel).
    - Uniform crossover from two parents.
    - Mutation: slot-safe replacement by copying a random donor genome's slot item_id.

    NOTE: elite_count is accepted for API stability, but is not used in this staged
    implementation (proper elite selection requires an argsort/scan strategy).
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)

    for g in range(n_genomes):
        state = ga_rng_state[g]
        pa = ga_parent_a[g]
        pb = ga_parent_b[g]

        # Uniform crossover per slot
        for s in range(n_slots):
            state = _xorshift32(state)
            take_a = (state & ti.u32(1)) != 0
            population_next_indices[g, s] = population_indices[pa, s] if take_a else population_indices[pb, s]

        # Mutation: with given probability mutate 1 slot by borrowing from a random donor genome.
        state = _xorshift32(state)
        if state < mutation_rate_fp:
            state = _xorshift32(state)
            slot = ti.cast(state % ti.cast(n_slots, ti.u32), ti.i32)
            state = _xorshift32(state)
            donor = ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
            population_next_indices[g, slot] = population_indices[donor, slot]

        ga_rng_state[g] = state


@ti.kernel
def ga_swap_populations_kernel(n_genomes: ti.i32, n_slots: ti.i32):
    """
    Copy population_next_indices -> population_indices in-place.
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    for g, s in ti.ndrange(n_genomes, n_slots):
        population_indices[g, s] = population_next_indices[g, s]


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
    # Body score (notes 101+) - base_value is already f32
    combo_val = ti.floor(base_value * combo_mul)
    fever_val = ti.floor(base_value * combo_mul * fever_mul)
    
    body_score = (ti.cast(count_fever, ti.f32) * fever_val) + (ti.cast(count_normal, ti.f32) * combo_val)
    
    # Head score (notes 1-100) with ramped combo
    factor = (combo_mul - 1.0) * base_value / 100.0
    head_score = 0.0
    
    for i in range(head_len):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        if fever_masks[work_idx, i] != 0:
            head_score += ti.floor(ramp_val * fever_mul)
        else:
            head_score += ti.floor(ramp_val)
    
    return ti.cast(body_score + head_score, ti.i32)


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
) -> ti.i32:
    """
    GPU port of optimize_core_jit (scoring_core.py:99-278).
    
    Greedy gem allocation: at each iteration, evaluates 4 options:
    - PP gem (Perfect Points)
    - CM gem (Combo Multiplier)
    - FM gem (Fever Multiplier)
    - OV gem (Overflow/Elemental)
    
    Picks the option that maximizes score. Repeats until budget exhausted.
    
    Returns:
        Best final score after gem allocation
    """
    # Constants (matching constants.py)
    GEM_SCALE_NORMAL: ti.i32 = 2
    GEM_SCALE_FEVER: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    
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
        c_mul_cur: ti.f32 = lookup_ref_cm(cm)
        f_mul_cur: ti.f32 = lookup_ref_fm(fm)

        # Start with OV as default so OV wins exact ties.
        t_p: ti.i32 = p_val + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
        t_s: ti.i32 = s_val + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
        pp_factor: ti.f32 = lookup_ref_pp(pp)
        base: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
        best_score: ti.i32 = calc_score_device(base, c_mul_cur, f_mul_cur, work_idx, head_len, count_fever, count_normal)
        best_opt: ti.i32 = 3

        pp_score: ti.i32 = -1

        # Option 0: PP gem
        if pp < MAX_STAT:
            t_pp: ti.i32 = pp + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus * is_s_ov)
            pp_factor = lookup_ref_pp(t_pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            pp_score = calc_score_device(base, c_mul_cur, f_mul_cur, work_idx, head_len, count_fever, count_normal)
            if pp_score > best_score:
                best_score = pp_score
                best_opt = 0

        # Option 1: CM gem
        if cm < MAX_STAT:
            t_cm: ti.i32 = cm + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_cm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_cm) + (fill_bonus * is_s_ov)
            pp_factor = lookup_ref_pp(pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            c_mul: ti.f32 = lookup_ref_cm(t_cm)
            score: ti.i32 = calc_score_device(base, c_mul, f_mul_cur, work_idx, head_len, count_fever, count_normal)
            if score > best_score:
                best_score = score
                best_opt = 1

        # Option 2: FM gem
        if fm < MAX_STAT:
            t_fm: ti.i32 = fm + GEM_SCALE_FEVER
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_fm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_fm) + (fill_bonus * is_s_ov)
            pp_factor = lookup_ref_pp(pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            f_mul: ti.f32 = lookup_ref_fm(t_fm)
            score = calc_score_device(base, c_mul_cur, f_mul, work_idx, head_len, count_fever, count_normal)
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
                pp_factor = lookup_ref_pp(t_pp)
                base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                score_k: ti.i32 = calc_score_device(base, c_mul_cur, f_mul_cur, work_idx, head_len, count_fever, count_normal)
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
    
    # Store results in output fields
    result_pp[work_idx] = gems_pp
    result_cm[work_idx] = gems_cm
    result_fm[work_idx] = gems_fm
    result_ov[work_idx] = gems_ov
    result_p_val[work_idx] = p_val
    result_s_val[work_idx] = s_val
    
    return best_final_score


@ti.func
def calc_score_with_grid(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    """
    Score calculation using grid-stored fever masks.
    Reads fever mask from grid_fever_masks[ft_idx, ff_idx, :].
    """
    # Body score (notes 101+)
    combo_val = ti.floor(base_value * combo_mul)
    fever_val = ti.floor(base_value * combo_mul * fever_mul)
    body_score = (ti.cast(count_fever, ti.f32) * fever_val) + (ti.cast(count_normal, ti.f32) * combo_val)
    
    # Head score (notes 1-100) with ramped combo
    factor = (combo_mul - 1.0) * base_value / 100.0
    head_score = 0.0
    
    for i in range(head_len):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        if grid_fever_masks[ft_idx, ff_idx, i] != 0:
            head_score += ti.floor(ramp_val * fever_mul)
        else:
            head_score += ti.floor(ramp_val)
    
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
    """
    # Body score (notes 101+)
    combo_val = ti.floor(base_value * combo_mul)
    fever_val = ti.floor(base_value * combo_mul * fever_mul)
    body_score = (ti.cast(count_fever, ti.f32) * fever_val) + (ti.cast(count_normal, ti.f32) * combo_val)

    # Head score (notes 1-100) with ramped combo
    factor = (combo_mul - 1.0) * base_value / 100.0
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

    return ti.cast(body_score + head_score, ti.i32)


# ============================================================================
# @ti.kernel ENTRY POINTS
# ============================================================================

@ti.kernel
def aggregate_population_stats_kernel(
    n_genomes: ti.i32,
    n_slots: ti.i32,
):
    """
    Aggregate per-genome base stats on GPU from integer population representation.

    Inputs:
      - population_indices[g, slot] -> item_id
      - item_stats[item_id, stat_id] -> int32 stat values
      - base_fixed_stats[stat_id] -> int32 fixed base stats to add for all genomes

    Outputs:
      - genome_base_* fields filled to match the gem solver expectations.

    stat_id schema must match gear_optimizer.solver.population_index.STAT_KEYS:
      0: PP, 1: CM, 2: FM, 3: FT, 4: FF, 5: Beat, 6: Vibe, 7: Rush, 8: Flow, 9: Chill
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)

    for g in range(n_genomes):
        # Start from fixed base stats.
        pp = base_fixed_stats[0]
        cm = base_fixed_stats[1]
        fm = base_fixed_stats[2]
        ft = base_fixed_stats[3]
        ff = base_fixed_stats[4]

        beat = base_fixed_stats[5]
        vibe = base_fixed_stats[6]
        rush = base_fixed_stats[7]
        flow = base_fixed_stats[8]
        chill = base_fixed_stats[9]

        for s in range(n_slots):
            item_id = population_indices[g, s]
            if item_id <= 0:
                continue

            pp += item_stats[item_id, 0]
            cm += item_stats[item_id, 1]
            fm += item_stats[item_id, 2]
            ft += item_stats[item_id, 3]
            ff += item_stats[item_id, 4]

            beat += item_stats[item_id, 5]
            vibe += item_stats[item_id, 6]
            rush += item_stats[item_id, 7]
            flow += item_stats[item_id, 8]
            chill += item_stats[item_id, 9]

        # Store outputs expected by downstream kernels.
        genome_base_pp[g] = pp
        genome_base_cm[g] = cm
        genome_base_fm[g] = fm
        genome_base_ft[g] = ft
        genome_base_ff[g] = ff

        # Note: p/s values depend on song metadata, so we don't compute them here.
        # Callers will fill genome_base_p_val/genome_base_s_val after mapping colors.

@ti.kernel
def solve_batch_kernel(
    n_items: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
):
    """
    Main kernel - processes all work items in parallel.
    
    Each work item represents one (FT_gems, FF_gems) timeline combination
    for one genome. The kernel parallelizes across all work items.
    
    Per-genome base stats are looked up from genome_base_* fields using
    work_genome_id mapping (fixes per-genome stats bug).
    
    Args:
        n_items: Number of work items to process
        is_*: Boolean flags (0/1) for color contributions
    """
    # Honor TAICHI_BLOCK_DIM (work-group size) for Vulkan kernels.
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    
    for i in range(n_items):
        budget: ti.i32 = work_budgets[i]
        count_fever: ti.i32 = work_count_fever[i]
        count_normal: ti.i32 = work_count_normal[i]
        ft_gems: ti.i32 = work_ft_gems[i]
        ff_gems: ti.i32 = work_ff_gems[i]
        head_len: ti.i32 = work_head_len[i]
        
        # Look up per-genome base stats (fixes the per-genome stats bug!)
        genome_id: ti.i32 = work_genome_id[i]
        base_pp: ti.i32 = genome_base_pp[genome_id]
        base_cm: ti.i32 = genome_base_cm[genome_id]
        base_fm: ti.i32 = genome_base_fm[genome_id]
        base_p_val: ti.i32 = genome_base_p_val[genome_id]
        base_s_val: ti.i32 = genome_base_s_val[genome_id]
        
        # Adjust base p/s values for FT/FF gem contributions to elemental stats
        # FT gems add to Beat (is_p_ft/is_s_ft tells us if Beat is primary/secondary)
        # FF gems add to Vibe (is_p_ff/is_s_ff tells us if Vibe is primary/secondary)
        p_val: ti.i32 = base_p_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val: ti.i32 = base_s_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_s_ff)
        
        score: ti.i32 = optimize_core_device(
            i, budget,
            base_pp, base_cm, base_fm,
            p_val, s_val,
            is_p_pp, is_s_pp,
            is_p_cm, is_s_cm,
            is_p_fm, is_s_fm,
            is_p_ov, is_s_ov,
            head_len, count_fever, count_normal,
        )
        result_scores[i] = score


@ti.kernel
def solve_genomes_with_ftff_kernel(
    n_genomes: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
):
    """
    New kernel that iterates FT/FF combinations INSIDE the GPU thread.
    
    Each thread handles one genome and iterates through all valid FT/FF
    combinations, using the preloaded timeline grid for O(1) lookups.
    
    This eliminates ~400k work item transfers per generation.
    
    Args:
        n_genomes: Number of genomes to process
        total_budget: Total gem budget (typically 90)
        gem_scale_fever: Gems per fever stat point (typically 3)
        is_*: Color contribution flags (0/1)
    """
    # Honor TAICHI_BLOCK_DIM (work-group size) for Vulkan kernels.
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    
    for genome_idx in range(n_genomes):
        # Load genome base stats
        base_pp: ti.i32 = genome_base_pp[genome_idx]
        base_cm: ti.i32 = genome_base_cm[genome_idx]
        base_fm: ti.i32 = genome_base_fm[genome_idx]
        base_p_val: ti.i32 = genome_base_p_val[genome_idx]
        base_s_val: ti.i32 = genome_base_s_val[genome_idx]
        base_ft_stat: ti.i32 = genome_base_ft[genome_idx]
        base_ff_stat: ti.i32 = genome_base_ff[genome_idx]
        
        # Compute max FT/FF gems based on stat headroom
        remaining_ft = MAX_STAT - base_ft_stat
        remaining_ff = MAX_STAT - base_ff_stat
        max_ft_gems: ti.i32 = remaining_ft // gem_scale_fever if remaining_ft > 0 else 0
        max_ff_gems: ti.i32 = remaining_ff // gem_scale_fever if remaining_ff > 0 else 0
        
        # Track best result across all FT/FF combinations
        best_score: ti.i32 = -1
        best_ft: ti.i32 = 0
        best_ff: ti.i32 = 0
        best_g_pp: ti.i32 = 0
        best_g_cm: ti.i32 = 0
        best_g_fm: ti.i32 = 0
        best_g_ov: ti.i32 = 0
        
        # Iterate all valid FT/FF combinations
        for ft in range(ti.min(total_budget, max_ft_gems) + 1):
            remaining_for_ff: ti.i32 = total_budget - ft
            
            for ff in range(ti.min(remaining_for_ff, max_ff_gems) + 1):
                # Compute stat indices for grid lookup
                ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
                ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
                ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
                ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
                
                # O(1) lookup from grid
                count_fever: ti.i32 = grid_count_body_fever[ft_idx, ff_idx]
                count_normal: ti.i32 = grid_count_body_normal[ft_idx, ff_idx]
                head_len: ti.i32 = grid_head_len[ft_idx, ff_idx]
                
                # Budget remaining for PP/CM/FM/OV gems
                budget: ti.i32 = total_budget - ft - ff
                
                # Adjust p/s values for FT/FF gem contributions
                p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
                s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
                
                # Run greedy gem allocation (inlined optimize_core_device variant)
                # We can't call optimize_core_device because it stores to work_item arrays
                gems_pp: ti.i32 = 0
                gems_cm: ti.i32 = 0
                gems_fm: ti.i32 = 0
                gems_ov: ti.i32 = 0
                cur_pp: ti.i32 = base_pp
                cur_cm: ti.i32 = base_cm
                cur_fm: ti.i32 = base_fm
                cur_p: ti.i32 = p_val
                cur_s: ti.i32 = s_val
                cur_remaining: ti.i32 = budget
                local_best_score: ti.i32 = 0
                PP_TIE_LOOKAHEAD_MAX: ti.i32 = 8
                
                GEM_SCALE_NORMAL: ti.i32 = 2
                GEM_SCALE_FEVER_LOCAL: ti.i32 = 3
                ELEMENTAL_GEM_SCALE: ti.i32 = 6
                
                while cur_remaining > 0:
                    fill_budget: ti.i32 = cur_remaining - 1
                    fill_bonus: ti.i32 = fill_budget * ELEMENTAL_GEM_SCALE if fill_budget > 0 else 0

                    # Precompute current multipliers (unchanged for PP/OV checks)
                    c_mul_cur: ti.f32 = lookup_ref_cm(cur_cm)
                    f_mul_cur: ti.f32 = lookup_ref_fm(cur_fm)

                    # Start with OV as default so OV wins exact ties.
                    t_p: ti.i32 = cur_p + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
                    t_s: ti.i32 = cur_s + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
                    pp_factor: ti.f32 = lookup_ref_pp(cur_pp)
                    base_val: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                    best_opt_score: ti.i32 = calc_score_with_grid(base_val, c_mul_cur, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
                    best_opt: ti.i32 = 3

                    pp_score: ti.i32 = -1

                    # Option 0: PP gem
                    if cur_pp < MAX_STAT:
                        t_pp: ti.i32 = cur_pp + GEM_SCALE_NORMAL
                        t_p = cur_p + (GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus * is_p_ov)
                        t_s = cur_s + (GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus * is_s_ov)
                        pp_factor = lookup_ref_pp(t_pp)
                        base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                        pp_score = calc_score_with_grid(base_val, c_mul_cur, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
                        if pp_score > best_opt_score:
                            best_opt_score = pp_score
                            best_opt = 0

                    # Option 1: CM gem
                    if cur_cm < MAX_STAT:
                        t_cm: ti.i32 = cur_cm + GEM_SCALE_NORMAL
                        t_p = cur_p + (GEM_STAT_TO_ELEMENT * is_p_cm) + (fill_bonus * is_p_ov)
                        t_s = cur_s + (GEM_STAT_TO_ELEMENT * is_s_cm) + (fill_bonus * is_s_ov)
                        pp_factor = lookup_ref_pp(cur_pp)
                        base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                        c_mul: ti.f32 = lookup_ref_cm(t_cm)
                        score: ti.i32 = calc_score_with_grid(base_val, c_mul, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
                        if score > best_opt_score:
                            best_opt_score = score
                            best_opt = 1

                    # Option 2: FM gem
                    if cur_fm < MAX_STAT:
                        t_fm: ti.i32 = cur_fm + GEM_SCALE_FEVER_LOCAL
                        t_p = cur_p + (GEM_STAT_TO_ELEMENT * is_p_fm) + (fill_bonus * is_p_ov)
                        t_s = cur_s + (GEM_STAT_TO_ELEMENT * is_s_fm) + (fill_bonus * is_s_ov)
                        pp_factor = lookup_ref_pp(cur_pp)
                        base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                        f_mul: ti.f32 = lookup_ref_fm(t_fm)
                        score = calc_score_with_grid(base_val, c_mul_cur, f_mul, ft_idx, ff_idx, head_len, count_fever, count_normal)
                        if score > best_opt_score:
                            best_opt_score = score
                            best_opt = 2

                    # PP lookahead: if OV wins a tie now, but a few PP gems would become a real
                    # improvement soon, start investing in PP.
                    if best_opt == 3 and pp_score == best_opt_score and cur_remaining > 1:
                        max_k: ti.i32 = cur_remaining
                        if max_k > PP_TIE_LOOKAHEAD_MAX:
                            max_k = PP_TIE_LOOKAHEAD_MAX
                        k: ti.i32 = 2
                        while k <= max_k:
                            fill_bonus_k: ti.i32 = (cur_remaining - k) * ELEMENTAL_GEM_SCALE
                            t_pp: ti.i32 = cur_pp + (k * GEM_SCALE_NORMAL)
                            t_p = cur_p + (k * GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus_k * is_p_ov)
                            t_s = cur_s + (k * GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus_k * is_s_ov)
                            pp_factor = lookup_ref_pp(t_pp)
                            base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                            score_k: ti.i32 = calc_score_with_grid(base_val, c_mul_cur, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
                            if score_k > best_opt_score:
                                best_opt = 0
                                break
                            k += 1
                    
                    # Apply best option
                    if best_opt == 0:
                        cur_pp += GEM_SCALE_NORMAL
                        cur_p += GEM_STAT_TO_ELEMENT * is_p_pp
                        cur_s += GEM_STAT_TO_ELEMENT * is_s_pp
                        gems_pp += 1
                    elif best_opt == 1:
                        cur_cm += GEM_SCALE_NORMAL
                        cur_p += GEM_STAT_TO_ELEMENT * is_p_cm
                        cur_s += GEM_STAT_TO_ELEMENT * is_s_cm
                        gems_cm += 1
                    elif best_opt == 2:
                        cur_fm += GEM_SCALE_FEVER_LOCAL
                        cur_p += GEM_STAT_TO_ELEMENT * is_p_fm
                        cur_s += GEM_STAT_TO_ELEMENT * is_s_fm
                        gems_fm += 1
                    else:
                        cur_p += ELEMENTAL_GEM_SCALE * is_p_ov
                        cur_s += ELEMENTAL_GEM_SCALE * is_s_ov
                        gems_ov += 1
                    
                    cur_remaining -= 1
                    local_best_score = best_opt_score
                
                # Check if this FT/FF combo is better
                if local_best_score > best_score:
                    best_score = local_best_score
                    best_ft = ft
                    best_ff = ff
                    best_g_pp = gems_pp
                    best_g_cm = gems_cm
                    best_g_fm = gems_fm
                    best_g_ov = gems_ov
        
        # Store best result for this genome
        genome_result_scores[genome_idx] = best_score
        genome_result_ft[genome_idx] = best_ft
        genome_result_ff[genome_idx] = best_ff
        genome_result_pp[genome_idx] = best_g_pp
        genome_result_cm[genome_idx] = best_g_cm
        genome_result_fm[genome_idx] = best_g_fm
        genome_result_ov[genome_idx] = best_g_ov


@ti.kernel
def solve_ftff_parallel_kernel(
    n_work_items: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
):
    """
    V2 kernel: Parallelize across (genome, ft, ff) combinations.
    
    Each thread handles ONE (genome, ft, ff) combination.
    This gives 500 genomes × ~800 combos = 400k parallel threads.
    
    Uses work_* fields for input (genome_id, ft, ff) and result_* for output.
    Reduction to find best per genome is done on CPU after kernel.
    """
    # Honor TAICHI_BLOCK_DIM (work-group size) for Vulkan kernels.
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    GEM_SCALE_NORMAL: ti.i32 = 2
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    
    for i in range(n_work_items):
        genome_idx: ti.i32 = work_genome_id[i]
        ft: ti.i32 = work_ft_gems[i]
        ff: ti.i32 = work_ff_gems[i]
        
        # Load genome base stats
        base_pp: ti.i32 = genome_base_pp[genome_idx]
        base_cm: ti.i32 = genome_base_cm[genome_idx]
        base_fm: ti.i32 = genome_base_fm[genome_idx]
        base_p_val: ti.i32 = genome_base_p_val[genome_idx]
        base_s_val: ti.i32 = genome_base_s_val[genome_idx]
        base_ft_stat: ti.i32 = genome_base_ft[genome_idx]
        base_ff_stat: ti.i32 = genome_base_ff[genome_idx]
        
        # Compute stat indices for grid lookup
        ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
        
        # O(1) lookup from grid
        count_fever: ti.i32 = grid_count_body_fever[ft_idx, ff_idx]
        count_normal: ti.i32 = grid_count_body_normal[ft_idx, ff_idx]
        head_len: ti.i32 = grid_head_len[ft_idx, ff_idx]
        
        # Budget remaining for PP/CM/FM/OV gems
        budget: ti.i32 = total_budget - ft - ff
        
        # Adjust p/s values for FT/FF gem contributions
        p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
        
        # Run greedy gem allocation
        gems_pp: ti.i32 = 0
        gems_cm: ti.i32 = 0
        gems_fm: ti.i32 = 0
        gems_ov: ti.i32 = 0
        cur_pp: ti.i32 = base_pp
        cur_cm: ti.i32 = base_cm
        cur_fm: ti.i32 = base_fm
        cur_p: ti.i32 = p_val
        cur_s: ti.i32 = s_val
        cur_remaining: ti.i32 = budget
        final_score: ti.i32 = 0
        
        while cur_remaining > 0:
            PP_TIE_LOOKAHEAD_MAX: ti.i32 = 8
            fill_budget: ti.i32 = cur_remaining - 1
            fill_bonus: ti.i32 = fill_budget * ELEMENTAL_GEM_SCALE if fill_budget > 0 else 0

            # Precompute current multipliers (unchanged for PP/OV checks)
            c_mul_cur: ti.f32 = lookup_ref_cm(cur_cm)
            f_mul_cur: ti.f32 = lookup_ref_fm(cur_fm)

            # Start with OV as default so OV wins exact ties.
            t_p: ti.i32 = cur_p + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
            t_s: ti.i32 = cur_s + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
            pp_factor: ti.f32 = lookup_ref_pp(cur_pp)
            base_val: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            best_opt_score: ti.i32 = calc_score_with_grid(base_val, c_mul_cur, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
            best_opt: ti.i32 = 3

            pp_score: ti.i32 = -1

            # Option 0: PP gem
            if cur_pp < MAX_STAT:
                t_pp: ti.i32 = cur_pp + GEM_SCALE_NORMAL
                t_p = cur_p + (GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus * is_p_ov)
                t_s = cur_s + (GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus * is_s_ov)
                pp_factor = lookup_ref_pp(t_pp)
                base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                pp_score = calc_score_with_grid(base_val, c_mul_cur, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
                if pp_score > best_opt_score:
                    best_opt_score = pp_score
                    best_opt = 0

            # Option 1: CM gem
            if cur_cm < MAX_STAT:
                t_cm: ti.i32 = cur_cm + GEM_SCALE_NORMAL
                t_p = cur_p + (GEM_STAT_TO_ELEMENT * is_p_cm) + (fill_bonus * is_p_ov)
                t_s = cur_s + (GEM_STAT_TO_ELEMENT * is_s_cm) + (fill_bonus * is_s_ov)
                pp_factor = lookup_ref_pp(cur_pp)
                base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                c_mul: ti.f32 = lookup_ref_cm(t_cm)
                score: ti.i32 = calc_score_with_grid(base_val, c_mul, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
                if score > best_opt_score:
                    best_opt_score = score
                    best_opt = 1

            # Option 2: FM gem
            if cur_fm < MAX_STAT:
                t_fm: ti.i32 = cur_fm + gem_scale_fever
                t_p = cur_p + (GEM_STAT_TO_ELEMENT * is_p_fm) + (fill_bonus * is_p_ov)
                t_s = cur_s + (GEM_STAT_TO_ELEMENT * is_s_fm) + (fill_bonus * is_s_ov)
                pp_factor = lookup_ref_pp(cur_pp)
                base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                f_mul: ti.f32 = lookup_ref_fm(t_fm)
                score = calc_score_with_grid(base_val, c_mul_cur, f_mul, ft_idx, ff_idx, head_len, count_fever, count_normal)
                if score > best_opt_score:
                    best_opt_score = score
                    best_opt = 2

            # PP lookahead: if OV wins a tie now, but a few PP gems would become a real
            # improvement soon, start investing in PP.
            if best_opt == 3 and pp_score == best_opt_score and cur_remaining > 1:
                max_k: ti.i32 = cur_remaining
                if max_k > PP_TIE_LOOKAHEAD_MAX:
                    max_k = PP_TIE_LOOKAHEAD_MAX
                k: ti.i32 = 2
                while k <= max_k:
                    fill_bonus_k: ti.i32 = (cur_remaining - k) * ELEMENTAL_GEM_SCALE
                    t_pp: ti.i32 = cur_pp + (k * GEM_SCALE_NORMAL)
                    t_p = cur_p + (k * GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus_k * is_p_ov)
                    t_s = cur_s + (k * GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus_k * is_s_ov)
                    pp_factor = lookup_ref_pp(t_pp)
                    base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                    score_k: ti.i32 = calc_score_with_grid(base_val, c_mul_cur, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
                    if score_k > best_opt_score:
                        best_opt = 0
                        break
                    k += 1
            
            # Apply best option
            if best_opt == 0:
                cur_pp += GEM_SCALE_NORMAL
                cur_p += GEM_STAT_TO_ELEMENT * is_p_pp
                cur_s += GEM_STAT_TO_ELEMENT * is_s_pp
                gems_pp += 1
            elif best_opt == 1:
                cur_cm += GEM_SCALE_NORMAL
                cur_p += GEM_STAT_TO_ELEMENT * is_p_cm
                cur_s += GEM_STAT_TO_ELEMENT * is_s_cm
                gems_cm += 1
            elif best_opt == 2:
                cur_fm += gem_scale_fever
                cur_p += GEM_STAT_TO_ELEMENT * is_p_fm
                cur_s += GEM_STAT_TO_ELEMENT * is_s_fm
                gems_fm += 1
            else:
                cur_p += ELEMENTAL_GEM_SCALE * is_p_ov
                cur_s += ELEMENTAL_GEM_SCALE * is_s_ov
                gems_ov += 1
            
            cur_remaining -= 1
            final_score = best_opt_score
        
        # Store result for this work item (reduction done by reduce_best_per_genome_kernel)
        result_scores[i] = final_score
        result_pp[i] = gems_pp
        result_cm[i] = gems_cm
        result_fm[i] = gems_fm
        result_ov[i] = gems_ov


@ti.kernel
def init_genome_results_kernel(n_genomes: ti.i32):
    """
    Initialize genome result fields to -1 (no valid result yet).
    
    Call this ONCE before processing any chunks. The reduction kernel
    will then accumulate best results across all chunks.
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    
    for g in range(n_genomes):
        genome_result_scores[g] = -1
        genome_result_ft[g] = 0
        genome_result_ff[g] = 0
        genome_result_pp[g] = 0
        genome_result_cm[g] = 0
        genome_result_fm[g] = 0
        genome_result_ov[g] = 0


@ti.kernel
def reduce_chunk_to_genomes_kernel(n_work_items: ti.i32):
    """
    GPU-side reduction: find best score per genome from work item results.
    
    This replaces the CPU-side reduction loop, downloading O(n_genomes) instead
    of O(n_work_items) results (~400k → ~500 rows).
    
    Uses atomic_max for thread-safe score comparison. When a thread wins,
    it writes the associated gem allocation. Race condition on writes is
    benign: if two threads have the same max score, either result is valid.
    
    NOTE: Call init_genome_results_kernel() once before the first chunk,
    then call this kernel after each chunk's solve kernel.
    
    Args:
        n_work_items: Number of work items in this chunk to reduce
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    
    for i in range(n_work_items):
        score = result_scores[i]
        gid = work_genome_id[i]
        
        # Atomic compare-and-swap pattern for max score
        # Returns old value, updates field if score > old
        old = ti.atomic_max(genome_result_scores[gid], score)
        
        # If we won (our score is the new max), write associated data
        # Note: benign race - if two threads have same max, one wins
        if old < score:
            genome_result_ft[gid] = work_ft_gems[i]
            genome_result_ff[gid] = work_ff_gems[i]
            genome_result_pp[gid] = result_pp[i]
            genome_result_cm[gid] = result_cm[i]
            genome_result_fm[gid] = result_fm[i]
            genome_result_ov[gid] = result_ov[i]
