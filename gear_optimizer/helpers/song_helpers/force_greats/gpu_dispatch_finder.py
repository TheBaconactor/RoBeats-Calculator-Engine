from __future__ import annotations
import logging
import time
from typing import Any, Optional
import numpy as np
from gear_optimizer.core.parsing import TRUTHY_ENV_VALUES, env_flag, truthy
from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from . import cache_validation, result_application
from .entry_utils import (
    _cached_fg_group_meta_is_reusable as _fg_group_meta_is_reusable,
    _normalize_fg_group_key as _coerce_fg_group_key,
    eval_data_from_entry,
    expected_selected_element,
    fg_group_meta_from_eval_data,
)
from .entry_resolution import (
    build_direct_ga_entry_items as _build_direct_ga_entry_items,
    entry_base_score,
    selected_count as _selected_count,
    sig_results_has_fg_improvement as _sig_results_has_fg_improvement,
)
from ....core.color_flags import build_color_flag_values
from ....core.fallback_monitor import warn_fallback
from ....core.utils import stats_signature
from ....solver.taichi_gem.ftff_combos import collect_ftff_pairs_from_centers
from .retained_variants import retain_and_build_fg_variants as _retain_and_build_fg_variants
from .signature_frontier import (
    build_signature_frontier_metas_from_rows as _build_signature_frontier_metas_from_rows_impl,
    resolve_signature_frontier_limit as _resolve_signature_frontier_limit_impl,
    signature_timing_bucket as _signature_timing_bucket_impl,
)
from . import gpu_dispatch_caches as _dispatch_caches
from .gpu_dispatch_batching import (
    _build_topk_keep_signature_set,
    _default_fused_payloads_per_request,
    _extract_group_payload,
    _has_valid_k1_rep,
    _is_empty_pairs,
    _should_use_fused_breakpoints_solve,
    _uses_timing_envelope_fg,
)
from .gpu_dispatch_utils import (
    iter_ftff_chunks as _iter_ftff_chunks,
    pack_pairs_int32 as _pack_pairs_int32,
    safe_metric_count as _safe_metric_count,
)
from .gpu_dispatch_finder_runtime import (
    DeferredGenomeStatsPool,
    FinderPhaseEmitter,
    record_finder_completion,
)
from gear_optimizer.core.cfg_window_decode import decode_cfg_counts_from_windows
from .work_budget import (
    estimate_fg_task_threads as _estimate_fg_task_threads,
    estimate_fused_payload_threads as _estimate_fused_payload_threads,
    split_items_by_work_budget as _split_items_by_work_budget,
)
from gear_optimizer.core.parsing import env_get
logger = logging.getLogger(__name__)
_GPU_STRICT = env_flag("GPU_STRICT", "1")
__all__ = [
    "_build_topk_keep_signature_set",
    "_default_fused_payloads_per_request",
    "_extract_group_payload",
    "_has_valid_k1_rep",
    "_is_empty_pairs",
    "_should_use_fused_breakpoints_solve",
    "_uses_timing_envelope_fg",
    "process_force_greats_gpu_finder",
]
def process_force_greats_gpu_finder(  # pyright: ignore[reportGeneralTypeIssues]
    loadout_entries,
    calc_song,
    ref_arrays,
    meta_primary_color,
    *,
    fg_search_radius: int | None = None,
    perf_timing: bool = False,
    gpu_client: Optional[Any] = None,
    ga_candidates=None,
    ga_registry=None,
):
    finder_wall_t0 = time.perf_counter()
    pre_song_slot = 0
    pre_song_key = ""
    try:
        if isinstance(calc_song, dict):
            pre_song_slot = int(calc_song.get("_gpu_song_slot", 0) or 0)
            pre_song_key = str(calc_song.get("_queue_key") or calc_song.get("_queue_label") or "").strip()
    except (KeyError, TypeError, ValueError, AttributeError):
        pre_song_slot = 0
        pre_song_key = ""
    _emit_pre_finder_phase = FinderPhaseEmitter(
        logger=logger,
        wall_t0=float(finder_wall_t0),
        song_slot=int(pre_song_slot),
        song_key=str(pre_song_key or ""),
        debug_label="_emit_pre_finder_phase",
    ).emit
    _emit_pre_finder_phase(
        "enter",
        loadout_entries=int(len(loadout_entries or {})) if isinstance(loadout_entries, dict) else 0,
        ga_candidates=int(len(ga_candidates or [])),
    )
    fg_variants = []
    perf = bool(perf_timing)
    computed = 0
    frontier_total_before = 0
    frontier_total_after = 0
    frontier_groups_reduced = 0
    breakpoint_group_cache_hits = 0
    breakpoint_group_cache_misses = 0
    fg_task_tile_batches = 0
    fg_task_tile_splits = 0
    fg_fused_tile_batches = 0
    fg_fused_tile_splits = 0
    fg_genome_stats_uploaded_batches = 0
    fg_genome_stats_uploaded_bytes_est = 0
    fg_surface_pair_drops = 0
    fg_surface_pair_reduce_sec = 0.0
    fg_first_submit_delay_sec: float | None = None
    from ....core.constants import (
        GEM_SCALE_FEVER,
        TOTAL_GEM_BUDGET,
        FG_SEARCH_RADIUS,
    )
    from ....solver.scoring import (
        _extract_base_stats,
        fg_baseline_params,
    )
    from ....solver.taichi_gem.force_greats.api import (
        fg_select_signature_frontier_batch,
        solve_force_greats_finder_gpu,
        solve_force_greats_finder_gpu_tasks,
    )
    meta = calc_song.get("metadata", {}) or {}
    p_color = meta.get("Primary Color", "")
    s_color = meta.get("Secondary Color", "")
    from ....solver.analytical_fg import create_scorer_from_calc_song, create_chart_scorer_from_calc_song
    from ....solver.taichi_gem.force_greats import fields as fg_fields
    from ....solver.taichi_gem.force_greats.api import (
        fg_reset_global_best,
        fg_download_global_best,
    )
    from ....solver.gpu_executor_types import GpuRequestType
    _emit_pre_finder_phase("imports_ready")
    _topk_env = str(env_get("FG_DOWNLOAD_TOPK", "1") or "").strip().lower()
    download_topk_enabled = truthy(_topk_env)
    topk_retry_on_empty = env_flag("FG_DOWNLOAD_TOPK_RETRY_ON_EMPTY", "1")
    try:
        download_topk_k = int(env_get("FG_DOWNLOAD_TOPK_K", str(LOADOUTS_PER_SONG_LIMIT)))
    except (ValueError, TypeError):
        download_topk_k = int(LOADOUTS_PER_SONG_LIMIT)
    download_topk_k = max(0, int(download_topk_k))
    song_slot = 0
    try:
        if isinstance(calc_song, dict):
            song_slot = int(calc_song.get("_gpu_song_slot", 0) or 0)
        else:
            song_slot = 0
    except (KeyError, TypeError, ValueError, AttributeError):
        song_slot = 0
    if song_slot < 0:
        song_slot = 0
    finder_song_key = ""
    try:
        if isinstance(calc_song, dict):
            finder_song_key = str(calc_song.get("_queue_key") or calc_song.get("_queue_label") or "").strip()
    except (KeyError, TypeError, ValueError, AttributeError):
        finder_song_key = ""
    _emit_finder_phase = FinderPhaseEmitter(
        logger=logger,
        wall_t0=float(finder_wall_t0),
        song_slot=int(song_slot),
        song_key=str(finder_song_key or ""),
        debug_label="_emit_finder_phase",
    ).emit
    sig_frontier_enabled = env_flag("FG_SIGNATURE_FRONTIER_ENABLED", "1")
    sig_frontier_limit = _resolve_signature_frontier_limit_impl(loadouts_per_song_limit=int(LOADOUTS_PER_SONG_LIMIT)) if sig_frontier_enabled else 0
    try:
        sig_frontier_center_bin = max(1, int(env_get("FG_SIGNATURE_FRONTIER_CENTER_BIN", "2") or 2))
    except (ValueError, TypeError):
        sig_frontier_center_bin = 2
    def _submit_fg_reset_global_best(n_genomes: int, *, blocking: bool = True):
        if gpu_client is not None:
            fut = gpu_client.submit(
                GpuRequestType.FG_RESET_GLOBAL_BEST,
                {"n_genomes": int(n_genomes), "song_slot": int(song_slot)},
            ).future
            if blocking:
                fut.result()
                return None
            return fut
        fg_reset_global_best(int(n_genomes), session_slot=int(song_slot))
        return None
    def _submit_fg_download_global_best(
        n_genomes: int,
        *,
        blocking: bool = True,
        topk: int | None = None,
        base_scores=None,
        keep_mask=None,
    ):
        if gpu_client is not None:
            payload = {"n_genomes": int(n_genomes), "song_slot": int(song_slot)}
            if topk is not None and base_scores is not None:
                payload["topk"] = int(topk)
                payload["base_scores"] = base_scores
                payload["keep_mask"] = keep_mask
            fut = gpu_client.submit(
                GpuRequestType.FG_DOWNLOAD_GLOBAL_BEST,
                payload,
            ).future
            return fut.result() if blocking else fut
        if topk is not None and base_scores is not None:
            return fg_download_global_best(
                int(n_genomes),
                session_slot=int(song_slot),
                topk=int(topk),
                base_scores=base_scores,
                keep_mask=keep_mask,
            )
        return fg_download_global_best(int(n_genomes), session_slot=int(song_slot))
    def _submit_solve_force_greats_finder(*args, blocking: bool = True, **kwargs):
        nonlocal timeline_precompute_queued
        if gpu_client is not None:
            need_timeline_precompute = bool(kwargs.get("pair_caps_from_timeline")) and (not timeline_precompute_queued)
            if need_timeline_precompute:
                kwargs["ensure_timeline_precompute"] = True
                kwargs["calc_song"] = calc_song
                timeline_precompute_queued = True
            if kwargs.get("ga_stage_coords") is not None:
                raise RuntimeError("GA->FG resident genome-stat staging has been removed")
            fut = gpu_client.submit_solve_force_greats_finder(*args, **kwargs).future
            return fut.result() if blocking else fut
        if kwargs.pop("ga_stage_coords", None) is not None:
            raise RuntimeError("GA->FG resident genome-stat staging has been removed")
        kwargs.pop("ga_stage_table_slot", None)
        kwargs.pop("ensure_timeline_precompute", None)
        kwargs.pop("calc_song", None)
        kwargs.pop("ga_stage_n_slots", None)
        need_timeline_precompute = bool(kwargs.get("pair_caps_from_timeline")) and (not timeline_precompute_queued)
        if need_timeline_precompute:
            try:
                from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu
                slot0 = int(kwargs.get("song_slot", song_slot) or song_slot)
                precompute_timeline_gpu(calc_song, ref_arrays, song_slot=int(slot0))
            except Exception as e:
                logger.debug(f"gpu_dispatch:_submit_solve_force_greats_finder: {e}")
            timeline_precompute_queued = True
        return solve_force_greats_finder_gpu(*args, **kwargs)
    def _submit_solve_force_greats_finder_tasks(*args, fg_tasks: list[dict], blocking: bool = True, **kwargs):
        nonlocal timeline_precompute_queued
        if gpu_client is not None:
            raise RuntimeError("direct FG task solve is only used without a GPU client")
        if kwargs.pop("ga_stage_coords", None) is not None:
            raise RuntimeError("GA->FG resident genome-stat staging has been removed")
        kwargs.pop("ga_stage_table_slot", None)
        kwargs.pop("ensure_timeline_precompute", None)
        kwargs.pop("calc_song", None)
        kwargs.pop("ga_stage_n_slots", None)
        need_timeline_precompute = bool(kwargs.get("pair_caps_from_timeline")) and (not timeline_precompute_queued)
        if need_timeline_precompute:
            try:
                from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu
                slot0 = int(kwargs.get("song_slot", song_slot) or song_slot)
                precompute_timeline_gpu(calc_song, ref_arrays, song_slot=int(slot0))
            except Exception as e:
                logger.debug(f"gpu_dispatch:_submit_solve_force_greats_finder_tasks: {e}")
            timeline_precompute_queued = True
        return solve_force_greats_finder_gpu_tasks(*args, fg_tasks=fg_tasks, **kwargs)
    def _uses_prefix_frontier_tasks(tasks: list[dict]) -> bool:
        for task in tasks:
            if not isinstance(task, dict):
                continue
            desc = task.get("counts_max_fp")
            if isinstance(desc, dict) and str(desc.get("mode") or "") == "gpu":
                return True
        return False
    from .gpu_dispatch_async import plan_fg_async_threshold_flush, resolve_fg_async_batching_settings
    async_settings = resolve_fg_async_batching_settings(gpu_client=gpu_client, song_slot=int(song_slot), perf=perf)
    in_process = bool(async_settings.in_process)
    enforce_single_request = bool(async_settings.enforce_single_request)
    fg_async_max_inflight = int(async_settings.max_inflight)
    fg_async_tasks_per_request = int(async_settings.tasks_per_request)
    _emit_finder_phase(
        "async_settings_ready",
        in_process=int(bool(in_process)),
        enforce_single_request=int(bool(enforce_single_request)),
        max_inflight=int(fg_async_max_inflight),
        tasks_per_request=int(fg_async_tasks_per_request),
    )
    fg_async_futures = []
    fg_tasks_batch = []
    genome_stats_uploaded = False
    sig_results: dict[str, dict] = {}
    first_group_iter_ready_emitted = False
    first_gpu_task_queued_emitted = False
    first_gpu_submit_emitted = False
    def _maybe_emit_first_group_iter_ready(
        *,
        group_mode: str,
        cache_hit: bool,
        ftff_pairs_count: int,
        sig_count: int,
        n_sections_value: int,
        n_pending_value: int,
    ) -> None:
        nonlocal first_group_iter_ready_emitted
        if first_group_iter_ready_emitted:
            return
        first_group_iter_ready_emitted = True
        _emit_finder_phase(
            "first_group_iter_ready",
            group_mode=str(group_mode),
            cache_hit=int(bool(cache_hit)),
            ftff_pairs=int(ftff_pairs_count),
            sig_count=int(sig_count),
            n_sections=int(n_sections_value),
            n_pending=int(n_pending_value),
            tasks_per_request=int(fg_async_tasks_per_request),
        )
    def _maybe_emit_first_gpu_task_queued(
        *,
        queue_mode: str,
        queue_len: int,
        pair_count: int,
        cfg_count: int,
        n_sections_value: int,
        n_pending_value: int,
    ) -> None:
        nonlocal first_gpu_task_queued_emitted
        if first_gpu_task_queued_emitted:
            return
        first_gpu_task_queued_emitted = True
        _emit_finder_phase(
            "first_gpu_task_queued",
            queue_mode=str(queue_mode),
            queue_len=int(queue_len),
            pair_count=int(pair_count),
            cfg_count=int(cfg_count),
            n_sections=int(n_sections_value),
            n_pending=int(n_pending_value),
            tasks_per_request=int(fg_async_tasks_per_request),
        )
    def _maybe_emit_first_gpu_submit(
        *,
        submit_mode: str,
        batch_size: int,
        tile_count: int,
        download_after: bool,
    ) -> None:
        nonlocal first_gpu_submit_emitted, fg_first_submit_delay_sec
        if first_gpu_submit_emitted:
            return
        first_gpu_submit_emitted = True
        try:
            fg_first_submit_delay_sec = time.perf_counter() - float(fg_submit_clock_start)
        except (ValueError, TypeError):
            fg_first_submit_delay_sec = None
        _emit_finder_phase(
            "first_gpu_submit",
            submit_mode=str(submit_mode),
            batch_size=int(batch_size),
            tile_count=int(tile_count),
            download_after=int(bool(download_after)),
            tasks_per_request=int(fg_async_tasks_per_request),
            first_submit_delay_ms=-1.0
            if fg_first_submit_delay_sec is None
            else float(fg_first_submit_delay_sec) * 1000.0,
        )
    def _record_gpu_results(
        *,
        pending_sigs: list,
        pending: list,
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
    ) -> None:
        nonlocal t_result_apply_sec
        collected, elapsed = result_application.collect_gpu_results_by_signature(
            pending_sigs=pending_sigs,
            pending=pending,
            sel_color=str(sel_color),
            n_sections=int(n_sections),
            max_per_section=int(max_per_section),
            counts_list=counts_list,
            fg_scorer=fg_scorer,
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
            perf=perf,
            materialize_stats=False,
        )
        sig_results.update(collected)
        t_result_apply_sec += elapsed
    def _accumulate_fused_surface_metrics(gpu_results: Any) -> None:
        nonlocal fg_surface_pair_drops, fg_surface_pair_reduce_sec
        if not isinstance(gpu_results, dict):
            return
        try:
            fg_surface_pair_drops += max(0, int(gpu_results.get("surface_pair_drops", 0) or 0))
        except (KeyError, TypeError, ValueError, AttributeError):
            pass
        try:
            fg_surface_pair_reduce_sec += max(0.0, float(gpu_results.get("surface_pair_reduce_ms", 0) or 0)) / 1000.0
        except (ValueError, TypeError, KeyError, AttributeError):
            pass
    need_reset = False
    timeline_precompute_queued = False
    genome_stats_arr = None
    genome_stats_n_genomes = 0
    def _flush_fg_tasks_batch(
        *,
        batch: list[dict] | None = None,
        download_after: bool = False,
        download_topk: int | None = None,
        download_base_scores=None,
        download_keep_mask=None,
    ):
        nonlocal fg_tasks_batch, need_reset, genome_stats_uploaded
        nonlocal genome_stats_n_genomes
        nonlocal fg_task_tile_batches, fg_task_tile_splits
        if gpu_client is None:
            return None
        if batch is None:
            if fg_tasks_batch:
                batch = fg_tasks_batch
                fg_tasks_batch = []
            elif not download_after:
                return None
            else:
                batch = []
        if batch:
            if enforce_single_request:
                task_tiles = [list(batch)]
            else:
                task_tiles = _split_items_by_work_budget(
                    list(batch),
                    max_work=int(fg_task_tile_max_threads),
                    estimate_fn=lambda item: _estimate_fg_task_threads(
                        item,
                        n_sections=int(n_sections),
                        n_genomes=int(genome_stats_n_genomes),
                    ),
                )
            if not task_tiles:
                return None
            fg_task_tile_batches += int(len(task_tiles))
            if len(task_tiles) > 1:
                fg_task_tile_splits += int(len(task_tiles) - 1)
        elif download_after:
            task_tiles = [[]]
        else:
            return None
        last_future = None
        for tile_idx, task_tile in enumerate(task_tiles):
            first = task_tile[0] if task_tile else {}
            if task_tile and not isinstance(first, dict):
                continue
            if task_tile:
                placeholder_counts = first.get("counts_list")
                placeholder_pairs = first.get("ftff_pairs")
                if placeholder_counts is None:
                    placeholder_counts = [tuple([0] * int(n_sections))]
                if placeholder_pairs is None:
                    continue
            else:
                placeholder_counts = [tuple([0] * int(n_sections))]
                placeholder_pairs = []
            submit_kwargs = dict(
                n_sections=n_sections,
                **flag_kwargs,
                ref_arrays=ref_arrays,
                total_budget=TOTAL_GEM_BUDGET,
                gem_scale_fever=GEM_SCALE_FEVER,
                pair_caps_grid=pair_caps_grid,
                pair_caps_from_timeline=bool(pair_caps_from_timeline),
                song_slot=int(song_slot),
                return_raw=True,
                accumulate_global=True,
                fg_tasks=task_tile,
            )
            submit_kwargs["upload_genome_stats"] = bool(not genome_stats_uploaded)
            if "base_cfg_offset" in first:
                try:
                    submit_kwargs["base_cfg_offset"] = int(first.get("base_cfg_offset", 0) or 0)
                except (ValueError, TypeError):
                    submit_kwargs["base_cfg_offset"] = 0
            if task_tile and _uses_prefix_frontier_tasks(task_tile):
                prebuild_kwargs = dict(submit_kwargs)
                prebuild_kwargs["prebuild_only"] = True
                _submit_solve_force_greats_finder(
                    genome_stats_arr,
                    timestamps,
                    great_candidates,
                    long_notes,
                    last_note_time,
                    placeholder_counts,
                    placeholder_pairs,
                    blocking=True,
                    **prebuild_kwargs,
                )
                genome_stats_uploaded = True
                submit_kwargs["upload_genome_stats"] = False
            if need_reset:
                submit_kwargs["fg_reset_before"] = True
                need_reset = False
            if download_after and int(tile_idx) == int(len(task_tiles) - 1):
                submit_kwargs["fg_download_after"] = True
                if download_topk is not None and download_base_scores is not None:
                    submit_kwargs["fg_download_topk"] = int(download_topk)
                    submit_kwargs["fg_download_base_scores"] = download_base_scores
                    submit_kwargs["fg_download_keep_mask"] = download_keep_mask
            _maybe_emit_first_gpu_submit(
                submit_mode="tasks",
                batch_size=int(len(task_tile)),
                tile_count=int(len(task_tiles)),
                download_after=bool(download_after),
            )
            last_future = _submit_solve_force_greats_finder(
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
            genome_stats_uploaded = True
            fg_async_futures.append(last_future)
            if len(fg_async_futures) >= fg_async_max_inflight:
                fg_async_futures.pop(0).result()
        return last_future
    groups = {}
    group_signature_rows = {}
    group_centers = {}  # key -> set of (center_ft, center_ff)
    entry_sig: dict[int, str] = {}
    t_collect_sec = 0.0
    t_cfg_build_sec = 0.0
    t_gpu_calls_sec = 0.0
    t_gpu_wait_sec = 0.0
    t_gpu_download_wait_sec = 0.0
    t_cache_check_sec = 0.0
    t_genome_build_sec = 0.0
    t_result_apply_sec = 0.0
    n_gpu_calls = 0
    db_cached_reuse = 0
    no_eval_skips = 0
    fg_group_meta_cached = 0
    fg_group_meta_built = 0
    gpu_call_shapes = []  # sample a few: (n_genomes, n_cfg, n_ftff, n_sections)
    per_pair_breakpoints = True
    breakpoint_group_cache_enabled = env_flag("FG_BREAKPOINT_GROUP_CACHE", "1")
    try:
        breakpoint_group_cache_max_pairs = max(
            0, int(env_get("FG_BREAKPOINT_GROUP_CACHE_MAX_PAIRS", "256") or "256")
        )
    except (ValueError, TypeError):
        breakpoint_group_cache_max_pairs = 256
    try:
        breakpoint_group_cache_max_base_pairs = max(
            0, int(env_get("FG_BREAKPOINT_GROUP_CACHE_MAX_BASE_PAIRS", "64") or "64")
        )
    except (ValueError, TypeError):
        breakpoint_group_cache_max_base_pairs = 64
    try:
        fg_task_tile_max_threads = int(
            env_get(
                "FG_TASK_TILE_MAX_THREADS",
                "125000000" if in_process else "50000000",
            )
            or ("125000000" if in_process else "50000000")
        )
    except (ValueError, TypeError):
        fg_task_tile_max_threads = 125000000 if in_process else 50000000
    fg_task_tile_max_threads = max(0, int(fg_task_tile_max_threads))
    try:
        fg_fused_tile_max_threads = int(
            env_get(
                "FG_FUSED_TILE_MAX_THREADS",
                "125000000" if in_process else "50000000",
            )
            or ("125000000" if in_process else "50000000")
        )
    except (ValueError, TypeError):
        fg_fused_tile_max_threads = 125000000 if in_process else 50000000
    fg_fused_tile_max_threads = max(0, int(fg_fused_tile_max_threads))
    if per_pair_breakpoints and not hasattr(process_force_greats_gpu_finder, "_fg_pair_breakpoint_log"):
        process_force_greats_gpu_finder._fg_pair_breakpoint_log = True
        logger.debug("[FG] Per-FT/FF breakpoint mode enabled (GPU finder)")
    direct_ga_items = _build_direct_ga_entry_items(ga_candidates, ga_registry=ga_registry)
    try:
        base_items = list(loadout_entries.items()) if isinstance(loadout_entries, dict) else []
    except (TypeError, AttributeError):
        base_items = []
    if direct_ga_items:
        base_items = [(k, v) for k, v in base_items if not (isinstance(v, dict) and bool(v.get("_fg_direct_ga")))]
    entry_items = list(base_items) + list(direct_ga_items)
    try:
        group_meta_grid_threshold = int(env_get("FG_GROUP_META_GRID_ENTRY_THRESHOLD", "512") or "512")
    except (ValueError, TypeError):
        group_meta_grid_threshold = 512
    group_meta_grid_threshold = max(0, min(int(group_meta_grid_threshold), 512))
    prefer_group_meta_grid = bool(
        group_meta_grid_threshold <= 0 or int(len(entry_items)) >= int(group_meta_grid_threshold)
    )
    _emit_finder_phase(
        "entry_items_ready",
        loadout_entries=int(len(base_items)),
        direct_ga_items=int(len(direct_ga_items)),
        entry_items=int(len(entry_items)),
        group_meta_grid=int(bool(prefer_group_meta_grid)),
    )
    _t_collect0 = time.perf_counter() if perf else 0.0
    for _entry_key, entry in entry_items:
        cached_force = entry.get("force")
        expected_sel = expected_selected_element(entry, meta_primary_color)
        eval_data = eval_data_from_entry(entry, meta_primary_color)
        if not eval_data:
            no_eval_skips += 1
            continue
        center_ft = int(eval_data.get("FT", 0) or 0)
        center_ff = int(eval_data.get("FF", 0) or 0)
        if cached_force and cache_validation.is_cached_force_valid_for_finder(
            cached_force, expected_sel, center_ft, center_ff
        ):
            db_cached_reuse += 1
            base_score = entry_base_score(entry)
            cached_fg_score = entry.get("fg_score", 0) or cached_force.get("Score", 0)
            if "base_score" not in entry:
                entry["base_score"] = base_score
            entry["fg_score"] = cached_fg_score
            continue
        gem_counts_existing = eval_data.get("GemCounts", {}) or {}
        base_stats = eval_data.get("BaseStats") if isinstance(eval_data.get("BaseStats"), dict) else None
        if not base_stats:
            stats = eval_data.get("Stats", {}) or {}
            sel_color = expected_selected_element(entry, meta_primary_color)
            base_stats = _extract_base_stats(stats, gem_counts_existing, sel_color, center_ft, center_ff)
        had_reusable_fg_group_meta = False
        try:
            had_reusable_fg_group_meta = bool(_fg_group_meta_is_reusable(eval_data.get("_fg_group_meta")))
        except (KeyError, TypeError, ValueError, AttributeError):
            had_reusable_fg_group_meta = False
        fg_group_meta = fg_group_meta_from_eval_data(
            eval_data,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            meta_primary_color=meta_primary_color,
            primary_color=str(p_color or ""),
            secondary_color=str(s_color or ""),
            base_stats=base_stats,
            prefer_grid=bool(prefer_group_meta_grid),
        )
        if had_reusable_fg_group_meta:
            fg_group_meta_cached += 1
        elif isinstance(fg_group_meta, dict):
            fg_group_meta_built += 1
        if isinstance(fg_group_meta, dict) and bool(fg_group_meta.get("skip")):
            continue
        if isinstance(fg_group_meta, dict):
            sel_color = str(fg_group_meta.get("selected_element", "") or "")
            coerced_key = _coerce_fg_group_key(fg_group_meta.get("group_key"))
            if coerced_key is not None:
                key = (sel_color or coerced_key[0], int(coerced_key[1]), int(coerced_key[2]))
                sig = fg_group_meta.get("signature")
                proxy_i = int(fg_group_meta.get("fg_proxy_score", 0) or 0)
                ga_run_idx = fg_group_meta.get("ga_run_idx")
                ga_row_idx = fg_group_meta.get("ga_row_idx")
            else:
                fg_group_meta = None
        if not isinstance(fg_group_meta, dict):
            sel_color = expected_selected_element(entry, meta_primary_color)
            n_sections, non_fever_base = fg_baseline_params(base_stats, calc_song, ref_arrays)
            if n_sections <= 0:
                continue
            max_per_section = min(int(non_fever_base or 0), 15)
            key = (str(sel_color), int(n_sections), int(max_per_section))
            sig = stats_signature(base_stats, calc_song, sel_color)
            ga_run_idx = eval_data.get("_ga_gpu_run_idx")
            ga_row_idx = eval_data.get("_ga_gpu_row_idx")
            proxy_i = 0
        try:
            entry_sig[int(id(entry))] = str(sig)
        except (ValueError, TypeError):
            pass
        groups.setdefault(key, {}).setdefault(sig, []).append((entry, eval_data))
        group_centers.setdefault(key, set()).add((int(center_ft), int(center_ff)))
        try:
            base_score_i = int(entry_base_score(entry) or 0)
        except (ValueError, TypeError):
            base_score_i = 0
        try:
            sig_rows = group_signature_rows.setdefault(key, {})
            row = sig_rows.get(sig)
            if not isinstance(row, dict):
                row = {
                    "sig": sig,
                    "base": int(base_score_i),
                    "proxy": int(proxy_i),
                    "priority": int(entry.get("_fg_priority", 0) or 0),
                    "center": (
                        int((base_stats or {}).get("Fever Time", 0) or 0),
                        int((base_stats or {}).get("Fever Fill Rate", 0) or 0),
                    ),
                    "timing_bucket": _signature_timing_bucket_impl(sig),
                    "base_stats": base_stats,
                    "ga_coord": (
                        (int(ga_run_idx), int(ga_row_idx))
                        if ga_run_idx is not None and ga_row_idx is not None
                        else None
                    ),
                }
                sig_rows[sig] = row
            else:
                if int(proxy_i) > int(row.get("proxy", 0) or 0):
                    row["proxy"] = int(proxy_i)
                try:
                    row["priority"] = max(int(row.get("priority", 0) or 0), int(entry.get("_fg_priority", 0) or 0))
                except (ValueError, TypeError):
                    pass
                if row.get("ga_coord") is None and ga_run_idx is not None and ga_row_idx is not None:
                    row["ga_coord"] = (int(ga_run_idx), int(ga_row_idx))
        except (KeyError, TypeError, ValueError, AttributeError):
            pass
        computed += 1
    if perf:
        t_collect_sec = time.perf_counter() - _t_collect0
    _emit_finder_phase(
        "collect_ready",
        entry_items=int(len(entry_items)),
        computed=int(computed),
        groups=int(len(groups)),
        db_cached_reuse=int(db_cached_reuse),
        no_eval_skips=int(no_eval_skips),
        fg_group_meta_cached=int(fg_group_meta_cached),
        fg_group_meta_built=int(fg_group_meta_built),
    )
    keep_sigs: set[str] = set()
    if download_topk_enabled:
        entry_count_guard = max(int(LOADOUTS_PER_SONG_LIMIT), int(len(entry_items)))
        base_keep_n = int(entry_count_guard)
        try:
            fg_proxy_keep_n = int(env_get("FG_DOWNLOAD_KEEP_PROXY_SIGS", str(entry_count_guard)) or 0)
        except (ValueError, TypeError):
            fg_proxy_keep_n = int(entry_count_guard)
        fg_proxy_keep_n = max(0, int(fg_proxy_keep_n))
        try:
            topk_cap = int(getattr(fg_fields, "FG_DOWNLOAD_TOPK_MAX", 256) or 256)
        except (ValueError, TypeError, AttributeError):
            topk_cap = 256
        default_keep_cap = max(int(entry_count_guard), int(topk_cap) - min(int(topk_cap), int(download_topk_k)))
        try:
            max_keep_total = int(env_get("FG_DOWNLOAD_KEEP_SIGS_MAX", str(default_keep_cap)) or 0)
        except (ValueError, TypeError):
            max_keep_total = int(default_keep_cap)
        max_keep_total = max(int(entry_count_guard), int(max_keep_total))
        keep_sigs = _build_topk_keep_signature_set(
            items=entry_items,
            entry_sig=entry_sig,
            group_signature_rows=group_signature_rows,
            base_keep_n=base_keep_n,
            fg_proxy_keep_n=fg_proxy_keep_n,
            max_keep_total=max_keep_total,
        )
    reduced_sig_lists: dict[tuple[str, int, int], list] = {}
    if groups:
        frontier_payloads: list[dict[str, object]] = []
        frontier_keys: list[tuple[str, int, int]] = []
        frontier_meta_batches: list[list[dict]] = []
        for group_key, sig_map in groups.items():
            sig_list0 = list(sig_map.keys())
            reduced_sig_lists[group_key] = list(sig_list0)
            frontier_total_before += int(len(sig_list0))
            if sig_frontier_limit <= 0 or len(sig_list0) <= int(sig_frontier_limit):
                frontier_total_after += int(len(sig_list0))
                continue
            sig_rows = group_signature_rows.get(group_key, {}) if isinstance(group_signature_rows, dict) else {}
            row_list = [sig_rows.get(sig0) for sig0 in sig_list0 if isinstance(sig_rows.get(sig0), dict)]
            metas = _build_signature_frontier_metas_from_rows_impl(
                row_list,
                keep_sigs=keep_sigs,
                center_bin=int(sig_frontier_center_bin),
            )
            if len(metas) <= int(sig_frontier_limit):
                reduced_sig_lists[group_key] = [m["sig"] for m in metas]
                frontier_total_after += int(len(metas))
                continue
            try:
                top_base_keep = min(int(sig_frontier_limit), int(LOADOUTS_PER_SONG_LIMIT))
            except (ValueError, TypeError):
                top_base_keep = int(sig_frontier_limit)
            timing_bucket_ids: dict[tuple[str, str, str, int], int] = {}
            next_timing_bucket_id = 1
            base_scores: list[int] = []
            proxy_scores: list[int] = []
            priorities: list[int] = []
            force_keep_flags: list[int] = []
            center_ft: list[int] = []
            center_ff: list[int] = []
            timing_buckets: list[int] = []
            for meta in metas:
                base_scores.append(int(meta["base"]))
                proxy_scores.append(int(meta["proxy"]))
                priorities.append(int(meta["priority"]))
                force_keep_flags.append(1 if bool(meta["force_keep"]) else 0)
                ft_bucket, ff_bucket = meta["center_bucket"]
                center_ft.append(int(ft_bucket))
                center_ff.append(int(ff_bucket))
                timing_bucket = meta["timing_bucket"]
                if timing_bucket == ("", "", "", 0):
                    timing_buckets.append(0)
                    continue
                bucket_id = timing_bucket_ids.get(timing_bucket)
                if bucket_id is None:
                    bucket_id = int(next_timing_bucket_id)
                    timing_bucket_ids[timing_bucket] = bucket_id
                    next_timing_bucket_id += 1
                timing_buckets.append(int(bucket_id))
            frontier_payloads.append(
                {
                    "base_scores": np.asarray(base_scores, dtype=np.int32),
                    "proxy_scores": np.asarray(proxy_scores, dtype=np.int32),
                    "priorities": np.asarray(priorities, dtype=np.int32),
                    "force_keep": np.asarray(force_keep_flags, dtype=np.int32),
                    "center_bucket_ft": np.asarray(center_ft, dtype=np.int32),
                    "center_bucket_ff": np.asarray(center_ff, dtype=np.int32),
                    "timing_bucket": np.asarray(timing_buckets, dtype=np.int32),
                    "limit": int(sig_frontier_limit),
                    "top_base_keep": int(top_base_keep),
                }
            )
            frontier_keys.append(group_key)
            frontier_meta_batches.append(metas)
        if frontier_payloads:
            try:
                if gpu_client is not None:
                    selected_batches = gpu_client.submit(
                        GpuRequestType.FG_SELECT_SIGNATURE_FRONTIER_BATCH,
                        {"payloads": frontier_payloads},
                    ).future.result()
                else:
                    selected_batches = fg_select_signature_frontier_batch(frontier_payloads)
            except Exception as exc:
                raise RuntimeError("GPU FG signature frontier batch selection failed") from exc
            for group_key, metas, selected_indices in zip(frontier_keys, frontier_meta_batches, selected_batches):
                out: list = []
                seen: set = set()
                for idx in list(np.asarray(selected_indices, dtype=np.int32)):
                    i = int(idx)
                    if i < 0 or i >= len(metas):
                        continue
                    sig = metas[i]["sig"]
                    if sig in seen:
                        continue
                    seen.add(sig)
                    out.append(sig)
                expected_n = min(int(sig_frontier_limit), int(len(metas)))
                if len(out) < expected_n:
                    raise RuntimeError(f"GPU FG frontier batch returned {len(out)} signatures; expected {expected_n}")
                reduced_sig_lists[group_key] = list(out[: int(sig_frontier_limit)])
                frontier_total_after += int(len(reduced_sig_lists[group_key]))
                if int(len(reduced_sig_lists[group_key])) < int(len(metas)):
                    frontier_groups_reduced += 1
    _emit_finder_phase(
        "frontier_ready",
        groups=int(len(groups)),
        frontier_before=int(frontier_total_before),
        frontier_after=int(frontier_total_after),
        frontier_groups_reduced=int(frontier_groups_reduced),
    )
    use_timing_envelope_fg = _uses_timing_envelope_fg(calc_song)
    if use_timing_envelope_fg:
        fg_scorer, fg_scorer_cache_hit = _dispatch_caches.get_cached_chart_scorer(
            calc_song, ref_arrays, create_chart_scorer_from_calc_song
        )
    else:
        fg_scorer = create_scorer_from_calc_song(calc_song, ref_arrays)
        fg_scorer_cache_hit = False
    if (not fg_scorer_cache_hit) and use_timing_envelope_fg:
        try:
            logger.debug(
                "[FG] Cached chart AnalyticalFGScorer: %s notes, head_len=%s",
                getattr(fg_scorer, "total_notes", "?"),
                getattr(fg_scorer, "head_len", "?"),
            )
        except Exception as e:
            logger.debug(f"gpu_dispatch:_flush_fg_tasks_batch: {e}")
    pair_caps_grid = None
    pair_caps_from_timeline = False
    caps_mode = str(env_get("FG_PAIR_CAPS_MODE", "timeline") or "").strip().lower()
    if caps_mode in {"timeline", "gpu", "1", "true", "yes", "on", ""}:
        pair_caps_from_timeline = True
    elif caps_mode in {"none", "off", "0", "false", "no"}:
        pair_caps_from_timeline = False
        pair_caps_grid = None  # unlimited caps
    else:
        raise ValueError(f"Unsupported FG_PAIR_CAPS_MODE={caps_mode!r}; expected 'timeline' or 'none'")
    if pair_caps_from_timeline and gpu_client is None:
        try:
            from ....solver.taichi_gem.api.timeline import precompute_timeline_gpu
            precompute_timeline_gpu(calc_song, ref_arrays, song_slot=int(song_slot))
        except Exception as e:
            raise RuntimeError("timeline pair-caps precompute failed") from e
    if (
        (not pair_caps_from_timeline)
        and pair_caps_grid is None
        and caps_mode not in {"none", "off", "0", "false", "no"}
    ):
        raise RuntimeError("FG pair caps require GPU timeline precompute or FG_PAIR_CAPS_MODE=none")
    _emit_finder_phase(
        "pair_caps_ready",
        timing_envelope_fg=int(bool(use_timing_envelope_fg)),
        fg_scorer_cache_hit=int(bool(fg_scorer_cache_hit)),
        pair_caps_from_timeline=int(bool(pair_caps_from_timeline)),
    )
    defer_group_apply = gpu_client is not None and per_pair_breakpoints
    deferred_genome_stats_pool_max_keep = max(2, min(32, int(fg_async_max_inflight) * 2))
    deferred_genome_stats_pool = DeferredGenomeStatsPool.for_owner(
        process_force_greats_gpu_finder,
        enabled=bool(defer_group_apply and in_process and gpu_client is not None),
        max_keep=int(deferred_genome_stats_pool_max_keep),
    )
    deferred_gpu_applies: list[dict] = []
    fused_breakpoints_solve = _should_use_fused_breakpoints_solve(
        in_process=bool(in_process),
        has_gpu_client=bool(gpu_client is not None),
    )
    fused_payloads_per_request = 1
    fused_payload_batch: list[dict] = []
    fused_ctx_batch: list[dict] = []
    if fused_breakpoints_solve:
        try:
            fused_payloads_per_request = max(
                1,
                int(
                    env_get(
                        "FG_FUSED_PAYLOADS_PER_REQUEST",
                        str(_default_fused_payloads_per_request()),
                    )
                    or str(_default_fused_payloads_per_request())
                ),
            )
        except (ValueError, TypeError):
            fused_payloads_per_request = _default_fused_payloads_per_request()
        fused_payloads_per_request = max(1, int(fused_payloads_per_request))
        if in_process and int(fused_payloads_per_request) > 8:
            if not hasattr(process_force_greats_gpu_finder, "_fg_fused_payloads_clamp_warned"):
                process_force_greats_gpu_finder._fg_fused_payloads_clamp_warned = True
                logger.warning(
                    "[FG] FG_FUSED_PAYLOADS_PER_REQUEST is very high (%s); clamping to 8 to reduce TDR/freezing risk.",
                    int(fused_payloads_per_request),
                )
            fused_payloads_per_request = 8
    _emit_finder_phase(
        "surface_ready",
        groups=int(len(groups)),
        frontier_before=int(frontier_total_before),
        frontier_after=int(frontier_total_after),
        per_pair_breakpoints=int(bool(per_pair_breakpoints)),
        fused_breakpoints_solve=int(bool(fused_breakpoints_solve)),
        timing_envelope_fg=int(bool(use_timing_envelope_fg)),
        tasks_per_request=int(fg_async_tasks_per_request),
        max_inflight=int(fg_async_max_inflight),
    )
    fg_submit_clock_start = time.perf_counter()
    def _flush_fused_payload_batch() -> None:
        nonlocal timeline_precompute_queued, n_gpu_calls
        nonlocal fg_fused_tile_batches, fg_fused_tile_splits
        if not fused_payload_batch:
            return
        if gpu_client is None:
            raise RuntimeError("fused payload batch requires gpu_client")
        timeline_precompute_queued = True
        max_pairs_total = 256
        try:
            max_pairs_total = int(env_get("FG_BREAKPOINTS_MAX_PAIRS_PER_REQUEST", "256") or "256")
        except (ValueError, TypeError):
            max_pairs_total = 256
        max_pairs_total = max(0, min(int(max_pairs_total), 256))
        def _pairs_len(payload: dict) -> int:
            pairs = payload.get("ftff_pairs")
            if pairs is None:
                return int(max_pairs_total) if int(max_pairs_total) > 0 else 0
            try:
                shape = getattr(pairs, "shape", None)
                if shape is not None and len(shape) > 0:
                    return max(0, int(shape[0]))
            except (ValueError, TypeError, KeyError, AttributeError):
                pass
            try:
                return max(0, int(len(pairs)))
            except (ValueError, TypeError):
                return 0
        def _submit_chunk(payloads: list[dict], ctxs: list[dict]) -> None:
            nonlocal n_gpu_calls
            fut_local = gpu_client.submit_fg_solve_with_breakpoints_batch(payloads).future
            for j, ctx_local in enumerate(ctxs):
                ctx_local["download_future"] = fut_local
                ctx_local["download_index"] = int(j)
                buf = ctx_local.get("_deferred_genome_stats_backing")
                if buf is not None:
                    deferred_genome_stats_pool.attach_release(fut_local, buf)
            n_gpu_calls += 1
        zipped_items = list(zip(fused_payload_batch, fused_ctx_batch))
        if enforce_single_request:
            pair_chunks = [zipped_items]
        elif max_pairs_total <= 0:
            pair_chunks = [zipped_items]
        else:
            pair_chunks: list[list[tuple[dict, dict]]] = []
            chunk_items: list[tuple[dict, dict]] = []
            chunk_pairs = 0
            for payload, ctx in zipped_items:
                p_len = int(_pairs_len(payload))
                if chunk_items and (int(chunk_pairs) + int(p_len)) > int(max_pairs_total):
                    pair_chunks.append(list(chunk_items))
                    chunk_items = []
                    chunk_pairs = 0
                chunk_items.append((payload, ctx))
                chunk_pairs += int(p_len)
            if chunk_items:
                pair_chunks.append(list(chunk_items))
        request_chunks: list[list[tuple[dict, dict]]] = []
        if enforce_single_request:
            request_chunks = [list(zipped_items)]
        else:
            for pair_chunk in pair_chunks:
                subchunks = _split_items_by_work_budget(
                    list(pair_chunk),
                    max_work=int(fg_fused_tile_max_threads),
                    estimate_fn=lambda item: _estimate_fused_payload_threads(item[0]),
                )
                request_chunks.extend(subchunks)
        fg_fused_tile_batches += int(len(request_chunks))
        if len(request_chunks) > 1:
            fg_fused_tile_splits += int(len(request_chunks) - 1)
        for chunk in request_chunks:
            payloads = [payload for payload, _ctx in chunk]
            ctxs = [ctx for _payload, ctx in chunk]
            _maybe_emit_first_gpu_submit(
                submit_mode="fused",
                batch_size=int(len(payloads)),
                tile_count=int(len(request_chunks)),
                download_after=False,
            )
            _submit_chunk(payloads, ctxs)
        fused_payload_batch.clear()
        fused_ctx_batch.clear()
    for group_key, sig_map in groups.items():
        if not (isinstance(group_key, tuple) and len(group_key) == 3):
            if not hasattr(process_force_greats_gpu_finder, "_fg_bad_group_key_warned"):
                process_force_greats_gpu_finder._fg_bad_group_key_warned = True
                warn_fallback(
                    "fg.group_key.bad_shape",
                    "invalid FG group key shape; skipping group",
                    context={"group_key": repr(group_key)},
                    fatal=False,
                )
            continue
        sel_color, n_sections, max_per_section = group_key
        _t_cfg0 = time.perf_counter() if perf else 0.0
        sig_rows_map = group_signature_rows.get(group_key, {}) or {}
        search_radius = int(FG_SEARCH_RADIUS)
        centers = group_centers.get(group_key, set())
        if search_radius >= TOTAL_GEM_BUDGET:
            search_radius = TOTAL_GEM_BUDGET
        fast_pairs = str(env_get("FG_FTFF_PAIRS_FAST", "0") or "").strip().lower() in (TRUTHY_ENV_VALUES | {""})
        sig_list = list(reduced_sig_lists.get(group_key, list(sig_map.keys())))
        if len(sig_list) < len(sig_map):
            centers = {
                tuple((sig_rows_map.get(sig0) or {}).get("center") or (0, 0))
                for sig0 in sig_list
                if isinstance(sig_rows_map.get(sig0), dict)
            }
            if not centers:
                centers = group_centers.get(group_key, set())
        ftff_pairs = collect_ftff_pairs_from_centers(
            centers,
            search_radius=int(search_radius),
            total_budget=int(TOTAL_GEM_BUDGET),
            use_fast=bool(fast_pairs),
        )
        ftff_pairs_packed = _pack_pairs_int32(ftff_pairs)
        counts_list = None
        if perf:
            t_cfg_build_sec += time.perf_counter() - _t_cfg0
        color_flags = build_color_flag_values(p_color, s_color, sel_color)
        flag_kwargs = color_flags.as_dict()
        fused_solve_kwargs_static = {
            "n_sections": int(n_sections),
            **flag_kwargs,
            "ref_arrays": ref_arrays,
            "total_budget": TOTAL_GEM_BUDGET,
            "gem_scale_fever": GEM_SCALE_FEVER,
            "pair_caps_grid": pair_caps_grid,
            "pair_caps_from_timeline": bool(pair_caps_from_timeline),
            "song_slot": int(song_slot),
            "return_raw": True,
            "accumulate_global": True,
        }
        max_genomes_per_batch = 1024
        if per_pair_breakpoints:
            try:
                merge_cfg_limit = int(env_get("FG_MERGE_MAX_CONFIGS", "5000"))
                threads_default = "200000000" if in_process else "50000000"
                merge_threads_limit = int(env_get("FG_MERGE_MAX_THREADS", threads_default))
            except (ValueError, TypeError):
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
                fused_floor = 128 if bool(fused_breakpoints_solve) else 0
                min_batch = max(fused_floor, 32) if in_process else 16
                max_genomes_per_batch = max(min_batch, min(int(max_genomes_per_batch), int(max_by_threads)))
        min_tail = 16 if in_process else 8
        idx0 = 0
        n_sig = len(sig_list)
        while idx0 < n_sig:
            remaining = n_sig - idx0
            if remaining <= max_genomes_per_batch:
                chunk_size = remaining
            elif remaining < (max_genomes_per_batch + min_tail):
                chunk_size = remaining - min_tail
                if chunk_size <= 0:
                    chunk_size = max_genomes_per_batch
            else:
                chunk_size = max_genomes_per_batch
            chunk_sigs = sig_list[idx0 : idx0 + chunk_size]
            idx0 += chunk_size
            _t_cache0 = time.perf_counter() if perf else 0.0
            pending = []
            pending_sigs = []
            for sig in chunk_sigs:
                rep_row = sig_rows_map.get(sig) if isinstance(sig_rows_map, dict) else None
                rep = (rep_row or {}).get("base_stats") if isinstance(rep_row, dict) else None
                if rep is None:
                    continue
                pending.append(rep)
                pending_sigs.append(sig)
            if perf:
                t_cache_check_sec += time.perf_counter() - _t_cache0
            if not pending:
                continue
            _t_genome0 = time.perf_counter() if perf else 0.0
            n_pending = len(pending)
            genome_stats_n_genomes = int(n_pending)
            genome_stats_arr = None
            download_base_scores = None
            download_keep_mask = None
            download_keep_count = None
            if download_topk_enabled:
                try:
                    base_buf = np.zeros((int(n_pending),), dtype=np.int32)
                    keep_buf = np.zeros((int(n_pending),), dtype=np.int32)
                    for i_sig, sig0 in enumerate(pending_sigs):
                        row0 = sig_rows_map.get(sig0) if isinstance(sig_rows_map, dict) else None
                        base_i = int((row0 or {}).get("base", 0) or 0) if isinstance(row0, dict) else 0
                        base_buf[int(i_sig)] = int(base_i)
                        keep_buf[int(i_sig)] = 1 if str(sig0) in keep_sigs else 0
                    download_base_scores = base_buf
                    download_keep_mask = keep_buf
                    try:
                        download_keep_count = int(int(keep_buf.sum()) if keep_buf is not None else 0)
                    except (ValueError, TypeError):
                        download_keep_count = None
                except (ValueError, TypeError, KeyError, AttributeError):
                    download_base_scores = None
                    download_keep_mask = None
                    download_keep_count = None
            genome_stats_backing = None
            genome_stats_arr = None
            if defer_group_apply and in_process and gpu_client is not None:
                genome_stats_arr, genome_stats_backing = deferred_genome_stats_pool.checkout(int(n_pending))
            else:
                if not hasattr(process_force_greats_gpu_finder, "_genome_stats_buf"):
                    process_force_greats_gpu_finder._genome_stats_buf = np.zeros((1024, 7), dtype=np.int32)
                genome_stats_buf = process_force_greats_gpu_finder._genome_stats_buf
                if genome_stats_buf.shape[0] < n_pending:
                    process_force_greats_gpu_finder._genome_stats_buf = np.zeros(
                        (max(1024, n_pending), 7), dtype=np.int32
                    )
                    genome_stats_buf = process_force_greats_gpu_finder._genome_stats_buf
                genome_stats_arr = genome_stats_buf[:n_pending, :]
            for i, bs in enumerate(pending):
                genome_stats_arr[i, 0] = int(bs.get("Perfect Points", 0))
                genome_stats_arr[i, 1] = int(bs.get("Combo Multiplier", 0))
                genome_stats_arr[i, 2] = int(bs.get("Fever Multiplier", 0))
                genome_stats_arr[i, 3] = int(bs.get(p_color, 0))  # p_val
                genome_stats_arr[i, 4] = int(bs.get(s_color, 0))  # s_val
                genome_stats_arr[i, 5] = int(bs.get("Fever Time", 0))  # ft_stat
                genome_stats_arr[i, 6] = int(bs.get("Fever Fill Rate", 0))  # ff_stat
            genome_stats_uploaded = False
            fg_genome_stats_uploaded_batches += 1
            fg_genome_stats_uploaded_bytes_est += int(n_pending) * 7 * 4
            song_data = calc_song.get("song_data", {}) or {}
            timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
            great_candidates = song_data.get("fg_great_candidate_timestamps")
            try:
                if isinstance(timestamps, np.ndarray) and timestamps.dtype != np.float32:
                    timestamps_f32 = np.asarray(timestamps, dtype=np.float32)
                    if not timestamps_f32.flags["C_CONTIGUOUS"]:
                        timestamps_f32 = np.ascontiguousarray(timestamps_f32)
                    if "fg_timestamps" in song_data:
                        song_data["fg_timestamps"] = timestamps_f32
                    else:
                        song_data["timestamps"] = timestamps_f32
                    timestamps = timestamps_f32
                elif isinstance(timestamps, np.ndarray) and not timestamps.flags["C_CONTIGUOUS"]:
                    timestamps = np.ascontiguousarray(timestamps, dtype=np.float32)
                    if "fg_timestamps" in song_data:
                        song_data["fg_timestamps"] = timestamps
                    else:
                        song_data["timestamps"] = timestamps
            except (ValueError, TypeError, KeyError):
                pass
            try:
                if isinstance(great_candidates, np.ndarray) and great_candidates.dtype != np.float32:
                    gc_f32 = np.asarray(great_candidates, dtype=np.float32)
                    if not gc_f32.flags["C_CONTIGUOUS"]:
                        gc_f32 = np.ascontiguousarray(gc_f32)
                    song_data["fg_great_candidate_timestamps"] = gc_f32
                    great_candidates = gc_f32
                elif isinstance(great_candidates, np.ndarray) and not great_candidates.flags["C_CONTIGUOUS"]:
                    great_candidates = np.ascontiguousarray(great_candidates, dtype=np.float32)
                    song_data["fg_great_candidate_timestamps"] = great_candidates
            except (ValueError, TypeError, KeyError):
                pass
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
            selected_indices = None
            cfg_counts_arr = None
            if per_pair_breakpoints:
                _t_cfg1 = time.perf_counter() if perf else 0.0
                base_stats_pairs = {
                    (int(bs.get("Fever Time", 0) or 0), int(bs.get("Fever Fill Rate", 0) or 0)) for bs in pending
                }
                base_pairs_list = sorted(base_stats_pairs)
                active_ftff_pairs = ftff_pairs
                active_ftff_pairs_packed = ftff_pairs_packed
                if not active_ftff_pairs:
                    if perf:
                        t_cfg_build_sec += time.perf_counter() - _t_cfg1
                    continue
                active_ftff_pairs_packed = _pack_pairs_int32(active_ftff_pairs)
                base_pairs_packed = _pack_pairs_int32(base_pairs_list)
                ftff_pairs_submit = (
                    active_ftff_pairs_packed if active_ftff_pairs_packed is not None else active_ftff_pairs
                )
                base_pairs_submit = base_pairs_packed if base_pairs_packed is not None else base_pairs_list
                try:
                    max_union_cfg = int(env_get("FG_MERGE_MAX_CONFIGS", "5000"))
                    threads_default = "200000000" if in_process else "50000000"
                    max_union_threads = int(env_get("FG_MERGE_MAX_THREADS", threads_default))
                except (ValueError, TypeError):
                    max_union_cfg = 5000
                    max_union_threads = 20000000
                if (
                    bool(fused_breakpoints_solve)
                    and gpu_client is not None
                    and in_process
                    and (not _is_empty_pairs(ftff_pairs_submit))
                ):
                    if base_pairs_list:
                        try:
                            solve_kwargs = dict(fused_solve_kwargs_static)
                            solve_kwargs["upload_genome_stats"] = True
                            fused_payload = {
                                "ftff_pairs": ftff_pairs_submit,
                                "base_stats_pairs": base_pairs_submit,
                                "n_sections": int(n_sections),
                                "song_slot": int(song_slot),
                                "gem_scale_fever": int(GEM_SCALE_FEVER),
                                "calc_song": calc_song,
                                "ensure_timeline_precompute": bool(pair_caps_from_timeline),
                                "genome_stats_list": genome_stats_arr,
                                "timestamps_np": timestamps,
                                "great_candidate_timestamps_np": great_candidates,
                                "long_notes": int(long_notes),
                                "last_note_time": float(last_note_time),
                                "solve_kwargs": solve_kwargs,
                                "fg_reset_before": True,
                                "fg_download_topk": int(download_topk_k) if download_topk_enabled else None,
                                "fg_download_base_scores": download_base_scores,
                                "fg_download_keep_mask": download_keep_mask,
                            }
                            if enforce_single_request:
                                fused_payload["fg_force_single_owner_request"] = True
                            if defer_group_apply:
                                ctx = {
                                    "mode": "breakpoints_fused",
                                    "pending_sigs": pending_sigs,
                                    "pending": pending,
                                    "sig_map": sig_map,
                                    "sel_color": sel_color,
                                    "n_sections": int(n_sections),
                                    "max_per_section": int(max_per_section),
                                    "n_pending": int(n_pending),
                                    "fg_scorer": fg_scorer,
                                    "download_future": None,
                                    "download_index": None,
                                    "futures": [],
                                    "download_topk": int(download_topk_k)
                                    if (download_topk_enabled and download_base_scores is not None)
                                    else None,
                                    "download_base_scores": download_base_scores,
                                    "download_keep_mask": download_keep_mask,
                                    "download_keep_count": int(download_keep_count)
                                    if download_keep_count is not None
                                    else None,
                                }
                                if genome_stats_backing is not None:
                                    ctx["_deferred_genome_stats_backing"] = genome_stats_backing
                                deferred_gpu_applies.append(ctx)
                                fused_payload_batch.append(fused_payload)
                                fused_ctx_batch.append(ctx)
                                _maybe_emit_first_gpu_task_queued(
                                    queue_mode="fused",
                                    queue_len=int(len(fused_payload_batch)),
                                    pair_count=int(_safe_metric_count(ftff_pairs_submit)),
                                    cfg_count=int(_safe_metric_count(base_pairs_submit)),
                                    n_sections_value=int(n_sections),
                                    n_pending_value=int(n_pending),
                                )
                                should_submit_fused = len(fused_payload_batch) >= int(fused_payloads_per_request)
                                if (not bool(enforce_single_request)) and (not first_gpu_submit_emitted):
                                    should_submit_fused = True
                                if should_submit_fused:
                                    _flush_fused_payload_batch()
                                continue
                            timeline_precompute_queued = True
                            fused_future = gpu_client.submit_ga_fg_fused_solve_with_breakpoints(fused_payload).future
                            n_gpu_calls += 1
                            genome_stats_uploaded = True
                            gpu_results = fused_future.result()
                            if not isinstance(gpu_results, dict):
                                raise RuntimeError("Fused FG request returned no result")
                            _accumulate_fused_surface_metrics(gpu_results)
                            result_final = gpu_results["final_score"]
                            result_base = gpu_results["base_score"]
                            result_cfg_idx = gpu_results["cfg_idx"]
                            cfg_counts_arr = gpu_results.get("cfg_counts")
                            result_ft = gpu_results["FT"]
                            result_ff = gpu_results["FF"]
                            result_g_pp = gpu_results["g_pp"]
                            result_g_cm = gpu_results["g_cm"]
                            result_g_fm = gpu_results["g_fm"]
                            result_g_ov = gpu_results["g_ov"]
                            selected_indices = gpu_results.get("selected_indices")
                        except Exception as _fuse_err:
                            raise RuntimeError("fused breakpoint+solve failed") from _fuse_err
                def _iter_groups_from_prefix_frontier():
                    yield {
                        "ftff_pairs": ftff_pairs_submit,
                        "counts_max_fp": {
                            "mode": "gpu",
                            "n_sections": int(n_sections),
                            "song_slot": int(song_slot),
                            "gem_scale_fever": int(GEM_SCALE_FEVER),
                        },
                    }
                group_mode = "prefix_frontier"
                group_compute_fn = _iter_groups_from_prefix_frontier
                can_cache_groups = (
                    bool(breakpoint_group_cache_enabled)
                    and int(n_sections) > 0
                    and int(len(base_pairs_list or [])) > 0
                    and int(len(base_pairs_list or [])) <= int(breakpoint_group_cache_max_base_pairs)
                    and int(len(active_ftff_pairs or [])) > 0
                    and int(len(active_ftff_pairs or [])) <= int(breakpoint_group_cache_max_pairs)
                )
                cacheable_groups_accum: list[dict] | None = None
                if can_cache_groups:
                    group_list = _dispatch_caches.peek_cached_breakpoint_groups(
                        calc_song=calc_song,
                        n_sections=int(n_sections),
                        ftff_pairs=active_ftff_pairs,
                        base_stats_pairs=base_pairs_list,
                        merge_threshold_cfgs=int(max_union_cfg),
                        merge_threshold_threads=int(max_union_threads),
                        n_genomes=int(n_pending),
                        gem_scale_fever=int(GEM_SCALE_FEVER),
                        mode=str(group_mode),
                    )
                    if group_list is not None:
                        breakpoint_group_cache_hits += 1
                        group_iter = iter(group_list)
                    else:
                        breakpoint_group_cache_misses += 1
                        cacheable_groups_accum = []
                        group_iter = group_compute_fn()
                else:
                    group_iter = group_compute_fn()
                logged_first = False
                group_count = 0
                _maybe_emit_first_group_iter_ready(
                    group_mode=str(group_mode),
                    cache_hit=bool(group_list is not None) if can_cache_groups else False,
                    ftff_pairs_count=int(_safe_metric_count(active_ftff_pairs)),
                    sig_count=int(len(sig_list or [])),
                    n_sections_value=int(n_sections),
                    n_pending_value=int(n_pending),
                )
                if perf:
                    t_cfg_build_sec += time.perf_counter() - _t_cfg1
                cfg_windows: list[dict] = []
                cfg_next_base = 0
                group_futures = []
                master_configs: list = []
                if gpu_client is not None:
                    need_reset = True
                else:
                    _submit_fg_reset_global_best(n_pending, blocking=True)
                for group in group_iter:
                    if cacheable_groups_accum is not None:
                        cacheable_groups_accum.append(group)
                    group_count += 1
                    counts_list, counts_max_fp, group_pairs = _extract_group_payload(group)
                    if (not counts_list and not counts_max_fp) or _is_empty_pairs(group_pairs):
                        continue
                    group_cfg_offset = int(cfg_next_base)
                    if counts_list:
                        cfg_len0 = int(len(counts_list))
                        cfg_windows.append(
                            {
                                "base": int(group_cfg_offset),
                                "len": int(cfg_len0),
                                "kind": "list",
                                "counts_list": counts_list,
                            }
                        )
                    else:
                        if isinstance(counts_max_fp, dict) and str(counts_max_fp.get("mode") or "") == "gpu":
                            cfg_len0 = 0
                            max_fp_norm = []
                        else:
                            raise RuntimeError("FG max-FP rectangle groups were removed; expected prefix frontier")
                        cfg_windows.append(
                            {
                                "base": int(group_cfg_offset),
                                "len": int(cfg_len0),
                                "kind": "prefix_frontier" if isinstance(counts_max_fp, dict) else "max_fp",
                                "max_fp": list(max_fp_norm),
                                "n_sections": int(n_sections),
                            }
                        )
                    cfg_next_base = int(group_cfg_offset) + int(cfg_len0)
                    if not logged_first:
                        logged_first = True
                        bps = group.get("section_breakpoints") or ()
                        if not bps:
                            try:
                                max_fp0 = list(group.get("counts_max_fp") or [])
                                if max_fp0:
                                    bps = [range(0, int(v) + 1) for v in max_fp0]
                            except (ValueError, TypeError, KeyError, AttributeError):
                                bps = ()
                        if bps and (env_flag("METAFINDER_DEBUG_PROFILE", "0") or env_flag("DEBUG_PROFILE", "0")):
                            logger.debug(
                                "[FG] Per-FT/FF Breakpoints (GPU accumulation): %s FT/FF pairs",
                                len(active_ftff_pairs),
                            )
                            for sec_idx, bp in enumerate(bps):
                                logger.debug(
                                    "     Section %s: %s%s",
                                    sec_idx + 1,
                                    list(bp)[:15],
                                    "..." if len(bp) > 15 else "",
                                )
                    _t_gpu0 = time.perf_counter() if perf else 0.0
                    if gpu_client is not None:
                        counts_list_packed = counts_list
                        if counts_list:
                            try:
                                arr_cfg = np.asarray(counts_list, dtype=np.int32)
                                if getattr(arr_cfg, "ndim", 0) == 2 and int(arr_cfg.shape[0]) == int(len(counts_list)):
                                    counts_list_packed = arr_cfg
                            except (ValueError, TypeError, KeyError):
                                counts_list_packed = counts_list
                        pairs_packed = group_pairs
                        try:
                            if group_pairs is not None and not isinstance(group_pairs, np.ndarray):
                                pairs_packed = np.asarray(group_pairs, dtype=np.int32)
                        except (ValueError, TypeError, KeyError):
                            pairs_packed = group_pairs
                        for ftff_chunk in _iter_ftff_chunks(pairs_packed, int(fg_fields.FG_MAX_FTFF)):
                            fg_tasks_batch.append(
                                {
                                    "counts_list": counts_list_packed if counts_list_packed is not None else None,
                                    "counts_max_fp": counts_max_fp if counts_max_fp else None,
                                    "ftff_pairs": ftff_chunk,
                                    "base_cfg_offset": int(group_cfg_offset),
                                }
                            )
                            _maybe_emit_first_gpu_task_queued(
                                queue_mode="breakpoints_per_pair",
                                queue_len=int(len(fg_tasks_batch)),
                                pair_count=int(_safe_metric_count(ftff_chunk)),
                                cfg_count=int(cfg_len0),
                                n_sections_value=int(n_sections),
                                n_pending_value=int(n_pending),
                            )
                            should_submit_tasks = len(fg_tasks_batch) >= fg_async_tasks_per_request
                            if (not bool(enforce_single_request)) and (not first_gpu_submit_emitted):
                                should_submit_tasks = True
                            if should_submit_tasks:
                                flush_plan = plan_fg_async_threshold_flush(
                                    pending_tasks=len(fg_tasks_batch),
                                    tasks_per_request=fg_async_tasks_per_request,
                                )
                                fut = None
                                if int(flush_plan.submit_count) > 0:
                                    submit_batch = fg_tasks_batch[: int(flush_plan.submit_count)]
                                    fg_tasks_batch = fg_tasks_batch[int(flush_plan.submit_count) :]
                                    fut = _flush_fg_tasks_batch(batch=submit_batch)
                                if fut is not None:
                                    group_futures.append(fut)
                    else:
                        for ftff_chunk in _iter_ftff_chunks(group_pairs, int(fg_fields.FG_MAX_FTFF)):
                            task_payload = {
                                "counts_list": counts_list if counts_list else None,
                                "counts_max_fp": counts_max_fp if counts_max_fp else None,
                                "ftff_pairs": ftff_chunk,
                                "base_cfg_offset": int(group_cfg_offset),
                            }
                            solve_kwargs = dict(
                                n_sections=n_sections,
                                **flag_kwargs,
                                ref_arrays=ref_arrays,
                                total_budget=TOTAL_GEM_BUDGET,
                                gem_scale_fever=GEM_SCALE_FEVER,
                                pair_caps_grid=pair_caps_grid,
                                pair_caps_from_timeline=bool(pair_caps_from_timeline),
                                song_slot=int(song_slot),
                                return_raw=True,
                                accumulate_global=True,
                                base_cfg_offset=group_cfg_offset,
                            )
                            uses_prefix_frontier = _uses_prefix_frontier_tasks([task_payload])
                            if uses_prefix_frontier:
                                _submit_solve_force_greats_finder_tasks(
                                    genome_stats_arr,
                                    timestamps,
                                    great_candidates,
                                    long_notes,
                                    last_note_time,
                                    fg_tasks=[task_payload],
                                    upload_genome_stats=True,
                                    prebuild_only=True,
                                    **solve_kwargs,
                                )
                            _submit_solve_force_greats_finder_tasks(
                                genome_stats_arr,
                                timestamps,
                                great_candidates,
                                long_notes,
                                last_note_time,
                                fg_tasks=[task_payload],
                                upload_genome_stats=not uses_prefix_frontier,
                                **solve_kwargs,
                            )
                    if perf:
                        t_gpu_calls_sec += time.perf_counter() - _t_gpu0
                        if len(gpu_call_shapes) < 12:
                            gpu_call_shapes.append((n_pending, int(cfg_len0), len(group_pairs), int(n_sections)))
                    n_gpu_calls += 1
                if cacheable_groups_accum is not None:
                    _dispatch_caches.store_cached_breakpoint_groups(
                        calc_song=calc_song,
                        n_sections=int(n_sections),
                        ftff_pairs=active_ftff_pairs,
                        base_stats_pairs=base_pairs_list,
                        merge_threshold_cfgs=int(max_union_cfg),
                        merge_threshold_threads=int(max_union_threads),
                        n_genomes=int(n_pending),
                        gem_scale_fever=int(GEM_SCALE_FEVER),
                        mode=str(group_mode),
                        groups=cacheable_groups_accum,
                    )
                if group_count == 1:
                    n_configs = int(cfg_next_base)
                    logger.debug(
                        "[FG] Merged breakpoint groups -> 1 batch (pairs=%s, configs=%s, GPU accumulation)",
                        len(active_ftff_pairs),
                        n_configs,
                    )
                _t_download0 = time.perf_counter() if perf else 0.0
                download_future = _flush_fg_tasks_batch(
                    download_after=True,
                    download_topk=int(download_topk_k) if download_topk_enabled else None,
                    download_base_scores=download_base_scores,
                    download_keep_mask=download_keep_mask,
                )
                fg_async_futures.clear()
                if download_future is not None:
                    group_futures.append(download_future)
                if defer_group_apply:
                    ctx = {
                        "mode": "breakpoints",
                        "pending_sigs": pending_sigs,
                        "pending": pending,
                        "sig_map": sig_map,
                        "sel_color": sel_color,
                        "n_sections": int(n_sections),
                        "max_per_section": int(max_per_section),
                        "n_pending": int(n_pending),
                        "master_configs": master_configs,
                        "cfg_windows": cfg_windows,
                        "fg_scorer": fg_scorer,
                        "download_future": download_future,
                        "futures": group_futures,
                        "download_topk": int(download_topk_k)
                        if (download_topk_enabled and download_base_scores is not None)
                        else None,
                        "download_base_scores": download_base_scores,
                        "download_keep_mask": download_keep_mask,
                        "download_keep_count": int(download_keep_count) if download_keep_count is not None else None,
                    }
                    if genome_stats_backing is not None:
                        ctx["_deferred_genome_stats_backing"] = genome_stats_backing
                        deferred_genome_stats_pool.attach_release(download_future, genome_stats_backing)
                    deferred_gpu_applies.append(ctx)
                    continue
                if hasattr(download_future, "result"):
                    _t_dl0 = time.perf_counter() if perf else 0.0
                    global_results = download_future.result()
                    if perf:
                        try:
                            t_gpu_download_wait_sec += time.perf_counter() - _t_dl0
                        except (ValueError, TypeError):
                            pass
                    for fut in fg_async_futures:
                        if hasattr(fut, "done") and fut.done():
                            _ = fut.exception()
                else:
                    global_results = None
                    for fut in group_futures:
                        _t_wait0 = time.perf_counter() if perf else 0.0
                        fut.result()
                        if perf:
                            try:
                                t_gpu_wait_sec += time.perf_counter() - _t_wait0
                            except (ValueError, TypeError):
                                pass
                if global_results is None:
                    global_results = _submit_fg_download_global_best(
                        n_pending,
                        blocking=True,
                        topk=int(download_topk_k) if download_topk_enabled else None,
                        base_scores=download_base_scores,
                        keep_mask=download_keep_mask,
                    )
                if perf:
                    t_download_sec = time.perf_counter() - _t_download0
                    logger.debug("[PERF] FG GPU global download: %.1fms", t_download_sec * 1000.0)
                result_final = global_results["final_score"]
                result_base = global_results["base_score"]
                result_ft = global_results["FT"]
                result_ff = global_results["FF"]
                result_g_pp = global_results["g_pp"]
                result_g_cm = global_results["g_cm"]
                result_g_fm = global_results["g_fm"]
                result_g_ov = global_results["g_ov"]
                selected_indices = global_results.get("selected_indices")
                cfg_idx_arr = global_results.get("cfg_idx")
                cfg_counts_arr = decode_cfg_counts_from_windows(cfg_idx_arr, cfg_windows, n_sections)
            apply_sigs = pending_sigs
            apply_pending = pending
            if selected_indices is not None:
                try:
                    import numpy as _np
                    idx_arr = _np.asarray(selected_indices, dtype=_np.int32)
                    n_res = int(getattr(result_final, "shape", (0,))[0] or 0) if result_final is not None else 0
                    if int(idx_arr.shape[0]) == int(n_res):
                        idx_list = [int(x) for x in idx_arr.tolist()]
                        apply_sigs = [pending_sigs[i] for i in idx_list]
                        apply_pending = [pending[i] for i in idx_list]
                except (ValueError, TypeError, KeyError, AttributeError):
                    apply_sigs = pending_sigs
                    apply_pending = pending
            _record_gpu_results(
                pending_sigs=apply_sigs,
                pending=apply_pending,
                sel_color=str(sel_color),
                n_sections=int(n_sections),
                max_per_section=int(max_per_section),
                counts_list=counts_list,
                fg_scorer=fg_scorer,
                result_final=result_final,
                result_base=result_base,
                result_cfg_idx=result_cfg_idx,
                result_cfg_counts=cfg_counts_arr,
                result_ft=result_ft,
                result_ff=result_ff,
                result_g_pp=result_g_pp,
                result_g_cm=result_g_cm,
                result_g_fm=result_g_fm,
                result_g_ov=result_g_ov,
            )
            if (
                bool(download_topk_enabled)
                and bool(topk_retry_on_empty)
                and selected_indices is not None
                and int(_selected_count(selected_indices)) < int(n_pending)
            ):
                full_results = _submit_fg_download_global_best(n_pending, blocking=True)
                _record_gpu_results(
                    pending_sigs=pending_sigs,
                    pending=pending,
                    sel_color=str(sel_color),
                    n_sections=int(n_sections),
                    max_per_section=int(max_per_section),
                    counts_list=[],
                    fg_scorer=fg_scorer,
                    result_final=full_results.get("final_score"),
                    result_base=full_results.get("base_score"),
                    result_cfg_idx=full_results.get("cfg_idx"),
                    result_cfg_counts=full_results.get("cfg_counts"),
                    result_ft=full_results.get("FT"),
                    result_ff=full_results.get("FF"),
                    result_g_pp=full_results.get("g_pp"),
                    result_g_cm=full_results.get("g_cm"),
                    result_g_fm=full_results.get("g_fm"),
                    result_g_ov=full_results.get("g_ov"),
                )
    if fused_payload_batch:
        _flush_fused_payload_batch()
    if deferred_gpu_applies:
        _download_future_result_cache = {}
        _done_checked_futures = set()
        _waited_futures = set()
        for ctx in deferred_gpu_applies:
            buf = ctx.get("_deferred_genome_stats_backing")
            futs = ctx.get("futures") or []
            n_pending = int(ctx.get("n_pending") or 0)
            if n_pending <= 0:
                if buf is not None:
                    deferred_genome_stats_pool.release(buf)
                    ctx["_deferred_genome_stats_backing"] = None
                continue
            download_future = ctx.get("download_future")
            gpu_results = None
            if download_future is not None and hasattr(download_future, "result"):
                fut_key = id(download_future)
                if fut_key in _download_future_result_cache:
                    gpu_results_raw = _download_future_result_cache[fut_key]
                else:
                    _t_dl0 = time.perf_counter() if perf else 0.0
                    gpu_results_raw = download_future.result()
                    _download_future_result_cache[fut_key] = gpu_results_raw
                    if perf:
                        try:
                            t_gpu_download_wait_sec += time.perf_counter() - _t_dl0
                        except (ValueError, TypeError):
                            pass
                for fut in futs:
                    if fut is download_future:
                        continue
                    other_key = id(fut)
                    if other_key in _done_checked_futures:
                        continue
                    if hasattr(fut, "done") and fut.done():
                        _ = fut.exception()
                        _done_checked_futures.add(other_key)
                if isinstance(gpu_results_raw, list):
                    try:
                        download_index = int(ctx.get("download_index") or 0)
                    except (ValueError, TypeError):
                        download_index = 0
                    if download_index < 0 or download_index >= int(len(gpu_results_raw)):
                        raise RuntimeError("Deferred FG download index out of range")
                    gpu_results = gpu_results_raw[int(download_index)]
                else:
                    gpu_results = gpu_results_raw
            if not isinstance(gpu_results, dict):
                for fut in futs:
                    fut_key = id(fut)
                    if fut_key in _waited_futures:
                        continue
                    _t_wait0 = time.perf_counter() if perf else 0.0
                    fut.result()
                    _waited_futures.add(fut_key)
                    if perf:
                        try:
                            t_gpu_wait_sec += time.perf_counter() - _t_wait0
                        except (ValueError, TypeError):
                            pass
                download_topk = ctx.get("download_topk")
                download_base_scores = ctx.get("download_base_scores")
                download_keep_mask = ctx.get("download_keep_mask")
                if download_topk is not None and download_base_scores is not None:
                    gpu_results = _submit_fg_download_global_best(
                        n_pending,
                        blocking=True,
                        topk=int(download_topk),
                        base_scores=download_base_scores,
                        keep_mask=download_keep_mask,
                    )
                else:
                    gpu_results = _submit_fg_download_global_best(n_pending, blocking=True)
            if not isinstance(gpu_results, dict):
                raise RuntimeError("Deferred FG download returned no result")
            _accumulate_fused_surface_metrics(gpu_results)
            mode = str(ctx.get("mode") or "")
            if mode not in {"breakpoints", "breakpoints_fused"}:
                if buf is not None:
                    deferred_genome_stats_pool.release(buf)
                    ctx["_deferred_genome_stats_backing"] = None
                continue
            cfg_idx_arr = gpu_results.get("cfg_idx")
            selected_indices = gpu_results.get("selected_indices")
            if mode == "breakpoints_fused":
                cfg_counts_arr = gpu_results.get("cfg_counts")
            else:
                cfg_windows = ctx.get("cfg_windows") or []
                cfg_counts_arr = decode_cfg_counts_from_windows(
                    cfg_idx_arr, cfg_windows, int(ctx.get("n_sections") or 0)
                )
            apply_sigs = ctx.get("pending_sigs") or []
            apply_pending = ctx.get("pending") or []
            if selected_indices is not None:
                try:
                    import numpy as _np
                    idx_arr = _np.asarray(selected_indices, dtype=_np.int32)
                    if int(idx_arr.shape[0]) == int(getattr(gpu_results.get("final_score"), "shape", (0,))[0] or 0):
                        idx_list = [int(x) for x in idx_arr.tolist()]
                        base_sigs = ctx.get("pending_sigs") or []
                        base_pending = ctx.get("pending") or []
                        apply_sigs = [base_sigs[i] for i in idx_list]
                        apply_pending = [base_pending[i] for i in idx_list]
                except (ValueError, TypeError, KeyError, AttributeError):
                    apply_sigs = ctx.get("pending_sigs") or []
                    apply_pending = ctx.get("pending") or []
            _record_gpu_results(
                pending_sigs=apply_sigs,
                pending=apply_pending,
                sel_color=str(ctx.get("sel_color") or ""),
                n_sections=int(ctx.get("n_sections") or 0),
                max_per_section=int(ctx.get("max_per_section") or 0),
                counts_list=[],
                fg_scorer=ctx.get("fg_scorer"),
                result_final=gpu_results["final_score"],
                result_base=gpu_results["base_score"],
                result_cfg_idx=cfg_idx_arr,
                result_cfg_counts=cfg_counts_arr,
                result_ft=gpu_results["FT"],
                result_ff=gpu_results["FF"],
                result_g_pp=gpu_results["g_pp"],
                result_g_cm=gpu_results["g_cm"],
                result_g_fm=gpu_results["g_fm"],
                result_g_ov=gpu_results["g_ov"],
            )
            if buf is not None:
                deferred_genome_stats_pool.release(buf)
                ctx["_deferred_genome_stats_backing"] = None
            if (
                bool(topk_retry_on_empty)
                and ctx.get("download_topk") is not None
                and selected_indices is not None
                and int(_selected_count(selected_indices)) < int(n_pending)
                and not _sig_results_has_fg_improvement(sig_results=sig_results, sigs=apply_sigs)
            ):
                full_results = _submit_fg_download_global_best(n_pending, blocking=True)
                _record_gpu_results(
                    pending_sigs=ctx.get("pending_sigs") or [],
                    pending=ctx.get("pending") or [],
                    sel_color=str(ctx.get("sel_color") or ""),
                    n_sections=int(ctx.get("n_sections") or 0),
                    max_per_section=int(ctx.get("max_per_section") or 0),
                    counts_list=[],
                    fg_scorer=ctx.get("fg_scorer"),
                    result_final=full_results.get("final_score"),
                    result_base=full_results.get("base_score"),
                    result_cfg_idx=full_results.get("cfg_idx"),
                    result_cfg_counts=full_results.get("cfg_counts"),
                    result_ft=full_results.get("FT"),
                    result_ff=full_results.get("FF"),
                    result_g_pp=full_results.get("g_pp"),
                    result_g_cm=full_results.get("g_cm"),
                    result_g_fm=full_results.get("g_fm"),
                    result_g_ov=full_results.get("g_ov"),
                )
    fg_variants = _retain_and_build_fg_variants(
        entry_items=entry_items,
        sig_results=sig_results,
        entry_sig=entry_sig,
        loadout_entries=loadout_entries,
        direct_ga_items=direct_ga_items,
        loadouts_per_song_limit=int(LOADOUTS_PER_SONG_LIMIT),
        entry_base_score_fn=entry_base_score,
    )
    record_finder_completion(
        logger=logger,
        meta=meta,
        fg_variants=fg_variants,
        computed=int(computed),
        groups=groups,
        perf=bool(perf),
        t_collect_sec=float(t_collect_sec),
        t_cfg_build_sec=float(t_cfg_build_sec),
        t_gpu_calls_sec=float(t_gpu_calls_sec),
        t_gpu_wait_sec=float(t_gpu_wait_sec),
        t_gpu_download_wait_sec=float(t_gpu_download_wait_sec),
        t_cache_check_sec=float(t_cache_check_sec),
        t_genome_build_sec=float(t_genome_build_sec),
        t_result_apply_sec=float(t_result_apply_sec),
        n_gpu_calls=int(n_gpu_calls),
        db_cached_reuse=int(db_cached_reuse),
        no_eval_skips=int(no_eval_skips),
        breakpoint_group_cache_hits=int(breakpoint_group_cache_hits),
        breakpoint_group_cache_misses=int(breakpoint_group_cache_misses),
        fg_task_tile_batches=int(fg_task_tile_batches),
        fg_task_tile_splits=int(fg_task_tile_splits),
        fg_fused_tile_batches=int(fg_fused_tile_batches),
        fg_fused_tile_splits=int(fg_fused_tile_splits),
        fg_genome_stats_uploaded_batches=int(fg_genome_stats_uploaded_batches),
        fg_genome_stats_uploaded_bytes_est=int(fg_genome_stats_uploaded_bytes_est),
        fg_surface_pair_drops=int(fg_surface_pair_drops),
        fg_surface_pair_reduce_sec=float(fg_surface_pair_reduce_sec),
        fg_first_submit_delay_sec=fg_first_submit_delay_sec,
        gpu_call_shapes=gpu_call_shapes,
        frontier_total_before=int(frontier_total_before),
        frontier_total_after=int(frontier_total_after),
        frontier_groups_reduced=int(frontier_groups_reduced),
        sig_frontier_limit=int(sig_frontier_limit),
    )
    return fg_variants
