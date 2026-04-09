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

import os
import sys
import taichi as ti

# Platform detection for atomic operations
IS_METAL = sys.platform == "darwin"

from . import kernels_helpers


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except Exception:
        return float(default)


_GA_DIVERSE_PARENT_B_RATE = max(0.0, min(1.0, _env_float("GPU_GA_DIVERSE_PARENT_B_RATE", 0.125)))
_GA_DIVERSE_PARENT_B_RATE_FP = int(_GA_DIVERSE_PARENT_B_RATE * 4294967295.0)


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
    # permutation-only genomes do not consume GA budget or create fake variance.
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


@ti.func
def _fg_proxy_for_genome(genome_idx: ti.i32) -> ti.i64:
    stats7 = kernels_helpers.genome_base_stats[genome_idx]
    return (
        ti.cast(stats7[2], ti.i64) * 4
        + ti.cast(stats7[6], ti.i64) * 4
        + ti.cast(stats7[5], ti.i64) * 3
        + ti.cast(stats7[1], ti.i64) * 2
        + ti.cast(stats7[0], ti.i64)
        + ti.cast(stats7[3], ti.i64) * 2
        + ti.cast(stats7[4], ti.i64)
    )


@ti.func
def _hash_exact_eval_input_for_genome(genome_idx: ti.i32, n_slots: ti.i32) -> ti.u32:
    h = ti.u32(2166136261)
    for s in ti.static(range(9)):
        v = ti.i32(0)
        if s < n_slots:
            v = kernels_helpers.population_indices[genome_idx, s]
        h = (h ^ ti.cast(v + 1, ti.u32)) * ti.u32(16777619)
    return h


@ti.func
def _exact_eval_key_matches(pos: ti.i32, genome_idx: ti.i32, n_slots: ti.i32) -> ti.i32:
    match = ti.i32(1)
    for s in ti.static(range(9)):
        want = ti.i32(0)
        if s < n_slots:
            want = kernels_helpers.population_indices[genome_idx, s]
        if kernels_helpers.ga_exact_eval_hash_keys[pos, s] != want:
            match = 0
    return match


@ti.func
def _exact_eval_input_matches_genomes(a: ti.i32, b: ti.i32, n_slots: ti.i32) -> ti.i32:
    match = ti.i32(1)
    for s in ti.static(range(9)):
        va = ti.i32(0)
        vb = ti.i32(0)
        if s < n_slots:
            va = kernels_helpers.population_indices[a, s]
            vb = kernels_helpers.population_indices[b, s]
        if va != vb:
            match = 0
    return match


@ti.func
def _store_exact_eval_key(pos: ti.i32, genome_idx: ti.i32, n_slots: ti.i32) -> None:
    for s in ti.static(range(9)):
        value = ti.i32(0)
        if s < n_slots:
            value = kernels_helpers.population_indices[genome_idx, s]
        kernels_helpers.ga_exact_eval_hash_keys[pos, s] = value


@ti.func
def _hash_exact_eval_base_stats_for_genome(genome_idx: ti.i32) -> ti.u32:
    h = ti.u32(2166136261)
    for i in ti.static(range(7)):
        # genome_base_stats is i16-backed; bias to keep negative values stable in the hash stream.
        v = ti.cast(kernels_helpers.genome_base_stats[genome_idx][i], ti.i32)
        h = (h ^ ti.cast(v + 32769, ti.u32)) * ti.u32(16777619)
    return h


@ti.func
def _exact_eval_base_stats_key_matches(pos: ti.i32, genome_idx: ti.i32) -> ti.i32:
    match = ti.i32(1)
    for i in ti.static(range(7)):
        want = ti.cast(kernels_helpers.genome_base_stats[genome_idx][i], ti.i32)
        if kernels_helpers.ga_exact_eval_hash_keys[pos, i] != want:
            match = 0
    return match


@ti.func
def _exact_eval_base_stats_matches_genomes(a: ti.i32, b: ti.i32) -> ti.i32:
    match = ti.i32(1)
    for i in ti.static(range(7)):
        if kernels_helpers.genome_base_stats[a][i] != kernels_helpers.genome_base_stats[b][i]:
            match = 0
    return match


