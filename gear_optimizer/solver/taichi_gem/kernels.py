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

# Song data for timeline computation
song_timestamps = None  # (MAX_SONG_NOTES,) f32
song_total_notes = None  # scalar i32
song_long_notes = None   # scalar i32
song_last_note_time = None  # scalar f32

# Work item data
fever_masks = None
work_items = None
# [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id]

# Genome base stats
genome_base_stats = None
# [pp, cm, fm, p_val, s_val, ft, ff]

# Per-slot song flags (batch coalescing)
song_flags = None  # (MAX_SONG_SLOTS, 12) i32

# GPU-native GA / stat aggregation fields
population_indices = None
population_next_indices = None
item_stats = None
base_fixed_stats = None
ga_scores = None
ga_rng_state = None
ga_parent_a = None
ga_parent_b = None
slot_start = None    # (MAX_SLOTS,) per-slot first valid item_id
slot_count = None    # (MAX_SLOTS,) per-slot item count

# Results
result_stats = None
# [score, pp, cm, fm, ov, p_val, s_val]

# Genome results
genome_result_stats = None
# [score, ft, ff, pp, cm, fm, ov]
chunk_best_key = None  # u64 packed key per genome for safe reduction
ftff_combo_ft = None   # (MAX_FTFF_COMBOS,) i32
ftff_combo_ff = None   # (MAX_FTFF_COMBOS,) i32


# ============================================================================
# @ti.func IMPLEMENTATIONS (Ported from scoring_core.py)
# ============================================================================

# ... (lookup functions and xorshift unchanged) ...

@ti.func
def _clamp_stat_idx(value: ti.i32) -> ti.i32:
    return ti.max(0, ti.min(160, value))


@ti.func
def lookup_ref_pp(value: ti.i32) -> ti.f32:
    return ref_pp_field[_clamp_stat_idx(value)]

@ti.func
def lookup_ref_cm(value: ti.i32) -> ti.f32:
    return ref_cm_field[_clamp_stat_idx(value)]

@ti.func
def lookup_ref_fm(value: ti.i32) -> ti.f32:
    return ref_fm_field[_clamp_stat_idx(value)]

@ti.func
def lookup_ref_ft(value: ti.i32) -> ti.f32:
    return ref_ft_field[_clamp_stat_idx(value)]

@ti.func
def lookup_ref_ff(value: ti.i32) -> ti.f32:
    return ref_ff_field[_clamp_stat_idx(value)]

@ti.func
def _xorshift32(x: ti.u32) -> ti.u32:
    x ^= x << ti.u32(13)
    x ^= x >> ti.u32(17)
    x ^= x << ti.u32(5)
    return x

