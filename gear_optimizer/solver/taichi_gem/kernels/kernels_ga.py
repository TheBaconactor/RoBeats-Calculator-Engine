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

# Platform detection for atomic operations
IS_METAL = sys.platform == "darwin"

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
def ga_seed_rng_runs_kernel(n_genomes_total: ti.i32, n_genomes_per_run: ti.i32, seed: ti.u32):
    """
    Initialize per-genome RNG state for multiple independent runs packed contiguously.

    This mirrors ga_seed_rng_kernel, but seeds each run as if its genomes were indexed
    [0..n_genomes_per_run) with the same seed (i.e., run-local indexing).
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    if n_genomes_per_run > 0:
        for g in range(n_genomes_total):
            local_g = g - (g // n_genomes_per_run) * n_genomes_per_run
            s = seed ^ (ti.cast(local_g, ti.u32) * ti.u32(747796405)) ^ ti.u32(2891336453)
            if s == ti.u32(0):
                s = ti.u32(1)
            kernels_helpers.ga_rng_state[g] = s


@ti.kernel
def ga_load_initial_population_kernel(run_idx: ti.i32, n_genomes: ti.i32, n_slots: ti.i32):
    """
    Copy a staged initial population into `population_indices`.

    This enables batching CPU->GPU uploads for multi-start runs:
      1) Upload N initial populations once into `ga_initial_populations`
      2) For each run, copy run_idx into `population_indices` via this kernel
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        for s in range(n_slots):
            kernels_helpers.population_indices[g, s] = kernels_helpers.ga_initial_populations[run_idx, g, s]


@ti.kernel
def ga_load_initial_populations_batch_kernel(
    run_idx_start: ti.i32,
    n_runs: ti.i32,
    n_genomes_per_run: ti.i32,
    n_slots: ti.i32,
):
    """
    Copy a batch of staged initial populations into `population_indices`.

    The output layout is contiguous by run:
      output genome index g in [0, n_runs*n_genomes_per_run)
        run = g // n_genomes_per_run
        local = g % n_genomes_per_run
      population_indices[g] = ga_initial_populations[run_idx_start + run, local]
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    if n_genomes_per_run > 0 and n_runs > 0:
        n_total = n_runs * n_genomes_per_run
        for g in range(n_total):
            run = g // n_genomes_per_run
            local_g = g - run * n_genomes_per_run
            src_run = run_idx_start + run
            for s in range(n_slots):
                kernels_helpers.population_indices[g, s] = kernels_helpers.ga_initial_populations[src_run, local_g, s]


@ti.kernel
def ga_upload_item_stats_and_slots_kernel(
    item_stats_src: ti.types.ndarray(dtype=ti.i32, ndim=2),
    n_items: ti.i32,
    slot_start_src: ti.types.ndarray(dtype=ti.i32, ndim=1),
    slot_count_src: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    """
    Upload per-item stats and slot pool boundaries without padded CPU buffers.

    This avoids uploading a full MAX_ITEMS x ITEM_STAT_DIM table for every song;
    only the first `n_items` rows are copied.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for i, j in ti.ndrange(n_items, ti.static(10)):
        kernels_helpers.item_stats[i, j] = item_stats_src[i, j]

    for s in ti.static(range(9)):
        kernels_helpers.slot_start[s] = slot_start_src[s]
        kernels_helpers.slot_count[s] = slot_count_src[s]


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

    for g in range(n_genomes):
        if ti.static(not IS_METAL):
            kernels_helpers.chunk_best_key[g] = ti.u64(0)
            for t in ti.static(range(kernels_helpers.CHUNK_BEST_KEY_TILES)):
                kernels_helpers.chunk_best_key_tiles[g, t] = ti.u64(0)
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
    immigrant_rate_fp: ti.u32,
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

            # Random immigrants (exploration): occasionally re-roll the entire genome.
            # This keeps diversity even when selection pressure is high.
            if immigrant_rate_fp != ti.u32(0):
                state = kernels_helpers._xorshift32(state)
                if state < immigrant_rate_fp:
                    for s in range(n_slots):
                        pool_start = kernels_helpers.slot_start[s]
                        pool_count = kernels_helpers.slot_count[s]
                        if pool_count > 0:
                            state = kernels_helpers._xorshift32(state)
                            new_item = pool_start + ti.cast(state % ti.cast(pool_count, ti.u32), ti.i32)
                            kernels_helpers.population_next_indices[g, s] = new_item

                    # Repair mini uniqueness again after re-roll
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

                    # Reset hints for immigrants (avoid inheriting misleading warm-starts).
                    for i in range(4):
                        kernels_helpers.genome_hint_allocation[g][i] = 0
                    pa = g

        kernels_helpers.ga_rng_state[g] = state

        # Store parent_a for hint inheritance (used in second pass)
        kernels_helpers.ga_parent_a[g] = pa


