"""
Taichi Kernels - GPU-Native Skyline candidate Operations.

This module contains the kernels that stage and aggregate Skyline candidate populations:
- skyline_load_initial_population_kernel / skyline_generate_initial_populations_kernel: Stage populations
- skyline_upload_item_stats_and_slots_kernel: Upload item stats and slot pools
- skyline_copy_population_indices_from_ndarray_kernel: Upload an encoded population
- skyline_aggregate_genome_stats_kernel: Aggregate item stats into genome stats
- skyline_aggregate_and_init_best_kernel: Aggregate stats and initialize each genome's best key
"""

import taichi as ti

from .. import fields as gpu_fields

from . import kernels_helpers


@ti.func
def _repair_mini_uniqueness(
    m0: ti.i32,
    m1: ti.i32,
    m2: ti.i32,
    mini_pool_start: ti.i32,
    mini_pool_count: ti.i32,
    state: ti.u32,
):
    if mini_pool_count > 1:
        for _ in range(10):
            if m1 == m0:
                state = kernels_helpers._xorshift32(state)
                m1 = mini_pool_start + ti.cast(state % ti.cast(mini_pool_count, ti.u32), ti.i32)

        for _ in range(10):
            if m2 == m0 or m2 == m1:
                state = kernels_helpers._xorshift32(state)
                m2 = mini_pool_start + ti.cast(state % ti.cast(mini_pool_count, ti.u32), ti.i32)
    # Minis are order-invariant for scoring. Canonicalize the team order so
    # permutation-only genomes do not consume skyline budget or create fake variance.
    if m0 > m1:
        tmp = m0
        m0 = m1
        m1 = tmp
    if m1 > m2:
        tmp = m1
        m1 = m2
        m2 = tmp
    if m0 > m1:
        tmp = m0
        m0 = m1
        m1 = tmp
    return m0, m1, m2, state


@ti.kernel
def skyline_load_initial_population_kernel(run_idx: ti.i32, n_genomes: ti.i32, n_slots: ti.i32):
    """
    Copy a staged initial population into `population_indices`.

    This enables batching CPU->GPU uploads for multi-start runs:
      1) Upload N initial populations once into `skyline_initial_populations`
      2) For each run, copy run_idx into `population_indices` via this kernel
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        for s in range(n_slots):
            kernels_helpers.population_indices[g, s] = kernels_helpers.skyline_initial_populations[run_idx, g, s]


@ti.kernel
def skyline_generate_initial_populations_kernel(
    run_idx_start: ti.i32,
    n_runs: ti.i32,
    n_genomes: ti.i32,
    n_slots: ti.i32,
    seed: ti.u32,
    heuristic_prob_fp: ti.u32,  # [0..2^32-1]
    heuristic_k: ti.i32,
    seed_prob_fp: ti.u32,  # [0..2^32-1]
    seed_copies: ti.i32,
    seed_mutations: ti.i32,
    heuristic_copies: ti.i32,
    seed_ids: ti.types.ndarray(dtype=ti.i32, ndim=1),  # (n_slots,)
):
    """
    Generate initial populations directly on GPU into `skyline_initial_populations`.

    This eliminates the CPU-side build+encode+upload loop for multi-start runs.

    Notes:
    - Slot pools (slot_start/slot_count) must already be uploaded (via skyline_upload_item_stats).
    - If heuristic_k <= 0, heuristic sampling is disabled.
    - If seed_ids is empty/invalid, seed injection becomes a no-op.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    # Clamp into locals (Taichi args are immutable in kernels).
    start = run_idx_start
    nr = n_runs
    ng = n_genomes
    ns = n_slots
    hk = heuristic_k
    sc = seed_copies

    if nr > 0 and ng > 0 and ns > 0:
        for r, g in ti.ndrange(nr, ng):
            run_id = start + r

            # Deterministic per-run gate for DB seed injection.
            run_state = seed ^ (ti.cast(run_id, ti.u32) * ti.u32(747796405)) ^ ti.u32(2891336453)
            if run_state == ti.u32(0):
                run_state = ti.u32(1)
            run_state = kernels_helpers._xorshift32(run_state)
            allow_seed = (seed_prob_fp > ti.u32(0)) and (run_state < seed_prob_fp)

            eff_seed_copies = sc if allow_seed else 0
            eff_seed_mut = seed_mutations if allow_seed else 0
            seed_block = eff_seed_copies + eff_seed_mut

            # Deterministic per-(run,genome) state derived from base seed.
            state = seed ^ (ti.cast(run_id, ti.u32) * ti.u32(747796405)) ^ (ti.cast(g, ti.u32) * ti.u32(2891336453))
            if state == ti.u32(0):
                state = ti.u32(1)

            state = kernels_helpers._xorshift32(state)

            if seed_block > 0 and g < seed_block:
                for s in range(ns):
                    kernels_helpers.skyline_initial_populations[run_id, g, s] = seed_ids[s]

                # Mutate DB seed copies (g >= eff_seed_copies) to inject diversity.
                if eff_seed_mut > 0 and g >= eff_seed_copies:
                    state = kernels_helpers._xorshift32(state)
                    mut_slot = ti.cast(state % ti.cast(ns, ti.u32), ti.i32)
                    pool_start = kernels_helpers.slot_start[mut_slot]
                    pool_count = kernels_helpers.slot_count[mut_slot]
                    if pool_count > 1:
                        state = kernels_helpers._xorshift32(state)
                        new_item = pool_start + ti.cast(state % ti.cast(pool_count, ti.u32), ti.i32)
                        tries = 0
                        while new_item == seed_ids[mut_slot] and tries < 4:
                            state = kernels_helpers._xorshift32(state)
                            new_item = pool_start + ti.cast(state % ti.cast(pool_count, ti.u32), ti.i32)
                            tries += 1
                        kernels_helpers.skyline_initial_populations[run_id, g, mut_slot] = new_item
            else:
                for s in range(ns):
                    pool_start = kernels_helpers.slot_start[s]
                    pool_count = kernels_helpers.slot_count[s]
                    if pool_count <= 0:
                        kernels_helpers.skyline_initial_populations[run_id, g, s] = 0
                        continue

                    state = kernels_helpers._xorshift32(state)
                    use_heuristic = False
                    if hk > 0:
                        if heuristic_copies > 0 and g < heuristic_copies:
                            use_heuristic = True
                        elif heuristic_prob_fp > ti.u32(0) and state < heuristic_prob_fp:
                            use_heuristic = True

                    if use_heuristic:
                        state = kernels_helpers._xorshift32(state)
                        idx = ti.cast(state % ti.cast(hk, ti.u32), ti.i32)
                        kernels_helpers.skyline_initial_populations[run_id, g, s] = kernels_helpers.skyline_init_heuristic_topk[
                            s, idx
                        ]
                    else:
                        state = kernels_helpers._xorshift32(state)
                        kernels_helpers.skyline_initial_populations[run_id, g, s] = pool_start + ti.cast(
                            state % ti.cast(pool_count, ti.u32), ti.i32
                        )

            # Mini uniqueness repair (slots 6-8). This matches crossover/mutation semantics.
            mini_pool_start = kernels_helpers.slot_start[6]
            mini_pool_count = kernels_helpers.slot_count[6]
            if mini_pool_count > 1 and ns >= 9:
                m0 = kernels_helpers.skyline_initial_populations[run_id, g, 6]
                m1 = kernels_helpers.skyline_initial_populations[run_id, g, 7]
                m2 = kernels_helpers.skyline_initial_populations[run_id, g, 8]
                m0, m1, m2, state = _repair_mini_uniqueness(
                    m0,
                    m1,
                    m2,
                    mini_pool_start,
                    mini_pool_count,
                    state,
                )

                kernels_helpers.skyline_initial_populations[run_id, g, 6] = m0
                kernels_helpers.skyline_initial_populations[run_id, g, 7] = m1
                kernels_helpers.skyline_initial_populations[run_id, g, 8] = m2