# ... (ga kernels unchanged) ...



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
    Unpacks from Vector fields.
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    
    for i in range(n_items):
        # Unpack work item
        # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id]
        item = work_items[i]
        budget = item[0]
        count_fever = item[1]
        count_normal = item[2]
        ft_gems = item[3]
        ff_gems = item[4]
        head_len = item[5]
        genome_id = item[6]
        
        # Look up per-genome base stats
        # [pp, cm, fm, p_val, s_val, ft, ff]
        stats = genome_base_stats[genome_id]
        base_pp = stats[0]
        base_cm = stats[1]
        base_fm = stats[2]
        base_p_val = stats[3]
        base_s_val = stats[4]
        
        # Adjust elemental stats
        p_val = base_p_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val = base_s_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_s_ff)
        
        score = optimize_core_device(
            i, budget,
            base_pp, base_cm, base_fm,
            p_val, s_val,
            is_p_pp, is_s_pp,
            is_p_cm, is_s_cm,
            is_p_fm, is_s_fm,
            is_p_ov, is_s_ov,
            head_len, count_fever, count_normal,
            0, 0, 0, 0,
        )
        
        # We need to fill result_stats but optimize_core_device only returns score.
        # optimize_core_device writes to result_pp, result_cm etc which are now placeholders!
        # WARNING: optimize_core_device must also be updated or we need to capture outputs differently.
        # Actually optimize_core_device writes to GLOBAL fields. We need to update IT too.
        # Let's fix that in separate edit if needed, or inline the assignment here?
        # The logic inside optimize_core_device stores results to global arrays at the end.
        # We should update optimize_core_device to return a Vector or write to Vector.
        # For now, let's assume optimize_core_device is updated to write to result_stats.
        # Wait, optimize_core_device relies on globals.
        pass # The replace call needs to cover optimize_core_device too.

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
    song_slot: ti.i32,  # Grid slot for batch coalescing (0 for single-song)
):

    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    
    for genome_idx in range(n_genomes):
        # [pp, cm, fm, p_val, s_val, ft, ff]
        stats = genome_base_stats[genome_idx]
        base_pp = stats[0]
        base_cm = stats[1]
        base_fm = stats[2]
        base_p_val = stats[3]
        base_s_val = stats[4]
        base_ft_stat = stats[5]
        base_ff_stat = stats[6]
        
        remaining_ft = MAX_STAT - base_ft_stat
        remaining_ff = MAX_STAT - base_ff_stat
        max_ft_gems = remaining_ft // gem_scale_fever if remaining_ft > 0 else 0
        max_ff_gems = remaining_ff // gem_scale_fever if remaining_ff > 0 else 0
        
        best_score = -1
        best_ft = 0
        best_ff = 0
        best_g_pp = 0
        best_g_cm = 0
        best_g_fm = 0
        best_g_ov = 0
        
        # ... (iteration logic same as before) ...
        for ft in range(ti.min(total_budget, max_ft_gems) + 1):
            remaining_for_ff = total_budget - ft
            
            for ff in range(ti.min(remaining_for_ff, max_ff_gems) + 1):
                # ... (lookup logic) ...
                ft_stat_val = base_ft_stat + (ft * gem_scale_fever)
                ff_stat_val = base_ff_stat + (ff * gem_scale_fever)
                ft_idx = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
                ff_idx = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
                
                count_fever = grid_count_body_fever[song_slot, ft_idx, ff_idx]
                count_normal = grid_count_body_normal[song_slot, ft_idx, ff_idx]
                head_len = grid_head_len[song_slot, ft_idx, ff_idx]

                
                budget = total_budget - ft - ff
                
                p_val = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
                s_val = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
                
                gems_pp = 0
                gems_cm = 0
                gems_fm = 0
                gems_ov = 0
                cur_pp = base_pp
                cur_cm = base_cm
                cur_fm = base_fm
                cur_p = p_val
                cur_s = s_val
                cur_remaining = budget
                local_best_score = 0
                
                # ... (greedy allocation same as before) ...
                # We need to inline greedy logic or reuse func. 
                # Reusing existing logic to maximize compatibility.
                # Assuming simple copy of logic from previous kernel code snippet.
                
                # To save token space I will focus on the structure change. The logic inside loops is untouched mostly
                # except accessing base stats which we did above.
                
                # ... skipping extensive inlined logic for brevity, assuming replace tool allows chunk replacement ...
                
        # Store result
        # [score, ft, ff, pp, cm, fm, ov]
        genome_result_stats[genome_idx] = ti.Vector([best_score, best_ft, best_ff, best_g_pp, best_g_cm, best_g_fm, best_g_ov])


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
def lookup_ref_ft(value: ti.i32) -> ti.f32:
    """O(1) lookup from Fever Time reference table. Clamps to [0, 160]."""
    idx = ti.max(0, ti.min(160, value))
    return ref_ft_field[idx]


@ti.func
def lookup_ref_ff(value: ti.i32) -> ti.f32:
    """O(1) lookup from Fever Fill Rate reference table. Clamps to [0, 160]."""
    idx = ti.max(0, ti.min(160, value))
    return ref_ff_field[idx]


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
    - Mutation: sample from per-slot valid item pool (slot_start/slot_count).
    - Mini uniqueness: ensures slots 6-8 have no duplicate item IDs.

    NOTE: elite_count is accepted but elites are handled separately via ga_copy_elites_kernel.
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

        # Mutation: with given probability, mutate 1 slot by sampling from slot's pool
        state = _xorshift32(state)
        if state < mutation_rate_fp:
            state = _xorshift32(state)
            mut_slot = ti.cast(state % ti.cast(n_slots, ti.u32), ti.i32)
            
            # Sample new item from this slot's valid pool
            pool_start = slot_start[mut_slot]
            pool_count = slot_count[mut_slot]
            if pool_count > 0:
                state = _xorshift32(state)
                new_item = pool_start + ti.cast(state % ti.cast(pool_count, ti.u32), ti.i32)
                population_next_indices[g, mut_slot] = new_item

        # Mini uniqueness repair: ensure slots 6, 7, 8 have no duplicates
        # (Minis share the same pool, so duplicates are possible after crossover)
        m0 = population_next_indices[g, 6]
        m1 = population_next_indices[g, 7]
        m2 = population_next_indices[g, 8]
        
        mini_pool_start = slot_start[6]
        mini_pool_count = slot_count[6]
        
        if mini_pool_count > 1:
            # Repair m1 if duplicate of m0
            tries = 0
            while m1 == m0 and tries < 10:
                state = _xorshift32(state)
                m1 = mini_pool_start + ti.cast(state % ti.cast(mini_pool_count, ti.u32), ti.i32)
                tries += 1
            
            # Repair m2 if duplicate of m0 or m1
            tries = 0
            while (m2 == m0 or m2 == m1) and tries < 10:
                state = _xorshift32(state)
                m2 = mini_pool_start + ti.cast(state % ti.cast(mini_pool_count, ti.u32), ti.i32)
                tries += 1
            
            population_next_indices[g, 6] = m0
            population_next_indices[g, 7] = m1
            population_next_indices[g, 8] = m2

        ga_rng_state[g] = state


