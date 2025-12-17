"""
API GA Operations - GPU-native genetic algorithm operators.

This module provides GPU-side GA operators (selection, crossover, mutation, evaluation):
- ga_upload_population_indices: Upload integer-encoded population to GPU
- ga_seed_rng: Seed per-genome RNG state
- ga_upload_item_stats: Upload item stats and slot pools
- ga_upload_base_fixed_stats: Upload fixed base stats
- ga_aggregate_stats: Aggregate item stats into genome stats on GPU
- ga_evaluate_population: Full GPU-native evaluation pipeline
- ga_set_scores: Manually set scores for custom evaluation
- ga_next_generation: Tournament selection + crossover + mutation + elitism
- ga_download_*: Download results from GPU

These functions are prep work for future GPU-native GA where the entire
population lives on GPU, avoiding CPU-GPU transfers during evolution.
"""
from __future__ import annotations

import numpy as np

from .. import fields
from ..fields import MAX_WORK_ITEMS
from ..kernel_loader import get_kernels

from .initialization import ensure_ready, _upload_song_flags, _ensure_ftff_combo_tables

# Get appropriate kernels for current platform (Metal-safe on macOS)
kernels = get_kernels()


# ============================================================================
# GPU-NATIVE GA OPERATORS (UNUSED - Future infrastructure)
# ============================================================================
# These functions implement GPU-side GA operators (selection, crossover, mutation)
# but are NOT currently wired into genetic.py. They exist as prep work for a
# future GPU-native GA where the entire population lives on GPU.
#
# To complete: need encoder (genome -> item_ids) and integration in genetic.py.
# ============================================================================

def ga_upload_population_indices(population_indices_np: np.ndarray, *, n_slots: int = 9) -> int:
    """
    Upload integer population to the GPU resident `fields.population_indices`.
    Returns n_genomes uploaded.
    """
    ensure_ready()
    n_genomes = int(population_indices_np.shape[0])
    if n_genomes <= 0:
        return 0
    if n_genomes > fields.MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {fields.MAX_GENOMES}")
    if int(n_slots) > fields.MAX_SLOTS:
        raise ValueError(f"Too many slots: {n_slots} > {fields.MAX_SLOTS}")

    pop_buf = np.zeros((fields.MAX_GENOMES, fields.MAX_SLOTS), dtype=np.int32)
    pop_buf[:n_genomes, : int(n_slots)] = np.asarray(population_indices_np[:, : int(n_slots)], dtype=np.int32)
    fields.population_indices.from_numpy(pop_buf)
    return n_genomes


def ga_seed_rng(n_genomes: int, seed: int = 12345) -> None:
    """Seed per-genome RNG state for GPU GA operators."""
    ensure_ready()
    kernels.ga_seed_rng_kernel(int(n_genomes), np.uint32(seed))
    # GPU-only op; no CPU readback needed.


def ga_upload_item_stats(
    item_stats_np: np.ndarray,
    slot_start_np: np.ndarray,
    slot_count_np: np.ndarray,
) -> int:
    """
    Upload item stats and slot pool boundaries for GPU-native GA.
    
    Args:
        item_stats_np: (n_items, 10) int32 - per-item stats
        slot_start_np: (9,) int32 - first item_id per slot
        slot_count_np: (9,) int32 - count of items per slot
        
    Returns:
        Number of items uploaded
    """
    ensure_ready()
    n_items = int(item_stats_np.shape[0])
    
    if n_items > fields.MAX_ITEMS:
        raise ValueError(f"Too many items: {n_items} > {fields.MAX_ITEMS}")
    
    # Upload item stats (padded to MAX_ITEMS)
    stats_buf = np.zeros((fields.MAX_ITEMS, fields.ITEM_STAT_DIM), dtype=np.int32)
    stats_buf[:n_items, :] = np.asarray(item_stats_np[:, :fields.ITEM_STAT_DIM], dtype=np.int32)
    fields.item_stats.from_numpy(stats_buf)
    
    # Upload slot pool boundaries
    start_buf = np.zeros(fields.MAX_SLOTS, dtype=np.int32)
    count_buf = np.zeros(fields.MAX_SLOTS, dtype=np.int32)
    start_buf[:len(slot_start_np)] = np.asarray(slot_start_np, dtype=np.int32)
    count_buf[:len(slot_count_np)] = np.asarray(slot_count_np, dtype=np.int32)
    fields.slot_start.from_numpy(start_buf)
    fields.slot_count.from_numpy(count_buf)
    
    return n_items


