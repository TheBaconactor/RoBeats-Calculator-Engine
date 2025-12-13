"""
Helper functions for genetic algorithm operations.

This module contains helper functions extracted from solve_coevolution_genetic()
to improve code modularity and maintainability. These functions handle:
- Pool initialization and pruning
- Genome factory functions
- Evaluation and caching
- Local search operations
- Population initialization
- Crossover and mutation
- Parallel evaluation
- Diversity and stagnation handling
"""
import os
import random

# Support deterministic testing via GA_SEED environment variable
_GA_SEED = os.environ.get("GA_SEED")
if _GA_SEED is not None:
    _GA_SEED = int(_GA_SEED)
    random.seed(_GA_SEED)

from ..core.constants import GA_POPULATION_SIZE, GA_MUTATION_RATE, GA_MUTATION_RATE_MAX, GA_ELITISM
from ..core.utils import prune_dominated_gear
from ..data.database import get_loadout_hash
from ..solver.scoring import worker_coevolution_evaluate, batch_evaluate_genomes


def initialize_pools(all_gears, all_minis, p_color, slots):
    """
    Initialize and prune gear and mini pools.

    Creates per-slot gear pools and filters minis by primary color.
    Applies dominance pruning to remove strictly inferior gear items.

    Args:
        all_gears: List of all gear items
        all_minis: List of all mini items
        p_color: Primary color for mini filtering
        slots: List of gear slot names

    Returns:
        tuple: (gear_pool, mini_pool, total_before, total_after)
            - gear_pool: Dict mapping slot names to lists of gear
            - mini_pool: List of valid minis
            - total_before: Total gear count before pruning
            - total_after: Total gear count after pruning
    """
    # Filter minis by primary color
    mini_pool = [m for m in all_minis if m.get(p_color, 0) > 0]
    if not mini_pool:
        print("No valid minis found (Primary Color check).")
        return None, [], 0, 0

    # Initialize gear pools by slot
    gear_pool = {s: [] for s in slots}
    for g in all_gears:
        if g["type"] in gear_pool:
            gear_pool[g["type"]].append(g)

    # Apply dominance pruning per slot to remove strictly inferior gear
    total_before = sum(len(gear_pool[s]) for s in slots)
    for s in slots:
        gear_pool[s] = prune_dominated_gear(gear_pool[s])
    total_after = sum(len(gear_pool[s]) for s in slots)

    if total_before > total_after:
        print(f"[Dominance Pruning] Removed {total_before - total_after} dominated gear items.")

    return gear_pool, mini_pool, total_before, total_after


def create_genome_functions(
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
):
    """
    Create genome factory and manipulation functions.

    Returns closures for creating random/heuristic genomes, reconstructing from DB,
    building seed lists, and mutating genomes.

    Args:
        gear_pool: Dict mapping slot names to gear lists
        mini_pool: List of valid minis
        gear_rank_cache: Dict mapping slots to ranked gear lists
        mini_rank_cache: Ranked list of minis
        gears_by_name: Dict mapping gear names to gear objects
        minis_by_name: Dict mapping mini names to mini objects
        slots: List of gear slot names
        optimize_gear: Whether to optimize gear
        optimize_minis: Whether to optimize minis
        fixed_gear: Fixed gear loadout if not optimizing
        fixed_minis: Fixed minis if not optimizing

    Returns:
        tuple: (create_random_genome, create_heuristic_genome,
                reconstruct_genome_from_db_list, build_seed_list_from_record,
                mutate_genome_once)
    """

    def create_random_genome():
        """Create a random genome from available pools."""
        genome = []
        if optimize_gear:
            for s in slots:
                genome.append(random.choice(gear_pool[s]) if gear_pool[s] else {})
        else:
            genome.extend(fixed_gear)

        if optimize_minis:
            if len(mini_pool) >= 3:
                genome.extend(random.sample(mini_pool, 3))
            else:
                genome.extend(random.sample(mini_pool, len(mini_pool)))
                while len(genome) < 9:
                    genome.append({})
        else:
            genome.extend(fixed_minis)
        return genome

    def create_heuristic_genome():
        """Create a genome biased toward high-ranked items."""
        genome = []
        if optimize_gear:
            for s in slots:
                candidates = gear_rank_cache.get(s, [])
                genome.append(random.choice(candidates[:5]) if candidates else {})
        else:
            genome.extend(fixed_gear)

        if optimize_minis:
            # Widen sampling from top 10 to top 25 to improve diversity
            # while still biasing toward high-scoring minis.
            # This helps discover synergistic combinations that don't rank
            # highest individually but score well together.
            sample_pool = mini_rank_cache[:25] if len(mini_rank_cache) >= 25 else mini_rank_cache
            if len(sample_pool) >= 3:
                genome.extend(random.sample(sample_pool, 3))
            else:
                genome.extend(random.sample(mini_pool, 3))
        else:
            genome.extend(fixed_minis)
        return genome

    def reconstruct_genome_from_db_list(db_list):
        """Rebuild full stats from just the names in the DB."""
        r_genome = []
        for i in range(6):
            name = db_list[i] if i < len(db_list) else ""
            if name in gears_by_name:
                r_genome.append(gears_by_name[name])
            else:
                r_genome.append({"Name": "(Empty)", "type": slots[i]})
        for i in range(6, 9):
            if i < len(db_list):
                name = db_list[i]
                if name in minis_by_name:
                    r_genome.append(minis_by_name[name])
                else:
                    r_genome.append({"Name": "(Empty)", "type": "Mini"})
            else:
                r_genome.append({"Name": "(Empty)", "type": "Mini"})
        return r_genome

    def build_seed_list_from_record(record):
        """
        Normalize any stored record into a compact list of names for seeding.
        Handles both dict format (with 'Name' key) and plain string names.
        Priority: legacy loadout -> gear + minis.
        """
        if not record:
            return None

        def extract_name(item):
            """Extract name from either a dict or string."""
            if isinstance(item, dict):
                return item.get("Name", "")
            return str(item) if item else ""

        if "loadout" in record:
            load = record.get("loadout") or []
            if isinstance(load, list):
                return [extract_name(item) for item in load]

        gear_items = record.get("gear") or []
        mini_items = record.get("minis") or []

        if gear_items or mini_items:
            gear_names = [extract_name(g) for g in gear_items]
            mini_names = [extract_name(m) for m in mini_items]
            return gear_names + mini_names
        return None

    def mutate_genome_once(genome):
        """Soft mutation around a seed genome for DB seeding."""
        g = list(genome)
        mutate_idx = random.randint(0, 8)

        if mutate_idx < 6 and optimize_gear:
            slot_type = slots[mutate_idx]
            if gear_pool[slot_type]:
                g[mutate_idx] = random.choice(gear_pool[slot_type])
        elif mutate_idx >= 6 and optimize_minis:
            # Extract current mini names, handling both dict and string formats
            current_mini_names = set()
            for m in g[6:]:
                if isinstance(m, dict):
                    current_mini_names.add(m.get("Name", ""))
                elif m:
                    current_mini_names.add(str(m))
            candidates = [m for m in mini_pool if m["Name"] not in current_mini_names]
            if candidates:
                g[mutate_idx] = random.choice(candidates)

        return g

    return (
        create_random_genome,
        create_heuristic_genome,
        reconstruct_genome_from_db_list,
        build_seed_list_from_record,
        mutate_genome_once,
    )