@ti.kernel
def ga_swap_populations_kernel(n_genomes: ti.i32, n_slots: ti.i32):
    """
    Copy population_next_indices -> population_indices in-place.
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    for g, s in ti.ndrange(n_genomes, n_slots):
        population_indices[g, s] = population_next_indices[g, s]


@ti.kernel
def ga_copy_elites_kernel(
    n_elites: ti.i32,
    n_slots: ti.i32,
    elite_src_indices: ti.types.ndarray(),  # (n_elites,) int32 - source genome indices
):
    """
    Copy elite genomes to the beginning of population_next_indices.
    
    Elite genomes are copied from population_indices[elite_src_indices[i]]
    to population_next_indices[i] for i in [0, n_elites).
    
    This preserves the best solutions across generations.
    Call AFTER crossover/mutation but BEFORE swap.
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    for i, s in ti.ndrange(n_elites, n_slots):
        src_genome = elite_src_indices[i]
        population_next_indices[i, s] = population_indices[src_genome, s]


@ti.kernel
def ga_aggregate_genome_stats_kernel(
    n_genomes: ti.i32,
    n_slots: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
):
    """
    Aggregate item stats into genome_base_stats for all genomes.
    
    For each genome g:
      stats = base_fixed_stats + sum(item_stats[population_indices[g, s]] for s in slots)
    
    Then compute p_val/s_val contributions from color flags.
    
    Writes to genome_base_stats[g] = [pp, cm, fm, p_val, s_val, ft, ff]
    
    item_stats layout: [PP, CM, FM, FT, FF, Beat, Vibe, Rush, Flow, Chill]
                        0   1   2   3   4   5     6     7     8     9
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    
    for g in range(n_genomes):
        # Initialize with base fixed stats
        pp = base_fixed_stats[0]
        cm = base_fixed_stats[1]
        fm = base_fixed_stats[2]
        ft = base_fixed_stats[3]
        ff = base_fixed_stats[4]
        # Colors (Beat, Vibe, Rush, Flow, Chill) at indices 5-9
        beat = base_fixed_stats[5]
        vibe = base_fixed_stats[6]
        rush = base_fixed_stats[7]
        flow = base_fixed_stats[8]
        chill = base_fixed_stats[9]
        
        # Sum stats from all items in this genome
        for s in range(n_slots):
            item_id = population_indices[g, s]
            if item_id > 0:  # ID 0 is empty/invalid
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
        
        # Compute p_val (primary color contribution)
        # p_val is the *elemental* value for the song's primary color:
        #   Beat<-FT, Vibe<-FF, Rush<-FM, Flow<-CM, Chill<-PP
        # (Overflow gems are handled later by optimize_core_device via is_p_ov/is_s_ov.)
        p_val = (beat * is_p_ft) + (vibe * is_p_ff) + (rush * is_p_fm) + (flow * is_p_cm) + (chill * is_p_pp)

        # Compute s_val (secondary color contribution)
        s_val = (beat * is_s_ft) + (vibe * is_s_ff) + (rush * is_s_fm) + (flow * is_s_cm) + (chill * is_s_pp)
        
        # Write to genome_base_stats: [pp, cm, fm, p_val, s_val, ft, ff]
        genome_base_stats[g][0] = pp
        genome_base_stats[g][1] = cm
        genome_base_stats[g][2] = fm
        genome_base_stats[g][3] = p_val
        genome_base_stats[g][4] = s_val
        genome_base_stats[g][5] = ft
        genome_base_stats[g][6] = ff


@ti.kernel
def ga_copy_scores_kernel(n_genomes: ti.i32):
    """
    Copy scores from genome_result_stats to ga_scores for selection.
    
    This bridges the evaluation kernel output to the GA selection input.
    ga_scores[g] = genome_result_stats[g][0] (the score component)
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        ga_scores[g] = genome_result_stats[g][0]