def ga_upload_base_fixed_stats(base_stats_np: np.ndarray) -> None:
    """
    Upload fixed base stats (added to all genomes during aggregation).
    
    Args:
        base_stats_np: (10,) int32 - base stats [PP, CM, FM, FT, FF, Beat, Vibe, Rush, Flow, Chill]
    """
    ensure_ready()
    buf = np.zeros(fields.ITEM_STAT_DIM, dtype=np.int32)
    buf[:len(base_stats_np)] = np.asarray(base_stats_np, dtype=np.int32)
    fields.base_fixed_stats.from_numpy(buf)


def ga_aggregate_stats(
    n_genomes: int,
    n_slots: int = 9,
    *,
    is_p_ft: int = 0, is_s_ft: int = 0,
    is_p_ff: int = 0, is_s_ff: int = 0,
    is_p_pp: int = 0, is_s_pp: int = 0,
    is_p_cm: int = 0, is_s_cm: int = 0,
    is_p_fm: int = 0, is_s_fm: int = 0,
    is_p_ov: int = 0, is_s_ov: int = 0,
) -> None:
    """
    Aggregate item stats into genome_base_stats on GPU.
    
    For each genome, sums base_fixed_stats + item_stats[population_indices[g, s]]
    across all slots, then computes p_val/s_val from color flags.
    
    PREREQUISITES:
    - Call ga_upload_population_indices() first
    - Call ga_upload_item_stats() first
    - Call ga_upload_base_fixed_stats() first
    
    Args:
        n_genomes: Number of genomes to aggregate
        n_slots: Number of slots per genome (default 9)
        is_p_*: Primary color contribution flags (0 or 1)
        is_s_*: Secondary color contribution flags (0 or 1)
    """
    ensure_ready()
    kernels.ga_aggregate_genome_stats_kernel(
        int(n_genomes),
        int(n_slots),
        int(is_p_ft), int(is_s_ft),
        int(is_p_ff), int(is_s_ff),
        int(is_p_pp), int(is_s_pp),
        int(is_p_cm), int(is_s_cm),
        int(is_p_fm), int(is_s_fm),
        int(is_p_ov), int(is_s_ov),
    )


