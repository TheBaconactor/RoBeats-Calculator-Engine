"""
Genetic algorithm solver for gear and mini co-evolution.

This module contains the main GA that optimizes both gear (6 slots) and minis (3 slots)
simultaneously to find optimal loadouts. Uses tournament selection, crossover, mutation,
and memetic local search.

The main function solve_coevolution_genetic() has been refactored to use helper functions
from helpers.ga_helpers for improved modularity and maintainability.
"""
import os
import random

# Support deterministic testing via GA_SEED environment variable
_GA_SEED = os.environ.get("GA_SEED")
if _GA_SEED is not None:
    _GA_SEED = int(_GA_SEED)
    random.seed(_GA_SEED)
    print(f"[GA] Deterministic mode: seed={_GA_SEED}")

from ..core.constants import (
    GA_POPULATION_SIZE,
    GA_GENERATIONS,
    GA_MUTATION_RATE,
    GA_ELITISM,
    GA_MUTATION_RATE_MAX,
    GA_MULTI_RUNS_DEFAULT,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
    LOADOUTS_PER_SONG_LIMIT,
    SKIP_ITEM_KEYS,
    GPU_GA_NUM_ISLANDS,
    GPU_GA_GENS_PER_MIGRATION,
    GPU_GA_MIGRATE_COUNT,
)
from ..core.utils import prune_dominated_gear, safe_int
from ..data.database import get_loadout_hash
from .scoring import worker_coevolution_evaluate, GEM_SOLVER_CACHE, FG_CACHE, FEVER_TIMELINE_CACHE
from ..data.models import GASettings
from ..helpers.ga_helpers import (
    initialize_pools,
    create_genome_functions,
    create_evaluation_functions,
    create_local_search_function,
    build_initial_population,
    perform_crossover_mutation,
    evaluate_population_parallel,
    update_mutation_and_diversity,
    compute_dynamic_mutation,
)

# Optional: GPU-native GA imports (only loaded if needed)
_GPU_NATIVE_AVAILABLE = False
try:
    from .item_registry import ItemRegistry
    from .taichi_gem import api as gpu_api
    import numpy as np
    _GPU_NATIVE_AVAILABLE = True
except ImportError:
    pass