@ti.kernel
def skyline_upload_item_stats_and_slots_kernel(
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
def skyline_copy_population_indices_from_ndarray_kernel(
    n_genomes: ti.i32,
    n_slots: ti.i32,
    population_src: ti.types.ndarray(dtype=ti.i32, ndim=2),
):
    """
    Copy a variable-length population buffer into GPU `population_indices`.

    This avoids full MAX_GENOMES x MAX_SLOTS host padding and upload when only a
    small active population slice is needed.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g, s in ti.ndrange(n_genomes, n_slots):
        kernels_helpers.population_indices[g, s] = population_src[g, s]


@ti.kernel
def skyline_aggregate_genome_stats_kernel(
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
        # (Overflow gems are handled later by the exact-bound allocator via is_p_ov/is_s_ov.)
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
def skyline_aggregate_and_init_best_kernel(
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
    reuse_exact_genome_base_stats: ti.i32,
):
    """
    FUSED: Aggregate item stats AND initialize chunk_best_key in one kernel.

    Combines skyline_aggregate_genome_stats_kernel + init_chunk_best_key_kernel
    to reduce kernel launch overhead.

    Args:
        n_genomes: Number of genomes
        n_slots: Number of equipment slots
        is_*: Color contribution flags (0/1) for primary/secondary
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    # Platform detection for atomic operations

    for g in range(n_genomes):
        if ti.static(not gpu_fields.IS_METAL):
            kernels_helpers.chunk_best_key[g] = ti.u64(0)
        else:
            kernels_helpers.chunk_best_score[g] = ti.cast(-2147483648, ti.i32)
            kernels_helpers.chunk_best_idx[g] = -1
        kernels_helpers.chunk_best_results[g, 0] = 0
        kernels_helpers.chunk_best_results[g, 1] = 0
        kernels_helpers.chunk_best_results[g, 2] = 0
        kernels_helpers.chunk_best_results[g, 3] = 0

        if reuse_exact_genome_base_stats != 0 and kernels_helpers.skyline_exact_eval_rep_idx[g] != g:
            continue

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