def ga_evaluate_population(
    n_genomes: int,
    n_slots: int = 9,
    *,
    total_budget: int,
    gem_scale_fever: int = 3,
    song_slot: int = 0,
    is_p_ft: int = 0, is_s_ft: int = 0,
    is_p_ff: int = 0, is_s_ff: int = 0,
    is_p_pp: int = 0, is_s_pp: int = 0,
    is_p_cm: int = 0, is_s_cm: int = 0,
    is_p_fm: int = 0, is_s_fm: int = 0,
    is_p_ov: int = 0, is_s_ov: int = 0,
    use_hints: int = 0,
) -> None:
    """
    GPU-native population evaluation: aggregate stats + evaluate + copy scores.
    
    This is the main GA evaluation function for GPU-native mode. It:
    1. Aggregates item stats → genome_base_stats (ga_aggregate_genome_stats_kernel)
    2. Evaluates all (ft, ff) combos → genome_result_stats (solve_genomes_with_ftff_kernel)
    3. Copies scores to ga_scores for selection (ga_copy_scores_kernel)
    
    PREREQUISITES:
    - Call ga_upload_population_indices() with encoded population
    - Call ga_upload_item_stats() with item stats and slot pools
    - Call ga_upload_base_fixed_stats() with base stats
    - Upload timeline grid using precompute_timeline_gpu() or _upload_timeline_grid()
    
    Args:
        n_genomes: Number of genomes to evaluate
        n_slots: Slots per genome (default 9)
        total_budget: Total gem budget
        gem_scale_fever: Stat points per FT/FF gem (default 3)
        song_slot: Timeline grid slot (0 for single-song)
        is_p_*, is_s_*: Color contribution flags
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    
    # Step 1: Aggregate item stats into genome_base_stats
    kernels.ga_aggregate_genome_stats_kernel(
        n_genomes, n_slots,
        int(is_p_ft), int(is_s_ft),
        int(is_p_ff), int(is_s_ff),
        int(is_p_pp), int(is_s_pp),
        int(is_p_cm), int(is_s_cm),
        int(is_p_fm), int(is_s_fm),
        int(is_p_ov), int(is_s_ov),
    )
    
    # Step 2: Evaluate genomes using existing FT/FF iteration kernel
    total_budget_i = int(total_budget)
    gem_scale_fever_i = int(gem_scale_fever)
    song_slot_i = int(song_slot)
    
    # Warm-start logic: Default to cold start (0) unless specified
    use_hints_i = int(use_hints)

    # Precompute FT/FF combo tables once per budget (tiny upload, reused across generations).
    n_combos = _ensure_ftff_combo_tables(total_budget_i)

    # Step 2: GPU-parallel evaluation across (genome, ft/ff combo), writing best key per genome.
    kernels.init_chunk_best_key_kernel(n_genomes)
    combo_chunk = n_combos
    # Chunk very large workloads to reduce kernel wall time (helps avoid Windows TDR on Vulkan).
    if n_genomes * n_combos > MAX_WORK_ITEMS:
        combo_chunk = 1024

    for offset in range(0, n_combos, combo_chunk):
        # Use warm-start kernel if available and requested
        if hasattr(kernels, "ga_find_best_combo_warmstart_kernel"):
            kernels.ga_find_best_combo_warmstart_kernel(
                n_genomes,
                n_combos,
                int(offset),
                int(min(combo_chunk, n_combos - offset)),
                total_budget_i,
                gem_scale_fever_i,
                int(is_p_ft), int(is_s_ft),
                int(is_p_ff), int(is_s_ff),
                int(is_p_pp), int(is_s_pp),
                int(is_p_cm), int(is_s_cm),
                int(is_p_fm), int(is_s_fm),
                int(is_p_ov), int(is_s_ov),
                song_slot_i,
                use_hints_i,
            )
        else:
            # Fallback to cold-start kernel if warm-start kernel missing
            kernels.ga_find_best_combo_key_kernel(
                n_genomes,
                n_combos,
                int(offset),
                int(min(combo_chunk, n_combos - offset)),
                total_budget_i,
                gem_scale_fever_i,
                int(is_p_ft), int(is_s_ft),
                int(is_p_ff), int(is_s_ff),
                int(is_p_pp), int(is_s_pp),
                int(is_p_cm), int(is_s_cm),
                int(is_p_fm), int(is_s_fm),
                int(is_p_ov), int(is_s_ov),
                song_slot_i,
            )

    # Step 3: Finalize best combo → genome_result_stats + ga_scores (one thread per genome).
    kernels.ga_write_best_results_from_key_kernel(
        n_genomes,
        total_budget_i,
        gem_scale_fever_i,
        int(is_p_ft), int(is_s_ft),
        int(is_p_ff), int(is_s_ff),
        int(is_p_pp), int(is_s_pp),
        int(is_p_cm), int(is_s_cm),
        int(is_p_fm), int(is_s_fm),
        int(is_p_ov), int(is_s_ov),
        song_slot_i,
    )


def ga_store_hints(n_genomes: int) -> None:
    """
    Store current best gem allocations as hints for next generation.
    Call this AFTER evaluation, BEFORE crossover.
    """
    ensure_ready()
    kernels.ga_store_hints_kernel(int(n_genomes))


def ga_inherit_hints(n_genomes: int) -> None:
    """
    Inherit hints from parents to children.
    Call this AFTER crossover, BEFORE next evaluation.
    """
    ensure_ready()
    kernels.ga_inherit_hints_kernel(int(n_genomes))


def ga_set_scores(scores_np: np.ndarray, *, n_genomes: int | None = None) -> int:
    """Upload fitness scores to GPU (fields.ga_scores). Returns n_genomes used."""
    ensure_ready()
    if n_genomes is None:
        n_genomes = int(scores_np.shape[0])
    n_genomes = int(n_genomes)
    if n_genomes <= 0:
        return 0
    if n_genomes > fields.MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {fields.MAX_GENOMES}")
    buf = np.zeros((fields.MAX_GENOMES,), dtype=np.int32)
    buf[:n_genomes] = np.asarray(scores_np[:n_genomes], dtype=np.int32)
    fields.ga_scores.from_numpy(buf)
    return n_genomes


def ga_next_generation(
    *,
    n_genomes: int,
    n_slots: int = 9,
    mutation_rate: float = 0.02,
    tournament_k: int = 3,
    elite_count: int = 2,
    elite_indices: np.ndarray | None = None,
) -> None:
    """
    Run one GPU-side GA operator step on resident population:
      selection -> crossover+mutation -> [elitism] -> swap buffers.
    
    Args:
        n_genomes: Population size
        n_slots: Slots per genome (default 9)
        mutation_rate: Probability of mutation per genome (default 0.02)
        tournament_k: Tournament size for selection (default 3)
        elite_count: Number of elites to preserve (default 2)
        elite_indices: Optional array of elite genome indices from current gen.
                      If provided, these genomes are copied to front of next gen.
                      If None and elite_count > 0, uses indices [0..elite_count-1].
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    elite_count = int(elite_count)
    tournament_k = int(tournament_k)
    if n_genomes <= 0:
        return
    if n_slots <= 0 or n_slots > fields.MAX_SLOTS:
        raise ValueError(f"Invalid n_slots: {n_slots}")
    if elite_count < 0:
        elite_count = 0
    if elite_count > n_genomes:
        elite_count = n_genomes
    if tournament_k < 1:
        tournament_k = 1

    # Convert probability to uint32 threshold.
    mr = float(mutation_rate)
    if mr <= 0.0:
        mr_fp = np.uint32(0)
    elif mr >= 1.0:
        mr_fp = np.uint32(0xFFFFFFFF)
    else:
        mr_fp = np.uint32(int(mr * 4294967295.0))

    # Step 1: Selection
    kernels.ga_select_parents_tournament_kernel(n_genomes, tournament_k)
    
    # Step 2: Crossover + Mutation (with mini uniqueness repair)
    kernels.ga_crossover_mutate_kernel(n_genomes, n_slots, mr_fp, elite_count)
    
    # Step 3: Elitism - copy elite genomes to front of next generation
    if elite_count > 0:
        if elite_indices is None:
            # Default: use first elite_count genomes as elites
            elite_indices = np.arange(elite_count, dtype=np.int32)
        else:
            elite_indices = np.asarray(elite_indices[:elite_count], dtype=np.int32)
        kernels.ga_copy_elites_kernel(len(elite_indices), n_slots, elite_indices)
    
    # Step 4: Swap buffers (next -> current)
    kernels.ga_swap_populations_kernel(n_genomes, n_slots)