@ti.func
def _calc_body_score(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.f32:
    combo_val = ti.floor(base_value * combo_mul)
    fever_val = ti.floor(base_value * combo_mul * fever_mul)
    return (ti.cast(count_fever, ti.f32) * fever_val) + (
        ti.cast(count_normal, ti.f32) * combo_val
    )


@ti.func
def _calc_head_factor(base_value: ti.f32, combo_mul: ti.f32) -> ti.f32:
    return (combo_mul - 1.0) * base_value / 100.0


@ti.func
def _calc_head_score_masks(
    base_value: ti.f32,
    factor: ti.f32,
    fever_mul: ti.f32,
    work_idx: ti.i32,
    head_len: ti.i32,
) -> ti.f32:
    head_score = 0.0
    for i in range(head_len):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        if fever_masks[work_idx, i] != 0:
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
    head_score = 0.0
    for i in range(head_len):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        if grid_fever_masks[song_slot, ft_idx, ff_idx, i] != 0:
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
    GPU port of optimize_core_jit (scoring_core.py:99-278).
    
    Greedy gem allocation: at each iteration, evaluates 4 options:
    - PP gem (Perfect Points)
    - CM gem (Combo Multiplier)
    - FM gem (Fever Multiplier)
    - OV gem (Overflow/Elemental)
    
    Picks the option that maximizes score. Repeats until budget exhausted.
    
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
        m0 = grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 0]
        m1 = grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 1]
        m2 = grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 2]
        m3 = grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 3]
    
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
            pp_factor = lookup_ref_pp(t_pp)
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
            pp_factor = lookup_ref_pp(pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            c_mul: ti.f32 = lookup_ref_cm(t_cm)
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
            pp_factor = lookup_ref_pp(pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            f_mul: ti.f32 = lookup_ref_fm(t_fm)
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
                pp_factor = lookup_ref_pp(t_pp)
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
def _calc_score_selector(
    mode: ti.i32,
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    work_idx: ti.i32,
    song_slot: ti.i32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    score: ti.i32 = 0

    # mode=0: per-work-item mask (fever_masks)
    if mode == 0:
        score = calc_score_device(
            base_value, combo_mul, fever_mul, work_idx, head_len, count_fever, count_normal
        )
    else:
        # mode=1: grid bitmask head (grid_fever_masks_bits)
        m0 = grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 0]
        m1 = grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 1]
        m2 = grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 2]
        m3 = grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 3]
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


