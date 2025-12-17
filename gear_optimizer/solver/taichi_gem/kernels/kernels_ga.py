"""
Taichi Kernels - GPU-Native Genetic Algorithm Operations.

This module contains 8 kernels implementing genetic algorithm operators:
- ga_seed_rng_kernel: Initialize per-genome RNG state
- ga_select_parents_tournament_kernel: Tournament selection
- ga_crossover_mutate_kernel: Crossover + mutation + mini uniqueness
- ga_swap_populations_kernel: Copy next generation to current
- ga_copy_elites_kernel: Preserve elite solutions
- ga_aggregate_genome_stats_kernel: Aggregate item stats into genome stats
- ga_copy_scores_kernel: Bridge evaluation to selection

These kernels enable fully GPU-native GA execution, avoiding CPU-GPU transfers
during population evolution.
"""
import sys
import taichi as ti

from . import kernels_helpers


@ti.kernel
def ga_seed_rng_kernel(n_genomes: ti.i32, seed: ti.u32):
    """
    Initialize per-genome RNG state deterministically.

    Args:
        n_genomes: Number of genomes in population
        seed: Base seed value for RNG
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        # Mix seed with genome index (avoid all-zero states).
        s = seed ^ (ti.cast(g, ti.u32) * ti.u32(747796405)) ^ ti.u32(2891336453)
        if s == ti.u32(0):
            s = ti.u32(1)
        kernels_helpers.ga_rng_state[g] = s


@ti.kernel
def ga_select_parents_tournament_kernel(n_genomes: ti.i32, tournament_k: ti.i32):
    """
    Tournament selection on GPU.

    Each genome selects two parents via tournament selection:
    - Sample k random genomes
    - Pick the one with highest score
    - Repeat for second parent

    Produces two parent indices per output genome (ga_parent_a/b).

    Args:
        n_genomes: Number of genomes in population
        tournament_k: Tournament size (typically 3-5)
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        state = kernels_helpers.ga_rng_state[g]

        # Pick parent A
        best_a = 0
        best_a_score = ti.cast(-2147483648, ti.i32)
        for _ in range(tournament_k):
            state = kernels_helpers._xorshift32(state)
            idx = ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
            sc = kernels_helpers.ga_scores[idx]
            if sc > best_a_score:
                best_a_score = sc
                best_a = idx

        # Pick parent B
        best_b = 0
        best_b_score = ti.cast(-2147483648, ti.i32)
        for _ in range(tournament_k):
            state = kernels_helpers._xorshift32(state)
            idx = ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
            sc = kernels_helpers.ga_scores[idx]
            if sc > best_b_score:
                best_b_score = sc
                best_b = idx

        pa = best_a
        pb = best_b

        kernels_helpers.ga_parent_a[g] = pa
        kernels_helpers.ga_parent_b[g] = pb
        kernels_helpers.ga_rng_state[g] = state


