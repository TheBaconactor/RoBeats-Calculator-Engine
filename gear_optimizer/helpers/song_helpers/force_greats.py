"""
Song Helpers - Force Greats - Force greats processing and optimization.

This module provides force greats operations:
- process_force_greats: Apply force greats to loadouts with GPU/CPU support
"""

import os
import threading
import time
from typing import TYPE_CHECKING, Optional

from ...solver.scoring import apply_force_greats_to_result
from ...core.utils import stats_signature
from ...solver.scoring.force_greats import FORCE_GREATS_ALGO_VERSION

if TYPE_CHECKING:
    from gear_optimizer.solver.gpu_service import GpuServiceClient


_FG_GPU_SEQUENCE_LOCK = threading.Lock()


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
    fg_search_radius: int | None = None,
    perf_timing: bool = False,
    gpu_client: Optional["GpuServiceClient"] = None,
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

    # NOTE:
    # Historically we routed the *entire* helper to the GPU-owner thread to avoid
    # touching Taichi from non-owner threads. That guarantees safety, but it also
    # makes the GPU-owner thread do a lot of CPU work (grouping, dict building,
    # cache checks, result application), which shows up as GPU utilization spikes
    # and idle gaps during in-flight FG interleaving.
    #
    # The GPU Finder fast path below can submit Taichi work via `gpu_client`, so
    # we default to doing CPU prep locally and sending only GPU kernels to the
    # executor. Set `FG_ROUTE_PROCESS_FORCE_GREATS=1` to force legacy behavior.
    if (
        gpu_client is not None
        and bool(use_gpu)
        and str(os.environ.get("FG_ROUTE_PROCESS_FORCE_GREATS", "0")).strip() == "1"
    ):
        return gpu_client.submit_process_force_greats(
            loadout_entries,
            manual_force_greats,
            force_greats_finder,
            force_greats_config,
            calc_song,
            ref_arrays,
            meta_primary_color,
            build_details_fn,
            db_loadouts_full_count,
            use_gpu=use_gpu,
            fg_search_radius=fg_search_radius,
            perf_timing=perf_timing,
            gpu_client=None,
        ).future.result()

    manual_counts = force_greats_config if (manual_force_greats and not force_greats_finder) else []

    def _names_list(items):
        names = []
        for it in items or []:
            if isinstance(it, dict):
                names.append(it.get("Name", ""))
            else:
                names.append(str(it) if it else "")
        return names

    # FG processing: Process ALL loadouts (DB + GA) without artificial budget limits.
    # The budget was previously used to limit compute, but this caused incomplete FG coverage.
    computed = 0
    print(f"[ForceGreats] Processing {len(loadout_entries)} unique loadouts (DB + GA)...")

    # ------------------------------------------------------------------
    # GPU Finder Fast Path:
    # When ForceGreatsFinder is enabled and GPU mode is on, batch/dedupe
    # across loadouts and run the full FG finder on the GPU.
    # ------------------------------------------------------------------
    if use_gpu and force_greats_finder:
        lock_acquired = False
        if gpu_client is not None:
            _FG_GPU_SEQUENCE_LOCK.acquire()
            lock_acquired = True
        try:
            from ...core.constants import (
                GEM_SCALE_NORMAL,
                GEM_SCALE_FEVER,
                GEM_STAT_TO_ELEMENT_SCALE,
                ELEMENTAL_GEM_SCALE,
                TOTAL_GEM_BUDGET,
                TOTAL_ROWS,
                FG_SEARCH_RADIUS,
            )
            from ...solver.scoring import (
                _extract_base_stats,
                fg_baseline_params,
                FG_CACHE,
                _force_greats_counts_to_dict,
            )
            from ...solver.taichi_gem_solver import solve_force_greats_finder_gpu

            meta = calc_song.get("metadata", {}) or {}
            p_color = meta.get("Primary Color", "")
            s_color = meta.get("Secondary Color", "")

            import numpy as np
            from ...helpers.fg_utils import (
                collect_analytical_breakpoints,
                iter_analytical_breakpoint_groups,
            )
            from ...solver.analytical_fg import create_scorer_from_calc_song
            from ...solver.taichi_gem.force_greats import fields as fg_fields
            from ...solver.taichi_gem.force_greats.api import (
                fg_reset_global_best,
                fg_download_global_best,
            )
            from ...solver.gpu_executor import GpuRequestType

            def _submit_fg_reset_global_best(n_genomes: int, *, blocking: bool = True):
                if gpu_client is not None:
                    fut = gpu_client.submit(
                        GpuRequestType.FG_RESET_GLOBAL_BEST,
                        {"n_genomes": int(n_genomes)},
                    ).future
                    if blocking:
                        fut.result()
                        return None
                    return fut
                fg_reset_global_best(int(n_genomes))
                return None

            def _submit_fg_download_global_best(n_genomes: int, *, blocking: bool = True):
                if gpu_client is not None:
                    fut = gpu_client.submit(
                        GpuRequestType.FG_DOWNLOAD_GLOBAL_BEST,
                        {"n_genomes": int(n_genomes)},
                    ).future
                    return fut.result() if blocking else fut
                return fg_download_global_best(int(n_genomes))

            def _submit_solve_force_greats_finder(*args, blocking: bool = True, **kwargs):
                if gpu_client is not None:
                    fut = gpu_client.submit_solve_force_greats_finder(*args, **kwargs).future
                    return fut.result() if blocking else fut
                return solve_force_greats_finder_gpu(*args, **kwargs)

            fg_async_max_inflight = 8
            try:
                fg_async_max_inflight = int(os.environ.get("FG_ASYNC_MAX_INFLIGHT", "8"))
            except Exception:
                fg_async_max_inflight = 8
            fg_async_max_inflight = max(1, int(fg_async_max_inflight))

            fg_async_tasks_per_request_default = 8
            if gpu_client is not None and "FG_ASYNC_TASKS_PER_REQUEST" not in os.environ:
                try:
                    in_process = False
                    try:
                        ex = getattr(gpu_client, "executor", None)
                        in_process = bool(getattr(ex, "_in_process_queues", False))
                    except Exception:
                        in_process = False

                    if in_process:
                        # In in-process (thread-queue) mode we can batch many FT/FF chunks into
                        # a single executor request so FG runs as one contiguous GPU job
                        # (reset + solve + download) with fewer request boundaries.
                        fg_async_tasks_per_request_default = 4096
                except Exception:
                    fg_async_tasks_per_request_default = 8

            fg_async_tasks_per_request = fg_async_tasks_per_request_default
            try:
                fg_async_tasks_per_request = int(
                    os.environ.get("FG_ASYNC_TASKS_PER_REQUEST", str(fg_async_tasks_per_request_default))
                )
            except Exception:
                fg_async_tasks_per_request = fg_async_tasks_per_request_default
            fg_async_tasks_per_request = max(1, int(fg_async_tasks_per_request))
            fg_async_futures = []
            fg_tasks_batch = []

            # OPTIMIZED: Apply gem allocations to base stats with raw int values (avoids dict lookups in hot loop).
            def _apply_gems_to_base_fast(
                base: dict, sel_color: str, ft: int, ff: int, g_pp: int, g_cm: int, g_fm: int, g_ov: int
            ) -> dict:
                out = dict(base or {})
                out["Perfect Points"] = out.get("Perfect Points", 0) + g_pp * GEM_SCALE_NORMAL
                out["Combo Multiplier"] = out.get("Combo Multiplier", 0) + g_cm * GEM_SCALE_NORMAL
                out["Fever Multiplier"] = out.get("Fever Multiplier", 0) + g_fm * GEM_SCALE_FEVER
                out["Fever Time"] = out.get("Fever Time", 0) + ft * GEM_SCALE_FEVER
                out["Fever Fill Rate"] = out.get("Fever Fill Rate", 0) + ff * GEM_SCALE_FEVER
                out["Chill"] = out.get("Chill", 0) + g_pp * GEM_STAT_TO_ELEMENT_SCALE
                out["Flow"] = out.get("Flow", 0) + g_cm * GEM_STAT_TO_ELEMENT_SCALE
                out["Rush"] = out.get("Rush", 0) + g_fm * GEM_STAT_TO_ELEMENT_SCALE
                out["Beat"] = out.get("Beat", 0) + ft * GEM_STAT_TO_ELEMENT_SCALE
                out["Vibe"] = out.get("Vibe", 0) + ff * GEM_STAT_TO_ELEMENT_SCALE
                if sel_color:
                    out[sel_color] = out.get(sel_color, 0) + g_ov * ELEMENTAL_GEM_SCALE
                return out

            def _fp_targets_to_forced_counts(
                fp_counts: list,
                base_stats: dict,
                ft_gems: int,
                ff_gems: int,
                scorer,
            ) -> list:
                if not fp_counts:
                    return []
                ft_stat = int(base_stats.get("Fever Time", 0)) + int(ft_gems) * GEM_SCALE_FEVER
                ff_stat = int(base_stats.get("Fever Fill Rate", 0)) + int(ff_gems) * GEM_SCALE_FEVER
                non_fever_base, _, _, raw_fever_fill = scorer.get_fever_params(ft_stat, ff_stat)
                if non_fever_base <= 0:
                    return [0] * len(fp_counts)
                import math

                base_ceil = math.ceil(raw_fever_fill)

                def _min_forced_for_fp(fp_target: int) -> int:
                    if fp_target <= 0:
                        return 0
                    delta = (base_ceil + fp_target - 1) - raw_fever_fill
                    if delta < 0:
                        return 0
                    return int(math.floor(delta * 2.0) + 1)

                forced_counts = []
                for fp in fp_counts:
                    fp_i = int(fp)
                    forced = _min_forced_for_fp(fp_i)
                    if forced > non_fever_base:
                        forced = non_fever_base
                    forced_counts.append(int(forced))
                return forced_counts

            def _apply_gpu_results_to_entries(
                *,
                pending_sigs: list,
                pending: list,
                sig_map: dict,
                sel_color: str,
                n_sections: int,
                max_per_section: int,
                counts_list,
                fg_scorer,
                result_final,
                result_base,
                result_cfg_idx,
                result_cfg_counts,
                result_ft,
                result_ff,
                result_g_pp,
                result_g_cm,
                result_g_fm,
                result_g_ov,
                result_score_penalty,
                result_fill_penalty,
            ) -> None:
                nonlocal t_result_apply_sec

                _t_apply0 = time.perf_counter() if perf else 0.0
                for idx, (sig, bs) in enumerate(zip(pending_sigs, pending)):
                    final_score = int(result_final[idx])
                    base_score = int(result_base[idx])
                    ft_val = int(result_ft[idx])
                    ff_val = int(result_ff[idx])
                    g_pp = int(result_g_pp[idx])
                    g_cm = int(result_g_cm[idx])
                    g_fm = int(result_g_fm[idx])
                    g_ov = int(result_g_ov[idx])
                    score_penalty = int(result_score_penalty[idx])
                    fill_penalty = int(result_fill_penalty[idx])
                    _ = score_penalty, fill_penalty

                    if result_cfg_counts is not None:
                        cfg_counts = list(result_cfg_counts[idx]) if result_cfg_counts[idx] else []
                    else:
                        cfg_idx = int(result_cfg_idx[idx]) if result_cfg_idx is not None else -1
                        cfg_counts = list(counts_list[cfg_idx]) if 0 <= cfg_idx < len(counts_list) else []

                    forced_counts = cfg_counts
                    if cfg_counts and fg_scorer is not None:
                        try:
                            forced_counts = _fp_targets_to_forced_counts(cfg_counts, bs, ft_val, ff_val, fg_scorer)
                        except Exception:
                            forced_counts = cfg_counts

                    gem_counts = {
                        "Perfect Points": g_pp,
                        "Combo Multiplier": g_cm,
                        "Fever Multiplier": g_fm,
                        "Element": g_ov,
                    }

                    final_stats = _apply_gems_to_base_fast(
                        bs,
                        str(sel_color),
                        ft_val,
                        ff_val,
                        g_pp,
                        g_cm,
                        g_fm,
                        g_ov,
                    )

                    fg_info = {
                        "config": _force_greats_counts_to_dict(forced_counts, max(2, len(forced_counts))),
                        "final_score": final_score,
                    }

                    fg_variant = {
                        "BaseScore": base_score,
                        "Score": final_score,
                        "FT": ft_val,
                        "FF": ff_val,
                        "GemCounts": gem_counts,
                        "Stats": final_stats,
                        "Selected Element": str(sel_color),
                        "ForceGreats": fg_info,
                    }

                    for entry, eval_data, _ in sig_map.get(sig, []):
                        if "base_score" not in entry:
                            entry["base_score"] = entry.get("score")

                        fg_variants.append(
                            {
                                "data": fg_variant,
                                "gear": entry.get("gear", []),
                                "minis": entry.get("minis", []),
                                "score": base_score,
                                "fg_score": final_score,
                                "base_score": base_score,
                            }
                        )
                        entry["force"] = {
                            "score": final_score,
                            "gear": _names_list(entry.get("gear", [])),
                            "minis": _names_list(entry.get("minis", [])),
                            "details": build_details_fn(fg_variant),
                        }
                        entry["fg_score"] = final_score

                        c_ft = int(eval_data.get("FT", 0) or 0)
                        c_ff = int(eval_data.get("FF", 0) or 0)
                        FG_CACHE[(sig, str(sel_color), c_ft, c_ff, int(n_sections), int(max_per_section))] = fg_variant

                if perf:
                    t_result_apply_sec += time.perf_counter() - _t_apply0

            def _is_cached_force_valid_for_finder(cached_force_obj, expected_selected_element, center_ft, center_ff):
                if not isinstance(cached_force_obj, dict):
                    return False
                details = cached_force_obj.get("details") or {}
                if not isinstance(details, dict):
                    return False
                fg_meta = details.get("ForceGreats") or {}
                if not isinstance(fg_meta, dict) or not fg_meta:
                    return False
                # Must have config with section greats
                if not fg_meta.get("config"):
                    return False
                # If present, require compatible finder metadata.
                # (Backwards-compatible: older DB entries may not have these fields.)
                try:
                    if fg_meta.get("mode") not in (None, "", "finder"):
                        return False
                    algo = fg_meta.get("algo_version")
                    if algo is not None and int(algo) != int(FORCE_GREATS_ALGO_VERSION):
                        return False
                    sr = fg_meta.get("search_radius")
                    if sr is not None and int(sr) != int(os.environ.get("FG_SEARCH_RADIUS", "5")):
                        return False
                except Exception:
                    return False
                cached_sel = details.get("SelectedElement") or details.get("Selected Element") or ""
                if expected_selected_element and cached_sel and cached_sel != expected_selected_element:
                    return False
                return True

            def _iter_ftff_chunks(pairs):
                chunk_size = int(fg_fields.FG_MAX_FTFF)
                if chunk_size <= 0:
                    yield pairs
                    return
                if len(pairs) <= chunk_size:
                    yield pairs
                    return
                for i in range(0, len(pairs), chunk_size):
                    yield pairs[i : i + chunk_size]

            need_reset = False

            def _flush_fg_tasks_batch(*, batch: list[dict] | None = None, download_after: bool = False):
                nonlocal fg_tasks_batch, need_reset
                if gpu_client is None:
                    return None

                if batch is None:
                    if not fg_tasks_batch:
                        return None
                    batch = fg_tasks_batch
                    fg_tasks_batch = []

                if not batch:
                    return None
                first = batch[0] if batch else {}
                if not isinstance(first, dict):
                    return None

                placeholder_counts = first.get("counts_list")
                placeholder_pairs = first.get("ftff_pairs")
                if placeholder_counts is None or placeholder_pairs is None:
                    return None

                submit_kwargs = dict(
                    n_sections=n_sections,
                    is_p_ft=is_p_ft,
                    is_s_ft=is_s_ft,
                    is_p_ff=is_p_ff,
                    is_s_ff=is_s_ff,
                    is_p_pp=is_p_pp,
                    is_s_pp=is_s_pp,
                    is_p_cm=is_p_cm,
                    is_s_cm=is_s_cm,
                    is_p_fm=is_p_fm,
                    is_s_fm=is_s_fm,
                    is_p_ov=is_p_ov,
                    is_s_ov=is_s_ov,
                    ref_arrays=ref_arrays,
                    total_budget=TOTAL_GEM_BUDGET,
                    gem_scale_fever=GEM_SCALE_FEVER,
                    pair_caps_grid=pair_caps_grid,
                    return_raw=True,
                    accumulate_global=True,
                    fg_tasks=batch,
                )
                if "base_cfg_offset" in first:
                    try:
                        submit_kwargs["base_cfg_offset"] = int(first.get("base_cfg_offset", 0) or 0)
                    except Exception:
                        submit_kwargs["base_cfg_offset"] = 0

                if need_reset:
                    submit_kwargs["fg_reset_before"] = True
                    need_reset = False
                if download_after:
                    submit_kwargs["fg_download_after"] = True

                fut = _submit_solve_force_greats_finder(
                    genome_stats_arr,
                    timestamps,
                    great_candidates,
                    long_notes,
                    last_note_time,
                    placeholder_counts,
                    placeholder_pairs,
                    blocking=False,
                    **submit_kwargs,
                )
                fg_async_futures.append(fut)
                if len(fg_async_futures) >= fg_async_max_inflight:
                    fg_async_futures.pop(0).result()
                return fut

            # Group work by (selected_element, n_sections, max_per_section)
            groups = {}
            group_centers = {}  # key -> set of (center_ft, center_ff)

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
            per_pair_breakpoints = os.environ.get("FG_PER_FTFF_BREAKPOINTS", "1") == "1"
            if per_pair_breakpoints and not hasattr(process_force_greats, "_fg_pair_breakpoint_log"):
                process_force_greats._fg_pair_breakpoint_log = True
                print("[FG] Per-FT/FF breakpoint mode enabled (GPU finder)")

            # Collect all candidates (no budget limit)
            _t_collect0 = time.perf_counter() if perf else 0.0
            for entry in loadout_entries.values():
                cached_force = entry.get("force")
                expected_sel = None
                try:
                    det0 = entry.get("details") or {}
                    expected_sel = det0.get("SelectedElement") or det0.get("Selected Element") or meta_primary_color
                except Exception:
                    expected_sel = meta_primary_color

                # Keep legacy cache reuse behavior for non-finder only. Finder recomputes for correctness.
                if cached_force and (cached_force.get("score") or entry.get("fg_score")) and (not force_greats_finder):
                    # Preserve base score when reusing cached FG
                    base_score = entry.get("base_score") or entry.get("score", 0)
                    cached_fg_score = cached_force.get("score", entry.get("fg_score", 0))

                    fg_variants.append(
                        {
                            "data": cached_force.get("details", {}),
                            "gear": entry.get("gear", []),
                            "minis": entry.get("minis", []),
                            "score": base_score,  # Keep base score
                            "fg_score": cached_fg_score,  # Store FG score separately
                        }
                    )
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
                        "Selected Element": det.get("SelectedElement")
                        or det.get("Selected Element")
                        or meta_primary_color,
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
                    # Preserve base score when reusing cached FG
                    base_score = entry.get("base_score") or entry.get("score", 0)
                    cached_fg_score = cached_force.get("score", entry.get("fg_score", 0))

                    fg_variants.append(
                        {
                            "data": cached_force.get("details", {}),
                            "gear": entry.get("gear", []),
                            "minis": entry.get("minis", []),
                            "score": base_score,  # Keep base score
                            "fg_score": cached_fg_score,  # Store FG score separately
                        }
                    )
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

                print(
                    f"[FG] Search bounds (at 0,{TOTAL_ROWS}) -> Gap: {song_gap}, Activations: {song_fever_activations}"
                )

                # VECTORIZED: Precompute pair_caps_grid using NumPy (~100x faster)
                # Uses the precomputed gap/activations arrays from the grid
                _t_grid0 = time.perf_counter() if perf else 0.0

                gpu_arrays = grid.to_gpu_arrays_minimal()
                gap_grid = gpu_arrays["gap"]  # (161, 161) int32
                acts_grid = gpu_arrays["fever_activations"]  # (161, 161) int32

                # Vectorized computation - replaces 26K loop with NumPy broadcasting
                pair_caps_grid = vectorized_calculate_section_caps_grid(gap_grid, acts_grid, max_per_section=100)

                if perf:
                    print(
                        f"[PERF] FG Pair Caps Grid precompute (VECTORIZED): {(time.perf_counter() - _t_grid0) * 1000:.1f}ms"
                    )
            except Exception as e:
                print(f"[FG] Gap/Grid precomputation FAILED: {type(e).__name__}: {e}")
                # Fallback to permissive caps (50) to avoid 0-clamping on GPU
                pair_caps_grid = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1, 16), 50, dtype=np.int32)

            # Generate SMART configs using Analytic Breakpoint Pruning
            # This scans the grid to find only the counts that fundamentally change fever coverage.
            # (Now moved inside group loop to be context-aware)

            # When using the in-process GPU client, defer per-group downloads/apply so we can enqueue
            # all FG work first (helps keep the GPU queue full, especially across song boundaries).
            defer_group_apply = gpu_client is not None and per_pair_breakpoints
            deferred_gpu_applies: list[dict] = []

            # Process each group in GPU batches
            for (sel_color, n_sections, max_per_section), sig_map in groups.items():
                _t_cfg0 = time.perf_counter() if perf else 0.0

                # Use configurable window around loadout centers for FT/FF search.
                # - fg_search_radius < 0: full search over all FT/FF gem allocations (within TOTAL_GEM_BUDGET).
                # - Otherwise: radius in gem-space around each loadout's (FT, FF) center.
                search_radius = fg_search_radius if fg_search_radius is not None else FG_SEARCH_RADIUS
                try:
                    search_radius = int(search_radius)
                except Exception:
                    search_radius = int(FG_SEARCH_RADIUS)

                # Collect all centers from this group
                centers = group_centers.get((sel_color, n_sections, max_per_section), set())
                needed_pairs_set = set()

                # Clamp to gem budget; any radius >= TOTAL_GEM_BUDGET implies full window.
                if search_radius >= TOTAL_GEM_BUDGET:
                    search_radius = TOTAL_GEM_BUDGET

                if search_radius < 0 or search_radius >= TOTAL_GEM_BUDGET:
                    # Full window: all valid (ft, ff) pairs within the FT/FF gem budget.
                    for ft in range(0, TOTAL_GEM_BUDGET + 1):
                        max_ff = TOTAL_GEM_BUDGET - ft
                        for ff in range(0, max_ff + 1):
                            needed_pairs_set.add((ft, ff))
                else:
                    # For each center, add all pairs within +-search_radius window
                    for center_ft, center_ff in centers:
                        for ft_offset in range(-search_radius, search_radius + 1):
                            ft = center_ft + ft_offset
                            if ft < 0 or ft > TOTAL_GEM_BUDGET:
                                continue
                            for ff_offset in range(-search_radius, search_radius + 1):
                                ff = center_ff + ff_offset
                                if ff < 0 or ft + ff > TOTAL_GEM_BUDGET:
                                    continue
                                needed_pairs_set.add((ft, ff))

                ftff_pairs = sorted(needed_pairs_set)

                # Per-Group Analytic Config Collection using PURE MATH (100x faster)
                # Create analytical scorer once per song (cached implicitly by calc_song)
                if "fg_scorer" not in locals():
                    fg_scorer = create_scorer_from_calc_song(calc_song, ref_arrays)
                    print(
                        f"[FG] Created AnalyticalFGScorer: {fg_scorer.total_notes} notes, head_len={fg_scorer.head_len}"
                    )

                counts_list = None
                if not per_pair_breakpoints:
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

                # Chunk unique genomes to fit GPU MAX_GENOMES (1024).
                #
                # When running per-FT/FF breakpoints, the total kernel work scales with:
                #   n_genomes * n_ftff_pairs * n_cfg
                # If n_genomes is large and n_sections >= 3, the heuristic may switch to
                # streaming mode, producing many small breakpoint groups (lots of GPU tasks).
                # Splitting genomes into smaller batches reduces the estimated work and
                # allows more merging, cutting per-song GPU task count dramatically.
                max_genomes_per_batch = 1024
                if per_pair_breakpoints:
                    try:
                        merge_cfg_limit = int(os.environ.get("FG_MERGE_MAX_CONFIGS", "5000"))
                        merge_threads_limit = int(os.environ.get("FG_MERGE_MAX_THREADS", "50000000"))
                    except Exception:
                        merge_cfg_limit = 5000
                        merge_threads_limit = 50_000_000

                    n_pairs_for_est = max(1, int(len(ftff_pairs)))
                    est_cfgs = 1
                    for _ in range(int(n_sections)):
                        est_cfgs *= int(max_per_section) + 1
                        if est_cfgs >= int(merge_cfg_limit):
                            est_cfgs = int(merge_cfg_limit)
                            break
                    est_cfgs = max(1, int(min(int(merge_cfg_limit), int(est_cfgs * 1.25))))
                    max_by_threads = int(merge_threads_limit // max(1, (n_pairs_for_est * est_cfgs)))
                    if max_by_threads > 0:
                        max_genomes_per_batch = max(1, min(int(max_genomes_per_batch), int(max_by_threads)))

                idx0 = 0
                while idx0 < len(sig_list):
                    chunk_sigs = sig_list[idx0 : idx0 + max_genomes_per_batch]
                    idx0 += max_genomes_per_batch

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

                    song_data = calc_song.get("song_data", {}) or {}
                    timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
                    great_candidates = song_data.get("fg_great_candidate_timestamps")
                    long_notes = int(calc_song.get("metadata", {}).get("Long Notes", 0) or 0)
                    last_note_time = float(calc_song.get("metadata", {}).get("Last Note Time", 0) or 0.0)
                    if perf:
                        t_genome_build_sec += time.perf_counter() - _t_genome0

                    result_final = None
                    result_base = None
                    result_cfg_idx = None
                    result_ft = None
                    result_ff = None
                    result_g_pp = None
                    result_g_cm = None
                    result_g_fm = None
                    result_g_ov = None
                    result_score_penalty = None
                    result_fill_penalty = None
                    result_cfg_counts = None

                    if per_pair_breakpoints:
                        _t_cfg1 = time.perf_counter() if perf else 0.0
                        base_stats_pairs = {(bs.get("Fever Time", 0), bs.get("Fever Fill Rate", 0)) for bs in pending}

                        # Read merge thresholds from env (same as before)
                        try:
                            max_union_cfg = int(os.environ.get("FG_MERGE_MAX_CONFIGS", "5000"))
                            max_union_threads = int(os.environ.get("FG_MERGE_MAX_THREADS", "50000000"))
                        except Exception:
                            max_union_cfg = 5000
                            max_union_threads = 20000000

                        breakpoint_batch_size = 20
                        try:
                            n_ftff_pairs = int(len(ftff_pairs))
                        except Exception:
                            n_ftff_pairs = 0
                        if n_ftff_pairs >= 200:
                            breakpoint_batch_size = 80
                        elif n_ftff_pairs >= 120:
                            breakpoint_batch_size = 50
                        elif n_ftff_pairs >= 60:
                            breakpoint_batch_size = 30

                        # Use generator to build groups incrementally (Approach A)
                        # Generator includes integrated merge logic
                        group_gen = iter_analytical_breakpoint_groups(
                            fg_scorer,
                            n_sections,
                            ftff_pairs,
                            base_stats_pairs,
                            gem_scale_fever=GEM_SCALE_FEVER,
                            batch_size=breakpoint_batch_size,
                            merge_threshold_cfgs=max_union_cfg,
                            merge_threshold_threads=max_union_threads,
                            n_genomes=n_pending,
                        )

                        # Logging (count groups as we go)
                        logged_first = False
                        group_count = 0

                        if perf:
                            t_cfg_build_sec += time.perf_counter() - _t_cfg1

                        # GPU-Resident Accumulation: Build master config list for global indexing
                        # This allows us to look up cfg_counts after a single download at the end
                        master_configs = []  # Will be extended by each group
                        group_futures = []

                        if gpu_client is not None:
                            need_reset = True
                        else:
                            _submit_fg_reset_global_best(n_pending, blocking=True)

                        # Pipelined processing with GPU accumulation:
                        # Process groups and accumulate best on GPU (no per-group downloads)
                        for group in group_gen:
                            group_count += 1
                            counts_list = group.get("counts_list") or []
                            group_pairs = group.get("ftff_pairs") or []
                            if not counts_list or not group_pairs:
                                continue

                            # Track where this group's configs start in master list
                            group_cfg_offset = len(master_configs)
                            master_configs.extend(counts_list)

                            # Log first group info (always show breakpoints)
                            if not logged_first:
                                logged_first = True
                                bps = group.get("section_breakpoints") or ()
                                if bps:
                                    print(
                                        f"[FG] Per-FT/FF Breakpoints (GPU accumulation): {len(ftff_pairs)} FT/FF pairs"
                                    )
                                    for sec_idx, bp in enumerate(bps):
                                        print(
                                            f"     Section {sec_idx + 1}: {list(bp)[:15]}{'...' if len(bp) > 15 else ''}"
                                        )

                            _t_gpu0 = time.perf_counter() if perf else 0.0
                            # Use accumulate_global=True to skip download, with base_cfg_offset for global indexing
                            if gpu_client is not None:
                                for ftff_chunk in _iter_ftff_chunks(group_pairs):
                                    fg_tasks_batch.append(
                                        {
                                            "counts_list": counts_list,
                                            "ftff_pairs": ftff_chunk,
                                            "base_cfg_offset": int(group_cfg_offset),
                                        }
                                    )
                                    if len(fg_tasks_batch) >= fg_async_tasks_per_request:
                                        fut = None
                                        if fg_async_tasks_per_request >= 2:
                                            spill = fg_tasks_batch[:-1]
                                            fg_tasks_batch = fg_tasks_batch[-1:]
                                            fut = _flush_fg_tasks_batch(batch=spill)
                                        else:
                                            fut = _flush_fg_tasks_batch()
                                        if fut is not None:
                                            group_futures.append(fut)
                            else:
                                for ftff_chunk in _iter_ftff_chunks(group_pairs):
                                    _submit_solve_force_greats_finder(
                                        genome_stats_arr,
                                        timestamps,
                                        great_candidates,
                                        long_notes,
                                        last_note_time,
                                        counts_list,
                                        ftff_chunk,
                                        n_sections=n_sections,
                                        is_p_ft=is_p_ft,
                                        is_s_ft=is_s_ft,
                                        is_p_ff=is_p_ff,
                                        is_s_ff=is_s_ff,
                                        is_p_pp=is_p_pp,
                                        is_s_pp=is_s_pp,
                                        is_p_cm=is_p_cm,
                                        is_s_cm=is_s_cm,
                                        is_p_fm=is_p_fm,
                                        is_s_fm=is_s_fm,
                                        is_p_ov=is_p_ov,
                                        is_s_ov=is_s_ov,
                                        ref_arrays=ref_arrays,
                                        total_budget=TOTAL_GEM_BUDGET,
                                        gem_scale_fever=GEM_SCALE_FEVER,
                                        pair_caps_grid=pair_caps_grid,
                                        return_raw=True,
                                        accumulate_global=True,
                                        base_cfg_offset=group_cfg_offset,
                                    )
                            if perf:
                                t_gpu_calls_sec += time.perf_counter() - _t_gpu0
                                if len(gpu_call_shapes) < 12:
                                    gpu_call_shapes.append(
                                        (n_pending, len(counts_list), len(group_pairs), int(n_sections))
                                    )
                            n_gpu_calls += 1

                        # Log merged status if we got a single batch (always log)
                        if group_count == 1:
                            # Get the master config count for merged batch info
                            n_configs = len(master_configs) if master_configs else 0
                            print(
                                f"[FG] Merged breakpoint groups -> 1 batch "
                                f"(pairs={len(ftff_pairs)}, configs={n_configs}, GPU accumulation)"
                            )
                            # Show config breakdown if available
                            if master_configs and len(master_configs) > 0:
                                n_sections_show = len(master_configs[0]) if master_configs[0] else 0
                                if n_sections_show > 0:
                                    # Find max value per section
                                    max_per_sec = [0] * n_sections_show
                                    for cfg in master_configs:
                                        for i, v in enumerate(cfg):
                                            if v > max_per_sec[i]:
                                                max_per_sec[i] = v
                                    for sec_idx, max_val in enumerate(max_per_sec):
                                        print(f"     Section {sec_idx + 1}: [0..{max_val}]")

                        # Single download at end - this is the key optimization!
                        _t_download0 = time.perf_counter() if perf else 0.0
                        download_future = _flush_fg_tasks_batch(download_after=True)
                        fg_async_futures.clear()

                        if download_future is not None:
                            group_futures.append(download_future)

                        if defer_group_apply:
                            deferred_gpu_applies.append(
                                {
                                    "mode": "breakpoints",
                                    "pending_sigs": pending_sigs,
                                    "pending": pending,
                                    "sig_map": sig_map,
                                    "sel_color": sel_color,
                                    "n_sections": int(n_sections),
                                    "max_per_section": int(max_per_section),
                                    "n_pending": int(n_pending),
                                    "master_configs": master_configs,
                                    "fg_scorer": fg_scorer if "fg_scorer" in locals() else None,
                                    "download_future": download_future,
                                    "futures": group_futures,
                                }
                            )
                            continue

                        for fut in group_futures:
                            fut.result()

                        global_results = download_future.result() if hasattr(download_future, "result") else None
                        if global_results is None:
                            global_results = _submit_fg_download_global_best(n_pending, blocking=True)
                        if perf:
                            t_download_sec = time.perf_counter() - _t_download0
                            print(f"[PERF] FG GPU global download: {t_download_sec * 1000:.1f}ms")

                        # Extract results from global download
                        result_final = global_results["final_score"]
                        result_base = global_results["base_score"]
                        result_ft = global_results["FT"]
                        result_ff = global_results["FF"]
                        result_g_pp = global_results["g_pp"]
                        result_g_cm = global_results["g_cm"]
                        result_g_fm = global_results["g_fm"]
                        result_g_ov = global_results["g_ov"]
                        result_score_penalty = global_results["score_penalty"]
                        result_fill_penalty = global_results["fill_penalty"]

                        # Build result_cfg_counts from master list using global cfg indices
                        result_cfg_counts = []
                        master_len = len(master_configs)
                        for idx in range(n_pending):
                            cfg_idx = int(global_results["cfg_idx"][idx])
                            if 0 <= cfg_idx < master_len:
                                result_cfg_counts.append(master_configs[cfg_idx])
                            else:
                                result_cfg_counts.append(None)
                    else:
                        _t_gpu0 = time.perf_counter() if perf else 0.0
                        # Use return_raw=True for numpy results (skip dict building in API)
                        if len(ftff_pairs) > int(fg_fields.FG_MAX_FTFF):
                            if gpu_client is not None:
                                need_reset = True
                            else:
                                _submit_fg_reset_global_best(n_pending, blocking=True)
                            if gpu_client is not None:
                                for ftff_chunk in _iter_ftff_chunks(ftff_pairs):
                                    fg_tasks_batch.append(
                                        {
                                            "counts_list": counts_list,
                                            "ftff_pairs": ftff_chunk,
                                        }
                                    )
                                    if len(fg_tasks_batch) >= fg_async_tasks_per_request:
                                        if fg_async_tasks_per_request >= 2:
                                            spill = fg_tasks_batch[:-1]
                                            fg_tasks_batch = fg_tasks_batch[-1:]
                                            _flush_fg_tasks_batch(batch=spill)
                                        else:
                                            _flush_fg_tasks_batch()
                            else:
                                for ftff_chunk in _iter_ftff_chunks(ftff_pairs):
                                    _submit_solve_force_greats_finder(
                                        genome_stats_arr,  # numpy array instead of list[dict]
                                        timestamps,
                                        great_candidates,
                                        long_notes,
                                        last_note_time,
                                        counts_list,
                                        ftff_chunk,
                                        n_sections=n_sections,
                                        is_p_ft=is_p_ft,
                                        is_s_ft=is_s_ft,
                                        is_p_ff=is_p_ff,
                                        is_s_ff=is_s_ff,
                                        is_p_pp=is_p_pp,
                                        is_s_pp=is_s_pp,
                                        is_p_cm=is_p_cm,
                                        is_s_cm=is_s_cm,
                                        is_p_fm=is_p_fm,
                                        is_s_fm=is_s_fm,
                                        is_p_ov=is_p_ov,
                                        is_s_ov=is_s_ov,
                                        ref_arrays=ref_arrays,
                                        total_budget=TOTAL_GEM_BUDGET,
                                        gem_scale_fever=GEM_SCALE_FEVER,
                                        pair_caps_grid=pair_caps_grid,
                                        return_raw=True,  # Return numpy arrays, not list[dict]
                                        accumulate_global=True,
                                    )

                            download_future = _flush_fg_tasks_batch(download_after=True)
                            for fut in fg_async_futures:
                                fut.result()
                            fg_async_futures.clear()

                            gpu_results = download_future.result() if hasattr(download_future, "result") else None
                            if gpu_results is None:
                                gpu_results = _submit_fg_download_global_best(n_pending, blocking=True)
                        else:
                            gpu_results = _submit_solve_force_greats_finder(
                                genome_stats_arr,  # numpy array instead of list[dict]
                                timestamps,
                                great_candidates,
                                long_notes,
                                last_note_time,
                                counts_list,
                                ftff_pairs,
                                n_sections=n_sections,
                                is_p_ft=is_p_ft,
                                is_s_ft=is_s_ft,
                                is_p_ff=is_p_ff,
                                is_s_ff=is_s_ff,
                                is_p_pp=is_p_pp,
                                is_s_pp=is_s_pp,
                                is_p_cm=is_p_cm,
                                is_s_cm=is_s_cm,
                                is_p_fm=is_p_fm,
                                is_s_fm=is_s_fm,
                                is_p_ov=is_p_ov,
                                is_s_ov=is_s_ov,
                                ref_arrays=ref_arrays,
                                total_budget=TOTAL_GEM_BUDGET,
                                gem_scale_fever=GEM_SCALE_FEVER,
                                pair_caps_grid=pair_caps_grid,
                                return_raw=True,  # Return numpy arrays, not list[dict]
                            )
                        if perf:
                            t_gpu_calls_sec += time.perf_counter() - _t_gpu0
                            if len(gpu_call_shapes) < 12:
                                gpu_call_shapes.append((n_pending, len(counts_list), len(ftff_pairs), int(n_sections)))
                        n_gpu_calls += 1

                        result_final = gpu_results["final_score"]
                        result_base = gpu_results["base_score"]
                        result_cfg_idx = gpu_results["cfg_idx"]
                        result_ft = gpu_results["FT"]
                        result_ff = gpu_results["FF"]
                        result_g_pp = gpu_results["g_pp"]
                        result_g_cm = gpu_results["g_cm"]
                        result_g_fm = gpu_results["g_fm"]
                        result_g_ov = gpu_results["g_ov"]
                        result_score_penalty = gpu_results["score_penalty"]
                        result_fill_penalty = gpu_results["fill_penalty"]

                    _apply_gpu_results_to_entries(
                        pending_sigs=pending_sigs,
                        pending=pending,
                        sig_map=sig_map,
                        sel_color=str(sel_color),
                        n_sections=int(n_sections),
                        max_per_section=int(max_per_section),
                        counts_list=counts_list,
                        fg_scorer=fg_scorer if "fg_scorer" in locals() else None,
                        result_final=result_final,
                        result_base=result_base,
                        result_cfg_idx=result_cfg_idx,
                        result_cfg_counts=result_cfg_counts,
                        result_ft=result_ft,
                        result_ff=result_ff,
                        result_g_pp=result_g_pp,
                        result_g_cm=result_g_cm,
                        result_g_fm=result_g_fm,
                        result_g_ov=result_g_ov,
                        result_score_penalty=result_score_penalty,
                        result_fill_penalty=result_fill_penalty,
                    )

            if deferred_gpu_applies:
                for ctx in deferred_gpu_applies:
                    futs = ctx.get("futures") or []
                    for fut in futs:
                        fut.result()

                    n_pending = int(ctx.get("n_pending") or 0)
                    if n_pending <= 0:
                        continue

                    download_future = ctx.get("download_future")
                    gpu_results = None
                    if download_future is not None and hasattr(download_future, "result"):
                        gpu_results = download_future.result()
                    if not isinstance(gpu_results, dict):
                        raise RuntimeError("Deferred FG download returned no result")

                    if ctx.get("mode") != "breakpoints":
                        continue

                    master_configs = ctx.get("master_configs") or []
                    master_len = len(master_configs)
                    cfg_idx_arr = gpu_results.get("cfg_idx")
                    result_cfg_counts = []
                    for i in range(n_pending):
                        try:
                            cfg_idx = int(cfg_idx_arr[i]) if cfg_idx_arr is not None else -1
                        except Exception:
                            cfg_idx = -1
                        if 0 <= cfg_idx < master_len:
                            result_cfg_counts.append(master_configs[cfg_idx])
                        else:
                            result_cfg_counts.append(None)

                    _apply_gpu_results_to_entries(
                        pending_sigs=ctx.get("pending_sigs") or [],
                        pending=ctx.get("pending") or [],
                        sig_map=ctx.get("sig_map") or {},
                        sel_color=str(ctx.get("sel_color") or ""),
                        n_sections=int(ctx.get("n_sections") or 0),
                        max_per_section=int(ctx.get("max_per_section") or 0),
                        counts_list=None,
                        fg_scorer=ctx.get("fg_scorer"),
                        result_final=gpu_results["final_score"],
                        result_base=gpu_results["base_score"],
                        result_cfg_idx=None,
                        result_cfg_counts=result_cfg_counts,
                        result_ft=gpu_results["FT"],
                        result_ff=gpu_results["FF"],
                        result_g_pp=gpu_results["g_pp"],
                        result_g_cm=gpu_results["g_cm"],
                        result_g_fm=gpu_results["g_fm"],
                        result_g_ov=gpu_results["g_ov"],
                        result_score_penalty=gpu_results["score_penalty"],
                        result_fill_penalty=gpu_results["fill_penalty"],
                    )

            unique_sig_count = 0
            try:
                unique_sig_count = sum(len(sig_map) for sig_map in (groups or {}).values())
            except Exception:
                unique_sig_count = 0
            print(
                f"[ForceGreats] {unique_sig_count} unique stat signatures, "
                f"{len(fg_variants)} FG variants generated (computed {computed})"
            )
            if perf:
                try:
                    print(
                        "[PERF] ForceGreatsFinder(GPU): "
                        f"collect={t_collect_sec:.3f}s cfg_build={t_cfg_build_sec:.3f}s "
                        f"gpu_calls={t_gpu_calls_sec:.3f}s n_gpu_calls={n_gpu_calls} "
                        f"FG_CACHE(hit={fg_cache_hits},miss={fg_cache_misses}) "
                        f"db_reuse={db_cached_reuse} no_eval_skips={no_eval_skips} "
                        f"groups={len(groups)} unique_sigs={unique_sig_count}"
                    )
                    print(
                        "[PERF] FG Detailed: "
                        f"cache_check={t_cache_check_sec * 1000:.1f}ms "
                        f"genome_build={t_genome_build_sec * 1000:.1f}ms "
                        f"result_apply={t_result_apply_sec * 1000:.1f}ms"
                    )
                    if gpu_call_shapes:
                        print(f"[PERF] FG GPU call shapes (n_genomes,n_cfg,n_ftff,n_sections): {gpu_call_shapes}")
                except Exception:
                    pass

            # Always-on compact workload summary (helps correlate GPU spikes with workload size)
            print(
                f"[ForceGreats] GPU complete: {len(fg_variants)} variants, "
                f"{n_gpu_calls} GPU calls, {computed} genomes computed"
            )
            return fg_variants
        except Exception as e:
            print(f"[ForceGreats][GPU] Batch FG finder failed; falling back to CPU per-loadout: {e}")
            if gpu_client is not None:
                # Last-resort fallback: run the full helper on the GPU-owner thread.
                # This preserves correctness (and allows GPU hill-climb paths) even
                # if the batched finder path fails for a particular song.
                try:
                    return gpu_client.submit_process_force_greats(
                        loadout_entries,
                        manual_force_greats,
                        force_greats_finder,
                        force_greats_config,
                        calc_song,
                        ref_arrays,
                        meta_primary_color,
                        build_details_fn,
                        db_loadouts_full_count,
                        use_gpu=use_gpu,
                        fg_search_radius=fg_search_radius,
                        perf_timing=perf_timing,
                        gpu_client=None,
                    ).future.result()
                except Exception:
                    pass
            # Reset state to allow CPU manual loop to run from scratch
            fg_variants = []
            computed = 0
            unique_stats_seen = set()
        finally:
            if lock_acquired:
                _FG_GPU_SEQUENCE_LOCK.release()
    # CPU fallback: Process all loadouts (no budget limit)
    unique_stats_seen = set()
    for entry in loadout_entries.values():

        def _is_cached_force_valid(cached_force_obj, expected_selected_element):
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
            if not isinstance(fg_meta, dict) or not fg_meta:
                return False
            # Must have config with section greats
            if not fg_meta.get("config"):
                return False
            # Guard against overflow-target mismatch (affects gem optimization and score)
            cached_sel = details.get("SelectedElement") or details.get("Selected Element") or ""
            if expected_selected_element and cached_sel and cached_sel != expected_selected_element:
                return False
            return True

        cached_force = entry.get("force")
        expected_sel = None
        try:
            det0 = entry.get("details") or {}
            expected_sel = det0.get("SelectedElement") or det0.get("Selected Element") or meta_primary_color
        except Exception:
            expected_sel = meta_primary_color

        # Reuse cached force results if they are compatible with current algo/version.
        if (
            cached_force
            and (cached_force.get("score") or entry.get("fg_score"))
            and _is_cached_force_valid(cached_force, expected_sel)
        ):
            # Preserve base score when reusing cached FG
            base_score = entry.get("base_score") or entry.get("score", 0)
            cached_fg_score = cached_force.get("score", entry.get("fg_score", 0))

            fg_variants.append(
                {
                    "data": cached_force.get("details", {}),
                    "gear": entry.get("gear", []),
                    "minis": entry.get("minis", []),
                    "score": base_score,  # Keep base score
                    "fg_score": cached_fg_score,  # Store FG score separately
                }
            )
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
            # If we're running under `gpu_client`, we are *not* on the GPU-owner
            # thread, so the per-loadout GPU hill-climb path is unsafe. The batched
            # finder path above should cover the GPU case; this loop is a slow
            # fallback and should remain CPU-only under orchestration.
            use_gpu=bool(use_gpu) and (gpu_client is None),
        )
        computed += 1
        if fg_variant:
            # Preserve base score (non-FG)
            base_score = entry.get("base_score") or entry.get("score", 0)
            fg_score = fg_variant.get("Score", 0)

            fg_variants.append(
                {
                    "data": fg_variant,
                    "gear": entry.get("gear", []),
                    "minis": entry.get("minis", []),
                    "score": base_score,  # Keep base score
                    "fg_score": fg_score,  # Store FG score separately
                }
            )
            entry["force"] = {
                "score": fg_score,
                "gear": _names_list(entry.get("gear", [])),
                "minis": _names_list(entry.get("minis", [])),
                "details": build_details_fn(fg_variant),
            }
            entry["fg_score"] = fg_score
    print(
        f"[ForceGreats] {len(unique_stats_seen)} unique stat signatures, {len(fg_variants)} FG variants generated (computed {computed})"
    )

    return fg_variants
