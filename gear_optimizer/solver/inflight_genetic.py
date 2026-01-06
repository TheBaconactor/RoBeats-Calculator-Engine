"""
In-flight (resumable) co-evolution GA driver.

This is an opt-in, generator-based variant of the CPU GA path that yields at
GPU-evaluation boundaries. It is intended for a multi-song in-flight
orchestrator that can interleave many songs while the GPU executor stays busy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generator, Optional, Any

from gear_optimizer.core.constants import (
    GA_MUTATION_RATE,
    GA_POPULATION_SIZE,
    GA_MULTI_RUNS_DEFAULT,
    TOTAL_GEM_BUDGET,
    GEM_SCALE_FEVER,
)
from gear_optimizer.core.utils import safe_int
from gear_optimizer.data.models import GASettings
from gear_optimizer.solver.scoring.genome_evaluation import (
    GpuBatchEvalPlan,
    prepare_gpu_batch_eval_plan,
    finalize_gpu_batch_eval_plan,
)


@dataclass(frozen=True)
class SolveGenomesJob:
    """A request to evaluate a population (unique stat signatures) on the GPU."""

    plan: GpuBatchEvalPlan
    payload: dict


@dataclass(frozen=True)
class InflightGAResult:
    best_score: int
    best_genome: list
    best_data: dict
    all_evaluated: list


def solve_coevolution_genetic_inflight(
    *,
    cfg: Any,
    ga_depth: int,
    base_stats_fixed: dict,
    calc_song: dict,
    ref_arrays: dict,
    all_gears: list,
    all_minis: list,
    gears_by_name: dict,
    minis_by_name: dict,
    optimize_gear: bool,
    optimize_minis: bool,
    fixed_gear: list,
    fixed_minis: list,
    known_loadouts: Optional[dict],
    db_seed: Optional[dict],
    song_slot: int,
    status_cb=None,
) -> Generator[SolveGenomesJob, Optional[list], InflightGAResult]:
    """
    Generator-based GA solver that yields GPU solve jobs and resumes with their results.
    """
    ga_settings = GASettings.from_cfg(cfg) if cfg is not None else GASettings.from_cfg(None)

    # Import helper functions lazily to avoid import-time costs in orchestration loops.
    from gear_optimizer.helpers.ga_helpers import (
        create_genome_functions,
        create_evaluation_functions,
        compute_dynamic_mutation,
        initialize_pools,
        build_initial_population,
        perform_crossover_mutation,
        update_mutation_and_diversity,
    )

    p_color = calc_song["metadata"].get("Primary Color", "Rush")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    selected_color = p_color

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    pools = initialize_pools(all_gears, all_minis, p_color, slots, s_color=s_color)
    if pools is None:
        raise RuntimeError("initialize_pools returned None (in-flight GA requires pools)")

    # `initialize_pools` returns (gear_pool, mini_pool, total_before, total_after[, whitelist]).
    if len(pools) >= 2:
        gear_pool = pools[0]
        mini_pool = pools[1]

    use_gpu_mode = False
    use_gpu_native = True
    try:
        use_gpu_mode = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=False)
    except Exception:
        use_gpu_mode = False
    try:
        use_gpu_native = cfg.getboolean("IterationEngine", "GPU_Native_GA", fallback=True)
    except Exception:
        use_gpu_native = True

    cfg_data = {
        "selected_color": selected_color,
        "use_gpu": bool(use_gpu_mode),
        "use_gpu_native": bool(use_gpu_native),
        "user_ft": safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0)),
        "user_ff": safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0)),
        "user_pp": safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0)),
        "user_cm": safe_int(cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0)),
        "user_fm": safe_int(cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0)),
        "static_elem_input": safe_int(cfg.get("ElementalGems", selected_color, fallback=0)),
    }

    cache_hits_tracker = [0]
    (
        _score_candidate,
        genome_key,
        check_persistent_cache,
        _evaluate_genome_local,  # NOTE: do not call in in-flight mode (can invoke Taichi on wrong thread)
        evaluation_cache,
        _batch_evaluator,
    ) = create_evaluation_functions(
        p_color,
        base_stats_fixed,
        cfg_data,
        calc_song,
        ref_arrays,
        known_loadouts,
        cache_hits_tracker,
    )

    # Rank caches for genome factory.
    gear_rank_max = getattr(ga_settings, "gear_rank_max", 40)
    mini_rank_max = getattr(ga_settings, "mini_rank_max", 40)
    gear_rank_cache = {s: gear_pool[s][:] for s in slots if s in gear_pool}
    for s in list(gear_rank_cache.keys()):
        gear_rank_cache[s] = sorted(gear_rank_cache[s], key=_score_candidate, reverse=True)[:gear_rank_max]
    mini_rank_cache = sorted(mini_pool, key=_score_candidate, reverse=True)[:mini_rank_max]

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

    num_runs = max(1, int(getattr(ga_settings, "multi_start", GA_MULTI_RUNS_DEFAULT) or 1))
    gens_per_run = max(1, (int(ga_depth) + num_runs - 1) // num_runs)

    best_global_score = -1
    best_global_genome: list = []
    best_global_data: dict = {}
    run_results: list[tuple[int, list, dict]] = []

    # ------------------------------------------------------------------
    # Yield-friendly evaluation helpers (no direct Taichi calls here).
    # ------------------------------------------------------------------

    def _submit_payload(plan: GpuBatchEvalPlan) -> dict:
        return {
            "genome_stats_list": plan.genome_stats_list,
            "timeline_grid": calc_song,
            "is_p_ft": plan.flags["is_p_ft"],
            "is_s_ft": plan.flags["is_s_ft"],
            "is_p_ff": plan.flags["is_p_ff"],
            "is_s_ff": plan.flags["is_s_ff"],
            "is_p_pp": plan.flags["is_p_pp"],
            "is_s_pp": plan.flags["is_s_pp"],
            "is_p_cm": plan.flags["is_p_cm"],
            "is_s_cm": plan.flags["is_s_cm"],
            "is_p_fm": plan.flags["is_p_fm"],
            "is_s_fm": plan.flags["is_s_fm"],
            "is_p_ov": plan.flags["is_p_ov"],
            "is_s_ov": plan.flags["is_s_ov"],
            "ref_arrays": ref_arrays,
            "total_budget": int(TOTAL_GEM_BUDGET),
            "gem_scale_fever": int(GEM_SCALE_FEVER),
            "song_slot": int(song_slot),
        }

    def _prime_persistent_cache(population: list) -> None:
        if not population:
            return
        key_to_genome = {}
        for genome in population:
            k = genome_key(genome)
            if k in key_to_genome:
                continue
            key_to_genome[k] = genome
            if k in evaluation_cache:
                continue
            cached_res = check_persistent_cache(genome)
            if cached_res:
                evaluation_cache[k] = cached_res
                cache_hits_tracker[0] += 1

    def _evaluate_population(
        population: list,
        *,
        use_cache: bool = True,
        use_persistent_cache: bool = True,
    ) -> Generator[SolveGenomesJob, Optional[list], list]:
        if use_cache and use_persistent_cache:
            _prime_persistent_cache(population)

        plan, immediate = prepare_gpu_batch_eval_plan(
            population,
            base_stats_fixed,
            cfg_data,
            calc_song,
            ref_arrays,
            genome_key_fn=genome_key if use_cache else None,
            evaluation_cache=evaluation_cache if use_cache else None,
        )

        if plan is None:
            return immediate or []

        gpu_results = yield SolveGenomesJob(plan=plan, payload=_submit_payload(plan))
        results = finalize_gpu_batch_eval_plan(plan, gpu_results=gpu_results)
        return results

    def _evaluate_one(
        genome: list,
        *,
        force_full: bool = False,
    ) -> Generator[SolveGenomesJob, Optional[list], dict]:
        if not genome:
            raise RuntimeError("Cannot evaluate empty genome")

        if not force_full:
            k = genome_key(genome)
            if k in evaluation_cache:
                return evaluation_cache[k]

        # Force-full evaluation bypasses both in-memory and DB caches so we always
        # end with a complete Data dict (GemCounts/Stats) suitable for persistence.
        results = yield from _evaluate_population(
            [genome],
            use_cache=not force_full,
            use_persistent_cache=not force_full,
        )
        res = results[0] if results else None
        if not isinstance(res, dict):
            raise RuntimeError("Genome evaluation returned no result")

        try:
            evaluation_cache[genome_key(genome)] = res
        except Exception:
            pass
        return res

    # ------------------------------------------------------------------
    # Yield-friendly local search (memetic + polishing), matching
    # gear_optimizer/helpers/ga_helpers/local_search.py behavior.
    # ------------------------------------------------------------------

    def _run_local_search(
        start_genome: list,
        max_steps: int,
        top_k_gear: int,
        top_k_minis: int,
        *,
        is_polishing: bool = False,
    ) -> Generator[SolveGenomesJob, Optional[list], tuple[dict, list]]:
        best_result = yield from _evaluate_one(list(start_genome))
        best_score = int(best_result.get("Score", 0) or 0)
        best_genome = list(best_result.get("Genome") or start_genome)

        local_gear_rank = {s: gear_rank_cache.get(s, [])[:top_k_gear] for s in slots}
        local_mini_rank = mini_rank_cache[:top_k_minis]

        steps = 0
        limit = 999999 if is_polishing else max(0, int(max_steps))

        while steps < limit:
            candidates = []

            if optimize_gear:
                for idx, slot in enumerate(slots):
                    curr_item = best_genome[idx]
                    current_name = (
                        curr_item.get("Name") if isinstance(curr_item, dict) else str(curr_item) if curr_item else ""
                    )
                    for cand in local_gear_rank.get(slot, []):
                        if cand.get("Name") == current_name:
                            continue
                        trial = best_genome[:]
                        trial[idx] = cand
                        candidates.append(trial)

            if optimize_minis:
                existing = set()
                for m in best_genome[6:]:
                    if isinstance(m, dict):
                        existing.add(m.get("Name", ""))
                    elif m:
                        existing.add(str(m))

                for idx in range(6, 9):
                    curr_item = best_genome[idx]
                    curr_name = (
                        curr_item.get("Name") if isinstance(curr_item, dict) else str(curr_item) if curr_item else ""
                    )
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

            candidate_results = yield from _evaluate_population(candidates)
            if not candidate_results:
                break

            best_cand = max(candidate_results, key=lambda x: x.get("Score", 0) or 0)
            step_best_score = int(best_cand.get("Score", 0) or 0)

            if step_best_score > best_score:
                best_score = step_best_score
                best_result = best_cand
                best_genome = list(best_cand.get("Genome") or best_genome)
                steps += 1
            else:
                break

        return best_result, best_genome

    def _polish_best_genome(
        best_genome: list,
    ) -> Generator[SolveGenomesJob, Optional[list], tuple[dict, list]]:
        from itertools import combinations, product

        top_k_gear = 6
        top_k_minis_sweep = min(8, len(mini_rank_cache))
        top_k_minis_local = min(20, len(mini_rank_cache))

        best_result = yield from _evaluate_one(list(best_genome))
        best_score = int(best_result.get("Score", 0) or 0)
        current_genome = list(best_genome)

        # Phase 1: exhaustive mini sweep
        if optimize_minis and len(mini_rank_cache) >= 3:
            mini_candidates = mini_rank_cache[:top_k_minis_sweep]
            all_mini_combos = list(combinations(mini_candidates, 3))
            if all_mini_combos:
                mini_trial_genomes = [current_genome[:6] + list(combo) for combo in all_mini_combos]
                mini_results = yield from _evaluate_population(mini_trial_genomes)
                if mini_results:
                    best_mini_result = max(mini_results, key=lambda x: x.get("Score", 0) or 0)
                    best_mini_score = int(best_mini_result.get("Score", 0) or 0)
                    if best_mini_score > best_score:
                        best_score = best_mini_score
                        best_result = best_mini_result
                        current_genome = list(best_mini_result.get("Genome") or current_genome)

        # Phase 2: k-swap gear neighborhood (k=2 then k=3 if enabled)
        if optimize_gear:
            local_gear_rank = {s: gear_rank_cache.get(s, [])[:top_k_gear] for s in slots}

            def _try_k_swap(k: int) -> Generator[SolveGenomesJob, Optional[list], bool]:
                nonlocal best_score, best_result, current_genome

                choices_by_idx = {}
                for idx, slot in enumerate(slots):
                    curr = current_genome[idx]
                    curr_name = curr.get("Name") if isinstance(curr, dict) else ""
                    choices_by_idx[idx] = [
                        cand for cand in local_gear_rank.get(slot, []) if cand.get("Name") != curr_name
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
                    return False

                GPU_BATCH_LIMIT = 3500
                all_results = []
                for chunk_start in range(0, len(swap_candidates), GPU_BATCH_LIMIT):
                    chunk = swap_candidates[chunk_start : chunk_start + GPU_BATCH_LIMIT]
                    chunk_results = yield from _evaluate_population(chunk)
                    if chunk_results:
                        all_results.extend(chunk_results)

                if not all_results:
                    return False

                best_k_swap = max(all_results, key=lambda x: x.get("Score", 0) or 0)
                best_k_score = int(best_k_swap.get("Score", 0) or 0)
                if best_k_score > best_score:
                    best_score = best_k_score
                    best_result = best_k_swap
                    current_genome = list(best_k_swap.get("Genome") or current_genome)
                    return True
                return False

            _ = yield from _try_k_swap(2)
            if getattr(ga_settings, "allow_3_swap", False):
                _ = yield from _try_k_swap(3)

        # Phase 3: standard 1-swap hill-climb until convergence
        final_result, final_genome = yield from _run_local_search(
            current_genome,
            0,
            top_k_gear,
            top_k_minis_local,
            is_polishing=True,
        )

        final_score = int(final_result.get("Score", 0) or 0)
        if final_score > best_score:
            return final_result, final_genome
        return best_result, current_genome

    def _batch_memetic_local_search(
        seed_genomes: list,
        max_steps: int,
        top_k_gear: int,
        top_k_minis: int,
    ) -> Generator[SolveGenomesJob, Optional[list], list]:
        if not seed_genomes:
            return []

        if max_steps <= 0:
            return (yield from _evaluate_population(seed_genomes))

        current_genomes = [list(g) for g in seed_genomes]
        current_results = yield from _evaluate_population(current_genomes)
        current_scores = [int(r.get("Score", 0) or 0) for r in current_results]

        local_gear_rank = {s: gear_rank_cache.get(s, [])[:top_k_gear] for s in slots}
        local_mini_rank = mini_rank_cache[:top_k_minis]

        for _step in range(max_steps):
            all_candidates = []
            candidate_map = []  # (seed_idx, start_idx, end_idx)

            for seed_idx, genome in enumerate(current_genomes):
                start_cand_idx = len(all_candidates)

                if optimize_gear:
                    for idx, slot in enumerate(slots):
                        curr_item = genome[idx]
                        current_name = (
                            curr_item.get("Name")
                            if isinstance(curr_item, dict)
                            else str(curr_item)
                            if curr_item
                            else ""
                        )
                        for cand in local_gear_rank.get(slot, []):
                            if cand.get("Name") == current_name:
                                continue
                            trial = genome[:]
                            trial[idx] = cand
                            all_candidates.append(trial)

                if optimize_minis:
                    existing = set()
                    for m in genome[6:]:
                        if isinstance(m, dict):
                            existing.add(m.get("Name", ""))
                        elif m:
                            existing.add(str(m))

                    for idx in range(6, 9):
                        curr_item = genome[idx]
                        curr_name = (
                            curr_item.get("Name")
                            if isinstance(curr_item, dict)
                            else str(curr_item)
                            if curr_item
                            else ""
                        )
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

            all_results = yield from _evaluate_population(all_candidates)

            improved_any = False
            for seed_idx, start_cand, end_cand in candidate_map:
                if start_cand == end_cand:
                    continue
                if start_cand >= len(all_results):
                    continue

                chunk_results = all_results[start_cand:end_cand]
                if not chunk_results:
                    continue

                best_cand_res = max(chunk_results, key=lambda x: x.get("Score", 0) or 0)
                best_cand_score = int(best_cand_res.get("Score", 0) or 0)
                if best_cand_score > current_scores[seed_idx]:
                    current_scores[seed_idx] = best_cand_score
                    current_results[seed_idx] = best_cand_res
                    current_genomes[seed_idx] = list(best_cand_res.get("Genome") or current_genomes[seed_idx])
                    improved_any = True

            if not improved_any:
                break

        return current_results

    # Soft non-regression guard: evaluate DB seed once up-front (if provided).
    db_seed_score = -1
    db_seed_genome = None
    db_seed_data = None
    if db_seed:
        try:
            seed_list = build_seed_list_from_record(db_seed)
            if seed_list:
                seed_genome = reconstruct_genome_from_db_list(seed_list)
                seed_res = yield from _evaluate_one(seed_genome, force_full=True)
                db_seed_score = int(seed_res.get("BaseScore") or seed_res.get("Score", -1) or -1)
                db_seed_genome = list(seed_genome)
                db_seed_data = dict(seed_res.get("Data") or {})
                if status_cb:
                    status_cb(f"DB seed baseline (soft): {db_seed_score}")
        except Exception as exc:
            if status_cb:
                status_cb(f"Warning: failed to evaluate DB seed: {exc}")

    for run_idx in range(num_runs):
        if status_cb:
            status_cb(f"Run {run_idx + 1}/{num_runs} starting")

        population = build_initial_population(
            create_random_genome,
            create_heuristic_genome,
            reconstruct_genome_from_db_list,
            build_seed_list_from_record,
            mutate_genome_once,
            db_seed=db_seed,
            ga_settings=ga_settings,
            fixed_gear=fixed_gear,
            fixed_minis=fixed_minis,
            force_db_seed=False,
        )

        best_run_score = -1
        last_improvement_gen = 0
        base_stagnation_limit = max(8, gens_per_run // 2)
        explore_stagnation_limit = max(8, gens_per_run // 3)
        mutation_rate = GA_MUTATION_RATE
        current_run_gens = gens_per_run
        cache_hits_tracker[0] = 0
        generation = 0
        current_mutation_rate = mutation_rate

        while generation < current_run_gens:
            generation += 1
            results = yield from _evaluate_population(population)

            results.sort(key=lambda x: x["Score"], reverse=True)
            if not results:
                break

            # --- MEMETIC GA STEP: local search on top elites (batched) ---
            if ga_settings.memetic_elites > 0 and ga_settings.memetic_steps > 0:
                elite_count = min(ga_settings.memetic_elites, len(results))
                seed_genomes = [results[i]["Genome"] for i in range(elite_count)]
                improved_results = yield from _batch_memetic_local_search(
                    seed_genomes,
                    ga_settings.memetic_steps,
                    ga_settings.memetic_top_gear,
                    ga_settings.memetic_top_minis,
                )

                for i, improved_res in enumerate(improved_results or []):
                    if i >= elite_count:
                        break
                    if improved_res and (improved_res.get("Score", 0) or 0) > (results[i].get("Score", 0) or 0):
                        results[i] = improved_res

                results.sort(key=lambda x: x["Score"], reverse=True)

            best_cand = results[0]
            if best_cand["Score"] > best_run_score:
                best_run_score = best_cand["Score"]
                last_improvement_gen = generation

            if best_cand["Score"] > best_global_score:
                best_global_score = best_cand["Score"]
                best_global_genome = best_cand["Genome"]
                best_global_data = best_cand["Data"]

            population = perform_crossover_mutation(
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
            )

            current_mutation_rate, current_run_gens = compute_dynamic_mutation(
                mutation_rate,
                cache_hits_tracker[0],
                generation,
                current_run_gens,
                gens_per_run,
                ga_settings,
            )

            total_evals_so_far = generation * GA_POPULATION_SIZE
            hit_ratio = cache_hits_tracker[0] / max(1, total_evals_so_far)
            exploration_boost = min(0.2, hit_ratio * 0.5) if ga_settings.deep_mining_enabled else 0.0

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

        if results:
            run_results.append((results[0]["Score"], results[0]["Genome"], results[0]["Data"]))

    for score, genome, data in run_results:
        if score > best_global_score:
            best_global_score = score
            best_global_genome = genome
            best_global_data = data

    # Polish best genome with exhaustive local search (matching the baseline path).
    if best_global_genome:
        polished_result, polished_genome = yield from _polish_best_genome(best_global_genome)

        # If result was cached (DB), force a full re-evaluation so we always have GemCounts/Stats.
        if polished_result.get("_cached"):
            polished_result = yield from _evaluate_one(polished_genome, force_full=True)

        polished_score = int(polished_result.get("Score", 0) or 0)
        if polished_score > best_global_score:
            best_global_score = polished_score
            best_global_genome = list(polished_genome or [])
            best_global_data = dict(polished_result.get("Data") or {})

    # Soft non-regression guard: if GA regresses vs DB seed, fall back.
    ga_true_score = (
        best_global_data.get("BaseScore", best_global_data.get("Score", 0)) if best_global_data else best_global_score
    )
    if db_seed_score > ga_true_score and db_seed_genome:
        best_global_score = int(db_seed_score)
        best_global_genome = list(db_seed_genome or [])
        best_global_data = dict(db_seed_data or {})

    # Ensure final best has complete gem allocation details.
    if best_global_genome and best_global_data and "GemCounts" not in best_global_data:
        full_res = yield from _evaluate_one(best_global_genome, force_full=True)
        best_global_score = int(full_res.get("Score", best_global_score) or best_global_score)
        best_global_genome = list(full_res.get("Genome") or best_global_genome)
        best_global_data = dict(full_res.get("Data") or best_global_data)

    all_evaluated = list(evaluation_cache.values())
    evaluation_cache.clear()

    return InflightGAResult(
        best_score=int(best_global_score),
        best_genome=list(best_global_genome or []),
        best_data=dict(best_global_data or {}),
        all_evaluated=all_evaluated,
    )