@ti.kernel
def ga_crossover_mutate_kernel(
    n_genomes: ti.i32,
    n_slots: ti.i32,
    mutation_rate_fp: ti.u32,  # [0..2^32-1]
):
    """
    Create next generation in population_next_indices (race-free, deterministic).

    Applies:
    1. Uniform crossover from two parents (provided via ga_parent_a/ga_parent_b)
    2. Mutation: with probability mutation_rate, replace one random slot
       with a random item from that slot's valid pool
    3. Mini uniqueness repair: ensures slots 6-8 have no duplicate item IDs

    Note: Elites are handled separately via ga_copy_elites_kernel (call after this).

    Args:
        n_genomes: Number of genomes in population
        n_slots: Number of equipment slots (typically 9)
        mutation_rate_fp: Mutation probability in fixed-point [0..2^32-1]
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    for g in range(n_genomes):
        state = kernels_helpers.ga_rng_state[g]
        pa = kernels_helpers.ga_parent_a[g]
        pb = kernels_helpers.ga_parent_b[g]

        # Uniform crossover per slot
        for s in range(n_slots):
            state = kernels_helpers._xorshift32(state)
            take_a = (state & ti.u32(1)) != 0
            if take_a:
                kernels_helpers.population_next_indices[g, s] = kernels_helpers.population_indices[pa, s]
            else:
                kernels_helpers.population_next_indices[g, s] = kernels_helpers.population_indices[pb, s]

        # Mutation: with given probability, mutate 1 slot by sampling from slot's pool
        state = kernels_helpers._xorshift32(state)
        if state < mutation_rate_fp:
            state = kernels_helpers._xorshift32(state)
            mut_slot = ti.cast(state % ti.cast(n_slots, ti.u32), ti.i32)

            # Sample new item from this slot's valid pool
            pool_start = kernels_helpers.slot_start[mut_slot]
            pool_count = kernels_helpers.slot_count[mut_slot]
            if pool_count > 0:
                state = kernels_helpers._xorshift32(state)
                new_item = pool_start + ti.cast(state % ti.cast(pool_count, ti.u32), ti.i32)
                kernels_helpers.population_next_indices[g, mut_slot] = new_item

        # Mini uniqueness repair: ensure slots 6, 7, 8 have no duplicates
        # (Minis share the same pool, so duplicates are possible after crossover)
        m0 = kernels_helpers.population_next_indices[g, 6]
        m1 = kernels_helpers.population_next_indices[g, 7]
        m2 = kernels_helpers.population_next_indices[g, 8]

        mini_pool_start = kernels_helpers.slot_start[6]
        mini_pool_count = kernels_helpers.slot_count[6]

        if mini_pool_count > 1:
            # Repair m1 if duplicate of m0
            tries = 0
            while m1 == m0 and tries < 10:
                state = kernels_helpers._xorshift32(state)
                m1 = mini_pool_start + ti.cast(state % ti.cast(mini_pool_count, ti.u32), ti.i32)
                tries += 1

            # Repair m2 if duplicate of m0 or m1
            tries = 0
            while (m2 == m0 or m2 == m1) and tries < 10:
                state = kernels_helpers._xorshift32(state)
                m2 = mini_pool_start + ti.cast(state % ti.cast(mini_pool_count, ti.u32), ti.i32)
                tries += 1

            kernels_helpers.population_next_indices[g, 6] = m0
            kernels_helpers.population_next_indices[g, 7] = m1
            kernels_helpers.population_next_indices[g, 8] = m2

        kernels_helpers.ga_rng_state[g] = state


@ti.kernel
def ga_swap_populations_kernel(n_genomes: ti.i32, n_slots: ti.i32):
    """
    Copy population_next_indices -> population_indices in-place.

    This advances the GA to the next generation.

    Args:
        n_genomes: Number of genomes in population
        n_slots: Number of equipment slots
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g, s in ti.ndrange(n_genomes, n_slots):
        kernels_helpers.population_indices[g, s] = kernels_helpers.population_next_indices[g, s]


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

    This preserves the best solutions across generations (elitism).
    Call AFTER crossover/mutation but BEFORE swap.

    Args:
        n_elites: Number of elite solutions to preserve
        n_slots: Number of equipment slots
        elite_src_indices: Source genome indices (sorted by descending score)
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for i, s in ti.ndrange(n_elites, n_slots):
        src_genome = elite_src_indices[i]
        kernels_helpers.population_next_indices[i, s] = kernels_helpers.population_indices[src_genome, s]