@ti.func
def _store_exact_eval_base_stats_key(pos: ti.i32, genome_idx: ti.i32) -> None:
    for i in ti.static(range(7)):
        kernels_helpers.ga_exact_eval_hash_keys[pos, i] = ti.cast(kernels_helpers.genome_base_stats[genome_idx][i], ti.i32)
    for i in ti.static(range(7, 9)):
        kernels_helpers.ga_exact_eval_hash_keys[pos, i] = 0


@ti.kernel
def _ga_prepare_exact_eval_reuse_sort_arrays_kernel(n_genomes: ti.i32, n_slots: ti.i32):
    """
    Prepare hash keys + indices for parallel sort grouping.

    The sorted arrays are consumed by `_ga_build_exact_eval_reuse_map_from_sorted_kernel`.
    """
    sentinel = ti.i32(2147483647)
    for i in range(kernels_helpers.ga_exact_eval_hash_sort_keys.shape[0]):
        if i < n_genomes:
            h = _hash_exact_eval_input_for_genome(i, n_slots)
            kernels_helpers.ga_exact_eval_hash_sort_keys[i] = ti.cast(h, ti.i32)
            kernels_helpers.ga_exact_eval_hash_sort_indices[i] = i
        else:
            kernels_helpers.ga_exact_eval_hash_sort_keys[i] = sentinel
            kernels_helpers.ga_exact_eval_hash_sort_indices[i] = -1
    kernels_helpers.ga_exact_eval_unique_count[0] = 0


@ti.kernel
def _ga_build_exact_eval_reuse_map_from_sorted_kernel(n_genomes: ti.i32, n_slots: ti.i32):
    """
    Build `ga_exact_eval_rep_idx` after sorting hash keys.

    We scan the full hash group (both directions) to avoid relying on stable ordering
    within equal-key regions (Taichi's parallel sort is not guaranteed stable).
    """
    n_genomes0 = ti.max(ti.i32(0), n_genomes)
    for g in range(n_genomes0):
        kernels_helpers.ga_exact_eval_rep_idx[g] = g

    n_total = kernels_helpers.ga_exact_eval_hash_sort_keys.shape[0]
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for i in range(n_total):
        g = kernels_helpers.ga_exact_eval_hash_sort_indices[i]
        if g < 0 or g >= n_genomes0:
            continue

        key = kernels_helpers.ga_exact_eval_hash_sort_keys[i]
        rep = g

        j = i - 1
        while j >= 0 and kernels_helpers.ga_exact_eval_hash_sort_keys[j] == key:
            cand = kernels_helpers.ga_exact_eval_hash_sort_indices[j]
            if cand >= 0 and cand < n_genomes0:
                if _exact_eval_input_matches_genomes(cand, g, n_slots) != 0:
                    rep = ti.min(rep, cand)
            j -= 1

        j = i + 1
        while j < n_total and kernels_helpers.ga_exact_eval_hash_sort_keys[j] == key:
            cand = kernels_helpers.ga_exact_eval_hash_sort_indices[j]
            if cand >= 0 and cand < n_genomes0:
                if _exact_eval_input_matches_genomes(cand, g, n_slots) != 0:
                    rep = ti.min(rep, cand)
            j += 1

        kernels_helpers.ga_exact_eval_rep_idx[g] = rep
        if rep == g:
            ti.atomic_add(kernels_helpers.ga_exact_eval_unique_count[0], 1)