def _run_gpu_native_ga(
    population: list,
    n_generations: int,
    registry: "ItemRegistry",
    cfg_data: dict,
    calc_song: dict,
    ref_arrays: dict,
    base_stats_fixed: dict,
    elite_count: int = 2,
    mutation_rate: float = 0.02,
    tournament_k: int = 3,
    color_flags: dict = None,
    status_cb=None,
) -> tuple:
    """
    Run GPU-native GA loop (internal function).

    This runs the GA entirely on GPU, only downloading scores for elitism
    and the final best genome. Eliminates per-generation CPU-GPU round-trips.

    Args:
        population: Initial population as list of genomes (item dicts)
        n_generations: Number of generations to run
        registry: ItemRegistry for encoding/decoding genomes
        cfg_data: Song configuration data
        calc_song: Song calculation context (for timeline)
        ref_arrays: Reference lookup arrays (PP, CM, FM, FT, FF)
        elite_count: Number of elites to preserve per generation
        mutation_rate: Mutation probability
        tournament_k: Tournament size for selection
        color_flags: Dict with is_p_*, is_s_* flags
        status_cb: Optional status callback

    Returns:
        tuple: (best_genome, best_score, best_result_array, all_evaluated)
    """
    if not _GPU_NATIVE_AVAILABLE:
        raise RuntimeError("GPU-native GA not available (missing dependencies)")
    
    n_genomes = len(population)
    n_slots = 9
    
    # Ensure color flags are set
    color_flags = color_flags or {}
    is_p_ft = color_flags.get("is_p_ft", 0)
    is_s_ft = color_flags.get("is_s_ft", 0)
    is_p_ff = color_flags.get("is_p_ff", 0)
    is_s_ff = color_flags.get("is_s_ff", 0)
    is_p_pp = color_flags.get("is_p_pp", 0)
    is_s_pp = color_flags.get("is_s_pp", 0)
    is_p_cm = color_flags.get("is_p_cm", 0)
    is_s_cm = color_flags.get("is_s_cm", 0)
    is_p_fm = color_flags.get("is_p_fm", 0)
    is_s_fm = color_flags.get("is_s_fm", 0)
    is_p_ov = color_flags.get("is_p_ov", 0)
    is_s_ov = color_flags.get("is_s_ov", 0)
    
    total_budget = cfg_data.get("TotalBudget", 90)
    gem_scale_fever = cfg_data.get("GemScaleFever", 3)
    
    # Upload item stats and slot pools (one-time per song)
    gpu_data = registry.to_gpu_arrays()
    gpu_api.ga_upload_item_stats(
        gpu_data["item_stats"],
        gpu_data["slot_start"],
        gpu_data["slot_count"],
    )
    
    # Upload base fixed stats (team buffs + user gems from config)
    # Format: [PP, CM, FM, FT, FF, Beat, Vibe, Rush, Flow, Chill]
    # base_stats_fixed contains team buff bonuses (e.g., T5: +25 PP, +30 to team color)
    base_stats_arr = np.array([
        base_stats_fixed.get("Perfect Points", 0),
        base_stats_fixed.get("Combo Multiplier", 0),
        base_stats_fixed.get("Fever Multiplier", 0),
        base_stats_fixed.get("Fever Time", 0),
        base_stats_fixed.get("Fever Fill Rate", 0),
        base_stats_fixed.get("Beat", 0),
        base_stats_fixed.get("Vibe", 0),
        base_stats_fixed.get("Rush", 0),
        base_stats_fixed.get("Flow", 0),
        base_stats_fixed.get("Chill", 0),
    ], dtype=np.int32)

    # Match scoring.solve_best_fever_combination(): subtract user-fixed gems and static elemental input
    # so the GPU optimizer starts from the same "base stats" as CPU.
    user_pp = int(cfg_data.get("user_pp", 0))
    user_cm = int(cfg_data.get("user_cm", 0))
    user_fm = int(cfg_data.get("user_fm", 0))
    user_ft = int(cfg_data.get("user_ft", 0))
    user_ff = int(cfg_data.get("user_ff", 0))
    static_elem_input = int(cfg_data.get("static_elem_input", 0))
    selected_color = str(cfg_data.get("selected_color", ""))

    if user_pp or user_cm or user_fm or user_ft or user_ff:
        base_stats_arr[0] -= user_pp * GEM_SCALE_NORMAL
        base_stats_arr[1] -= user_cm * GEM_SCALE_NORMAL
        base_stats_arr[2] -= user_fm * GEM_SCALE_FEVER
        base_stats_arr[3] -= user_ft * GEM_SCALE_FEVER
        base_stats_arr[4] -= user_ff * GEM_SCALE_FEVER

        base_stats_arr[9] -= user_pp * GEM_STAT_TO_ELEMENT_SCALE   # Chill
        base_stats_arr[8] -= user_cm * GEM_STAT_TO_ELEMENT_SCALE   # Flow
        base_stats_arr[7] -= user_fm * GEM_STAT_TO_ELEMENT_SCALE   # Rush
        base_stats_arr[5] -= user_ft * GEM_STAT_TO_ELEMENT_SCALE   # Beat
        base_stats_arr[6] -= user_ff * GEM_STAT_TO_ELEMENT_SCALE   # Vibe

    if static_elem_input and selected_color:
        color_to_idx = {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}
        idx = color_to_idx.get(selected_color)
        if idx is not None:
            base_stats_arr[idx] -= static_elem_input * ELEMENTAL_GEM_SCALE
    gpu_api.ga_upload_base_fixed_stats(base_stats_arr)

    # NOTE: Timeline grid is already precomputed by caller (solve_coevolution_genetic)
    # No need to re-upload here - GPU fields persist across calls

    # Encode and upload initial population
    pop_ids = registry.encode_population(population)
    gpu_api.ga_upload_population_indices(pop_ids, n_slots=n_slots)
    gpu_api.ga_seed_rng(n_genomes, seed=42)
    
    # CPU-side best tracking (faster than GPU-side for this use case)
    best_score = -1
    best_genome_ids = None
    best_result_row = None  # [score, ft, ff, pp, cm, fm, ov] - gem allocation for best genome
    results_snapshot = None  # Downloaded with pop_snapshot to avoid race condition

    # --- ISLAND MODEL SETUP ---
    # Partition population into islands (contiguous index ranges)
    num_islands = min(GPU_GA_NUM_ISLANDS, n_genomes // 10)  # At least 10 per island
    if num_islands < 1:
        num_islands = 1
    island_size = n_genomes // num_islands
    
    # Island boundaries: island i owns indices [island_start[i], island_start[i+1])
    island_starts = [i * island_size for i in range(num_islands)]
    island_starts.append(n_genomes)  # Sentinel for last island end
    
    print(f"  >> Island Model: {num_islands} islands, ~{island_size} genomes each")

    # Track population snapshot - only downloaded when best improves or during migrations
    pop_snapshot = None
    pop_snapshot_gen = -1  # Generation when pop_snapshot was taken (-1 = invalid)

    # Main GPU-native GA loop with island migration
    for gen in range(n_generations):
        # Evaluate ENTIRE population on GPU (all islands at once - efficient)
        gpu_api.ga_evaluate_population(
            n_genomes=n_genomes,
            n_slots=n_slots,
            total_budget=total_budget,
            gem_scale_fever=gem_scale_fever,
            song_slot=0,
            is_p_ft=is_p_ft, is_s_ft=is_s_ft,
            is_p_ff=is_p_ff, is_s_ff=is_s_ff,
            is_p_pp=is_p_pp, is_s_pp=is_s_pp,
            is_p_cm=is_p_cm, is_s_cm=is_s_cm,
            is_p_fm=is_p_fm, is_s_fm=is_s_fm,
            is_p_ov=is_p_ov, is_s_ov=is_s_ov,
        )
        
        # Download scores for elitism (small transfer: n_genomes ints)
        scores = gpu_api.ga_download_scores(n_genomes)
        
        # Track global best across all islands
        gen_best_idx = int(np.argmax(scores))
        gen_best_score = int(scores[gen_best_idx])
        
        if gen_best_score > best_score:
            best_score = gen_best_score
            # CRITICAL: Must capture genome IDs AND gem results NOW, not at end of run!
            # ga_next_generation will modify the population, overwriting the genome at this index.
            # Optimization: reuse pop_snapshot if already downloaded this generation
            if pop_snapshot is None or pop_snapshot_gen != gen:
                pop_snapshot = gpu_api.ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots)
                # Also download results (gem allocations) - same race condition applies!
                results_snapshot = gpu_api.ga_download_results(n_genomes)
                pop_snapshot_gen = gen
            best_genome_ids = pop_snapshot[gen_best_idx].copy()
            best_result_row = results_snapshot[gen_best_idx].copy()  # [score, ft, ff, pp, cm, fm, ov]
            
            if status_cb:
                status_cb(f"GPU-Native Gen {gen+1}/{n_generations}: New Best {best_score}")
            elif (gen + 1) % 10 == 0:
                print(f"  >> GPU-Native Gen {gen+1}: Best {best_score}")
        elif (gen + 1) % 10 == 0 and status_cb is None:
            print(f"  >> GPU-Native Gen {gen+1}: Best {gen_best_score} (global {best_score})")
        
        # --- ISLAND-AWARE ELITISM ---
        # Find elite indices PER ISLAND (not global) to maintain island diversity
        elite_indices_list = []
        for isl in range(num_islands):
            isl_start = island_starts[isl]
            isl_end = island_starts[isl + 1]
            isl_scores = scores[isl_start:isl_end]
            # Get top 'elite_count' indices within this island, then offset to global
            isl_top = np.argsort(isl_scores)[-elite_count:] + isl_start
            elite_indices_list.extend(isl_top.tolist())
        
        elite_indices = np.array(elite_indices_list, dtype=np.int32)
        
        # --- MIGRATION PHASE (every GPU_GA_GENS_PER_MIGRATION generations) ---
        is_migration_gen = num_islands > 1 and (gen + 1) % GPU_GA_GENS_PER_MIGRATION == 0
        if is_migration_gen:
            # Download population for migration (reuse if already current)
            if pop_snapshot is None or pop_snapshot_gen != gen:
                pop_snapshot = gpu_api.ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots)
                pop_snapshot_gen = gen
            
            # Ring topology: island i sends to island (i+1) % num_islands
            for isl in range(num_islands):
                src_start = island_starts[isl]
                src_end = island_starts[isl + 1]
                dst_isl = (isl + 1) % num_islands
                dst_start = island_starts[dst_isl]
                
                # Get top MIGRATE_COUNT from source island
                src_scores = scores[src_start:src_end]
                src_top_local = np.argsort(src_scores)[-GPU_GA_MIGRATE_COUNT:]
                src_top_global = src_top_local + src_start
                
                # Copy to destination island (overwrite worst in destination)
                dst_end = island_starts[dst_isl + 1]
                dst_scores = scores[dst_start:dst_end]
                dst_worst_local = np.argsort(dst_scores)[:GPU_GA_MIGRATE_COUNT]
                dst_worst_global = dst_worst_local + dst_start
                
                for mi, (src_idx, dst_idx) in enumerate(zip(src_top_global, dst_worst_global)):
                    pop_snapshot[dst_idx] = pop_snapshot[src_idx].copy()
            
            # Re-upload patched population and invalidate cache
            gpu_api.ga_upload_population_indices(pop_snapshot, n_slots=n_slots)
            pop_snapshot = None  # Invalidate - population changed
            pop_snapshot_gen = -1
        
        # Skip ga_next_generation on final iteration - we don't use that population
        # This saves one generation step per run (30 total per song)
        if gen < n_generations - 1:
            # Run next generation (selection + crossover + mutation + elitism + swap)
            gpu_api.ga_next_generation(
                n_genomes=n_genomes,
                n_slots=n_slots,
                mutation_rate=mutation_rate,
                tournament_k=tournament_k,
                elite_count=len(elite_indices),
                elite_indices=elite_indices,
            )

    # --- END OF GA RUN: Download final population for FG candidate extraction ---
    # NOTE: best_genome_ids and best_result_row were captured when best score was found (during loop)
    # We need pop_snapshot for extracting OTHER candidates.
    pop_snapshot = gpu_api.ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots)
    
    # Decode best genome (already captured correctly during loop)
    best_genome = registry.decode_genome(best_genome_ids) if best_genome_ids is not None else []
    
    # Download final results for FG candidate gem allocations only (not for best genome)
    results = gpu_api.ga_download_results(n_genomes)
    
    # Best result uses the captured best_result_row (has correct gem allocations from when best was found)
    if best_result_row is not None:
        best_result = best_result_row.copy()
    else:
        best_result = np.zeros(7, dtype=np.int32)

    # --- FG CANDIDATE EXTRACTION ---
    # Extract top N unique genomes to seed Force Greats solver (mimics CPU GA output compatibility)
    all_evaluated = []
    if best_genome_ids is not None:
        # Sort by score descending
        # We use a stable sort or simple argsort. Scores are already on CPU.
        top_indices = np.argsort(scores)[::-1]
        
        # Take up to LIMIT candidates (decoding excessively many is slow)
        limit = min(n_genomes, LOADOUTS_PER_SONG_LIMIT * 2) # 2x buffer for duplicates
        top_indices = top_indices[:limit]
        
        # Reuse pop_snapshot from end-of-run download (avoid redundant GPU transfer)
        full_pop_indices = pop_snapshot
        
        for idx in top_indices:
            score_val = int(scores[idx])
            # Skip zero-score garbage
            if score_val <= 0:
                continue

            genome_ids = full_pop_indices[idx]
            genome = registry.decode_genome(genome_ids)
            
            # Reconstruct result details
            res_row = results[idx]
            g_ft = int(res_row[1])
            g_ff = int(res_row[2])
            g_pp = int(res_row[3])
            g_cm = int(res_row[4])
            g_fm = int(res_row[5])
            g_ov = int(res_row[6])

            # Reconstruct full Data object for Force Greats compatibility
            # 1. Sum base item stats
            current_stats = base_stats_fixed.copy()
            for item in genome:
                for k, v in item.items():
                    if k not in SKIP_ITEM_KEYS:
                        current_stats[k] = current_stats.get(k, 0) + v

            # 2. Add Gem Stats
            current_stats["Perfect Points"] = current_stats.get("Perfect Points", 0) + g_pp * GEM_SCALE_NORMAL
            current_stats["Combo Multiplier"] = current_stats.get("Combo Multiplier", 0) + g_cm * GEM_SCALE_NORMAL
            current_stats["Fever Multiplier"] = current_stats.get("Fever Multiplier", 0) + g_fm * GEM_SCALE_FEVER
            current_stats["Fever Time"] = current_stats.get("Fever Time", 0) + g_ft * GEM_SCALE_FEVER
            current_stats["Fever Fill Rate"] = current_stats.get("Fever Fill Rate", 0) + g_ff * GEM_SCALE_FEVER

            current_stats["Chill"] = current_stats.get("Chill", 0) + g_pp * GEM_STAT_TO_ELEMENT_SCALE
            current_stats["Flow"] = current_stats.get("Flow", 0) + g_cm * GEM_STAT_TO_ELEMENT_SCALE
            current_stats["Rush"] = current_stats.get("Rush", 0) + g_fm * GEM_STAT_TO_ELEMENT_SCALE
            current_stats["Beat"] = current_stats.get("Beat", 0) + g_ft * GEM_STAT_TO_ELEMENT_SCALE
            current_stats["Vibe"] = current_stats.get("Vibe", 0) + g_ff * GEM_STAT_TO_ELEMENT_SCALE

            sel_color = cfg_data.get("selected_color", "")
            if sel_color:
                current_stats[sel_color] = current_stats.get(sel_color, 0) + g_ov * ELEMENTAL_GEM_SCALE

            data_obj = {
                "Score": score_val,
                "FT": g_ft,
                "FF": g_ff,
                "GemCounts": {
                    "Perfect Points": g_pp,
                    "Combo Multiplier": g_cm,
                    "Fever Multiplier": g_fm,
                    "Element Overflow": g_ov,
                },
                "Stats": current_stats,
                "Selected Element": sel_color,
                "BaseScore": score_val
            }
            
            cand_data = {
                "Score": score_val,
                "BaseScore": score_val, # GPU GA only calculates BaseScore
                "Genome": genome,
                "Gear": genome[:6],
                "Minis": genome[6:9],
                "GearNames": [g.get("Name", "None") for g in genome[:6]],
                "MiniNames": [m.get("Name", "None") for m in genome[6:9]],
                "Data": data_obj,
                "Details": {
                    "FeverGems": g_ft,
                    "FeverFillGems": g_ff,
                    "PP": g_pp,
                    "CM": g_cm,
                    "FM": g_fm,
                    "OV": g_ov,
                }
            }
            all_evaluated.append(cand_data)
            
            # Stop if we have enough
            if len(all_evaluated) >= LOADOUTS_PER_SONG_LIMIT:
                break
    
    return best_genome, best_score, best_result, all_evaluated