def create_evaluation_functions(
    p_color,
    base_stats_fixed,
    cfg_data,
    calc_song,
    ref_arrays,
    known_loadouts,
    cache_hits_tracker,
    heuristic_mode="modern",
):
    """
    Create evaluation and caching functions.

    Returns closures for scoring candidates, genome keying, and cache operations.

    Args:
        p_color: Primary color for scoring
        base_stats_fixed: Fixed base stats dictionary
        cfg_data: Configuration data for evaluation
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays
        known_loadouts: Dict of known loadouts from database
        cache_hits_tracker: List [count] for tracking cache hits (mutable)

    Returns:
        tuple: (score_candidate, genome_key, check_persistent_cache,
                evaluate_genome_local, evaluation_cache)
    """

    # Extract secondary color from song metadata
    s_color = None
    if calc_song and calc_song.get("metadata"):
        s_color = calc_song["metadata"].get("Secondary Color")
    
    def score_candidate(x):
        """
        Heuristic scoring used to rank candidate gear/minis before GA search.
        Supports multiple modes via GASettings:
        - modern: base-stats dominant (default)
        - legacy: color-heavy (closer to legacy script behavior)
        - hybrid: take the max(modern, legacy) to keep both benefits
        
        Note: This is NOT the true score function; it's only used to build the
        top-K ranked caches that seed the GA and local search neighborhoods.
        """
        pp = x.get("Perfect Points", 0)
        cm = x.get("Combo Multiplier", 0)
        fm = x.get("Fever Multiplier", 0)
        ft = x.get("Fever Time", 0)
        ff = x.get("Fever Fill Rate", 0)

        primary_val = x.get(p_color, 0) if p_color else 0
        secondary_val = x.get(s_color, 0) if (s_color and s_color != p_color) else 0

        # --- Modern heuristic (base-stats dominant) ---
        modern_base = (pp * 3) + (cm * 3) + (fm * 3) + (ft * 2) + (ff * 2)
        modern_elemental_bonus = (primary_val * 2) + (secondary_val * 1)
        modern_score = modern_base + (modern_elemental_bonus // 2)

        # --- Legacy-like heuristic (color-heavy) ---
        # Mirrors the legacy idea: prioritize primary-color stat strongly while
        # still valuing PP/CM/FM (but not FT/FF).
        legacy_score = (primary_val * 3) + ((pp + cm + fm) * 2) + (secondary_val * 1)

        mode = (heuristic_mode or "modern").strip().lower()
        if mode == "legacy":
            return legacy_score
        if mode == "hybrid":
            return max(modern_score, legacy_score)
        return modern_score

    def genome_key(genome):
        """Generate a unique key for a genome for caching."""
        # Helper to extract name from dict or string
        def get_name(item):
            if isinstance(item, dict):
                return item.get("Name", "")
            return str(item) if item else ""

        # Gear (first 6 slots): order matters because slots are positional.
        gear_names = tuple(get_name(item) for item in genome[:6])
        # Minis (last 3 slots): order-invariant - only the set/multiset matters.
        # Sorting canonicalizes permutations so [A,B,C] and [C,B,A] share a key.
        mini_names = tuple(sorted(get_name(item) for item in genome[6:]))
        return gear_names + mini_names

    evaluation_cache = {}

    def check_persistent_cache(genome):
        """Check if genome exists in persistent database cache."""
        if known_loadouts:
            gear_part = genome[:6]
            mini_part = genome[6:]
            h = get_loadout_hash(gear_part, mini_part)
            if h in known_loadouts:
                entry = known_loadouts[h]

                # DB rows are stored as (score, fg_score, force_data); fall back gracefully
                score = fg_score = force_data = None
                if isinstance(entry, dict):
                    score = entry.get("score")
                    fg_score = entry.get("fg_score")
                    force_data = entry.get("force_data") or entry.get("force_details")
                elif isinstance(entry, (list, tuple)):
                    if len(entry) >= 2:
                        score, fg_score = entry[0], entry[1]
                    if len(entry) >= 3:
                        force_data = entry[2]
                else:
                    # Unknown shape; skip cache usage rather than crashing
                    return None

                if score is None or fg_score is None:
                    return None

                return {
                    "Score": score,
                    "FG_Score": fg_score,
                    "Genome": genome,
                    "Gear": gear_part,
                    "Minis": mini_part,
                    "MiniNames": [
                        m.get("Name", "") if isinstance(m, dict) else str(m) for m in mini_part
                    ],
                    "Data": {
                        "Score": score,
                        "_cached_db": True,
                        "ForceDetails": force_data,
                    },
                    "_cached": True,  # Flag so we force a full re-eval when polishing
                }
        return None

    def evaluate_genome_local(genome):
        """Evaluate a genome with in-memory and persistent caching."""
        k = genome_key(genome)
        if k in evaluation_cache:
            return evaluation_cache[k]

        cached_res = check_persistent_cache(genome)
        if cached_res:
            evaluation_cache[k] = cached_res
            cache_hits_tracker[0] += 1
            return cached_res

        res = worker_coevolution_evaluate(
            (genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
        )
        evaluation_cache[k] = res
        return res

    def batch_evaluator(population):
        """
        Evaluate a batch of genomes using the configured batch settings.
        Falls back to serial evaluation if population is small or GPU disabled.
        """
        if not population:
            return []
            
        return evaluate_population_parallel(
            population,
            genome_key,
            evaluation_cache,
            check_persistent_cache,
            base_stats_fixed,
            cfg_data,
            calc_song,
            ref_arrays,
            None, # No executor needed for GPU path
            cache_hits_tracker,
            use_gpu_batch=cfg_data.get("use_gpu", False)
        )

    return (
        score_candidate,
        genome_key,
        check_persistent_cache,
        evaluate_genome_local,
        evaluation_cache,
        batch_evaluator,
    )


def create_local_search_function(
    evaluate_genome_local,
    batch_evaluator,
    gear_rank_cache,
    mini_rank_cache,
    mini_pool,
    gear_pool,
    slots,
    optimize_gear,
    optimize_minis,
):
    """
    Create local search function for memetic GA and polishing.

    Args:
        evaluate_genome_local: Function to evaluate single genome (fallback)
        batch_evaluator: Function to evaluate batch of genomes
        gear_rank_cache: Dict mapping slots to ranked gear lists
        mini_rank_cache: Ranked list of minis
        mini_pool: List of valid minis
        gear_pool: Dict mapping slots to all gear items (full pool)
        slots: List of gear slot names
        optimize_gear: Whether to optimize gear
        optimize_minis: Whether to optimize minis

    Returns:
        tuple: (run_local_search, polish_best_genome, memetic_local_search)
    """

    def run_local_search(start_genome, max_steps, top_k_gear, top_k_minis, is_polishing=False):
        """
        Unified local search logic using Batch Evaluation (Best Improvement).
        Generates all neighbors, evaluates them in parallel, and picks the best.
        """
        best_genome = list(start_genome)
        best_result = evaluate_genome_local(best_genome)
        best_score = best_result["Score"]

        # Pre-trim candidate lists
        local_gear_rank = {
            s: gear_rank_cache.get(s, [])[:top_k_gear] for s in slots
        }
        local_mini_rank = mini_rank_cache[:top_k_minis]

        steps = 0
        limit = 999999 if is_polishing else max_steps

        while steps < limit:
            candidates = []
            
            # 1. Generate Gear Candidates
            if optimize_gear:
                for idx, slot in enumerate(slots):
                    curr_item = best_genome[idx]
                    current_name = curr_item.get("Name") if isinstance(curr_item, dict) else str(curr_item) if curr_item else ""
                    
                    for cand in local_gear_rank.get(slot, []):
                        if cand.get("Name") == current_name:
                            continue
                        
                        # Create candidate genome
                        trial = best_genome[:]
                        trial[idx] = cand
                        candidates.append(trial)

            # 2. Generate Mini Candidates
            if optimize_minis:
                # Extract existing mini names
                existing = set()
                for m in best_genome[6:]:
                    if isinstance(m, dict):
                        existing.add(m.get("Name", ""))
                    elif m:
                        existing.add(str(m))
                        
                for idx in range(6, 9):
                    curr_item = best_genome[idx]
                    curr_name = curr_item.get("Name") if isinstance(curr_item, dict) else str(curr_item) if curr_item else ""
                    
                    for cand in local_mini_rank:
                        c_name = cand.get("Name")
                        if c_name == curr_name:
                            continue
                        if c_name in existing:
                            continue
                            
                        trial = best_genome[:]
                        trial[idx] = cand
                        candidates.append(trial)

            if not candidates:
                break

            # 3. Batch Evaluate All Candidates
            # This uses the GPU batch path if available!
            candidate_results = batch_evaluator(candidates)
            
            # 4. Find Best Improvement
            step_best_res = None
            step_best_score = -1

            if candidate_results:
                # Find max score in batch
                best_cand = max(candidate_results, key=lambda x: x["Score"])
                step_best_score = best_cand["Score"]
                step_best_res = best_cand

            # 5. Adopt if better
            if step_best_res and step_best_score > best_score:
                best_score = step_best_score
                best_result = step_best_res
                best_genome = step_best_res["Genome"]
                steps += 1
            else:
                # Local Optimum Reached
                break

        return best_result, best_genome

    def polish_best_genome(best_genome):
        """
        Enhanced polishing with exhaustive mini permutation and 2-move neighborhood.
        
        Phase 0: Combined gear+mini exploration - try alternative gear WITH alternative minis
        Phase 1: Exhaustive mini permutation - try all C(top_k, 3) mini combinations
        Phase 2: 2-swap gear neighborhood - try all pairs of gear swaps
        Phase 3: Standard 1-swap local search until convergence
        
        This helps escape local optima that require coordinated changes.
        """
        from itertools import combinations, product
        
        top_k_gear = 15  # expanded to use more of the gear_rank_cache (25 items)
        top_k_minis_sweep = min(10, len(mini_rank_cache))  # For exhaustive: top 10 -> C(10,3)=120 combos
        top_k_minis_local = min(25, len(mini_rank_cache))  # For 1-swap local search
        
        best_result = evaluate_genome_local(best_genome)
        best_score = best_result["Score"]
        current_genome = list(best_genome)
        
        # Phase 0 removed - the improved heuristic (MAX of color OR base-stat score) 
        # should now properly rank items with strong base stats, making exhaustive
        # search unnecessary.
        
        
        # === PHASE 1: Exhaustive Mini Permutation ===
        # Try ALL combinations of top-ranked minis with current gear
        # This guarantees finding the optimal mini team for the current gear.
        if optimize_minis and len(mini_rank_cache) >= 3:
            mini_candidates = mini_rank_cache[:top_k_minis_sweep]
            all_mini_combos = list(combinations(mini_candidates, 3))
            
            if all_mini_combos:
                # Build genomes for all mini combinations
                mini_trial_genomes = []
                for combo in all_mini_combos:
                    trial = current_genome[:6] + list(combo)
                    mini_trial_genomes.append(trial)
                
                # Batch evaluate all mini combinations
                mini_results = batch_evaluator(mini_trial_genomes)
                
                if mini_results:
                    best_mini_result = max(mini_results, key=lambda x: x["Score"])
                    if best_mini_result["Score"] > best_score:
                        best_score = best_mini_result["Score"]
                        best_result = best_mini_result
                        current_genome = list(best_mini_result["Genome"])
                        print(f"  >> [Polish] Exhaustive mini sweep improved score to {best_score}")
        
        # === PHASE 2: 2-Swap Gear Neighborhood ===
        # Try all pairs of gear swaps to escape 2-move basins
        if optimize_gear:
            local_gear_rank = {
                s: gear_rank_cache.get(s, [])[:top_k_gear] for s in slots
            }
            
            two_swap_candidates = []
            
            # Generate all (slot_i, gear_a, slot_j, gear_b) combinations
            for i, slot_i in enumerate(slots):
                for j, slot_j in enumerate(slots):
                    if j <= i:
                        continue  # Only consider i < j pairs
                    
                    curr_i = current_genome[i]
                    curr_j = current_genome[j]
                    curr_i_name = curr_i.get("Name") if isinstance(curr_i, dict) else ""
                    curr_j_name = curr_j.get("Name") if isinstance(curr_j, dict) else ""
                    
                    for cand_i in local_gear_rank.get(slot_i, []):
                        if cand_i.get("Name") == curr_i_name:
                            continue
                        for cand_j in local_gear_rank.get(slot_j, []):
                            if cand_j.get("Name") == curr_j_name:
                                continue
                            
                            trial = current_genome[:]
                            trial[i] = cand_i
                            trial[j] = cand_j
                            two_swap_candidates.append(trial)
            
            if two_swap_candidates:
                # Batch evaluate in chunks to avoid exceeding GPU batch size limit
                GPU_BATCH_LIMIT = 2000  # Stay safely under 4096 limit
                all_two_swap_results = []
                
                for chunk_start in range(0, len(two_swap_candidates), GPU_BATCH_LIMIT):
                    chunk = two_swap_candidates[chunk_start:chunk_start + GPU_BATCH_LIMIT]
                    chunk_results = batch_evaluator(chunk)
                    if chunk_results:
                        all_two_swap_results.extend(chunk_results)
                
                if all_two_swap_results:
                    best_two_swap = max(all_two_swap_results, key=lambda x: x["Score"])
                    if best_two_swap["Score"] > best_score:
                        best_score = best_two_swap["Score"]
                        best_result = best_two_swap
                        current_genome = list(best_two_swap["Genome"])
                        print(f"  >> [Polish] 2-swap gear improved score to {best_score}")
        
        # === PHASE 2.5: 3-Swap Gear Neighborhood ===
        # Try all triplets of gear swaps to escape 3-move basins
        # This is critical for loadouts where the true optimum differs in 3+ slots
        if optimize_gear:
            three_swap_candidates = []
            
            # Generate all (slot_i, slot_j, slot_k) triplet combinations
            for i, slot_i in enumerate(slots):
                for j, slot_j in enumerate(slots):
                    if j <= i:
                        continue
                    for k, slot_k in enumerate(slots):
                        if k <= j:
                            continue  # Only consider i < j < k triplets
                        
                        curr_i = current_genome[i]
                        curr_j = current_genome[j]
                        curr_k = current_genome[k]
                        curr_i_name = curr_i.get("Name") if isinstance(curr_i, dict) else ""
                        curr_j_name = curr_j.get("Name") if isinstance(curr_j, dict) else ""
                        curr_k_name = curr_k.get("Name") if isinstance(curr_k, dict) else ""
                        
                        for cand_i in local_gear_rank.get(slot_i, []):
                            if cand_i.get("Name") == curr_i_name:
                                continue
                            for cand_j in local_gear_rank.get(slot_j, []):
                                if cand_j.get("Name") == curr_j_name:
                                    continue
                                for cand_k in local_gear_rank.get(slot_k, []):
                                    if cand_k.get("Name") == curr_k_name:
                                        continue
                                    
                                    trial = current_genome[:]
                                    trial[i] = cand_i
                                    trial[j] = cand_j
                                    trial[k] = cand_k
                                    three_swap_candidates.append(trial)
            
            if three_swap_candidates:
                # Batch evaluate in chunks to avoid exceeding GPU batch size limit
                GPU_BATCH_LIMIT = 2000
                all_three_swap_results = []
                
                for chunk_start in range(0, len(three_swap_candidates), GPU_BATCH_LIMIT):
                    chunk = three_swap_candidates[chunk_start:chunk_start + GPU_BATCH_LIMIT]
                    chunk_results = batch_evaluator(chunk)
                    if chunk_results:
                        all_three_swap_results.extend(chunk_results)
                
                if all_three_swap_results:
                    best_three_swap = max(all_three_swap_results, key=lambda x: x["Score"])
                    if best_three_swap["Score"] > best_score:
                        best_score = best_three_swap["Score"]
                        best_result = best_three_swap
                        current_genome = list(best_three_swap["Genome"])
                        print(f"  >> [Polish] 3-swap gear improved score to {best_score}")
        
        # === PHASE 3: Standard 1-Swap Local Search ===
        # Continue with traditional hill climbing until convergence
        final_result, final_genome = run_local_search(
            current_genome, 0, top_k_gear, top_k_minis_local, is_polishing=True
        )
        
        if final_result["Score"] > best_score:
            return final_result, final_genome
        else:
            return best_result, current_genome

    def memetic_local_search(start_genome, max_steps, top_k_gear, top_k_minis):
        """Lightweight local search around a genome (Sequential)."""
        if max_steps <= 0:
            res = evaluate_genome_local(start_genome)
            return res

        res, _ = run_local_search(start_genome, max_steps, top_k_gear, top_k_minis, is_polishing=False)
        return res

    def batch_memetic_local_search(seed_genomes, max_steps, top_k_gear, top_k_minis):
        """
        Batched local search for multiple seeds simultaneously.
        Reduces kernel launch overhead by ~4x compared to sequential memetic search.
        """
        if not seed_genomes:
            return []
        if max_steps <= 0:
            return batch_evaluator(seed_genomes)

        current_genomes = [list(g) for g in seed_genomes]
        current_results = batch_evaluator(current_genomes)
        current_scores = [r["Score"] for r in current_results]
        
        # Pre-trim candidate lists (shared across all seeds)
        local_gear_rank = {
            s: gear_rank_cache.get(s, [])[:top_k_gear] for s in slots
        }
        local_mini_rank = mini_rank_cache[:top_k_minis]

        for step in range(max_steps):
            all_candidates = []
            candidate_map = [] # (seed_idx, start_idx, end_idx)

            # Generate candidates for EACH seed
            for seed_idx, genome in enumerate(current_genomes):
                start_cand_idx = len(all_candidates)
                
                # 1. Gear Candidates
                if optimize_gear:
                    for idx, slot in enumerate(slots):
                        curr_item = genome[idx]
                        current_name = curr_item.get("Name") if isinstance(curr_item, dict) else str(curr_item) if curr_item else ""
                        
                        for cand in local_gear_rank.get(slot, []):
                            if cand.get("Name") == current_name:
                                continue
                            trial = genome[:]
                            trial[idx] = cand
                            all_candidates.append(trial)

                # 2. Mini Candidates
                if optimize_minis:
                    existing = set()
                    for m in genome[6:]:
                        if isinstance(m, dict):
                            existing.add(m.get("Name", ""))
                        elif m:
                            existing.add(str(m))
                            
                    for idx in range(6, 9):
                        curr_item = genome[idx]
                        curr_name = curr_item.get("Name") if isinstance(curr_item, dict) else str(curr_item) if curr_item else ""
                        
                        for cand in local_mini_rank:
                            c_name = cand.get("Name")
                            if c_name == curr_name:
                                continue
                            if c_name in existing:
                                continue
                            trial = genome[:]
                            trial[idx] = cand
                            all_candidates.append(trial)
                
                end_cand_idx = len(all_candidates)
                candidate_map.append((seed_idx, start_cand_idx, end_cand_idx))

            if not all_candidates:
                break

            # Batch evaluate EVERYTHING (GPU handles chunking)
            all_results = batch_evaluator(all_candidates)
            
            # Distribute results back to seeds
            improved_any = False
            for seed_idx, start_cand, end_cand in candidate_map:
                if start_cand == end_cand:
                    continue
                
                # Careful slice bounds check
                chunk_len = end_cand - start_cand
                if chunk_len <= 0:
                   continue

                # Ensure we don't index out of bounds if batch_evaluator dropped items (unlikely)
                if start_cand >= len(all_results):
                    continue
                
                chunk_results = all_results[start_cand:end_cand]
                if not chunk_results:
                    continue

                best_cand_res = max(chunk_results, key=lambda x: x["Score"])
                if best_cand_res["Score"] > current_scores[seed_idx]:
                    current_scores[seed_idx] = best_cand_res["Score"]
                    current_results[seed_idx] = best_cand_res
                    current_genomes[seed_idx] = best_cand_res["Genome"]
                    improved_any = True
            
            if not improved_any:
                break
        
        return current_results

    return run_local_search, polish_best_genome, memetic_local_search, batch_memetic_local_search


def build_initial_population(
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
):
    """
    Build the initial population for a GA run.

    Injects DB seeds, fixed loadouts, heuristic genomes, and random genomes.

    Args:
        create_random_genome: Function to create random genomes
        create_heuristic_genome: Function to create heuristic genomes
        reconstruct_genome_from_db_list: Function to reconstruct genome from DB
        build_seed_list_from_record: Function to build seed list from record
        mutate_genome_once: Function to mutate a genome once
        db_seed: Previous best loadout from database
        ga_settings: GA configuration settings
        fixed_gear: Fixed gear loadout if not optimizing
        fixed_minis: Fixed minis if not optimizing

    Returns:
        list: Initial population of genomes
    """
    population = []
    seed_list = build_seed_list_from_record(db_seed)
    should_inject = bool(seed_list) and (
        force_db_seed or (random.random() < ga_settings.db_seed_prob)
    )
    if seed_list and should_inject:
        try:
            if force_db_seed:
                print(
                    f" >> [Evolution] Injecting previous best (forced) (Score: {db_seed.get('score', 0)})"
                )
            else:
                print(
                    f" >> [Evolution] Injecting previous best (Score: {db_seed.get('score', 0)})"
                )
            seed_genome = reconstruct_genome_from_db_list(seed_list)
            population.append(seed_genome[:])
            population.append(mutate_genome_once(seed_genome))
        except Exception as e:
            print(f" >> [Evolution] Failed to inject seed: {e}")
    elif seed_list:
        print(" >> [Evolution] Skipping DB seed this run (probability gate).")

    if fixed_gear and fixed_minis:
        seed_genome = fixed_gear + fixed_minis
        for _ in range(ga_settings.fixed_seed_copies):
            population.append(seed_genome[:])

    # Inject more heuristic genomes (25 instead of 10) to ensure each of the 
    # top-ranked minis gets tested in at least a few combinations.
    # This helps discover synergistic combos that don't rank highest individually.
    for _ in range(25):
        population.append(create_heuristic_genome())

    while len(population) < GA_POPULATION_SIZE:
        population.append(create_random_genome())
    return population


def perform_crossover_mutation(
    results,
    create_random_genome,
    mini_pool,
    gear_pool,
    slots,
    optimize_gear,
    optimize_minis,
    fixed_minis,
    current_mutation_rate,
    global_elites=None,
):
    """
    Perform crossover and mutation to create next generation.

    Args:
        results: Evaluated population sorted by score
        create_random_genome: Function to create random genomes
        mini_pool: List of valid minis
        gear_pool: Dict mapping slot names to gear lists
        slots: List of gear slot names
        optimize_gear: Whether to optimize gear
        optimize_minis: Whether to optimize minis
        fixed_minis: Fixed minis if not optimizing
        current_mutation_rate: Current mutation rate
        global_elites: Optional list of elite genomes from previous runs (cross-run sharing)

    Returns:
        list: Next generation population
    """
    next_gen = [results[i]["Genome"] for i in range(GA_ELITISM)]

    # When exploration is high (e.g., after stagnation/diversity injection),
    # widen parent selection and increase random injection to help cross
    # multi-gene fitness valleys caused by strong stat/gem interactions.
    #
    # current_mutation_rate is already dynamic (see compute_dynamic_mutation),
    # so we use it as a proxy for "how stuck are we?".
    if current_mutation_rate >= 0.35:
        parent_pool_size = 120
        random_inject_prob = 0.35
    elif current_mutation_rate >= 0.30:
        parent_pool_size = 80
        random_inject_prob = 0.25
    else:
        parent_pool_size = 50
        random_inject_prob = 0.18

    parent_pool_size = min(parent_pool_size, len(results))

    # Cross-run elite sharing probability - allows good building blocks from
    # previous runs to propagate via crossover without forcing DB seed injection.
    elite_crossover_prob = 0.15 if global_elites else 0.0

    while len(next_gen) < GA_POPULATION_SIZE:
        if random.random() < random_inject_prob:
            next_gen.append(create_random_genome())
            continue

        # Parent selection with optional cross-run elite sharing
        if global_elites and random.random() < elite_crossover_prob:
            p1 = random.choice(global_elites)
        else:
            p1 = random.choice(results[:parent_pool_size])["Genome"]
        
        if global_elites and random.random() < elite_crossover_prob:
            p2 = random.choice(global_elites)
        else:
            p2 = random.choice(results[:parent_pool_size])["Genome"]

        child = []
        L = min(len(p1), len(p2))
        for i in range(L):
            child.append(p1[i] if random.random() > 0.5 else p2[i])

        child_gear = child[:6]
        child_minis = child[6:]

        seen_names = set()
        unique_minis = []
        for m in child_minis:
            name = m.get("Name", None) if isinstance(m, dict) else None
            if name and name not in seen_names and name != "(Empty)":
                unique_minis.append(m)
                seen_names.add(name)

        if optimize_minis:
            while len(unique_minis) < 3:
                candidates = [m for m in mini_pool if m["Name"] not in seen_names]
                if candidates:
                    new_m = random.choice(candidates)
                    unique_minis.append(new_m)
                    seen_names.add(new_m["Name"])
                else:
                    break
        else:
            # Shallow copy suffices; minis are read-only dicts.
            unique_minis = list(fixed_minis)

        child = child_gear + unique_minis

        # Mutation:
        # - Always preserve the existing behavior at low exploration (single-gene mutation).
        # - Under high exploration, allow *macro-mutation* (2-4 independent gene edits)
        #   to jump across fitness valleys where any single edit is detrimental but a
        #   coordinated set is beneficial (common with gem allocation interactions).
        if random.random() < current_mutation_rate:
            # Decide how many independent edits to apply.
            # (This is intentionally small to avoid destabilizing the GA.)
            n_edits = 1
            if current_mutation_rate >= 0.35:
                r = random.random()
                if r < 0.35:
                    n_edits = 4
                elif r < 0.75:
                    n_edits = 3
                else:
                    n_edits = 2
            elif current_mutation_rate >= 0.30 and random.random() < 0.5:
                n_edits = 2

            for _ in range(n_edits):
                mutate_idx = random.randint(0, 8)
                if mutate_idx < 6 and optimize_gear:
                    slot_type = slots[mutate_idx]
                    if gear_pool[slot_type]:
                        child[mutate_idx] = random.choice(gear_pool[slot_type])
                elif mutate_idx >= 6 and optimize_minis:
                    current_mini_names = {
                        m.get("Name") for m in child[6:] if isinstance(m, dict)
                    }
                    candidates = [
                        m for m in mini_pool if m["Name"] not in current_mini_names
                    ]
                    if candidates:
                        child[mutate_idx] = random.choice(candidates)

        next_gen.append(child)

    return next_gen


def evaluate_population_parallel(
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
    use_gpu_batch=False,
):
    """
    Evaluate population in parallel using process pool or GPU batch.

    Args:
        population: List of genomes to evaluate
        genome_key: Function to generate genome keys
        evaluation_cache: Dict of cached evaluations
        check_persistent_cache: Function to check persistent cache
        base_stats_fixed: Fixed base stats dictionary
        cfg_data: Configuration data for evaluation
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays
        executor: Process pool executor (or None for serial)
        cache_hits_tracker: List [count] for tracking cache hits (mutable)
        use_gpu_batch: If True, use GPU batch evaluation instead of parallel CPU

    Returns:
        list: Evaluated results sorted by score
    """
    # GPU batch path - evaluate all uncached genomes in single pass
    if use_gpu_batch:
        # First check persistent cache for all unique genomes
        key_to_genome = {}
        for genome in population:
            k = genome_key(genome)
            if k not in key_to_genome:
                key_to_genome[k] = genome
                if k not in evaluation_cache:
                    cached_res = check_persistent_cache(genome)
                    if cached_res:
                        evaluation_cache[k] = cached_res
                        cache_hits_tracker[0] += 1
        
        # Use batch evaluation with deduplication
        results = batch_evaluate_genomes(
            population,
            base_stats_fixed,
            cfg_data,
            calc_song,
            ref_arrays,
            genome_key_fn=genome_key,
            evaluation_cache=evaluation_cache,
        )
        results.sort(key=lambda x: x["Score"], reverse=True)
        return results
    
    # CPU parallel path (original implementation)
    key_to_genome = {}
    pending_keys = []
    tasks = []
    for genome in population:
        k = genome_key(genome)
        if k in key_to_genome:
            continue
        key_to_genome[k] = genome
        if k not in evaluation_cache:
            pending_keys.append(k)
            tasks.append((genome, base_stats_fixed, cfg_data, calc_song, ref_arrays))

    if pending_keys:
        keys_to_calc = []
        tasks_to_calc = []

        for k, genome, task_payload in zip(pending_keys, [key_to_genome[k] for k in pending_keys], tasks):
            # Check persistent cache first
            cached_res = check_persistent_cache(genome)
            if cached_res:
                evaluation_cache[k] = cached_res
                cache_hits_tracker[0] += 1
            else:
                keys_to_calc.append(k)
                tasks_to_calc.append(task_payload)

        if keys_to_calc:
            if executor:
                worker_count = getattr(executor, "_max_workers", None) or (
                    os.cpu_count() or 1
                )
                chunk = max(1, len(tasks_to_calc) // (worker_count * 4))
                for k, res in zip(
                    keys_to_calc,
                    executor.map(
                        worker_coevolution_evaluate, tasks_to_calc, chunksize=chunk
                    ),
                ):
                    evaluation_cache[k] = res
            else:
                for k, payload in zip(keys_to_calc, tasks_to_calc):
                    evaluation_cache[k] = worker_coevolution_evaluate(payload)

    results = [evaluation_cache[genome_key(g)] for g in population]
    results.sort(key=lambda x: x["Score"], reverse=True)

    return results


def update_mutation_and_diversity(
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
    mini_pool=None,
    gear_pool=None,
    slots=None,
    optimize_gear=True,
    optimize_minis=True,
):
    """
    Update mutation rate and inject diversity if stagnated.

    Args:
        population: Current population
        results: Evaluated results
        generation: Current generation number
        last_improvement_gen: Last generation with improvement
        stagnation_limit: Generations before injecting diversity
        mutation_rate: Base mutation rate
        create_random_genome: Function to create random genomes
        create_heuristic_genome: Function to create heuristic genomes
        run_idx: Current run index
        current_mutation_rate: Current mutation rate with exploration boost
        exploration_boost: Exploration boost amount
        mini_pool: Optional list of minis for coordinated perturbation
        gear_pool: Optional dict of gear pools for coordinated perturbation
        slots: Optional list of slot names for coordinated perturbation
        optimize_gear: Whether gear optimization is enabled
        optimize_minis: Whether mini optimization is enabled

    Returns:
        tuple: (updated_population, updated_mutation_rate, updated_last_improvement_gen)
    """
    if generation - last_improvement_gen >= stagnation_limit:
        # Bump the *base* mutation rate, then compute an "effective" rate that
        # includes the exploration boost (cache-hit driven) so downstream logic
        # can react immediately in this generation.
        #
        # NOTE: Historically we printed/used the pre-bump `current_mutation_rate`
        # (computed earlier in the loop), which under-reported mutation and
        # made diversity injection less aggressive than intended.
        mutation_rate = min(GA_MUTATION_RATE_MAX, mutation_rate + 0.08)
        effective_mutation_rate = min(0.6, mutation_rate + exploration_boost)
        print(
            f"  >> Stagnation detected (Run {run_idx + 1}), "
            f"mutation_base -> {mutation_rate:.3f} "
            f"(effective: {effective_mutation_rate:.3f}, boost: {exploration_boost:.3f}), "
            f"injecting diversity"
        )
        elites = [r["Genome"] for r in results[:GA_ELITISM]]
        population = elites[:]
        
        # NEW: Coordinated Elite Perturbation
        # Create variants of each elite with 2-3 genes swapped simultaneously.
        # This helps escape fitness valleys that require coordinated changes
        # (e.g., swapping a mini AND changing gear simultaneously).
        if mini_pool and gear_pool and slots:
            for elite in elites:
                for _ in range(3):  # 3 perturbation variants per elite
                    perturbed = list(elite)
                    n_swaps = random.choice([2, 2, 3])  # Bias toward 2 swaps
                    
                    # Choose swap indices - at least one gear, at least one mini
                    swap_indices = []
                    if optimize_gear and random.random() < 0.7:
                        swap_indices.append(random.randint(0, 5))  # gear
                    if optimize_minis and random.random() < 0.8:
                        swap_indices.append(random.randint(6, 8))  # mini
                    
                    # Fill remaining swaps randomly
                    while len(swap_indices) < n_swaps:
                        idx = random.randint(0, 8)
                        if idx not in swap_indices:
                            swap_indices.append(idx)
                    
                    # Apply swaps
                    for idx in swap_indices:
                        if idx < 6 and optimize_gear:
                            slot_type = slots[idx]
                            if gear_pool.get(slot_type):
                                perturbed[idx] = random.choice(gear_pool[slot_type])
                        elif idx >= 6 and optimize_minis:
                            current_names = {
                                m.get("Name") for m in perturbed[6:] 
                                if isinstance(m, dict)
                            }
                            candidates = [
                                m for m in mini_pool 
                                if m.get("Name") not in current_names
                            ]
                            if candidates:
                                perturbed[idx] = random.choice(candidates)
                    
                    population.append(perturbed)
        
        # === FIX 2: Diverse Mini Injection ===
        # When stuck, explicitly inject genomes using minis that are NOT in the current best.
        # This forces exploration of alternative mini teams.
        if mini_pool and optimize_minis and results:
            # Get the best genome's minis
            best_genome = results[0]["Genome"]
            best_mini_names = set()
            for m in best_genome[6:]:
                if isinstance(m, dict):
                    best_mini_names.add(m.get("Name", ""))
                elif m:
                    best_mini_names.add(str(m))
            
            # Get alternative minis (NOT in current best but in top pool)
            # Use broader pool for diversity
            alternative_minis = [
                m for m in mini_pool 
                if m.get("Name") not in best_mini_names
            ]
            
            if len(alternative_minis) >= 3:
                # Inject genomes using top 10 alternative minis
                top_alt = alternative_minis[:10]
                for _ in range(8):  # 8 diverse mini genomes
                    # Use random gear from pool + alternative minis
                    genome = []
                    if optimize_gear and gear_pool and slots:
                        for s in slots:
                            genome.append(random.choice(gear_pool[s]) if gear_pool.get(s) else {})
                    else:
                        genome.extend(best_genome[:6])  # Keep current best gear
                    
                    # Sample 3 random minis from alternatives
                    sample_size = min(3, len(top_alt))
                    genome.extend(random.sample(top_alt, sample_size))
                    population.append(genome)
                
                # Also inject a few genomes using the BEST gear but alternative minis
                # This specifically tests if the current gear + different minis is better
                for _ in range(5):
                    genome = list(best_genome[:6])  # Clone best gear
                    sample_size = min(3, len(top_alt))
                    genome.extend(random.sample(top_alt, sample_size))
                    population.append(genome)
        
        # More aggressive reinjection when exploration is already high.
        # This helps escape deep local basins where single-gene improvements are rare.
        reinject_frac = 0.4
        if effective_mutation_rate >= 0.35:
            reinject_frac = 0.7
        elif effective_mutation_rate >= 0.30:
            reinject_frac = 0.55

        reinject_target = int(GA_POPULATION_SIZE * reinject_frac)
        while len(population) < reinject_target:
            population.append(create_random_genome())
        while len(population) < GA_POPULATION_SIZE:
            population.append(create_heuristic_genome())
        last_improvement_gen = generation

    return population, mutation_rate, last_improvement_gen


def compute_dynamic_mutation(
    mutation_rate,
    cache_hits_in_run,
    generation,
    current_run_gens,
    gens_per_run,
    ga_settings,
):
    """
    Compute dynamic mutation rate and generation limit based on cache hits.

    Implements "deep mining" - extends search when cache hits indicate known territory
    and increases mutation rate to explore more aggressively.

    Args:
        mutation_rate: Base mutation rate
        cache_hits_in_run: Number of cache hits in current run
        generation: Current generation number
        current_run_gens: Current generation limit for this run
        gens_per_run: Base generations per run
        ga_settings: GA configuration settings

    Returns:
        tuple: (current_mutation_rate, updated_current_run_gens)
    """
    # Update dynamic generation limit
    # "run longer about 1 gen for each hit"
    # We add the hits to the base limit.
    if ga_settings.deep_mining_enabled:
        current_run_gens = gens_per_run + cache_hits_in_run

    # "increase the exploration"
    # If we have many cache hits, we are in known territory. Increase mutation.
    # Base mutation is ~0.275. Max is 0.45.
    # If we have > 10% cache hits in the run, boost mutation.
    # Let's calculate a dynamic boost based on hit density.
    total_evals_so_far = generation * GA_POPULATION_SIZE
    hit_ratio = cache_hits_in_run / max(1, total_evals_so_far)

    # Boost mutation by up to 0.2 if hit ratio is high
    exploration_boost = min(0.2, hit_ratio * 0.5)
    if not ga_settings.deep_mining_enabled:
        # DeepMining disabled => do not apply cache-hit driven mutation boosts.
        exploration_boost = 0.0
    current_mutation_rate = min(0.6, mutation_rate + exploration_boost)  # Allow going slightly higher than normal max

    # Cap the extension to avoid infinite loops (e.g. max 5000 gens)
    if current_run_gens > 5000:
        current_run_gens = 5000

    return current_mutation_rate, current_run_gens