@ti.kernel
def _ga_build_exact_eval_reuse_map_serial_kernel(n_genomes: ti.i32, n_slots: ti.i32):
    """
    Original open-addressing implementation (serialized).

    Kept for the current Metal path and as a correctness fallback.
    """
    for i in range(kernels_helpers.ga_exact_eval_hash_used.shape[0]):
        kernels_helpers.ga_exact_eval_hash_used[i] = 0
    kernels_helpers.ga_exact_eval_unique_count[0] = 0

    ti.loop_config(serialize=True)
    for g in range(n_genomes):
        h = _hash_exact_eval_input_for_genome(g, n_slots)
        mask = kernels_helpers.ga_exact_eval_hash_used.shape[0] - 1
        pos = ti.cast(h & ti.u32(mask), ti.i32)
        rep = g
        handled = ti.i32(0)

        for _ in range(kernels_helpers.ga_exact_eval_hash_used.shape[0]):
            entry = kernels_helpers.ga_exact_eval_hash_used[pos]
            if entry == 0:
                kernels_helpers.ga_exact_eval_hash_used[pos] = g + 1
                _store_exact_eval_key(pos, g, n_slots)
                kernels_helpers.ga_exact_eval_unique_count[0] = kernels_helpers.ga_exact_eval_unique_count[0] + 1
                rep = g
                handled = 1
                break

            if _exact_eval_key_matches(pos, g, n_slots) != 0:
                rep = entry - 1
                handled = 1
                break

            pos = (pos + 1) & mask

        if handled == 0:
            rep = g
        kernels_helpers.ga_exact_eval_rep_idx[g] = rep


def ga_build_exact_eval_reuse_map_kernel(n_genomes: int, n_slots: int) -> None:
    """
    Build a representative map for exact duplicate evaluation inputs.
    """
    n_genomes_i = int(n_genomes)
    if n_genomes_i <= 1:
        kernels_helpers.ga_exact_eval_unique_count[0] = 0
        if n_genomes_i == 1:
            kernels_helpers.ga_exact_eval_rep_idx[0] = 0
            kernels_helpers.ga_exact_eval_unique_count[0] = 1
        return

    n_slots_i = int(n_slots)
    if IS_METAL:
        _ga_build_exact_eval_reuse_map_serial_kernel(n_genomes_i, n_slots_i)
        return

    _ga_prepare_exact_eval_reuse_sort_arrays_kernel(n_genomes_i, n_slots_i)
    from taichi.algorithms import parallel_sort as _parallel_sort

    _parallel_sort(kernels_helpers.ga_exact_eval_hash_sort_keys, kernels_helpers.ga_exact_eval_hash_sort_indices)
    _ga_build_exact_eval_reuse_map_from_sorted_kernel(n_genomes_i, n_slots_i)


@ti.kernel
def _ga_prepare_exact_eval_base_stats_reuse_sort_arrays_kernel(n_genomes: ti.i32):
    sentinel = ti.i32(2147483647)
    for i in range(kernels_helpers.ga_exact_eval_hash_sort_keys.shape[0]):
        if i < n_genomes:
            h = _hash_exact_eval_base_stats_for_genome(i)
            kernels_helpers.ga_exact_eval_hash_sort_keys[i] = ti.cast(h, ti.i32)
            kernels_helpers.ga_exact_eval_hash_sort_indices[i] = i
        else:
            kernels_helpers.ga_exact_eval_hash_sort_keys[i] = sentinel
            kernels_helpers.ga_exact_eval_hash_sort_indices[i] = -1
    kernels_helpers.ga_exact_eval_unique_count[0] = 0


@ti.kernel
def _ga_build_exact_eval_reuse_map_from_base_stats_sorted_kernel(n_genomes: ti.i32):
    n_genomes0 = ti.max(ti.i32(0), n_genomes)
    for g in range(n_genomes0):
        kernels_helpers.ga_exact_eval_rep_idx[g] = g

    n_total = kernels_helpers.ga_exact_eval_hash_sort_keys.shape[0]
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for i in range(n_total):
        g = kernels_helpers.ga_exact_eval_hash_sort_indices[i]
        if g < 0 or g >= n_genomes0:
            continue

        key = kernels_helpers.ga_exact_eval_hash_sort_keys[i]
        rep = g

        j = i - 1
        while j >= 0 and kernels_helpers.ga_exact_eval_hash_sort_keys[j] == key:
            cand = kernels_helpers.ga_exact_eval_hash_sort_indices[j]
            if cand >= 0 and cand < n_genomes0:
                if _exact_eval_base_stats_matches_genomes(cand, g) != 0:
                    rep = ti.min(rep, cand)
            j -= 1

        j = i + 1
        while j < n_total and kernels_helpers.ga_exact_eval_hash_sort_keys[j] == key:
            cand = kernels_helpers.ga_exact_eval_hash_sort_indices[j]
            if cand >= 0 and cand < n_genomes0:
                if _exact_eval_base_stats_matches_genomes(cand, g) != 0:
                    rep = ti.min(rep, cand)
            j += 1

        kernels_helpers.ga_exact_eval_rep_idx[g] = rep
        if rep == g:
            ti.atomic_add(kernels_helpers.ga_exact_eval_unique_count[0], 1)