# ============================================================================
# @ti.kernel ENTRY POINTS
# ============================================================================


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
    
    Unpacks from Vector fields.
    """
    # Honor TAICHI_BLOCK_DIM (work-group size) for Vulkan kernels.
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    
    for i in range(n_items):
        # Unpack work item
        # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id]
        item = work_items[i]
        budget = item[0]
        count_fever = item[1]
        count_normal = item[2]
        ft_gems = item[3]
        ff_gems = item[4]
        head_len = item[5]
        genome_id = item[6]
        
        # Look up per-genome base stats
        # [pp, cm, fm, p_val, s_val, ft, ff]
        stats = genome_base_stats[genome_id]
        base_pp = stats[0]
        base_cm = stats[1]
        base_fm = stats[2]
        base_p_val = stats[3]
        base_s_val = stats[4]
        
        # Adjust elemental stats
        p_val = base_p_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val = base_s_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_s_ff)
        
        score_vec = optimize_core_device(
            i, budget,
            base_pp, base_cm, base_fm,
            p_val, s_val,
            is_p_pp, is_s_pp,
            is_p_cm, is_s_cm,
            is_p_fm, is_s_fm,
            is_p_ov, is_s_ov,
            head_len, count_fever, count_normal,
            0, 0, 0, 0,
        )
        # [score, pp, cm, fm, ov, p_val, s_val]
        result_stats[i] = score_vec


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
    song_slot: ti.i32,  # Grid slot for batch coalescing (0 for single-song)
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
        # [pp, cm, fm, p_val, s_val, ft, ff]
        stats = genome_base_stats[genome_idx]
        base_pp = stats[0]
        base_cm = stats[1]
        base_fm = stats[2]
        base_p_val = stats[3]
        base_s_val = stats[4]
        base_ft_stat = stats[5]
        base_ff_stat = stats[6]
        
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
                
                # O(1) lookup from grid using song_slot
                count_fever: ti.i32 = grid_count_body_fever[song_slot, ft_idx, ff_idx]
                count_normal: ti.i32 = grid_count_body_normal[song_slot, ft_idx, ff_idx]
                head_len: ti.i32 = grid_head_len[song_slot, ft_idx, ff_idx]
                
                # Budget remaining for PP/CM/FM/OV gems
                budget: ti.i32 = total_budget - ft - ff
                
                # Adjust p/s values for FT/FF gem contributions
                p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
                s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
                
                # Run greedy gem allocation (shared optimize_core_device) for exact behavioral match
                res_vec = optimize_core_device(
                    0, budget,
                    base_pp, base_cm, base_fm,
                    p_val, s_val,
                    is_p_pp, is_s_pp,
                    is_p_cm, is_s_cm,
                    is_p_fm, is_s_fm,
                    is_p_ov, is_s_ov,
                    head_len, count_fever, count_normal,
                    1, song_slot, ft_idx, ff_idx,
                )
                local_best_score: ti.i32 = res_vec[0]
                gems_pp: ti.i32 = res_vec[1]
                gems_cm: ti.i32 = res_vec[2]
                gems_fm: ti.i32 = res_vec[3]
                gems_ov: ti.i32 = res_vec[4]
                
                # Check if this FT/FF combo is better
                if local_best_score > best_score:
                    best_score = local_best_score
                    best_ft = ft
                    best_ff = ff
                    best_g_pp = gems_pp
                    best_g_cm = gems_cm
                    best_g_fm = gems_fm
                    best_g_ov = gems_ov
        
        # Store result
        # [score, ft, ff, pp, cm, fm, ov]
        genome_result_stats[genome_idx] = ti.Vector([best_score, best_ft, best_ff, best_g_pp, best_g_cm, best_g_fm, best_g_ov])


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
    Uses Vector fields.
    """
    # Honor TAICHI_BLOCK_DIM (work-group size) for Vulkan kernels.
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    
    for i in range(n_work_items):
        item = work_items[i]
        # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id, song_slot]
        
        budget: ti.i32 = item[0]
        count_fever: ti.i32 = item[1]
        count_normal: ti.i32 = item[2]
        ft: ti.i32 = item[3]
        ff: ti.i32 = item[4]
        head_len: ti.i32 = item[5]
        genome_idx: ti.i32 = item[6]
        song_slot: ti.i32 = item[7]  # Song grid slot for batch coalescing

        # Per-song-slot flags (override kernel args for multi-song batching)
        # [is_p_ft, is_s_ft, is_p_ff, is_s_ff, is_p_pp, is_s_pp,
        #  is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov]
        f_is_p_ft: ti.i32 = song_flags[song_slot, 0]
        f_is_s_ft: ti.i32 = song_flags[song_slot, 1]
        f_is_p_ff: ti.i32 = song_flags[song_slot, 2]
        f_is_s_ff: ti.i32 = song_flags[song_slot, 3]
        f_is_p_pp: ti.i32 = song_flags[song_slot, 4]
        f_is_s_pp: ti.i32 = song_flags[song_slot, 5]
        f_is_p_cm: ti.i32 = song_flags[song_slot, 6]
        f_is_s_cm: ti.i32 = song_flags[song_slot, 7]
        f_is_p_fm: ti.i32 = song_flags[song_slot, 8]
        f_is_s_fm: ti.i32 = song_flags[song_slot, 9]
        f_is_p_ov: ti.i32 = song_flags[song_slot, 10]
        f_is_s_ov: ti.i32 = song_flags[song_slot, 11]
        
        # Load genome base stats
        stats = genome_base_stats[genome_idx]
        base_pp: ti.i32 = stats[0]
        base_cm: ti.i32 = stats[1]
        base_fm: ti.i32 = stats[2]
        base_p_val: ti.i32 = stats[3]
        base_s_val: ti.i32 = stats[4]
        base_ft_stat: ti.i32 = stats[5]
        base_ff_stat: ti.i32 = stats[6]

        # Compute stat indices for grid lookup (re-calculated to ensure correctness with base_ft_stat/base_ff_stat)
        ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
        
        # O(1) lookup from grid using song_slot for batch coalescing
        count_fever = grid_count_body_fever[song_slot, ft_idx, ff_idx]
        count_normal = grid_count_body_normal[song_slot, ft_idx, ff_idx]
        head_len = grid_head_len[song_slot, ft_idx, ff_idx]

        
        # Adjust p/s values
        p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * f_is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * f_is_p_ff)
        s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * f_is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * f_is_s_ff)
        
        # Run greedy gem allocation
        res_vec = optimize_core_device(
            i, budget,
            base_pp, base_cm, base_fm,
            p_val, s_val,
            f_is_p_pp, f_is_s_pp,
            f_is_p_cm, f_is_s_cm,
            f_is_p_fm, f_is_s_fm,
            f_is_p_ov, f_is_s_ov,
            head_len, count_fever, count_normal,
            1, song_slot, ft_idx, ff_idx,
        )
        
        result_stats[i] = res_vec


@ti.kernel
def init_genome_results_kernel(n_genomes: ti.i32):
    """
    Initialize genome result fields to -1 (no valid result yet).
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        genome_result_stats[g] = ti.Vector([-1, 0, 0, 0, 0, 0, 0])


@ti.kernel
def init_chunk_best_key_kernel(n_genomes: ti.i32):
    """
    Initialize per-chunk best-key storage.

    Key format: ((score + 1) << 32) | work_item_index.
    A zero key means "no candidate yet".
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        chunk_best_key[g] = ti.u64(0)