@ti.kernel
def ga_next_generation_full_islands_kernel(
    n_genomes: ti.i32,
    n_slots: ti.i32,
    n_islands: ti.i32,
    elites_per_island: ti.i32,
    tournament_k: ti.i32,
    mutation_rate_fp: ti.u32,
    immigrant_rate_fp: ti.u32,
):
    """
    FUSED next generation with on-the-fly island elitism (no ga_find_island_elites kernel required).

    This kernel replaces the sequence:
      ga_find_island_elites() -> ga_next_generation_full_kernel()

    by computing each elite source genome directly inside the elite threads.
    This avoids an extra kernel launch per generation and also skips elite selection
    entirely on the final generation (since next-gen is not run on the final step).

    Notes:
    - We intentionally mirror the tie-breaking behavior of ga_find_island_elites_kernel:
      strict `>` comparisons preserve the first-seen genome for equal scores.
    - `elites_per_island` is clamped to MAX_ELITES_PER_ISLAND for static local arrays.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    MAX_ELITES_PER_ISLAND: ti.i32 = 16

    # Kernel arguments are immutable in Taichi; clamp into local vars.
    n_islands_i: ti.i32 = n_islands
    elites_per_island_i: ti.i32 = elites_per_island
    tournament_k_i: ti.i32 = tournament_k

    # Clamp invalid inputs defensively.
    if n_islands_i < 1:
        n_islands_i = 1
    if elites_per_island_i < 1:
        elites_per_island_i = 1
    if elites_per_island_i > MAX_ELITES_PER_ISLAND:
        elites_per_island_i = MAX_ELITES_PER_ISLAND
    if tournament_k_i < 1:
        tournament_k_i = 1

    n_elites: ti.i32 = n_islands_i * elites_per_island_i
    if n_elites > n_genomes:
        n_elites = n_genomes

    for g in range(n_genomes):
        state = kernels_helpers.ga_rng_state[g]
        pa = 0

        if g < n_elites:
            isl: ti.i32 = g // elites_per_island_i
            elite_rank: ti.i32 = g - (isl * elites_per_island_i)

            # If the mapping goes out of range (possible if n_elites was clamped),
            # fall back to the non-elite path.
            if isl >= n_islands_i:
                elite_rank = -1
            else:
                isl_start: ti.i32 = kernels_helpers.island_boundaries[isl]
                isl_end: ti.i32 = kernels_helpers.island_boundaries[isl + 1]
                isl_size: ti.i32 = isl_end - isl_start

                k: ti.i32 = elites_per_island_i
                if k > isl_size:
                    k = isl_size
                if k < 1:
                    elite_rank = -1
                elif elite_rank >= k:
                    elite_rank = -1

                if elite_rank >= 0:
                    top_scores = ti.Vector([-1] * 16)
                    top_indices = ti.Vector([-1] * 16)

                    for local_idx in range(isl_size):
                        idx = isl_start + local_idx
                        score: ti.i32 = kernels_helpers.ga_scores[idx]

                        if score > top_scores[k - 1]:
                            insert_pos: ti.i32 = k - 1
                            found_better: ti.i32 = 0
                            for j in ti.static(range(16)):
                                if found_better == 0 and j < k and score > top_scores[j]:
                                    insert_pos = j
                                    found_better = 1

                            for j in ti.static(range(15, 0, -1)):
                                if j > insert_pos and j < k:
                                    top_scores[j] = top_scores[j - 1]
                                    top_indices[j] = top_indices[j - 1]

                            top_scores[insert_pos] = score
                            top_indices[insert_pos] = idx

                    src_genome: ti.i32 = top_indices[elite_rank]
                    if src_genome < 0:
                        src_genome = isl_start

                    for s in range(n_slots):
                        kernels_helpers.population_next_indices[g, s] = kernels_helpers.population_indices[
                            src_genome, s
                        ]
                    pa = src_genome
                else:
                    elite_rank = -1

            # If elite selection was not possible, fall through to non-elite logic.
            if elite_rank >= 0:
                kernels_helpers.ga_rng_state[g] = state
                kernels_helpers.ga_parent_a[g] = pa
                continue

        # Non-elite path: tournament selection + crossover + mutation + optional immigrants.
        best_a = 0
        best_a_score = ti.cast(-2147483648, ti.i32)
        for _ in range(tournament_k_i):
            state = kernels_helpers._xorshift32(state)
            idx = ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
            sc = kernels_helpers.ga_scores[idx]
            if sc > best_a_score:
                best_a_score = sc
                best_a = idx

        best_b = 0
        best_b_score = ti.cast(-2147483648, ti.i32)
        for _ in range(tournament_k_i):
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

        if immigrant_rate_fp != ti.u32(0):
            state = kernels_helpers._xorshift32(state)
            if state < immigrant_rate_fp:
                for s in range(n_slots):
                    pool_start = kernels_helpers.slot_start[s]
                    pool_count = kernels_helpers.slot_count[s]
                    if pool_count > 0:
                        state = kernels_helpers._xorshift32(state)
                        new_item = pool_start + ti.cast(state % ti.cast(pool_count, ti.u32), ti.i32)
                        kernels_helpers.population_next_indices[g, s] = new_item

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

                for i in range(4):
                    kernels_helpers.genome_hint_allocation[g][i] = 0
                pa = g

        kernels_helpers.ga_rng_state[g] = state
        kernels_helpers.ga_parent_a[g] = pa


@ti.kernel
def ga_next_generation_full_runs_kernel(
    n_runs: ti.i32,
    n_genomes_per_run: ti.i32,
    n_slots: ti.i32,
    n_islands: ti.i32,
    elites_per_island: ti.i32,
    tournament_k: ti.i32,
    mutation_rate_fp: ti.u32,
    immigrant_rate_fp: ti.u32,
):
    """
    FUSED next generation for multiple independent runs packed contiguously.

    This kernel preserves the per-run "multi-start" semantics by ensuring:
    - Tournament selection samples only within the run segment
    - Island elitism is computed per-run and elites are written within each run segment
    - No cross-run migration / mixing occurs
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    MAX_ELITES_PER_ISLAND: ti.i32 = 16

    n_runs_i: ti.i32 = n_runs
    n_genomes_per_run_i: ti.i32 = n_genomes_per_run
    n_islands_i: ti.i32 = n_islands
    elites_per_island_i: ti.i32 = elites_per_island
    tournament_k_i: ti.i32 = tournament_k

    if n_runs_i < 1:
        n_runs_i = 1
    if n_genomes_per_run_i < 1:
        n_genomes_per_run_i = 1
    if n_islands_i < 1:
        n_islands_i = 1
    if n_islands_i > n_genomes_per_run_i:
        n_islands_i = n_genomes_per_run_i
    if elites_per_island_i < 1:
        elites_per_island_i = 1
    if elites_per_island_i > MAX_ELITES_PER_ISLAND:
        elites_per_island_i = MAX_ELITES_PER_ISLAND
    if tournament_k_i < 1:
        tournament_k_i = 1

    island_size: ti.i32 = n_genomes_per_run_i // n_islands_i
    if island_size < 1:
        island_size = 1

    n_elites_per_run: ti.i32 = n_islands_i * elites_per_island_i
    if n_elites_per_run > n_genomes_per_run_i:
        n_elites_per_run = n_genomes_per_run_i

    n_total: ti.i32 = n_runs_i * n_genomes_per_run_i

    for g in range(n_total):
        run: ti.i32 = g // n_genomes_per_run_i
        local_g: ti.i32 = g - run * n_genomes_per_run_i
        run_start: ti.i32 = run * n_genomes_per_run_i

        state = kernels_helpers.ga_rng_state[g]
        pa = run_start  # Parent A (global index)

        # --- Elitism (per-run, per-island) ---
        if local_g < n_elites_per_run:
            isl: ti.i32 = local_g // elites_per_island_i
            elite_rank: ti.i32 = local_g - (isl * elites_per_island_i)

            if isl < n_islands_i:
                isl_start_local: ti.i32 = isl * island_size
                isl_end_local: ti.i32 = (isl + 1) * island_size
                if isl == n_islands_i - 1:
                    isl_end_local = n_genomes_per_run_i

                isl_start: ti.i32 = run_start + isl_start_local
                isl_end: ti.i32 = run_start + isl_end_local
                isl_size: ti.i32 = isl_end - isl_start

                k: ti.i32 = elites_per_island_i
                if k > isl_size:
                    k = isl_size

                if k > 0 and elite_rank < k:
                    top_scores = ti.Vector([-1] * 16)
                    top_indices = ti.Vector([-1] * 16)

                    for local_idx in range(isl_size):
                        idx = isl_start + local_idx
                        score: ti.i32 = kernels_helpers.ga_scores[idx]

                        if score > top_scores[k - 1]:
                            insert_pos: ti.i32 = k - 1
                            found_better: ti.i32 = 0
                            for j in ti.static(range(16)):
                                if found_better == 0 and j < k and score > top_scores[j]:
                                    insert_pos = j
                                    found_better = 1

                            for j in ti.static(range(15, 0, -1)):
                                if j > insert_pos and j < k:
                                    top_scores[j] = top_scores[j - 1]
                                    top_indices[j] = top_indices[j - 1]

                            top_scores[insert_pos] = score
                            top_indices[insert_pos] = idx

                    src_genome: ti.i32 = top_indices[elite_rank]
                    if src_genome < 0:
                        src_genome = isl_start

                    for s in range(n_slots):
                        kernels_helpers.population_next_indices[g, s] = kernels_helpers.population_indices[
                            src_genome, s
                        ]
                    pa = src_genome

                    kernels_helpers.ga_rng_state[g] = state
                    kernels_helpers.ga_parent_a[g] = pa
                    continue

        # --- Non-elite path: tournament selection within run + crossover + mutation ---
        best_a = run_start
        best_a_score = ti.cast(-2147483648, ti.i32)
        for _ in range(tournament_k_i):
            state = kernels_helpers._xorshift32(state)
            idx_local = ti.cast(state % ti.cast(n_genomes_per_run_i, ti.u32), ti.i32)
            idx = run_start + idx_local
            sc = kernels_helpers.ga_scores[idx]
            if sc > best_a_score:
                best_a_score = sc
                best_a = idx

        best_b = run_start
        best_b_score = ti.cast(-2147483648, ti.i32)
        for _ in range(tournament_k_i):
            state = kernels_helpers._xorshift32(state)
            idx_local = ti.cast(state % ti.cast(n_genomes_per_run_i, ti.u32), ti.i32)
            idx = run_start + idx_local
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

        if immigrant_rate_fp != ti.u32(0):
            state = kernels_helpers._xorshift32(state)
            if state < immigrant_rate_fp:
                for s in range(n_slots):
                    pool_start = kernels_helpers.slot_start[s]
                    pool_count = kernels_helpers.slot_count[s]
                    if pool_count > 0:
                        state = kernels_helpers._xorshift32(state)
                        new_item = pool_start + ti.cast(state % ti.cast(pool_count, ti.u32), ti.i32)
                        kernels_helpers.population_next_indices[g, s] = new_item

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

                for i in range(4):
                    kernels_helpers.genome_hint_allocation[g][i] = 0
                pa = g

        kernels_helpers.ga_rng_state[g] = state
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