@ti.kernel
def _ga_build_exact_eval_reuse_map_from_base_stats_serial_kernel(n_genomes: ti.i32):
    for i in range(kernels_helpers.ga_exact_eval_hash_used.shape[0]):
        kernels_helpers.ga_exact_eval_hash_used[i] = 0
    kernels_helpers.ga_exact_eval_unique_count[0] = 0

    ti.loop_config(serialize=True)
    for g in range(n_genomes):
        h = _hash_exact_eval_base_stats_for_genome(g)
        mask = kernels_helpers.ga_exact_eval_hash_used.shape[0] - 1
        pos = ti.cast(h & ti.u32(mask), ti.i32)
        rep = g
        handled = ti.i32(0)

        for _ in range(kernels_helpers.ga_exact_eval_hash_used.shape[0]):
            entry = kernels_helpers.ga_exact_eval_hash_used[pos]
            if entry == 0:
                kernels_helpers.ga_exact_eval_hash_used[pos] = g + 1
                _store_exact_eval_base_stats_key(pos, g)
                kernels_helpers.ga_exact_eval_unique_count[0] = kernels_helpers.ga_exact_eval_unique_count[0] + 1
                rep = g
                handled = 1
                break

            if _exact_eval_base_stats_key_matches(pos, g) != 0:
                rep = entry - 1
                handled = 1
                break

            pos = (pos + 1) & mask

        if handled == 0:
            rep = g
        kernels_helpers.ga_exact_eval_rep_idx[g] = rep


def ga_build_exact_eval_reuse_map_from_base_stats_kernel(n_genomes: int) -> None:
    """
    Build a representative map for exact-cold evaluations keyed on aggregated base stats.

    Within a single song/run, `genome_base_stats` is the exact score-relevant state for the
    base gem solver. Reusing by this key is therefore stronger than raw-genome dedup while
    preserving exactness for cold evaluations.
    """
    n_genomes_i = int(n_genomes)
    if n_genomes_i <= 1:
        kernels_helpers.ga_exact_eval_unique_count[0] = 0
        if n_genomes_i == 1:
            kernels_helpers.ga_exact_eval_rep_idx[0] = 0
            kernels_helpers.ga_exact_eval_unique_count[0] = 1
        return

    if IS_METAL:
        _ga_build_exact_eval_reuse_map_from_base_stats_serial_kernel(n_genomes_i)
        return

    _ga_prepare_exact_eval_base_stats_reuse_sort_arrays_kernel(n_genomes_i)
    from taichi.algorithms import parallel_sort as _parallel_sort

    _parallel_sort(kernels_helpers.ga_exact_eval_hash_sort_keys, kernels_helpers.ga_exact_eval_hash_sort_indices)
    _ga_build_exact_eval_reuse_map_from_base_stats_sorted_kernel(n_genomes_i)


@ti.kernel
def ga_propagate_exact_eval_reuse_base_stats_kernel(n_genomes: ti.i32):
    """Copy deterministic base stats from representative rows to duplicate genomes."""
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        rep = kernels_helpers.ga_exact_eval_rep_idx[g]
        if rep >= 0 and rep != g:
            for i in ti.static(range(7)):
                kernels_helpers.genome_base_stats[g][i] = kernels_helpers.genome_base_stats[rep][i]