@ti.kernel
def ga_copy_island_elites_kernel(
    n_elites: ti.i32,
    n_slots: ti.i32,
):
    """
    Copy elite genomes to the beginning of population_next_indices (GPU-resident version).

    Reads elite indices from the GPU-resident island_elite_indices field (set by
    ga_find_island_elites_kernel) instead of a CPU ndarray. This avoids the
    expensive GPU->CPU transfer per generation.

    Elite genomes are copied from population_indices[island_elite_indices[i]]
    to population_next_indices[i] for i in [0, n_elites).

    This preserves the best solutions across generations (elitism).
    Call AFTER crossover/mutation but BEFORE swap.

    Args:
        n_elites: Number of elite solutions to preserve (n_islands * elites_per_island)
        n_slots: Number of equipment slots
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for i, s in ti.ndrange(n_elites, n_slots):
        src_genome = kernels_helpers.island_elite_indices[i]
        kernels_helpers.population_next_indices[i, s] = kernels_helpers.population_indices[src_genome, s]


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

    Then compute p_val/s_val contributions from color flags:
      p_val is the elemental value for the song's primary color:
        Beat<-FT, Vibe<-FF, Rush<-FM, Flow<-CM, Chill<-PP
      s_val is the elemental value for the song's secondary color

    Writes to genome_base_stats[g] = [pp, cm, fm, p_val, s_val, ft, ff]

    item_stats layout: [PP, CM, FM, FT, FF, Beat, Vibe, Rush, Flow, Chill]
                        0   1   2   3   4   5     6     7     8     9

    Args:
        n_genomes: Number of genomes
        n_slots: Number of equipment slots
        is_*: Color contribution flags (0/1) for primary/secondary
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    for g in range(n_genomes):
        # Initialize with base fixed stats
        pp = kernels_helpers.base_fixed_stats[0]
        cm = kernels_helpers.base_fixed_stats[1]
        fm = kernels_helpers.base_fixed_stats[2]
        ft = kernels_helpers.base_fixed_stats[3]
        ff = kernels_helpers.base_fixed_stats[4]
        # Colors (Beat, Vibe, Rush, Flow, Chill) at indices 5-9
        beat = kernels_helpers.base_fixed_stats[5]
        vibe = kernels_helpers.base_fixed_stats[6]
        rush = kernels_helpers.base_fixed_stats[7]
        flow = kernels_helpers.base_fixed_stats[8]
        chill = kernels_helpers.base_fixed_stats[9]

        # Sum stats from all items in this genome
        for s in range(n_slots):
            item_id = kernels_helpers.population_indices[g, s]
            if item_id > 0:  # ID 0 is empty/invalid
                pp += kernels_helpers.item_stats[item_id, 0]
                cm += kernels_helpers.item_stats[item_id, 1]
                fm += kernels_helpers.item_stats[item_id, 2]
                ft += kernels_helpers.item_stats[item_id, 3]
                ff += kernels_helpers.item_stats[item_id, 4]
                beat += kernels_helpers.item_stats[item_id, 5]
                vibe += kernels_helpers.item_stats[item_id, 6]
                rush += kernels_helpers.item_stats[item_id, 7]
                flow += kernels_helpers.item_stats[item_id, 8]
                chill += kernels_helpers.item_stats[item_id, 9]

        # Compute p_val (primary color contribution)
        # p_val is the *elemental* value for the song's primary color:
        #   Beat<-FT, Vibe<-FF, Rush<-FM, Flow<-CM, Chill<-PP
        # (Overflow gems are handled later by optimize_core_device via is_p_ov/is_s_ov.)
        p_val = (beat * is_p_ft) + (vibe * is_p_ff) + (rush * is_p_fm) + (flow * is_p_cm) + (chill * is_p_pp)

        # Compute s_val (secondary color contribution)
        s_val = (beat * is_s_ft) + (vibe * is_s_ff) + (rush * is_s_fm) + (flow * is_s_cm) + (chill * is_s_pp)

        # Write to genome_base_stats: [pp, cm, fm, p_val, s_val, ft, ff]
        kernels_helpers.genome_base_stats[g][0] = ti.cast(pp, ti.i16)
        kernels_helpers.genome_base_stats[g][1] = ti.cast(cm, ti.i16)
        kernels_helpers.genome_base_stats[g][2] = ti.cast(fm, ti.i16)
        kernels_helpers.genome_base_stats[g][3] = ti.cast(p_val, ti.i16)
        kernels_helpers.genome_base_stats[g][4] = ti.cast(s_val, ti.i16)
        kernels_helpers.genome_base_stats[g][5] = ti.cast(ft, ti.i16)
        kernels_helpers.genome_base_stats[g][6] = ti.cast(ff, ti.i16)


@ti.kernel
def ga_aggregate_and_init_best_kernel(
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
    FUSED: Aggregate item stats AND initialize chunk_best_key in one kernel.

    Combines ga_aggregate_genome_stats_kernel + init_chunk_best_key_kernel
    to reduce kernel launch overhead.

    Args:
        n_genomes: Number of genomes
        n_slots: Number of equipment slots
        is_*: Color contribution flags (0/1) for primary/secondary
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    # Platform detection for atomic operations
    # Metal (macOS) doesn't support u64 atomics, so we use separate 32-bit fields
    IS_METAL = (sys.platform == "darwin")

    for g in range(n_genomes):
        if ti.static(not IS_METAL):
            kernels_helpers.chunk_best_key[g] = ti.u64(0)
        else:
            kernels_helpers.chunk_best_score[g] = ti.cast(-2147483648, ti.i32)
            kernels_helpers.chunk_best_idx[g] = -1

        pp = kernels_helpers.base_fixed_stats[0]
        cm = kernels_helpers.base_fixed_stats[1]
        fm = kernels_helpers.base_fixed_stats[2]
        ft = kernels_helpers.base_fixed_stats[3]
        ff = kernels_helpers.base_fixed_stats[4]
        beat = kernels_helpers.base_fixed_stats[5]
        vibe = kernels_helpers.base_fixed_stats[6]
        rush = kernels_helpers.base_fixed_stats[7]
        flow = kernels_helpers.base_fixed_stats[8]
        chill = kernels_helpers.base_fixed_stats[9]

        for s in range(n_slots):
            item_id = kernels_helpers.population_indices[g, s]
            if item_id > 0:
                pp += kernels_helpers.item_stats[item_id, 0]
                cm += kernels_helpers.item_stats[item_id, 1]
                fm += kernels_helpers.item_stats[item_id, 2]
                ft += kernels_helpers.item_stats[item_id, 3]
                ff += kernels_helpers.item_stats[item_id, 4]
                beat += kernels_helpers.item_stats[item_id, 5]
                vibe += kernels_helpers.item_stats[item_id, 6]
                rush += kernels_helpers.item_stats[item_id, 7]
                flow += kernels_helpers.item_stats[item_id, 8]
                chill += kernels_helpers.item_stats[item_id, 9]

        p_val = (beat * is_p_ft) + (vibe * is_p_ff) + (rush * is_p_fm) + (flow * is_p_cm) + (chill * is_p_pp)
        s_val = (beat * is_s_ft) + (vibe * is_s_ff) + (rush * is_s_fm) + (flow * is_s_cm) + (chill * is_s_pp)

        kernels_helpers.genome_base_stats[g][0] = ti.cast(pp, ti.i16)
        kernels_helpers.genome_base_stats[g][1] = ti.cast(cm, ti.i16)
        kernels_helpers.genome_base_stats[g][2] = ti.cast(fm, ti.i16)
        kernels_helpers.genome_base_stats[g][3] = ti.cast(p_val, ti.i16)
        kernels_helpers.genome_base_stats[g][4] = ti.cast(s_val, ti.i16)
        kernels_helpers.genome_base_stats[g][5] = ti.cast(ft, ti.i16)
        kernels_helpers.genome_base_stats[g][6] = ti.cast(ff, ti.i16)


@ti.kernel
def ga_copy_scores_kernel(n_genomes: ti.i32):
    """
    Copy scores from genome_result_stats to ga_scores for selection.

    This bridges the evaluation kernel output to the GA selection input.
    ga_scores[g] = genome_result_stats[g][0] (the score component)

    Args:
        n_genomes: Number of genomes
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        kernels_helpers.ga_scores[g] = kernels_helpers.genome_result_stats[g][0]