def solve_coevolution_genetic(
    cfg,
    base_stats_fixed,
    paths,
    calc_song,
    ref_arrays,
    all_gears,
    all_minis,
    gears_by_name,
    minis_by_name,
    optimize_gear=True,
    optimize_minis=True,
    fixed_gear=None,
    fixed_minis=None,
    ga_depth=75,
    db_seed=None,
    ga_settings=None,
    status_cb=None,
    executor=None,
    known_loadouts=None,
):
    """
    Main genetic algorithm solver for gear and mini co-evolution.

    Features:
    - Multi-start restarts for better global search
    - Memetic local search on elite candidates
    - Deep mining: extends search when cache hits indicate known territory
    - Dynamic mutation rate based on stagnation
    - Polishing phase at end with exhaustive local search

    Args:
        cfg: Configuration object
        base_stats_fixed: Fixed base stats dictionary
        paths: Path configuration
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays
        all_gears: List of all gear items
        all_minis: List of all mini items
        gears_by_name: Dict mapping gear names to gear objects
        minis_by_name: Dict mapping mini names to mini objects
        optimize_gear: Whether to optimize gear (vs fixed)
        optimize_minis: Whether to optimize minis (vs fixed)
        fixed_gear: Fixed gear loadout if not optimizing
        fixed_minis: Fixed minis if not optimizing
        ga_depth: Total generations across all runs
        db_seed: Previous best loadout from database
        ga_settings: GA configuration settings
        status_cb: Optional status callback function
        executor: Optional process pool executor for parallel evaluation
        known_loadouts: Dict of known loadouts from database

    Returns:
        tuple: (best_data, best_gear, best_minis, None, [], [], all_evaluated)
    """
    # Caches are now cleared in process_song_task, but clearing here is safe redundancy.
    GEM_SOLVER_CACHE.clear()
    FG_CACHE.clear()
    FEVER_TIMELINE_CACHE.clear()

    print("\n=== STARTING GENETIC ALGORITHM SOLVER ===")
    print(f"Configuration: GearOptimization={optimize_gear}, MiniOptimization={optimize_minis}")

    ga_settings = ga_settings or GASettings.from_cfg(cfg)

    p_color = calc_song["metadata"].get("Primary Color", "Rush")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    selected_color = p_color  # For overflow gems (could be customized per loadout)

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    # Initialize pools and apply dominance pruning
    gear_pool, mini_pool, total_before, total_after, whitelisted_minis = initialize_pools(
        all_gears, all_minis, p_color, slots, s_color=s_color
    )
    if gear_pool is None:
        print(f"[GA Error] initialize_pools failed for song {calc_song['metadata'].get('Song Name', 'Unknown')}")
        return None, [], [], None, [], [], []
    
    if whitelisted_minis:
        print(f"[GA] Force-including {len(whitelisted_minis)} whitelisted minis in initialization.")

    # Build configuration data
    # Read GPU mode setting from config
    use_gpu_mode = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=False) if hasattr(cfg, 'getboolean') else False
    use_gpu_native = cfg.getboolean("IterationEngine", "GPU_Native_GA", fallback=True) if hasattr(cfg, 'getboolean') else True
    
    # FG fitness heuristic was removed: GA always optimizes true base score (all perfects).
    # The FG finder separately evaluates loadouts with FG configs to find the best FG score.
    if use_gpu_mode:
        print(f"[GPU] GPU_Mode enabled (Native GA: {use_gpu_native})")
    

    cfg_data = {
        "selected_color": selected_color,
        "use_gpu": use_gpu_mode,
        "use_gpu_native": use_gpu_native,

        "user_ft": safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0)),
        "user_ff": safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0)),
        "user_pp": safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0)),
        "user_cm": safe_int(
            cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0)
        ),
        "user_fm": safe_int(
            cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0)
        ),
        "static_elem_input": safe_int(
            cfg.get("ElementalGems", selected_color, fallback=0)
        ),
    }

    # --- GPU-NATIVE GA PATH ---
    # If using GPU mode, bypass the entire CPU loop mechanism.
    if cfg_data.get("use_gpu", False) and cfg_data.get("use_gpu_native", True) and _GPU_NATIVE_AVAILABLE:
        print("\n=== RUNNING GPU-NATIVE GENETIC ALGORITHM ===")
        print(f"  Population: {GA_POPULATION_SIZE}, Generations: {ga_depth}")

        # CRITICAL: Upload GPU prerequisites for evaluation
        from .taichi_gem.api import load_ref_arrays, precompute_timeline_gpu

        # 1. Load reference bonus lookup tables (required by optimize_core_device)
        load_ref_arrays(ref_arrays)

        # 2. Precompute timeline grid (required by solve_genomes_with_ftff_kernel)
        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0)

        # 3. Create Registry
        registry = ItemRegistry(gear_pool, mini_pool, slots)

        # 4. Create simple rank caches for genome factory (not needed for random genomes, but required by function signature)
        # GPU-native GA uses random initialization, not heuristic, so these won't be used
        gear_rank_cache = {s: gear_pool[s] for s in slots}  # Just use full pools
        mini_rank_cache = mini_pool

        # 5. Build explicit factories for initial population
        # We reuse the existing factories to robustly create valid random genomes
        (
            create_random_genome,
            create_heuristic_genome,
            reconstruct_genome_from_db_list,
            build_seed_list_from_record,
            mutate_genome_once,
        ) = create_genome_functions(
            gear_pool,
            mini_pool,
            gear_rank_cache,
            mini_rank_cache,
            gears_by_name,
            minis_by_name,
            slots,
            optimize_gear,
            optimize_minis,
            fixed_gear,
            fixed_minis,
        )

        # 6. Create initial population functions (created once)
        # We reuse the existing factories to robustly create valid random genomes

        # --- MULTI-START LOOP ---
        num_runs = ga_settings.multi_start
        # Match CPU logic: split total depth across runs (Micro-GA strategy)
        # or use full depth if multi-start is 1.
        gens_per_run = max(1, (ga_depth + num_runs - 1) // num_runs)
        
        print(f"  Multi-start runs: {num_runs} (generations per run: {gens_per_run})")

        best_global_score = -1
        best_global_genome = None
        best_global_res_arr = None
        all_evaluated_global = []

        for run_idx in range(num_runs):
            print(f"  >> GPU GA Run {run_idx + 1}/{num_runs}...")
            
            # Re-initialize population for each run to get fresh random start
            initial_pop = build_initial_population(
                create_random_genome,
                create_heuristic_genome,
                reconstruct_genome_from_db_list,
                build_seed_list_from_record,
                mutate_genome_once,
                db_seed,
                ga_settings,
                fixed_gear,
                fixed_minis,
                force_db_seed=False,
            )

            # Run GPU-Native GA
            run_best_genome, run_best_score, run_best_res_arr, run_evaluated = _run_gpu_native_ga(
                population=initial_pop,
                n_generations=gens_per_run,
                registry=registry,
                cfg_data=cfg_data,
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                base_stats_fixed=base_stats_fixed,
                elite_count=GA_ELITISM,
                mutation_rate=GA_MUTATION_RATE,
                # Use color flags for correct p_val/s_val calculation
                color_flags={
                    "is_p_ft": 1 if p_color == "Beat" else 0,
                    "is_s_ft": 1 if s_color == "Beat" else 0,
                    "is_p_ff": 1 if p_color == "Vibe" else 0,
                    "is_s_ff": 1 if s_color == "Vibe" else 0,
                    "is_p_pp": 1 if p_color == "Chill" else 0,
                    "is_s_pp": 1 if s_color == "Chill" else 0,
                    "is_p_cm": 1 if p_color == "Flow" else 0,
                    "is_s_cm": 1 if s_color == "Flow" else 0,
                    "is_p_fm": 1 if p_color == "Rush" else 0,
                    "is_s_fm": 1 if s_color == "Rush" else 0,
                    "is_p_ov": 1 if selected_color == p_color else 0,
                    "is_s_ov": 1 if selected_color == s_color else 0,
                },
                status_cb=status_cb,
            )
            
            # Aggregate candidates
            all_evaluated_global.extend(run_evaluated)
            
            # Update global best
            if run_best_score > best_global_score:
                best_global_score = run_best_score
                best_global_genome = run_best_genome
                best_global_res_arr = run_best_res_arr

        # 8. Format results to match expected return signature
        # Use simple fallback if no valid genome found (shouldn't happen)
        if best_global_genome is None:
             # Should practically never happen unless 0 runs
             best_global_genome = initial_pop[0]
             best_global_score = 0
             best_global_res_arr = [0]*7

        best_gear = best_global_genome[:6]
        best_minis = best_global_genome[6:9]
        
        best_data = {
            "Score": best_global_score,
            "BaseScore": best_global_score,
            "Genome": best_global_genome,
            "Gear": best_gear,
            "Minis": best_minis,
            "GearNames": [g.get("Name", "None") for g in best_gear],
            "MiniNames": [m.get("Name", "None") for m in best_minis],
            # FT/FF at root level for build_details() compatibility
            "FT": int(best_global_res_arr[1]),
            "FF": int(best_global_res_arr[2]),
            "GemCounts": {
                "Perfect Points": int(best_global_res_arr[3]),
                "Combo Multiplier": int(best_global_res_arr[4]),
                "Fever Multiplier": int(best_global_res_arr[5]),
                "Element Overflow": int(best_global_res_arr[6]),
            },
            "Selected Element": selected_color,  # For correct overflow gem labeling
            # Reconstruct result details from kernel output
            # [score, ft, ff, pp, cm, fm, ov]
            "Details": {
                "FeverGems": int(best_global_res_arr[1]),
                "FeverFillGems": int(best_global_res_arr[2]),
                "PP": int(best_global_res_arr[3]),
                "CM": int(best_global_res_arr[4]),
                "FM": int(best_global_res_arr[5]),
                "OV": int(best_global_res_arr[6]),
            }
        }
        
        print(f"=== GPU-NATIVE GA COMPLETE: Best Score {best_global_score} ===")
        
        # Deduplicate all_evaluated to prevent duplicate loadouts from multiple runs
        # Key by tuple of names (Gear + Minis)
        unique_evaluated = []
        seen_hashes = set()
        
        for cand in all_evaluated_global:
            # Create a stable hashable key from gear names and mini names
            # Genome usually has 9 dicts.
            key_parts = []
            for item in cand.get("Genome", []):
                key_parts.append(item.get("Name", ""))
            
            cand_hash = tuple(key_parts)
            if cand_hash not in seen_hashes:
                seen_hashes.add(cand_hash)
                unique_evaluated.append(cand)

        # Sort by score descending and truncate to limit
        unique_evaluated.sort(key=lambda c: c.get("Score", 0), reverse=True)
        unique_evaluated = unique_evaluated[:LOADOUTS_PER_SONG_LIMIT]

        return best_data, best_gear, best_minis, None, [], [], unique_evaluated

    # --- MEMETIC GA PARAMETERS (configurable from [IterationEngine]) ---
    if ga_settings.memetic_elites > 0 and ga_settings.memetic_steps > 0:
        print(
            f"[Memetic GA] Enabled: elites={ga_settings.memetic_elites}, "
            f"steps={ga_settings.memetic_steps}, top_gear={ga_settings.memetic_top_gear}, "
            f"top_minis={ga_settings.memetic_top_minis}"
        )
    else:
        print("[Memetic GA] Disabled (elites or steps <= 0).")

    # Create evaluation functions and caches
    cache_hits_tracker = [0]  # Mutable container for tracking cache hits
    (
        score_candidate,
        genome_key,
        check_persistent_cache,
        evaluate_genome_local,
        evaluation_cache,
        batch_evaluator,
    ) = create_evaluation_functions(
        p_color,
        base_stats_fixed,
        cfg_data,
        calc_song,
        ref_arrays,
        known_loadouts,
        cache_hits_tracker,
        getattr(ga_settings, "heuristic_mode", "modern"),
    )

    # Build ranked candidate caches
    gear_rank_max = 40  # expanded to help find items heuristic underranks
    mini_rank_max = 40  # widen minis to escape local minima
    gear_rank_cache = {
        s: sorted(gear_pool[s], key=score_candidate, reverse=True)[:gear_rank_max]
        for s in slots
    }
    sorted_minis = sorted(mini_pool, key=score_candidate, reverse=True)
    mini_rank_cache = sorted_minis[:mini_rank_max]

    # Create genome factory functions
    (
        create_random_genome,
        create_heuristic_genome,
        reconstruct_genome_from_db_list,
        build_seed_list_from_record,
        mutate_genome_once,
    ) = create_genome_functions(
        gear_pool,
        mini_pool,
        gear_rank_cache,
        mini_rank_cache,
        gears_by_name,
        minis_by_name,
        slots,
        optimize_gear,
        optimize_minis,
        fixed_gear,
        fixed_minis,
    )

    # Create local search functions
    run_local_search, polish_best_genome, memetic_local_search, batch_memetic_local_search = create_local_search_function(
        evaluate_genome_local,
        batch_evaluator,
        gear_rank_cache,
        mini_rank_cache,
        mini_pool,
        gear_pool,
        slots,
        optimize_gear,
        optimize_minis,
        ga_settings=ga_settings,
    )

    # Setup multi-start runs
    num_runs = ga_settings.multi_start
    gens_per_run = max(1, (ga_depth + num_runs - 1) // num_runs)
    print(f"Multi-start runs: {num_runs} (generations per run: {gens_per_run})")

    best_global_score = -1
    best_global_genome = []
    best_global_data = {}

    # Store each run's best for comparison at the end
    run_results = []  # List of (score, genome, data) tuples

    # Cross-run elite sharing: DISABLED - each run is independent now
    # global_elites = []

    # Soft non-regression guard:
    # Evaluate DB seed once up-front and cache it, but DON'T lock it as global best.
    # This allows the GA to explore freely without being anchored to the DB score.
    # We only use the DB seed for non-regression comparison at the END.
    db_seed_score = -1
    db_seed_genome = None
    db_seed_data = None
    if db_seed:
        try:
            seed_list = build_seed_list_from_record(db_seed)
            if seed_list:
                seed_genome = reconstruct_genome_from_db_list(seed_list)
                seed_res = worker_coevolution_evaluate(
                    (seed_genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
                )
                evaluation_cache[genome_key(seed_genome)] = seed_res
                # Use BaseScore (true score) for DB comparison. (Score is the GA fitness score
                # and is currently the same as BaseScore.)
                db_seed_score = seed_res.get("BaseScore") or seed_res["Score"]
                db_seed_genome = seed_genome
                db_seed_data = seed_res["Data"]
                print(
                    f" >> [Evolution] DB seed baseline (soft): {db_seed_score}"
                )
        except Exception as exc:
            print(f" >> [Evolution] Warning: failed to evaluate DB seed: {exc}")

    # Read Deep Mining config
    if ga_settings.deep_mining_enabled:
        print(" >> [Deep Mining] Enabled: Will extend search based on cache hits.")
    else:
        print(" >> [Deep Mining] Disabled: Fixed generation count.")

    # Main multi-start GA loop
    for run_idx in range(num_runs):
        print(f"\n--- GA Run {run_idx + 1}/{num_runs} ---")
        if status_cb:
            status_cb(f"Run {run_idx + 1}/{num_runs} starting")

        # Initialize population
        population = build_initial_population(
            create_random_genome,
            create_heuristic_genome,
            reconstruct_genome_from_db_list,
            build_seed_list_from_record,
            mutate_genome_once,
            db_seed,
            ga_settings,
            fixed_gear,
            fixed_minis,
            force_db_seed=False,  # Use db_seed_prob probability instead of guaranteed injection
        )

        # Track progress within THIS run (not global best).
        # This avoids "false stagnation" when the global best is already locked.
        best_run_score = -1
        last_improvement_gen = 0

        # Reset global best at start of each run to ensure independence
        # The best across all runs will be selected after all runs complete
        best_global_score = -1
        best_global_genome = []
        best_global_data = {}

        base_stagnation_limit = max(8, gens_per_run // 2)
        explore_stagnation_limit = max(8, gens_per_run // 3)
        mutation_rate = GA_MUTATION_RATE

        # Dynamic generation limit based on cache hits
        current_run_gens = gens_per_run
        cache_hits_tracker[0] = 0  # Reset for each run
        generation = 0
        current_mutation_rate = mutation_rate

        # Evolution loop
        while generation < current_run_gens:
            generation += 1

            # Evaluate population in parallel
            results = evaluate_population_parallel(
                population,
                genome_key,
                evaluation_cache,
                check_persistent_cache,
                base_stats_fixed,
                cfg_data,
                calc_song,
                ref_arrays,
                executor,
                cache_hits_tracker,
                use_gpu_batch=cfg_data.get("use_gpu", False),
            )

            # Track best candidate (global best with tie-awareness)
            def consider_candidate(cand):
                nonlocal best_global_score, best_global_genome, best_global_data
                cand_score = cand["Score"]
                cand_genome = cand["Genome"]
                cand_data = cand["Data"]
                # CRITICAL: Inject BaseScore into cand_data so build_db_payload can access it.
                # The outer wrapper has BaseScore (true score), but cand_data (inner dict) doesn't.
                # Without this, build_db_payload uses cand_data["Score"] which may be outdated.
                if "BaseScore" in cand:
                    cand_data["BaseScore"] = cand["BaseScore"]
                best_key = genome_key(best_global_genome) if best_global_genome else None
                cand_key = genome_key(cand_genome)

                if cand_score > best_global_score:
                    best_global_score = cand_score
                    best_global_genome = cand_genome
                    best_global_data = cand_data
                    return 2  # strict improvement

                if cand_score == best_global_score and cand_key != best_key:
                    # Same score, different loadout: treat as a variant, not an improvement.
                    best_global_genome = cand_genome
                    best_global_data = cand_data
                    return 1  # tie variant

                return 0

            # --- MEMETIC GA STEP: local search on top elites ---
            if ga_settings.memetic_elites > 0 and ga_settings.memetic_steps > 0:
                elite_count = min(ga_settings.memetic_elites, len(results))
                
                # BATCHED PATH: Process all elites simultaneously
                # This reduces kernel launch overhead by packing all neighbors into fewer batches.
                seed_genomes = [results[i]["Genome"] for i in range(elite_count)]
                improved_results = batch_memetic_local_search(
                    seed_genomes,
                    ga_settings.memetic_steps,
                    ga_settings.memetic_top_gear,
                    ga_settings.memetic_top_minis,
                )
                
                # Update population with improved versions if score increased
                for i, improved_res in enumerate(improved_results):
                    if improved_res["Score"] > results[i]["Score"]:
                        results[i] = improved_res
                
                # Resort after memetic improvements
                results.sort(key=lambda x: x["Score"], reverse=True)

            # Best candidate AFTER memetic (this is the generation winner)
            best_cand = results[0]

            # Update run-best tracking (used for stagnation handling)
            if best_cand["Score"] > best_run_score:
                best_run_score = best_cand["Score"]
                last_improvement_gen = generation
                mutation_rate = GA_MUTATION_RATE

            promote_status = consider_candidate(best_cand)
            if promote_status == 2:
                m_names = best_cand["MiniNames"]
                print(
                    f"  >> Gen {generation} (Run {run_idx + 1}): New Best {best_global_score} (Minis: {m_names})"
                )
                if status_cb:
                    status_cb(
                        f"Run {run_idx + 1}/{num_runs} Gen {generation}: New Best {best_global_score}"
                    )
            elif promote_status == 1:
                # Tie score, but a different loadout at the same global score.
                # Don't call it a "new best" to avoid confusing plateaus with improvements.
                if generation % 10 == 0:
                    m_names = best_cand["MiniNames"]
                    print(
                        f"  >> Gen {generation} (Run {run_idx + 1}): "
                        f"BestVariant {best_global_score} (Minis: {m_names})"
                    )
            else:
                if generation % 10 == 0:
                    print(
                        f"  >> Gen {generation} (Run {run_idx + 1}): "
                        f"BestInRun {best_cand['Score']} | GlobalBest {best_global_score}"
                    )
                    if status_cb:
                        status_cb(
                            f"Run {run_idx + 1}/{num_runs} Gen {generation}: "
                            f"BestInRun {best_cand['Score']} | GlobalBest {best_global_score}"
                        )

            # Generate next generation via crossover and mutation
            next_gen = perform_crossover_mutation(
                results,
                create_random_genome,
                mini_pool,
                gear_pool,
                slots,
                optimize_gear,
                optimize_minis,
                fixed_minis,
                current_mutation_rate,
                global_elites=None,  # Cross-run sharing disabled - runs are independent
            )

            population = next_gen
            next_gen = None  # Break reference to help GC

            # Compute dynamic mutation rate and generation limit
            current_mutation_rate, current_run_gens = compute_dynamic_mutation(
                mutation_rate,
                cache_hits_tracker[0],
                generation,
                current_run_gens,
                gens_per_run,
                ga_settings,
            )

            # Cache-hit driven exploration boost is only applied when DeepMining is enabled.
            total_evals_so_far = generation * GA_POPULATION_SIZE
            hit_ratio = cache_hits_tracker[0] / max(1, total_evals_so_far)
            exploration_boost = min(0.2, hit_ratio * 0.5) if ga_settings.deep_mining_enabled else 0.0

            # Handle stagnation
            # If this run is far below the global best, trigger diversity injection sooner
            # to avoid wasting many generations in a clearly inferior basin.
            stagnation_limit = base_stagnation_limit
            if best_global_score > 0 and best_run_score > 0 and best_run_score < best_global_score:
                stagnation_limit = explore_stagnation_limit

            population, mutation_rate, last_improvement_gen = update_mutation_and_diversity(
                population,
                results,
                generation,
                last_improvement_gen,
                stagnation_limit,
                mutation_rate,
                create_random_genome,
                create_heuristic_genome,
                run_idx,
                current_mutation_rate,
                exploration_boost,
                mini_pool=mini_pool,
                gear_pool=gear_pool,
                slots=slots,
                optimize_gear=optimize_gear,
                optimize_minis=optimize_minis,
            )

        # Cross-run elite sharing: add this run's best to the global elite pool.
        # This makes discoveries available for crossover in subsequent runs.
        if best_run_score > 0:
            # Store this run's best result (using heuristic Score for GA selection)
            run_best_genome = results[0]["Genome"] if results else None
            run_best_score = results[0]["Score"] if results else -1
            run_best_data = results[0]["Data"] if results else {}
            if run_best_genome and run_best_score > 0:
                run_results.append((run_best_score, run_best_genome, run_best_data))

    # Select the best result across all independent runs (using true base scores)
    for run_score, run_genome, run_data in run_results:
        if run_score > best_global_score:
            best_global_score = run_score
            best_global_genome = run_genome
            best_global_data = run_data

    # Polish best genome with exhaustive local search
    if best_global_genome:
        polished_result, polished_genome = polish_best_genome(best_global_genome)

        # If result was cached, re-evaluate fully to get all details
        if polished_result.get("_cached"):
            polished_result = worker_coevolution_evaluate(
                (polished_genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
            )

        # Use Score for GA selection (BaseScore only for DB comparisons)
        polished_score = polished_result["Score"]

        if polished_score > best_global_score:
            best_global_score = polished_score
            best_global_data = polished_result["Data"]
            best_global_genome = polished_genome

    # Soft non-regression guard: If GA's best is worse than DB seed, fall back.
    # This ensures we never regress while still allowing free exploration.
    # Compare using true base score.
    ga_true_score = (
        best_global_data.get("BaseScore", best_global_data.get("Score", 0))
        if best_global_data
        else best_global_score
    )
    if db_seed_score > ga_true_score and db_seed_genome:
        print(f" >> [Evolution] GA best ({ga_true_score}) < DB seed ({db_seed_score}); using DB seed.")
        best_global_score = db_seed_score
        best_global_genome = db_seed_genome
        best_global_data = db_seed_data

    # CRITICAL: Re-evaluate if best_global_data is missing GemCounts (from DB cache path).
    # This ensures the final result always has complete gem allocation details for display.
    if best_global_genome and best_global_data and "GemCounts" not in best_global_data:
        full_result = worker_coevolution_evaluate(
            (best_global_genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
        )
        best_global_data = full_result["Data"]

    best_gear = best_global_genome[:6] if best_global_genome else []
    best_minis = best_global_genome[6:] if best_global_genome else []

    # Return all unique evaluated loadouts from the cache
    all_evaluated = list(evaluation_cache.values())

    # Memory leak fix: Clear cache immediately after extraction
    # This prevents the cache from lingering until function exit
    evaluation_cache.clear()

    # Memory leak fix: Clear all generation-scoped data before returning
    population = None
    results = None
    
    if not best_global_data:
        print(f"[GA Error] GA completed but found no valid candidates (best_global_score={best_global_score})")

    return (
        best_global_data if best_global_data else None,
        best_gear,
        best_minis,
        None,
        [],
        [],
        all_evaluated,  # All unique loadouts evaluated by GA (capped before DB persistence)
    )