@ti.kernel
def ga_propagate_exact_eval_reuse_chunk_best_kernel(n_genomes: ti.i32):
    """Copy best-combo search outputs from representative rows to duplicate genomes."""
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        rep = kernels_helpers.ga_exact_eval_rep_idx[g]
        if rep >= 0 and rep != g:
            if ti.static(not IS_METAL):
                kernels_helpers.chunk_best_key[g] = kernels_helpers.chunk_best_key[rep]
            else:
                kernels_helpers.chunk_best_score[g] = kernels_helpers.chunk_best_score[rep]
                kernels_helpers.chunk_best_idx[g] = kernels_helpers.chunk_best_idx[rep]
            for i in ti.static(range(4)):
                kernels_helpers.chunk_best_results[g, i] = kernels_helpers.chunk_best_results[rep, i]


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
def ga_generate_initial_populations_kernel(
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
    Generate initial populations directly on GPU into `ga_initial_populations`.

    This eliminates the CPU-side build+encode+upload loop for multi-start runs.

    Notes:
    - Slot pools (slot_start/slot_count) must already be uploaded (via ga_upload_item_stats).
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
                    kernels_helpers.ga_initial_populations[run_id, g, s] = seed_ids[s]

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
                        kernels_helpers.ga_initial_populations[run_id, g, mut_slot] = new_item
            else:
                for s in range(ns):
                    pool_start = kernels_helpers.slot_start[s]
                    pool_count = kernels_helpers.slot_count[s]
                    if pool_count <= 0:
                        kernels_helpers.ga_initial_populations[run_id, g, s] = 0
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
                        kernels_helpers.ga_initial_populations[run_id, g, s] = kernels_helpers.ga_init_heuristic_topk[
                            s, idx
                        ]
                    else:
                        state = kernels_helpers._xorshift32(state)
                        kernels_helpers.ga_initial_populations[run_id, g, s] = pool_start + ti.cast(
                            state % ti.cast(pool_count, ti.u32), ti.i32
                        )

            # Mini uniqueness repair (slots 6-8). This matches crossover/mutation semantics.
            mini_pool_start = kernels_helpers.slot_start[6]
            mini_pool_count = kernels_helpers.slot_count[6]
            if mini_pool_count > 1 and ns >= 9:
                m0 = kernels_helpers.ga_initial_populations[run_id, g, 6]
                m1 = kernels_helpers.ga_initial_populations[run_id, g, 7]
                m2 = kernels_helpers.ga_initial_populations[run_id, g, 8]
                m0, m1, m2, state = _repair_mini_uniqueness(
                    m0,
                    m1,
                    m2,
                    mini_pool_start,
                    mini_pool_count,
                    state,
                )

                kernels_helpers.ga_initial_populations[run_id, g, 6] = m0
                kernels_helpers.ga_initial_populations[run_id, g, 7] = m1
                kernels_helpers.ga_initial_populations[run_id, g, 8] = m2


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
def ga_copy_population_indices_from_ndarray_kernel(
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

        # Pick parent B. Occasionally bias this tournament toward an FG proxy
        # so the population keeps fever-heavy niches without replacing the
        # score-driven anchor parent.
        best_b = 0
        best_b_score = ti.cast(-2147483648, ti.i32)
        best_b_proxy = ti.i64(-1)
        state = kernels_helpers._xorshift32(state)
        use_diverse_b = ti.i32(0)
        if ti.static(_GA_DIVERSE_PARENT_B_RATE_FP > 0):
            if state < ti.u32(_GA_DIVERSE_PARENT_B_RATE_FP):
                use_diverse_b = ti.i32(1)
        for _ in range(tournament_k):
            state = kernels_helpers._xorshift32(state)
            idx = ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
            sc = kernels_helpers.ga_scores[idx]
            if use_diverse_b != 0:
                proxy = _fg_proxy_for_genome(idx)
                if proxy > best_b_proxy or (proxy == best_b_proxy and sc > best_b_score):
                    best_b_proxy = proxy
                    best_b_score = sc
                    best_b = idx
            elif sc > best_b_score:
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
            m0, m1, m2, state = _repair_mini_uniqueness(
                m0,
                m1,
                m2,
                mini_pool_start,
                mini_pool_count,
                state,
            )

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
    reuse_exact_genome_base_stats: ti.i32,
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
        else:
            kernels_helpers.chunk_best_score[g] = ti.cast(-2147483648, ti.i32)
            kernels_helpers.chunk_best_idx[g] = -1
        kernels_helpers.chunk_best_results[g, 0] = 0
        kernels_helpers.chunk_best_results[g, 1] = 0
        kernels_helpers.chunk_best_results[g, 2] = 0
        kernels_helpers.chunk_best_results[g, 3] = 0

        if reuse_exact_genome_base_stats != 0 and kernels_helpers.ga_exact_eval_rep_idx[g] != g:
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

        # Pick parent B. Occasionally bias this tournament toward an FG proxy
        # so the population keeps fever-heavy niches without replacing the
        # score-driven anchor parent.
        best_b = 0
        best_b_score = ti.cast(-2147483648, ti.i32)
        best_b_proxy = ti.i64(-1)
        state = kernels_helpers._xorshift32(state)
        use_diverse_b = ti.i32(0)
        if ti.static(_GA_DIVERSE_PARENT_B_RATE_FP > 0):
            if state < ti.u32(_GA_DIVERSE_PARENT_B_RATE_FP):
                use_diverse_b = ti.i32(1)
        for _ in range(tournament_k):
            state = kernels_helpers._xorshift32(state)
            idx = ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
            sc = kernels_helpers.ga_scores[idx]
            if use_diverse_b != 0:
                proxy = _fg_proxy_for_genome(idx)
                if proxy > best_b_proxy or (proxy == best_b_proxy and sc > best_b_score):
                    best_b_proxy = proxy
                    best_b_score = sc
                    best_b = idx
            elif sc > best_b_score:
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
            m0, m1, m2, state = _repair_mini_uniqueness(
                m0,
                m1,
                m2,
                mini_pool_start,
                mini_pool_count,
                state,
            )

            kernels_helpers.population_next_indices[g, 6] = m0
            kernels_helpers.population_next_indices[g, 7] = m1
            kernels_helpers.population_next_indices[g, 8] = m2

        kernels_helpers.ga_rng_state[g] = state
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
    FULLY FUSED: Selection + Crossover + Mutation + Elitism + Swap.

    This kernel combines 4 separate kernels into 1 to reduce launch overhead:
    1. Tournament selection (picks pa, pb)
    2. Crossover + mutation (writes to population_next_indices)
    3. Elite copy (from GPU-resident island_elite_indices)
    4. Swap (next -> current)

    The kernel operates in two phases:
    - Phase 1 (g >= n_elites): Tournament + crossover + mutation for non-elite slots
    - Phase 2 (g < n_elites): Copy elites directly
    - Phase 3: Swap population buffers (done in the follow-up kernel)

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
        pa = 0  # Initialize parent A index for diagnostics / compatibility

        # For elites (g < n_elites): copy from original population
        # For non-elites (g >= n_elites): do tournament + crossover + mutation
        if g < n_elites:
            # Elite path: copy from island_elite_indices[g]
            src_genome = kernels_helpers.island_elite_indices[g]
            for s in range(n_slots):
                kernels_helpers.population_next_indices[g, s] = kernels_helpers.population_indices[src_genome, s]
            pa = src_genome
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

            # Pick parent B. Occasionally bias this tournament toward an FG proxy
            # so the population keeps fever-heavy niches without replacing the
            # score-driven anchor parent.
            best_b = 0
            best_b_score = ti.cast(-2147483648, ti.i32)
            best_b_proxy = ti.i64(-1)
            state = kernels_helpers._xorshift32(state)
            use_diverse_b = ti.i32(0)
            if ti.static(_GA_DIVERSE_PARENT_B_RATE_FP > 0):
                if state < ti.u32(_GA_DIVERSE_PARENT_B_RATE_FP):
                    use_diverse_b = ti.i32(1)
            for _ in range(tournament_k):
                state = kernels_helpers._xorshift32(state)
                idx = ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
                sc = kernels_helpers.ga_scores[idx]
                if use_diverse_b != 0:
                    proxy = _fg_proxy_for_genome(idx)
                    if proxy > best_b_proxy or (proxy == best_b_proxy and sc > best_b_score):
                        best_b_proxy = proxy
                        best_b_score = sc
                        best_b = idx
                elif sc > best_b_score:
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
                m0, m1, m2, state = _repair_mini_uniqueness(
                    m0,
                    m1,
                    m2,
                    mini_pool_start,
                    mini_pool_count,
                    state,
                )

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
                        m0, m1, m2, state = _repair_mini_uniqueness(
                            m0,
                            m1,
                            m2,
                            mini_pool_start,
                            mini_pool_count,
                            state,
                        )

                        kernels_helpers.population_next_indices[g, 6] = m0
                        kernels_helpers.population_next_indices[g, 7] = m1
                        kernels_helpers.population_next_indices[g, 8] = m2

                    pa = -1

        kernels_helpers.ga_rng_state[g] = state

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
        best_b_proxy = ti.i64(-1)
        state = kernels_helpers._xorshift32(state)
        use_diverse_b = ti.i32(0)
        if ti.static(_GA_DIVERSE_PARENT_B_RATE_FP > 0):
            if state < ti.u32(_GA_DIVERSE_PARENT_B_RATE_FP):
                use_diverse_b = ti.i32(1)
        for _ in range(tournament_k_i):
            state = kernels_helpers._xorshift32(state)
            idx = ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
            sc = kernels_helpers.ga_scores[idx]
            if use_diverse_b != 0:
                proxy = _fg_proxy_for_genome(idx)
                if proxy > best_b_proxy or (proxy == best_b_proxy and sc > best_b_score):
                    best_b_proxy = proxy
                    best_b_score = sc
                    best_b = idx
            elif sc > best_b_score:
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
            m0, m1, m2, state = _repair_mini_uniqueness(
                m0,
                m1,
                m2,
                mini_pool_start,
                mini_pool_count,
                state,
            )

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
                    m0, m1, m2, state = _repair_mini_uniqueness(
                        m0,
                        m1,
                        m2,
                        mini_pool_start,
                        mini_pool_count,
                        state,
                    )

                    kernels_helpers.population_next_indices[g, 6] = m0
                    kernels_helpers.population_next_indices[g, 7] = m1
                    kernels_helpers.population_next_indices[g, 8] = m2

                pa = -1

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
        best_b_proxy = ti.i64(-1)
        state = kernels_helpers._xorshift32(state)
        use_diverse_b = ti.i32(0)
        if ti.static(_GA_DIVERSE_PARENT_B_RATE_FP > 0):
            if state < ti.u32(_GA_DIVERSE_PARENT_B_RATE_FP):
                use_diverse_b = ti.i32(1)
        for _ in range(tournament_k_i):
            state = kernels_helpers._xorshift32(state)
            idx_local = ti.cast(state % ti.cast(n_genomes_per_run_i, ti.u32), ti.i32)
            idx = run_start + idx_local
            sc = kernels_helpers.ga_scores[idx]
            if use_diverse_b != 0:
                proxy = _fg_proxy_for_genome(idx)
                if proxy > best_b_proxy or (proxy == best_b_proxy and sc > best_b_score):
                    best_b_proxy = proxy
                    best_b_score = sc
                    best_b = idx
            elif sc > best_b_score:
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
            m0, m1, m2, state = _repair_mini_uniqueness(
                m0,
                m1,
                m2,
                mini_pool_start,
                mini_pool_count,
                state,
            )

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
                    m0, m1, m2, state = _repair_mini_uniqueness(
                        m0,
                        m1,
                        m2,
                        mini_pool_start,
                        mini_pool_count,
                        state,
                    )

                    kernels_helpers.population_next_indices[g, 6] = m0
                    kernels_helpers.population_next_indices[g, 7] = m1
                    kernels_helpers.population_next_indices[g, 8] = m2

                pa = -1

        kernels_helpers.ga_rng_state[g] = state
        kernels_helpers.ga_parent_a[g] = pa

@ti.kernel
def ga_swap_population_kernel(n_genomes: ti.i32, n_slots: ti.i32):
    """
    FUSED: swap the next-generation population into the active buffer.

    This is Phase 2 of the fused next-generation operation:
    1. Copy population_next_indices -> population_indices (swap)

    Args:
        n_genomes: Population size
        n_slots: Slots per genome
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        # Swap
        for s in range(n_slots):
            kernels_helpers.population_indices[g, s] = kernels_helpers.population_next_indices[g, s]
