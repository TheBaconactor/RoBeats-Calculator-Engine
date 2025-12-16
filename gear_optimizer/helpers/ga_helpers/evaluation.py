"""
GA Evaluation - Genome evaluation and caching.

This module provides evaluation functions with caching:
- create_evaluation_functions: Evaluation with per-song and per-loadout caching
- evaluate_population_parallel: Parallel batch evaluation
"""
from ...data.database import get_loadout_hash
from ...solver.scoring import worker_coevolution_evaluate, batch_evaluate_genomes
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

    # Color stats for mini primary/secondary determination
    color_stats = ["Rush", "Flow", "Chill", "Beat", "Vibe"]
    song_colors = {p_color} if p_color else set()
    if s_color:
        song_colors.add(s_color)

    def get_item_colors(item):
        """Get an item's primary and secondary colors (top 2 highest stat colors)."""
        color_values = [(c, item.get(c, 0)) for c in color_stats]
        sorted_colors = sorted(color_values, key=lambda cv: cv[1], reverse=True)
        primary = sorted_colors[0][0] if sorted_colors[0][1] > 0 else None
        secondary = sorted_colors[1][0] if len(sorted_colors) > 1 and sorted_colors[1][1] > 0 else None
        return primary, secondary

    def score_candidate(x):
        """
        Heuristic scoring used to rank candidate gear/minis before GA search.
        Supports multiple modes via GASettings:
        - modern: base-stats dominant (default)
        - legacy: color-heavy (closer to legacy script behavior)
        - hybrid: take the max(modern, legacy) to keep both benefits

        Minis whose primary/secondary matches the song's primary/secondary
        get a ranking boost to ensure they're included in the heuristic pool.

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
            base_score = legacy_score
        elif mode == "hybrid":
            base_score = max(modern_score, legacy_score)
        else:
            base_score = modern_score

        # Boost minis whose primary/secondary matches song's primary/secondary
        # Heavily favor mini primary matching song primary > mini primary matching song secondary
        item_primary, item_secondary = get_item_colors(x)
        color_match_bonus = 0

        # Mini's primary color matches song's primary color (highest priority)
        if item_primary and item_primary == p_color:
            color_match_bonus += 25
        # Mini's primary color matches song's secondary color (medium priority)
        elif item_primary and s_color and item_primary == s_color:
            color_match_bonus += 12

        # Mini's secondary color matches song colors (lower priority)
        if item_secondary and item_secondary == p_color:
            color_match_bonus += 8
        elif item_secondary and s_color and item_secondary == s_color:
            color_match_bonus += 5

        return base_score + color_match_bonus

    def genome_key(genome):
        """Generate a unique key for a genome for caching.
        
        OPTIMIZATION: Inlined get_name, avoid isinstance where possible.
        This function is called 241K+ times per run.
        """
        # Gear (first 6 slots): order matters because slots are positional.
        # Inline name extraction: most items are dicts
        gear_names = tuple(
            (item.get("Name", "") if isinstance(item, dict) else (str(item) if item else ""))
            for item in genome[:6]
        )
        # Minis (last 3 slots): order-invariant - only the set/multiset matters.
        # Sorting canonicalizes permutations so [A,B,C] and [C,B,A] share a key.
        mini_names = tuple(sorted(
            (item.get("Name", "") if isinstance(item, dict) else (str(item) if item else ""))
            for item in genome[6:]
        ))
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

                # DB rows are stored as (score, fg_score, force_data, details_data); fall back gracefully
                score = fg_score = force_data = details_data = None
                if isinstance(entry, dict):
                    score = entry.get("score")
                    fg_score = entry.get("fg_score")
                    force_data = entry.get("force_data") or entry.get("force_details")
                    details_data = entry.get("details_data")
                elif isinstance(entry, (list, tuple)):
                    if len(entry) >= 2:
                        score, fg_score = entry[0], entry[1]
                    if len(entry) >= 3:
                        force_data = entry[2]
                    if len(entry) >= 4:
                        details_data = entry[3]
                else:
                    # Unknown shape; skip cache usage rather than crashing
                    return None

                if score is None or fg_score is None:
                    return None

                base_score = score
                fitness_score = base_score

                data_dict = {
                    "Score": base_score, # Data.Score is typically the base score
                    "_cached_db": True,
                    "ForceDetails": force_data,
                }
                
                # Verify details_data contains expected fields before updating
                if details_data and isinstance(details_data, dict):
                    # Only update if it looks like valid details (has GemCounts or FT/FF)
                    if "GemCounts" in details_data or "FT" in details_data:
                        data_dict.update(details_data)

                return {
                    "Score": fitness_score,
                    "BaseScore": base_score,
                    "FG_Score": fg_score,
                    "Genome": genome,
                    "Gear": gear_part,
                    "Minis": mini_part,
                    "MiniNames": [
                        m.get("Name", "") if isinstance(m, dict) else str(m) for m in mini_part
                    ],
                    "Data": data_dict,
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