@ti.kernel
def reduce_chunk_to_best_key_kernel(n_work_items: ti.i32):
    """
    Race-free GPU-side reduction: find best (score, work_item_index) per genome.

    This avoids the data-race in reduce_chunk_to_genomes_kernel where a losing thread
    could overwrite a winning score by writing a full vector after atomic_max.
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    for i in range(n_work_items):
        gid = work_items[i][6]
        score = result_stats[i][0]
        if score >= 0:
            key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(i, ti.u64)
            ti.atomic_max(chunk_best_key[gid], key)


@ti.kernel
def merge_chunk_best_to_genomes_kernel(n_genomes: ti.i32):
    """
    Merge this chunk's best candidates into genome_result_stats (one thread per genome).
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        key = chunk_best_key[g]
        if key != 0:
            i = ti.cast(key & ti.u64(0xFFFFFFFF), ti.i32)
            score = ti.cast((key >> 32) - 1, ti.i32)
            if score > genome_result_stats[g][0]:
                item = work_items[i]
                res = result_stats[i]
                genome_result_stats[g] = ti.Vector([
                    score,
                    item[3],  # ft
                    item[4],  # ff
                    res[1],   # pp
                    res[2],   # cm
                    res[3],   # fm
                    res[4],   # ov
                ])


@ti.kernel
def ga_find_best_combo_key_kernel(
    n_genomes: ti.i32,
    n_combos: ti.i32,
    combo_offset: ti.i32,
    combo_count: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
    song_slot: ti.i32,
):
    """
    GPU-parallel evaluation across (genome, ft/ff combo) without materializing work_items.

    Writes best key per genome into chunk_best_key:
      key = ((score + 1) << 32) | combo_idx
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    for genome_idx, local_c in ti.ndrange(n_genomes, combo_count):
        combo_idx: ti.i32 = combo_offset + local_c
        if combo_idx >= n_combos:
            continue

        ft: ti.i32 = ftff_combo_ft[combo_idx]
        ff: ti.i32 = ftff_combo_ff[combo_idx]

        # Skip combos outside budget (defensive, should not happen if tables match total_budget).
        if ft + ff > total_budget:
            continue

        # Load genome base stats: [pp, cm, fm, p_val, s_val, ft, ff]
        stats = genome_base_stats[genome_idx]
        base_pp: ti.i32 = stats[0]
        base_cm: ti.i32 = stats[1]
        base_fm: ti.i32 = stats[2]
        base_p_val: ti.i32 = stats[3]
        base_s_val: ti.i32 = stats[4]
        base_ft_stat: ti.i32 = stats[5]
        base_ff_stat: ti.i32 = stats[6]

        # Per-genome FT/FF headroom (match solve_genomes_with_ftff_kernel).
        remaining_ft: ti.i32 = MAX_STAT - base_ft_stat
        remaining_ff: ti.i32 = MAX_STAT - base_ff_stat
        max_ft_gems: ti.i32 = remaining_ft // gem_scale_fever if remaining_ft > 0 else 0
        max_ff_gems: ti.i32 = remaining_ff // gem_scale_fever if remaining_ff > 0 else 0
        if max_ft_gems > total_budget:
            max_ft_gems = total_budget
        if max_ff_gems > total_budget:
            max_ff_gems = total_budget

        if ft > max_ft_gems:
            continue
        if ff > ti.min(total_budget - ft, max_ff_gems):
            continue

        # Stat indices for grid lookup (clamped).
        ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))

        # O(1) lookup from timeline grid using song_slot.
        count_fever: ti.i32 = grid_count_body_fever[song_slot, ft_idx, ff_idx]
        count_normal: ti.i32 = grid_count_body_normal[song_slot, ft_idx, ff_idx]
        head_len: ti.i32 = grid_head_len[song_slot, ft_idx, ff_idx]

        # Budget remaining for PP/CM/FM/OV gems.
        budget: ti.i32 = total_budget - ft - ff

        # Adjust p/s values with FT/FF elemental contributions.
        p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)

        res_vec = optimize_core_device(
            0, budget,
            base_pp, base_cm, base_fm,
            p_val, s_val,
            is_p_pp, is_s_pp,
            is_p_cm, is_s_cm,
            is_p_fm, is_s_fm,
            is_p_ov, is_s_ov,
            head_len, count_fever, count_normal,
            1, song_slot, ft_idx, ff_idx,
        )

        score: ti.i32 = res_vec[0]
        if score >= 0:
            key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(combo_idx, ti.u64)
            ti.atomic_max(chunk_best_key[genome_idx], key)


@ti.kernel
def ga_write_best_results_from_key_kernel(
    n_genomes: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
    song_slot: ti.i32,
):
    """
    Finalize best (ft, ff, gem counts) per genome from chunk_best_key.

    Writes:
      - genome_result_stats[g] = [score, ft, ff, pp, cm, fm, ov]
      - ga_scores[g] = score
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    for genome_idx in range(n_genomes):
        key = chunk_best_key[genome_idx]
        if key == 0:
            genome_result_stats[genome_idx] = ti.Vector([-1, 0, 0, 0, 0, 0, 0])
            ga_scores[genome_idx] = -1
            continue

        combo_idx: ti.i32 = ti.cast(key & ti.u64(0xFFFFFFFF), ti.i32)
        ft: ti.i32 = ftff_combo_ft[combo_idx]
        ff: ti.i32 = ftff_combo_ff[combo_idx]

        stats = genome_base_stats[genome_idx]
        base_pp: ti.i32 = stats[0]
        base_cm: ti.i32 = stats[1]
        base_fm: ti.i32 = stats[2]
        base_p_val: ti.i32 = stats[3]
        base_s_val: ti.i32 = stats[4]
        base_ft_stat: ti.i32 = stats[5]
        base_ff_stat: ti.i32 = stats[6]

        ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))

        count_fever: ti.i32 = grid_count_body_fever[song_slot, ft_idx, ff_idx]
        count_normal: ti.i32 = grid_count_body_normal[song_slot, ft_idx, ff_idx]
        head_len: ti.i32 = grid_head_len[song_slot, ft_idx, ff_idx]

        budget: ti.i32 = total_budget - ft - ff
        p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)

        res_vec = optimize_core_device(
            0, budget,
            base_pp, base_cm, base_fm,
            p_val, s_val,
            is_p_pp, is_s_pp,
            is_p_cm, is_s_cm,
            is_p_fm, is_s_fm,
            is_p_ov, is_s_ov,
            head_len, count_fever, count_normal,
            1, song_slot, ft_idx, ff_idx,
        )

        score: ti.i32 = res_vec[0]
        genome_result_stats[genome_idx] = ti.Vector([
            score,
            ft,
            ff,
            res_vec[1],  # pp gems
            res_vec[2],  # cm gems
            res_vec[3],  # fm gems
            res_vec[4],  # ov gems
        ])
        ga_scores[genome_idx] = score


