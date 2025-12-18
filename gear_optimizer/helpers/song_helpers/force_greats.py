"""
Song Helpers - Force Greats - Force greats processing and optimization.

This module provides force greats operations:
- process_force_greats: Apply force greats to loadouts with GPU/CPU support
"""
import time

from ...solver.scoring import apply_force_greats_to_result
from ...core.utils import stats_signature


def process_force_greats(
    loadout_entries,
    manual_force_greats,
    force_greats_finder,
    force_greats_config,
    calc_song,
    ref_arrays,
    meta_primary_color,
    build_details_fn,
    db_loadouts_full_count,
    use_gpu: bool = False,
    perf_timing: bool = False,
):
    """
    Apply force greats to loadouts.

    Args:
        loadout_entries: Dictionary of loadout entries
        manual_force_greats: Whether manual force greats is enabled
        force_greats_finder: Whether force greats finder is enabled
        force_greats_config: Force greats configuration
        calc_song: Song calculation data
        ref_arrays: Reference arrays for calculation
        meta_primary_color: Primary color from metadata
        build_details_fn: Function to build details dict from data dict
        db_loadouts_full_count: Number of DB loadouts (for budget)
        perf_timing: If True, prints a detailed breakdown of FG grouping/caching/GPU calls.

    Returns:
        list: List of force greats variants
    """
    fg_variants = []
    perf = bool(perf_timing)

    manual_counts = (
        force_greats_config if (manual_force_greats and not force_greats_finder) else []
    )

    def _names_list(items):
        names = []
        for it in items or []:
            if isinstance(it, dict):
                names.append(it.get("Name", ""))
            else:
                names.append(str(it) if it else "")
        return names

    # FG processing budget: number of DB loadouts (dynamic). Skip (reuse) does NOT consume budget.
    unique_stats_seen = set()
    max_fg_compute = db_loadouts_full_count if db_loadouts_full_count else len(loadout_entries)
    computed = 0
    print(f"[ForceGreats] Processing {len(loadout_entries)} unique loadouts (DB + GA)...")

    # ------------------------------------------------------------------
    # GPU Finder Fast Path:
    # When ForceGreatsFinder is enabled and GPU mode is on, batch/dedupe
    # across loadouts and run the full FG finder on the GPU.
    # ------------------------------------------------------------------
    if use_gpu and force_greats_finder:
        try:
            from ...core.constants import (
                GEM_SCALE_NORMAL,
                GEM_SCALE_FEVER,
                GEM_STAT_TO_ELEMENT_SCALE,
                ELEMENTAL_GEM_SCALE,
                TOTAL_GEM_BUDGET,
                TOTAL_ROWS,
            )
            from ...solver.scoring import _extract_base_stats, fg_baseline_params, FG_CACHE, _force_greats_counts_to_dict
            from ...solver.taichi_gem_solver import solve_force_greats_finder_gpu

            meta = calc_song.get("metadata", {}) or {}
            p_color = meta.get("Primary Color", "")
            s_color = meta.get("Secondary Color", "")
            
            import numpy as np
            from ...helpers.fg_utils import calculate_section_caps, collect_analytical_breakpoints
            from ...solver.analytical_fg import create_scorer_from_calc_song

            # Helper: apply gem allocations to base stats to produce a final Stats dict
            def _apply_gems_to_base(base: dict, sel_color: str, ft: int, ff: int, gem_counts: dict) -> dict:
                out = dict(base or {})
                g_pp = int((gem_counts or {}).get("Perfect Points", 0))
                g_cm = int((gem_counts or {}).get("Combo Multiplier", 0))
                g_fm = int((gem_counts or {}).get("Fever Multiplier", 0))
                g_ov = int((gem_counts or {}).get("Element Overflow", 0))

                out["Perfect Points"] = out.get("Perfect Points", 0) + g_pp * GEM_SCALE_NORMAL
                out["Combo Multiplier"] = out.get("Combo Multiplier", 0) + g_cm * GEM_SCALE_NORMAL
                out["Fever Multiplier"] = out.get("Fever Multiplier", 0) + g_fm * GEM_SCALE_FEVER
                out["Fever Time"] = out.get("Fever Time", 0) + int(ft) * GEM_SCALE_FEVER
                out["Fever Fill Rate"] = out.get("Fever Fill Rate", 0) + int(ff) * GEM_SCALE_FEVER

                # Stat-to-element contributions
                out["Chill"] = out.get("Chill", 0) + g_pp * GEM_STAT_TO_ELEMENT_SCALE
                out["Flow"] = out.get("Flow", 0) + g_cm * GEM_STAT_TO_ELEMENT_SCALE
                out["Rush"] = out.get("Rush", 0) + g_fm * GEM_STAT_TO_ELEMENT_SCALE
                out["Beat"] = out.get("Beat", 0) + int(ft) * GEM_STAT_TO_ELEMENT_SCALE
                out["Vibe"] = out.get("Vibe", 0) + int(ff) * GEM_STAT_TO_ELEMENT_SCALE

                # Overflow gems
                if sel_color:
                    out[sel_color] = out.get(sel_color, 0) + g_ov * ELEMENTAL_GEM_SCALE
                return out

            def _is_cached_force_valid_for_finder(cached_force_obj, expected_selected_element, center_ft, center_ff):
                if not isinstance(cached_force_obj, dict):
                    return False
                details = cached_force_obj.get("details") or {}
                if not isinstance(details, dict):
                    return False
                fg_meta = details.get("ForceGreats") or {}
                if not isinstance(fg_meta, dict):
                    return False
                algo_ver = fg_meta.get("algo_version")
                if int(algo_ver or 0) != 3:
                    return False
                if not fg_meta.get("finder") or not fg_meta.get("gpu"):
                    return False
                cached_sel = details.get("SelectedElement") or details.get("Selected Element") or ""
                if expected_selected_element and cached_sel and cached_sel != expected_selected_element:
                    return False
                # Require same FT/FF center to ensure same search window assumptions
                try:
                    if int(fg_meta.get("center_ft", -999)) != int(center_ft):
                        return False
                    if int(fg_meta.get("center_ff", -999)) != int(center_ff):
                        return False
                except Exception:
                    return False
                return True

            # Group work by (selected_element, n_sections, max_per_section)
            groups = {}
            group_centers = {} # key -> set of (center_ft, center_ff)
            group_items = []

            # PERF counters (opt-in; enabled via caller)
            t_collect_sec = 0.0
            t_cfg_build_sec = 0.0
            t_gpu_calls_sec = 0.0
            t_cache_check_sec = 0.0
            t_genome_build_sec = 0.0
            t_result_apply_sec = 0.0
            n_gpu_calls = 0
            fg_cache_hits = 0
            fg_cache_misses = 0
            db_cached_reuse = 0
            no_eval_skips = 0
            gpu_call_shapes = []  # sample a few: (n_genomes, n_cfg, n_ftff, n_sections)

            # Collect candidates up to compute budget
            _t_collect0 = time.perf_counter() if perf else 0.0
            for entry in loadout_entries.values():
                if computed >= max_fg_compute:
                    break

                cached_force = entry.get("force")
                expected_sel = None
                try:
                    det0 = entry.get("details") or {}
                    expected_sel = det0.get("SelectedElement") or det0.get("Selected Element") or meta_primary_color
                except Exception:
                    expected_sel = meta_primary_color

                # Keep legacy cache reuse behavior for non-finder only. Finder recomputes for correctness.
                if (
                    cached_force
                    and (cached_force.get("score") or entry.get("fg_score"))
                    and (not force_greats_finder)
                ):
                    fg_variants.append({
                        "data": cached_force.get("details", {}),
                        "gear": entry.get("gear", []),
                        "minis": entry.get("minis", []),
                        "score": cached_force.get("score", entry.get("fg_score", 0)),
                    })
                    continue

                eval_data = entry.get("eval_data")
                if not eval_data:
                    det = entry.get("details") or {}
                    stats = det.get("Stats") or {}
                    if not stats:
                        no_eval_skips += 1
                        continue
                    eval_data = {
                        "Stats": stats,
                        "Selected Element": det.get("SelectedElement") or det.get("Selected Element") or meta_primary_color,
                        "FT": det.get("FT", 0),
                        "FF": det.get("FF", 0),
                        "GemCounts": det.get("GemCounts", {}),
                    }

                stats = eval_data.get("Stats", {}) or {}
                sel_color = eval_data.get("Selected Element", meta_primary_color)
                center_ft = int(eval_data.get("FT", 0) or 0)
                center_ff = int(eval_data.get("FF", 0) or 0)

                # Reuse DB cached FG finder results when compatible (major compute savings)
                if cached_force and _is_cached_force_valid_for_finder(cached_force, expected_sel, center_ft, center_ff):
                    db_cached_reuse += 1
                    fg_variants.append({
                        "data": cached_force.get("details", {}),
                        "gear": entry.get("gear", []),
                        "minis": entry.get("minis", []),
                        "score": cached_force.get("score", entry.get("fg_score", 0)),
                    })
                    continue
                gem_counts_existing = eval_data.get("GemCounts", {}) or {}

                # Extract base stats (pre-gem) so the GPU solver can allocate gems correctly
                base_stats = _extract_base_stats(stats, gem_counts_existing, sel_color, center_ft, center_ff)

                # Determine how many non-fever sections exist and the notes-to-fill baseline
                n_sections, non_fever_base = fg_baseline_params(base_stats, calc_song, ref_arrays)
                if n_sections <= 0:
                    continue
                max_per_section = min(int(non_fever_base or 0), 15)

                key = (str(sel_color), int(n_sections), int(max_per_section))
                sig = stats_signature(base_stats, calc_song, sel_color)
                unique_stats_seen.add(sig)

                groups.setdefault(key, {}).setdefault(sig, []).append((entry, eval_data, base_stats))
                group_centers.setdefault(key, set()).add((int(center_ft), int(center_ff)))
                computed += 1

            if perf:
                t_collect_sec = time.perf_counter() - _t_collect0

            # Precompute gap and fever_activations ONCE per song
            # Use a representative middle point (80, 80) - typical gem allocation
            song_gap = None
            song_fever_activations = None
            try:
                from ...solver.fever_timeline import get_song_timeline_grid
                from ...helpers.fg_utils import vectorized_calculate_section_caps_grid
                grid = get_song_timeline_grid(calc_song, ref_arrays)
                
                # Use conservative estimates for search space bounds:
                # 1. Maximize gap (Low FT, High FF) -> Index 0, TOTAL_ROWS
                # Low FT (short fevers) + High FF (fast fill) = Fevers finish earliest -> Max Gap
                # This ensures we find opportunities even if they only exist at high stats.
                # Note: Previous (0,0) was flawed (Low FF pushes fevers late -> small gap).
                _, _, _, acts_max, last_fever_end_early = grid.get_timeline(0, TOTAL_ROWS)
                
                song_gap = max(0, grid.total_notes - last_fever_end_early)
                song_fever_activations = acts_max

                print(f"[FG] Search bounds (at 0,{TOTAL_ROWS}) -> Gap: {song_gap}, Activations: {song_fever_activations}")

                # VECTORIZED: Precompute pair_caps_grid using NumPy (~100x faster)
                # Uses the precomputed gap/activations arrays from the grid
                _t_grid0 = time.perf_counter() if perf else 0.0
                
                gpu_arrays = grid.to_gpu_arrays()
                gap_grid = gpu_arrays['gap']  # (161, 161) int32
                acts_grid = gpu_arrays['fever_activations']  # (161, 161) int32
                
                # Vectorized computation - replaces 26K loop with NumPy broadcasting
                pair_caps_grid = vectorized_calculate_section_caps_grid(
                    gap_grid, acts_grid, max_per_section=100
                )
                
                if perf:
                    print(f"[PERF] FG Pair Caps Grid precompute (VECTORIZED): {(time.perf_counter() - _t_grid0)*1000:.1f}ms")
            except Exception as e:
                print(f"[FG] Gap/Grid precomputation FAILED: {type(e).__name__}: {e}")
                # Fallback to permissive caps (50) to avoid 0-clamping on GPU
                pair_caps_grid = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1, 16), 50, dtype=np.int32)

            # Generate SMART configs using Analytic Breakpoint Pruning
            # This scans the grid to find only the counts that fundamentally change fever coverage.
            # (Now moved inside group loop to be context-aware)

            # Process each group in GPU batches
            for (sel_color, n_sections, max_per_section), sig_map in groups.items():
                _t_cfg0 = time.perf_counter() if perf else 0.0

                # Build Union of FT/FF windows
                centers = group_centers.get((sel_color, n_sections, max_per_section), [])
                needed_pairs = set()
                for c_ft, c_ff in centers:
                    start_ft = max(0, c_ft - 5)
                    end_ft = min(TOTAL_GEM_BUDGET, c_ft + 5)
                    start_ff = max(0, c_ff - 5)
                    end_ff = min(TOTAL_GEM_BUDGET, c_ff + 5)
                    for ft in range(start_ft, end_ft + 1):
                        for ff in range(start_ff, end_ff + 1):
                            if ft + ff <= TOTAL_GEM_BUDGET:
                                needed_pairs.add((ft, ff))

                if len(needed_pairs) == 0:
                    ftff_pairs = []
                    stat_bounds = (0, 0, 0, 0) # Should not happen
                else:
                    ft_vals = [p[0] for p in needed_pairs]
                    ff_vals = [p[1] for p in needed_pairs]
                    # Map gem counts to stat indices for collect_analytic_configs.
                    # Groups may contain loadouts with different base stats, so we need to find
                    # the union of their active stat regions.
                    # FT_Stat = Base + Gems*3, where Base varies per loadout.
                    
                    min_base_ft = 999
                    max_base_ft = -999
                    min_base_ff = 999
                    max_base_ff = -999
                    
                    # sig_map: sig -> list of (entry, eval, base_stats)
                    for _, items in sig_map.items():
                        for _, _, bs in items: 
                            bft = bs.get("Fever Time", 0)
                            bff = bs.get("Fever Fill Rate", 0)
                            if bft < min_base_ft: min_base_ft = bft
                            if bft > max_base_ft: max_base_ft = bft
                            if bff < min_base_ff: min_base_ff = bff
                            if bff > max_base_ff: max_base_ff = bff
                    
                    # Calculate stat bounds reachable by this group
                    # Max gems ~10, Min gems 0.
                    # But we specifically care about the 'needed_pairs' search window.
                    # needed_pairs has (ft_gem, ff_gem).
                    # MinStat = MinBase + MinGem*3
                    # MaxStat = MaxBase + MaxGem*3
                    
                    min_gem_ft = min(ft_vals)
                    max_gem_ft = max(ft_vals)
                    min_gem_ff = min(ff_vals)
                    max_gem_ff = max(ff_vals)
                    
                    # Constants
                    GEM_SCALE = 3 
                    
                    bound_min_ft = max(0, min_base_ft + min_gem_ft * GEM_SCALE - 5) # -5 margin
                    bound_max_ft = min(TOTAL_ROWS, max_base_ft + max_gem_ft * GEM_SCALE + 5)
                    bound_min_ff = max(0, min_base_ff + min_gem_ff * GEM_SCALE - 5)
                    bound_max_ff = min(TOTAL_ROWS, max_base_ff + max_gem_ff * GEM_SCALE + 5)
                    
                    stat_bounds = (bound_min_ft, bound_max_ft, bound_min_ff, bound_max_ff)

                ftff_pairs = sorted(list(needed_pairs))
                # Safety cap (should fit in 1024, but if not, we truncate to avoid crash)
                if len(ftff_pairs) > 1024:
                    print(f"[ForceGreats][GPU] Warning: FT/FF union size {len(ftff_pairs)} > 1024. Truncating.")
                    ftff_pairs = ftff_pairs[:1024]

                # Per-Group Analytic Config Collection using PURE MATH (100x faster)
                # Create analytical scorer once per song (cached implicitly by calc_song)
                if 'fg_scorer' not in locals():
                    fg_scorer = create_scorer_from_calc_song(calc_song, ref_arrays)
                    print(f"[FG] Created AnalyticalFGScorer: {fg_scorer.total_notes} notes, head_len={fg_scorer.head_len}")
                
                # Get breakpoints using pure math (no simulation needed)
                group_counts_list = collect_analytical_breakpoints(fg_scorer, n_sections)
                
                if not group_counts_list:
                    group_counts_list = [tuple([0] * song_fever_activations)]

                # Already sliced to n_sections by collect_analytical_breakpoints
                # Just deduplicate and sort
                if n_sections <= 0:
                    counts_list = [()]
                else:
                    counts_list = sorted(list(set(group_counts_list)))
                    
                if perf:
                    t_cfg_build_sec += time.perf_counter() - _t_cfg0
                
                # ... (rest of loop uses counts_list)
                if perf:
                    t_cfg_build_sec += time.perf_counter() - _t_cfg0

                # Color flags for GPU
                is_p_pp = 1 if "Chill" == p_color else 0
                is_s_pp = 1 if "Chill" == s_color else 0
                is_p_cm = 1 if "Flow" == p_color else 0
                is_s_cm = 1 if "Flow" == s_color else 0
                is_p_fm = 1 if "Rush" == p_color else 0
                is_s_fm = 1 if "Rush" == s_color else 0
                is_p_ft = 1 if "Beat" == p_color else 0
                is_s_ft = 1 if "Beat" == s_color else 0
                is_p_ff = 1 if "Vibe" == p_color else 0
                is_s_ff = 1 if "Vibe" == s_color else 0
                is_p_ov = 1 if str(sel_color) == p_color else 0
                is_s_ov = 1 if str(sel_color) == s_color else 0

                sig_list = list(sig_map.keys())

                # Chunk unique genomes to fit GPU MAX_GENOMES (1024)
                idx0 = 0
                while idx0 < len(sig_list):
                    chunk_sigs = sig_list[idx0:idx0 + 1024]
                    idx0 += 1024

                    # Check in-memory FG_CACHE first
                    _t_cache0 = time.perf_counter() if perf else 0.0
                    pending = []
                    pending_sigs = []
                    for sig in chunk_sigs:
                        # Skip cache check in batch mode since center varies per-entry within signature groups.
                        # GPU computation is fast enough for uncached entries.
                        rep = sig_map[sig][0][2]
                        pending.append(rep)
                        pending_sigs.append(sig)

                    if perf:
                        t_cache_check_sec += time.perf_counter() - _t_cache0

                    if not pending:
                        continue

                    _t_genome0 = time.perf_counter() if perf else 0.0
                    
                    # FAST PATH: Build numpy array directly instead of list[dict]
                    # Column order: pp, cm, fm, p_val, s_val, ft_stat, ff_stat
                    n_pending = len(pending)
                    genome_stats_arr = np.zeros((n_pending, 7), dtype=np.int32)
                    for i, bs in enumerate(pending):
                        genome_stats_arr[i, 0] = int(bs.get("Perfect Points", 0))
                        genome_stats_arr[i, 1] = int(bs.get("Combo Multiplier", 0))
                        genome_stats_arr[i, 2] = int(bs.get("Fever Multiplier", 0))
                        genome_stats_arr[i, 3] = int(bs.get(p_color, 0))  # p_val
                        genome_stats_arr[i, 4] = int(bs.get(s_color, 0))  # s_val
                        genome_stats_arr[i, 5] = int(bs.get("Fever Time", 0))  # ft_stat
                        genome_stats_arr[i, 6] = int(bs.get("Fever Fill Rate", 0))  # ff_stat

                    timestamps = calc_song["song_data"]["timestamps"]
                    long_notes = int(calc_song.get("metadata", {}).get("Long Notes", 0) or 0)
                    last_note_time = float(calc_song.get("metadata", {}).get("Last Note Time", 0) or 0.0)
                    if perf:
                        t_genome_build_sec += time.perf_counter() - _t_genome0

                    _t_gpu0 = time.perf_counter() if perf else 0.0
                    # Use return_raw=True for numpy results (skip dict building in API)
                    gpu_results = solve_force_greats_finder_gpu(
                        genome_stats_arr,  # numpy array instead of list[dict]
                        timestamps,
                        long_notes,
                        last_note_time,
                        counts_list,
                        ftff_pairs,
                        n_sections=n_sections,
                        is_p_ft=is_p_ft, is_s_ft=is_s_ft,
                        is_p_ff=is_p_ff, is_s_ff=is_s_ff,
                        is_p_pp=is_p_pp, is_s_pp=is_s_pp,
                        is_p_cm=is_p_cm, is_s_cm=is_s_cm,
                        is_p_fm=is_p_fm, is_s_fm=is_s_fm,
                        is_p_ov=is_p_ov, is_s_ov=is_s_ov,
                        ref_arrays=ref_arrays,
                        total_budget=TOTAL_GEM_BUDGET,
                        gem_scale_fever=GEM_SCALE_FEVER,
                        pair_caps_grid=pair_caps_grid,
                        return_raw=True,  # Return numpy arrays, not list[dict]
                    )
                    if perf:
                        t_gpu_calls_sec += time.perf_counter() - _t_gpu0
                        n_gpu_calls += 1
                        if len(gpu_call_shapes) < 12:
                            gpu_call_shapes.append(
                                (n_pending, len(counts_list), len(ftff_pairs), int(n_sections))
                            )

                    # Apply results back to all entries sharing the same signature
                    # gpu_results is now a dict of numpy arrays (from return_raw=True)
                    _t_apply0 = time.perf_counter() if perf else 0.0
                    for idx, (sig, bs) in enumerate(zip(pending_sigs, pending)):
                        # Index into raw numpy arrays (much faster than dict.get)
                        cfg_idx = int(gpu_results["cfg_idx"][idx])
                        final_score = int(gpu_results["final_score"][idx])
                        base_score = int(gpu_results["base_score"][idx])
                        ft_val = int(gpu_results["FT"][idx])
                        ff_val = int(gpu_results["FF"][idx])
                        g_pp = int(gpu_results["g_pp"][idx])
                        g_cm = int(gpu_results["g_cm"][idx])
                        g_fm = int(gpu_results["g_fm"][idx])
                        g_ov = int(gpu_results["g_ov"][idx])
                        score_penalty = int(gpu_results["score_penalty"][idx])
                        fill_penalty = int(gpu_results["fill_penalty"][idx])
                        
                        cfg_counts = list(counts_list[cfg_idx]) if 0 <= cfg_idx < len(counts_list) else []

                        # Build gem_counts dict
                        gem_counts = {
                            "Perfect Points": g_pp,
                            "Combo Multiplier": g_cm,
                            "Fever Multiplier": g_fm,
                            "Element Overflow": g_ov,
                        }

                        final_stats = _apply_gems_to_base(
                            bs,
                            str(sel_color),
                            ft_val,
                            ff_val,
                            gem_counts,
                        )

                        fg_info = {
                            "enabled": True,
                            "algo_version": 3,
                            "config": _force_greats_counts_to_dict(cfg_counts, max(2, len(cfg_counts))),
                            "base_score": base_score,
                            "final_score": final_score,
                            "score_penalty": score_penalty,
                            "fill_penalty": fill_penalty,
                            "total_penalty": score_penalty + fill_penalty,
                            "num_non_fever_sections": int(n_sections),
                            "penalty_analysis": {},
                            "finder": True,
                            "gpu": True,
                            "center_ft": int(center_ft),
                            "center_ff": int(center_ff),
                            "search_radius": 5,
                        }

                        fg_variant = {
                            "Score": final_score,
                            "FT": ft_val,
                            "FF": ff_val,
                            "GemCounts": gem_counts,
                            "Stats": final_stats,
                            "Selected Element": str(sel_color),
                            "ForceGreats": {**fg_info, "variant_applied": True},
                        }

                        # Store results in cache for future lookups.

                        for entry, eval_data, _ in sig_map.get(sig, []):
                            # Update entry
                            fg_variants.append({
                                "data": fg_variant,
                                "gear": entry.get("gear", []),
                                "minis": entry.get("minis", []),
                                "score": final_score,
                            })
                            entry["force"] = {
                                "score": final_score,
                                "gear": _names_list(entry.get("gear", [])),
                                "minis": _names_list(entry.get("minis", [])),
                                "details": build_details_fn(fg_variant),
                            }
                            entry["fg_score"] = final_score

                            # Cache under the entry's specific requirements so future single lookups find it
                            c_ft = int(eval_data.get("FT", 0) or 0)
                            c_ff = int(eval_data.get("FF", 0) or 0)
                            FG_CACHE[(sig, str(sel_color), c_ft, c_ff, int(n_sections), int(max_per_section))] = fg_variant
                    if perf:
                        t_result_apply_sec += time.perf_counter() - _t_apply0

            print(f"[ForceGreats] {len(unique_stats_seen)} unique stat signatures, {len(fg_variants)} FG variants generated (computed {computed}, budget {max_fg_compute})")
            if perf:
                try:
                    print(
                        "[PERF] ForceGreatsFinder(GPU): "
                        f"collect={t_collect_sec:.3f}s cfg_build={t_cfg_build_sec:.3f}s "
                        f"gpu_calls={t_gpu_calls_sec:.3f}s n_gpu_calls={n_gpu_calls} "
                        f"FG_CACHE(hit={fg_cache_hits},miss={fg_cache_misses}) "
                        f"db_reuse={db_cached_reuse} no_eval_skips={no_eval_skips} "
                        f"groups={len(groups)} unique_sigs={len(unique_stats_seen)}"
                    )
                    print(
                        "[PERF] FG Detailed: "
                        f"cache_check={t_cache_check_sec*1000:.1f}ms "
                        f"genome_build={t_genome_build_sec*1000:.1f}ms "
                        f"result_apply={t_result_apply_sec*1000:.1f}ms"
                    )
                    if gpu_call_shapes:
                        print(
                            "[PERF] FG GPU call shapes (n_genomes,n_cfg,n_ftff,n_sections): "
                            f"{gpu_call_shapes}"
                        )
                except Exception:
                    pass
            return fg_variants
        except Exception as e:
            print(f"[ForceGreats][GPU] Batch FG finder failed; falling back to CPU per-loadout: {e}")
            # Reset state to allow CPU manual loop to run from scratch
            fg_variants = []
            computed = 0
            unique_stats_seen = set()
    for entry in loadout_entries.values():
        if computed >= max_fg_compute:
            break

        def _is_cached_force_valid(cached_force_obj, expected_selected_element, center_ft, center_ff, finder_enabled):
            """
            Validate that a DB-cached ForceGreats payload is compatible with the current code/config.
            This prevents stale FG results (from older algorithms or wrong overflow target) from
            presenting as score inflation.
            """
            if not isinstance(cached_force_obj, dict):
                return False
            details = cached_force_obj.get("details") or {}
            if not isinstance(details, dict):
                return False
            fg_meta = details.get("ForceGreats") or {}
            if not isinstance(fg_meta, dict):
                return False
            # Require version tag to avoid trusting old/broken FG payloads
            algo_ver = fg_meta.get("algo_version")
            if algo_ver is None:
                return False
            if int(algo_ver or 0) != 3:
                return False
            if finder_enabled:
                # Finder results must be from finder path to be reused safely
                if not fg_meta.get("finder"):
                    return False
                try:
                    if int(fg_meta.get("center_ft", -999)) != int(center_ft):
                        return False
                    if int(fg_meta.get("center_ff", -999)) != int(center_ff):
                        return False
                except Exception:
                    return False
            # Guard against overflow-target mismatch (affects gem optimization and score)
            cached_sel = details.get("SelectedElement") or details.get("Selected Element") or ""
            if expected_selected_element and cached_sel and cached_sel != expected_selected_element:
                return False
            return True

        cached_force = entry.get("force")
        expected_sel = None
        expected_center_ft = 0
        expected_center_ff = 0
        try:
            det0 = entry.get("details") or {}
            expected_sel = det0.get("SelectedElement") or det0.get("Selected Element") or meta_primary_color
            expected_center_ft = det0.get("FT", 0) or 0
            expected_center_ff = det0.get("FF", 0) or 0
        except Exception:
            expected_sel = meta_primary_color

        # Reuse cached force results if they are compatible with current algo/version.
        if (
            cached_force
            and (cached_force.get("score") or entry.get("fg_score"))
            and _is_cached_force_valid(cached_force, expected_sel, expected_center_ft, expected_center_ff, force_greats_finder)
        ):
            fg_variants.append({
                "data": cached_force.get("details", {}),
                "gear": entry.get("gear", []),
                "minis": entry.get("minis", []),
                "score": cached_force.get("score", entry.get("fg_score", 0)),
            })
            # Skipped entries do not consume compute budget
            continue

        eval_data = entry.get("eval_data")
        if not eval_data:
            det = entry.get("details") or {}
            stats = det.get("Stats") or {}
            if not stats:
                continue
            eval_data = {
                "Stats": stats,
                "Selected Element": det.get("SelectedElement") or det.get("Selected Element") or meta_primary_color,
                "FT": det.get("FT", 0),
                "FF": det.get("FF", 0),
                "GemCounts": det.get("GemCounts", {}),
            }

        stats = eval_data.get("Stats", {})
        sel_color = eval_data.get("Selected Element", meta_primary_color)
        sig = stats_signature(stats, calc_song, sel_color)
        unique_stats_seen.add(sig)

        fg_variant = apply_force_greats_to_result(
            eval_data,
            calc_song,
            ref_arrays,
            manual_counts=manual_counts,
            use_finder=force_greats_finder,
            use_gpu=use_gpu,
        )
        computed += 1
        if fg_variant:
            fg_variants.append({
                "data": fg_variant,
                "gear": entry.get("gear", []),
                "minis": entry.get("minis", []),
                "score": fg_variant.get("Score", 0),
            })
            entry["force"] = {
                "score": fg_variant.get("Score", 0),
                "gear": _names_list(entry.get("gear", [])),
                "minis": _names_list(entry.get("minis", [])),
                "details": build_details_fn(fg_variant),
            }
            entry["fg_score"] = fg_variant.get("Score", 0)
    print(f"[ForceGreats] {len(unique_stats_seen)} unique stat signatures, {len(fg_variants)} FG variants generated (computed {computed}, budget {max_fg_compute})")

    return fg_variants