@ti.kernel
def ga_select_crossover_mutate_kernel(
    n_genomes: ti.i32,
    n_slots: ti.i32,
    tournament_k: ti.i32,
    mutation_rate_fp: ti.u32,
):
    """
    FUSED: Tournament selection + crossover + mutation in one kernel.

    Combines ga_select_parents_tournament_kernel + ga_crossover_mutate_kernel
    to reduce kernel launch overhead.

    For each genome:
    1. Tournament selection to pick two parents
    2. Uniform crossover from parents
    3. Mutation with given probability
    4. Mini uniqueness repair for slots 6-8

    Note: Elites are handled separately via ga_copy_elites_kernel (call after this).

    Args:
        n_genomes: Number of genomes in population
        n_slots: Number of equipment slots (typically 9)
        tournament_k: Tournament size for selection
        mutation_rate_fp: Mutation probability in fixed-point [0..2^32-1]
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    for g in range(n_genomes):
        state = kernels_helpers.ga_rng_state[g]

        best_a = 0
        best_a_score = ti.cast(-2147483648, ti.i32)
        for _ in range(tournament_k):
            state = kernels_helpers._xorshift32(state)
            idx = ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
            sc = kernels_helpers.ga_scores[idx]
            if sc > best_a_score:
                best_a_score = sc
                best_a = idx

        # Pick parent B
        best_b = 0
        best_b_score = ti.cast(-2147483648, ti.i32)
        for _ in range(tournament_k):
            state = kernels_helpers._xorshift32(state)
            idx = ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
            sc = kernels_helpers.ga_scores[idx]
            if sc > best_b_score:
                best_b_score = sc
                best_b = idx

        pa = best_a
        pb = best_b

        for s in range(n_slots):
            state = kernels_helpers._xorshift32(state)
            take_a = (state & ti.u32(1)) != 0
            if take_a:
                kernels_helpers.population_next_indices[g, s] = kernels_helpers.population_indices[pa, s]
            else:
                kernels_helpers.population_next_indices[g, s] = kernels_helpers.population_indices[pb, s]

        state = kernels_helpers._xorshift32(state)
        if state < mutation_rate_fp:
            state = kernels_helpers._xorshift32(state)
            mut_slot = ti.cast(state % ti.cast(n_slots, ti.u32), ti.i32)

            pool_start = kernels_helpers.slot_start[mut_slot]
            pool_count = kernels_helpers.slot_count[mut_slot]
            if pool_count > 0:
                state = kernels_helpers._xorshift32(state)
                new_item = pool_start + ti.cast(state % ti.cast(pool_count, ti.u32), ti.i32)
                kernels_helpers.population_next_indices[g, mut_slot] = new_item

        m0 = kernels_helpers.population_next_indices[g, 6]
        m1 = kernels_helpers.population_next_indices[g, 7]
        m2 = kernels_helpers.population_next_indices[g, 8]

        mini_pool_start = kernels_helpers.slot_start[6]
        mini_pool_count = kernels_helpers.slot_count[6]

        if mini_pool_count > 1:
            tries = 0
            while m1 == m0 and tries < 10:
                state = kernels_helpers._xorshift32(state)
                m1 = mini_pool_start + ti.cast(state % ti.cast(mini_pool_count, ti.u32), ti.i32)
                tries += 1

            tries = 0
            while (m2 == m0 or m2 == m1) and tries < 10:
                state = kernels_helpers._xorshift32(state)
                m2 = mini_pool_start + ti.cast(state % ti.cast(mini_pool_count, ti.u32), ti.i32)
                tries += 1

            kernels_helpers.population_next_indices[g, 6] = m0
            kernels_helpers.population_next_indices[g, 7] = m1
            kernels_helpers.population_next_indices[g, 8] = m2

        kernels_helpers.ga_rng_state[g] = state


@ti.kernel
def ga_store_hints_kernel(n_genomes: ti.i32):
    """
    Store current best gem allocation as hints for next generation.
    
    Reads from genome_result_stats[g] = [score, ft, ff, pp, cm, fm, ov]
    Writes to genome_hint_allocation[g] = [pp, cm, fm, ov]
    
    Call this AFTER evaluation, BEFORE crossover/mutation.
    The hints will be used to warm-start the solver in the next generation.
    
    Args:
        n_genomes: Number of genomes
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        result = kernels_helpers.genome_result_stats[g]
        # genome_result_stats layout: [score, ft, ff, pp, cm, fm, ov]
        # genome_hint_allocation layout: [pp, cm, fm, ov]
        kernels_helpers.genome_hint_allocation[g][0] = result[3]  # pp gems
        kernels_helpers.genome_hint_allocation[g][1] = result[4]  # cm gems
        kernels_helpers.genome_hint_allocation[g][2] = result[5]  # fm gems
        kernels_helpers.genome_hint_allocation[g][3] = result[6]  # ov gems