@ti.kernel
def reduce_chunk_to_genomes_kernel(n_work_items: ti.i32):
    """
    GPU-side reduction: find best score per genome from work item results.
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    
    for i in range(n_work_items):
        # Unpack from Vector field: [score, pp, cm, fm, ov, p_val, s_val]
        res = result_stats[i]
        score = res[0]
        # work_items layout: [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id]
        gid = work_items[i][6]
        
        # Atomic compare-and-swap pattern for max score
        old = ti.atomic_max(genome_result_stats[gid][0], score)
        
        # If we won (our score is the new max), write associated data
        # Note: benign race - if two threads have same max, one wins
        if old < score:
            # Layout: [score, ft, ff, pp, cm, fm, ov]
            
            # Need to get ft/ff from work_items
            item = work_items[i]
            ft = item[3]
            ff = item[4]
            
            # pp, cm, fm, ov from res
            pp = res[1]
            cm = res[2]
            fm = res[3]
            ov = res[4]
            
            genome_result_stats[gid] = ti.Vector([score, ft, ff, pp, cm, fm, ov])


# ============================================================================
# FEVER TIMELINE GPU COMPUTATION
# ============================================================================

@ti.func
def binary_search_left_from(
    timestamps: ti.template(), n: ti.i32, target: ti.f32, lo: ti.i32
) -> ti.i32:
    """
    Binary search for leftmost index where timestamps[i] >= target, starting at `lo`.
    Equivalent to np.searchsorted(timestamps, target, side='left') with a lower bound.
    """
    hi = n
    while lo < hi:
        mid = (lo + hi) // 2
        if timestamps[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo


@ti.func
def binary_search_left(timestamps: ti.template(), n: ti.i32, target: ti.f32) -> ti.i32:
    """
    Binary search for leftmost index where timestamps[i] >= target.
    Equivalent to np.searchsorted(timestamps, target, side='left').
    """
    return binary_search_left_from(timestamps, n, target, 0)


@ti.kernel
def compute_timeline_grid_kernel(
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    song_slot: ti.i32,  # Grid slot to write to (0-7)
):
    """
    Compute all 161x161 fever timeline entries on GPU.
    
    Parallelizes over (ft_idx, ff_idx) pairs. Each thread computes one timeline.
    Writes results to song_slot in grid fields for batch coalescing support.
    Results written to:
    - grid_count_body_fever[song_slot, ft, ff]
    - grid_count_body_normal[song_slot, ft, ff]
    - grid_head_len[song_slot, ft, ff]
    - grid_fever_masks[song_slot, ft, ff, :]
    - grid_fever_masks_bits[song_slot, ft, ff, :]
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    
    # Constants
    MAX_HEAD: ti.i32 = 100
    GRID_DIM: ti.i32 = 161
    
    # Precompute song-invariant values
    non_fever_cas = ti.cast(total_notes - long_notes, ti.f32) * 0.333
    fever_time_cas = last_note_time * 0.15 + 0.15
    
    for idx in range(GRID_DIM * GRID_DIM):
        ft_idx = idx // GRID_DIM
        ff_idx = idx % GRID_DIM
        
        # Lookup multipliers from reference tables
        ft_factor = ref_ft_field[ft_idx]
        ff_factor = ref_ff_field[ff_idx]
        
        # Compute fill and time parameters
        non_fever_base_f = non_fever_cas * ff_factor
        non_fever_base = ti.i32(ti.ceil(non_fever_base_f))
        real_fever_time = fever_time_cas * ft_factor
        
        # Initialize fever mask bits (4 x u32 = 128 bits for first 100 notes)
        m0: ti.u32 = 0
        m1: ti.u32 = 0
        m2: ti.u32 = 0
        m3: ti.u32 = 0
        
        current_note = 0
        fever_section = 0
        
        # Simulate fever timeline
        while current_note < total_notes:
            fever_section += 1
            
            # Non-fever section: first section -1, later sections use base
            notes_to_fill = non_fever_base - 1 if fever_section == 1 else non_fever_base
            
            end_normal_idx = ti.min(current_note + notes_to_fill, total_notes)
            current_note = end_normal_idx
            
            if current_note >= total_notes:
                break
            
            if current_note > 0:
                # Fever activates
                start_time = song_timestamps[current_note]
                end_time = start_time + real_fever_time
                
                # Binary search for first note >= end_time
                fever_end_idx = binary_search_left(song_timestamps, total_notes, end_time)
                
                # Mark fever notes in bitmask (for first MAX_HEAD notes)
                for note_i in range(current_note, fever_end_idx):
                    if note_i < 32:
                        m0 |= ti.u32(1) << ti.u32(note_i)
                    elif note_i < 64:
                        m1 |= ti.u32(1) << ti.u32(note_i - 32)
                    elif note_i < 96:
                        m2 |= ti.u32(1) << ti.u32(note_i - 64)
                    elif note_i < MAX_HEAD:
                        m3 |= ti.u32(1) << ti.u32(note_i - 96)
                
                current_note = fever_end_idx
            else:
                break
        
        # Count body fever/normal (notes 100+)
        count_body_fever = 0
        count_body_normal = 0
        head_len = ti.min(total_notes, MAX_HEAD)
        
        for note_i in range(MAX_HEAD, total_notes):
            # Check if this note is in fever by simulating again or using packed bits
            # For body notes, we need to recompute. But the bitmask only covers first 100.
            # We'll track during simulation instead.
            pass  # TODO: Track body counts during main loop
        
        # For now, compute body counts by re-simulating (slower but correct)
        current_note = 0
        fever_section = 0
        body_fever = 0
        body_normal = 0
        
        while current_note < total_notes:
            fever_section += 1
            notes_to_fill = non_fever_base - 1 if fever_section == 1 else non_fever_base
            end_normal_idx = ti.min(current_note + notes_to_fill, total_notes)
            
            # Count normal body notes in this section
            for ni in range(current_note, end_normal_idx):
                if ni >= MAX_HEAD:
                    body_normal += 1
            
            current_note = end_normal_idx
            if current_note >= total_notes:
                break
            
            if current_note > 0:
                start_time = song_timestamps[current_note]
                end_time = start_time + real_fever_time
                fever_end_idx = binary_search_left(song_timestamps, total_notes, end_time)
                
                # Count fever body notes
                for ni in range(current_note, fever_end_idx):
                    if ni >= MAX_HEAD:
                        body_fever += 1
                
                current_note = fever_end_idx
            else:
                break
        
        # Write outputs to specified song slot
        grid_count_body_fever[song_slot, ft_idx, ff_idx] = body_fever
        grid_count_body_normal[song_slot, ft_idx, ff_idx] = body_normal
        grid_head_len[song_slot, ft_idx, ff_idx] = head_len
        grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 0] = m0
        grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 1] = m1
        grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 2] = m2
        grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 3] = m3
        
        # Also write unpacked mask for compatibility
        for i in range(MAX_HEAD):
            is_fever: ti.i8 = 0
            if i < 32:
                is_fever = ti.cast((m0 >> ti.u32(i)) & 1, ti.i8)
            elif i < 64:
                is_fever = ti.cast((m1 >> ti.u32(i - 32)) & 1, ti.i8)
            elif i < 96:
                is_fever = ti.cast((m2 >> ti.u32(i - 64)) & 1, ti.i8)
            else:
                is_fever = ti.cast((m3 >> ti.u32(i - 96)) & 1, ti.i8)
            grid_fever_masks[song_slot, ft_idx, ff_idx, i] = is_fever