def ga_download_population_indices(*, n_genomes: int, n_slots: int = 9) -> np.ndarray:
    """Download the current resident population indices (for testing / debugging)."""
    ensure_ready()
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    out = fields.population_indices.to_numpy()
    return np.asarray(out[:n_genomes, :n_slots], dtype=np.int32)


def ga_download_scores(n_genomes: int) -> np.ndarray:
    """
    Download fitness scores from GPU (for CPU-side elitism).
    
    Args:
        n_genomes: Number of genomes to download
        
    Returns:
        np.ndarray: (n_genomes,) int32 array of scores
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    out = fields.ga_scores.to_numpy()
    return np.asarray(out[:n_genomes], dtype=np.int32)


def ga_download_results(n_genomes: int) -> np.ndarray:
    """
    Download full evaluation results from GPU.
    
    Args:
        n_genomes: Number of genomes to download
        
    Returns:
        np.ndarray: (n_genomes, 7) int32 array [score, ft, ff, pp, cm, fm, ov]
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    out = fields.genome_result_stats.to_numpy()
    return np.asarray(out[:n_genomes], dtype=np.int32)


# ============================================================================
# GPU-SIDE GLOBAL BEST TRACKING
# ============================================================================

def ga_init_global_best() -> None:
    """
    Initialize global best tracking at the start of a GA run.
    
    Resets ga_global_best_score to -1 (no best yet).
    Call this once at the start of each GA run.
    """
    ensure_ready()
    kernels.ga_init_global_best_kernel()