@ti.kernel
def ga_inherit_hints_kernel(n_genomes: ti.i32):
    """
    Inherit hints from parents to children after crossover.
    
    Each child inherits the hint from parent A (the first parent).
    This provides a warm-start point for the next evaluation.
    
    Call this AFTER crossover/mutation, BEFORE evaluation.
    
    The hint_next buffer is used to store inherited hints, then swapped.
    For simplicity, we just copy from parent A's hint to child's hint.
    
    Args:
        n_genomes: Number of genomes
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        parent_a = kernels_helpers.ga_parent_a[g]
        # Copy parent A's hint to child
        for i in range(4):
            kernels_helpers.genome_hint_allocation[g][i] = kernels_helpers.genome_hint_allocation[parent_a][i]


@ti.kernel
def ga_next_generation_full_kernel(
    n_genomes: ti.i32,
    n_slots: ti.i32,
    n_elites: ti.i32,
    tournament_k: ti.i32,
    mutation_rate_fp: ti.u32,
):
    """
    FULLY FUSED: Selection + Crossover + Mutation + Elitism + Swap + Hint Inheritance.
    
    This kernel combines 4 separate kernels into 1 to reduce launch overhead:
    1. Tournament selection (picks pa, pb)
    2. Crossover + mutation (writes to population_next_indices)
    3. Elite copy (from GPU-resident island_elite_indices)
    4. Swap (next -> current) + hint inheritance
    
    The kernel operates in two phases:
    - Phase 1 (g >= n_elites): Tournament + crossover + mutation for non-elite slots
    - Phase 2 (g < n_elites): Copy elites directly
    - Phase 3: Swap and inherit hints (done in same iteration)
    
    Args:
        n_genomes: Population size
        n_slots: Slots per genome (typically 9)
        n_elites: Number of elites to preserve (reads from island_elite_indices)
        tournament_k: Tournament size for selection
        mutation_rate_fp: Mutation probability in fixed-point [0..2^32-1]
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    for g in range(n_genomes):
        state = kernels_helpers.ga_rng_state[g]
        pa = 0  # Initialize pa (used for hint inheritance)
        
        # For elites (g < n_elites): copy from original population
        # For non-elites (g >= n_elites): do tournament + crossover + mutation
        if g < n_elites:
            # Elite path: copy from island_elite_indices[g]
            src_genome = kernels_helpers.island_elite_indices[g]
            for s in range(n_slots):
                kernels_helpers.population_next_indices[g, s] = kernels_helpers.population_indices[src_genome, s]
            # Inherit hint from source elite
            pa = src_genome  # For hint inheritance
        else:
            # Non-elite path: tournament selection + crossover + mutation
            # Pick parent A
            best_a = 0
            best_a_score = ti.cast(-2147483648, ti.i32)
            for _ in range(tournament_k):
                state = kernels_helpers._xorshift32(state)
                idx = ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
                sc = kernels_helpers.ga_scores[idx]
                if sc > best_a_score:
                    best_a_score = sc
                    best_a = idx

            # Pick parent B
            best_b = 0
            best_b_score = ti.cast(-2147483648, ti.i32)
            for _ in range(tournament_k):
                state = kernels_helpers._xorshift32(state)
                idx = ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
                sc = kernels_helpers.ga_scores[idx]
                if sc > best_b_score:
                    best_b_score = sc
                    best_b = idx

            pa = best_a
            pb = best_b

            # Crossover per slot
            for s in range(n_slots):
                state = kernels_helpers._xorshift32(state)
                take_a = (state & ti.u32(1)) != 0
                if take_a:
                    kernels_helpers.population_next_indices[g, s] = kernels_helpers.population_indices[pa, s]
                else:
                    kernels_helpers.population_next_indices[g, s] = kernels_helpers.population_indices[pb, s]

            # Mutation
            state = kernels_helpers._xorshift32(state)
            if state < mutation_rate_fp:
                state = kernels_helpers._xorshift32(state)
                mut_slot = ti.cast(state % ti.cast(n_slots, ti.u32), ti.i32)

                pool_start = kernels_helpers.slot_start[mut_slot]
                pool_count = kernels_helpers.slot_count[mut_slot]
                if pool_count > 0:
                    state = kernels_helpers._xorshift32(state)
                    new_item = pool_start + ti.cast(state % ti.cast(pool_count, ti.u32), ti.i32)
                    kernels_helpers.population_next_indices[g, mut_slot] = new_item

            # Mini uniqueness repair
            m0 = kernels_helpers.population_next_indices[g, 6]
            m1 = kernels_helpers.population_next_indices[g, 7]
            m2 = kernels_helpers.population_next_indices[g, 8]

            mini_pool_start = kernels_helpers.slot_start[6]
            mini_pool_count = kernels_helpers.slot_count[6]

            if mini_pool_count > 1:
                tries = 0
                while m1 == m0 and tries < 10:
                    state = kernels_helpers._xorshift32(state)
                    m1 = mini_pool_start + ti.cast(state % ti.cast(mini_pool_count, ti.u32), ti.i32)
                    tries += 1

                tries = 0
                while (m2 == m0 or m2 == m1) and tries < 10:
                    state = kernels_helpers._xorshift32(state)
                    m2 = mini_pool_start + ti.cast(state % ti.cast(mini_pool_count, ti.u32), ti.i32)
                    tries += 1

                kernels_helpers.population_next_indices[g, 6] = m0
                kernels_helpers.population_next_indices[g, 7] = m1
                kernels_helpers.population_next_indices[g, 8] = m2

        kernels_helpers.ga_rng_state[g] = state
        
        # Store parent_a for hint inheritance (used in second pass)
        kernels_helpers.ga_parent_a[g] = pa


@ti.kernel
def ga_swap_and_inherit_hints_kernel(n_genomes: ti.i32, n_slots: ti.i32):
    """
    FUSED: Swap populations AND inherit hints in one kernel.
    
    This is Phase 2 of the fused next-generation operation:
    1. Copy population_next_indices -> population_indices (swap)
    2. Inherit hints from parent A (stored in ga_parent_a) to child
    
    Args:
        n_genomes: Population size
        n_slots: Slots per genome
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        # Swap
        for s in range(n_slots):
            kernels_helpers.population_indices[g, s] = kernels_helpers.population_next_indices[g, s]
        
        # Inherit hints from parent A
        parent_a = kernels_helpers.ga_parent_a[g]
        for i in range(4):
            kernels_helpers.genome_hint_allocation[g][i] = kernels_helpers.genome_hint_allocation[parent_a][i]
