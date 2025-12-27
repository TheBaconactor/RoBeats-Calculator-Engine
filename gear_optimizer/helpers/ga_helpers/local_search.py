"""
GA Local Search - Local search operations for genome refinement.

This module provides local search functions:
- create_local_search_function: Hill-climbing local search for genome refinement
"""

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
    ga_settings=None,
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
        ga_settings: GASettings object containing allow_3_swap flag

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

        # OPTIMIZATION: Reduced from 15 to 6 to cut polish time by ~75%
        # This reduces 2-swap from 3,375 to 540 genomes (6x faster)
        top_k_gear = 6
        top_k_minis_sweep = min(8, len(mini_rank_cache))  # Reduced from 10 -> C(8,3)=56 combos
        top_k_minis_local = min(20, len(mini_rank_cache))  # Reduced from 25
        
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
        
        # === PHASE 2: k-Swap Gear Neighborhood (k=2 then k=3) ===
        # Try coordinated k-slot changes to escape multi-move basins.
        if optimize_gear:
            local_gear_rank = {s: gear_rank_cache.get(s, [])[:top_k_gear] for s in slots}

            def try_k_swap(k: int, label: str):
                nonlocal best_score, best_result, current_genome

                # Pre-filter candidates per slot index (exclude current gear).
                choices_by_idx = {}
                for idx, slot in enumerate(slots):
                    curr = current_genome[idx]
                    curr_name = curr.get("Name") if isinstance(curr, dict) else ""
                    choices_by_idx[idx] = [
                        cand
                        for cand in local_gear_rank.get(slot, [])
                        if cand.get("Name") != curr_name
                    ]

                swap_candidates = []
                for idxs in combinations(range(len(slots)), k):
                    candidate_lists = [choices_by_idx[i] for i in idxs]
                    if any(not lst for lst in candidate_lists):
                        continue
                    for replacements in product(*candidate_lists):
                        trial = current_genome[:]
                        for i, cand in zip(idxs, replacements):
                            trial[i] = cand
                        swap_candidates.append(trial)

                if not swap_candidates:
                    return

                # OPTIMIZATION: Increased batch limit to 3500 to reduce kernel launches
                # With reduced top_k_gear=6, max candidates ~540, so single batch usually
                GPU_BATCH_LIMIT = 3500  # Increased from 2000 (safe under 4096 limit)
                all_results = []
                for chunk_start in range(0, len(swap_candidates), GPU_BATCH_LIMIT):
                    chunk = swap_candidates[chunk_start : chunk_start + GPU_BATCH_LIMIT]
                    chunk_results = batch_evaluator(chunk)
                    if chunk_results:
                        all_results.extend(chunk_results)

                if not all_results:
                    return

                best_k_swap = max(all_results, key=lambda x: x["Score"])
                improved = False
                if best_k_swap["Score"] > best_score:
                    best_score = best_k_swap["Score"]
                    best_result = best_k_swap
                    current_genome = list(best_k_swap["Genome"])
                    print(f"  >> [Polish] {label} gear improved score to {best_score}")
                    improved = True
                return improved

            # OPTIMIZATION: Only try 2-swap by default, skip expensive 3-swap (saves ~15s)
            # 3-swap generates 67,500 genomes vs 540 for 2-swap
            improved = try_k_swap(2, "2-swap")
            # Conditionally try 3-swap if enabled in config (adds ~15s)
            if ga_settings and getattr(ga_settings, 'allow_3_swap', False):
                try_k_swap(3, "3-swap")
        
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