def ga_update_global_best(n_genomes: int, n_slots: int = 9) -> None:
    """
    Update global best genome on GPU if current generation has a better score.
    
    Atomically tracks the best genome across all generations on GPU,
    avoiding expensive per-generation CPU downloads.
    
    Call this after each ga_evaluate_population() call.
    
    Args:
        n_genomes: Number of genomes to check
        n_slots: Number of equipment slots per genome
    """
    ensure_ready()
    kernels.ga_update_global_best_kernel(int(n_genomes), int(n_slots))


def ga_download_global_best() -> tuple[int, np.ndarray, np.ndarray]:
    """
    Download the global best genome and results from GPU.
    
    Returns:
        Tuple of (best_score, best_genome_ids, best_results):
        - best_score: int - the best score found across all generations
        - best_genome_ids: np.ndarray (n_slots,) int32 - item IDs of best genome
        - best_results: np.ndarray (7,) int32 - [score, ft, ff, pp, cm, fm, ov]
    """
    ensure_ready()
    best_score = int(fields.ga_global_best_score.to_numpy()[0])
    best_genome_ids = fields.ga_global_best_genome.to_numpy().copy()
    best_results = fields.ga_global_best_results.to_numpy().copy()
    return best_score, best_genome_ids, best_results


def ga_upload_island_boundaries(island_starts: np.ndarray) -> None:
    """
    Upload island boundary indices to GPU for island-based elitism.
    
    Args:
        island_starts: (n_islands + 1,) int32 array of island boundaries.
                      Format: [start0, start1, ..., end_last]
                      Island i owns indices [start[i], start[i+1])
    """
    ensure_ready()
    buf = np.zeros(fields.MAX_ISLANDS + 1, dtype=np.int32)
    n = min(len(island_starts), fields.MAX_ISLANDS + 1)
    buf[:n] = np.asarray(island_starts[:n], dtype=np.int32)
    fields.island_boundaries.from_numpy(buf)


def ga_find_island_elites(n_genomes: int, n_islands: int, elites_per_island: int) -> None:
    """
    GPU-side island elite selection: find top-k genomes per island.
    
    This replaces the CPU-side score download + argsort previously used.
    Must call ga_upload_island_boundaries() first.
    
    After calling, elite indices are available in island_elite_indices field.
    Use ga_download_island_elite_indices() to retrieve them if needed.
    
    Args:
        n_genomes: Total population size
        n_islands: Number of islands
        elites_per_island: Number of elites to select per island
    """
    ensure_ready()
    kernels.ga_find_island_elites_kernel(
        int(n_genomes), int(n_islands), int(elites_per_island)
    )


def ga_download_island_elite_indices(n_elites: int) -> np.ndarray:
    """
    Download the elite genome indices computed by ga_find_island_elites.
    
    Args:
        n_elites: Total number of elites (n_islands * elites_per_island)
        
    Returns:
        np.ndarray: (n_elites,) int32 array of elite genome indices
    """
    ensure_ready()
    out = fields.island_elite_indices.to_numpy()
    return np.asarray(out[:n_elites], dtype=np.int32)

