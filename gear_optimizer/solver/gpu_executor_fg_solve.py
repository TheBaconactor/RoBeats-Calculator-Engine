from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse

logger = logging.getLogger(__name__)


def execute_solve_force_greats_finder(
    request: GpuRequest,
    *,
    solve_fn: Callable[..., Any],
    tasks_fn: Callable[..., Any],
    reset_global_best_fn: Callable[..., Any],
    download_global_best_fn: Callable[..., Any],
    precompute_timeline_fn: Callable[..., Any],
    record_tasks_batch_fn: Callable[[int], None] | None = None,
) -> GpuResponse:
    """Execute solve_force_greats_finder_gpu on the GPU-owner thread."""
    payload = request.payload or {}
    args = payload.get("args", ())
    kwargs = payload.get("kwargs", {})

    if not isinstance(args, (list, tuple)):
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="Invalid payload for SOLVE_FORCE_GREATS_FINDER (expected args list/tuple)",
        )
    if not isinstance(kwargs, dict):
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="Invalid payload for SOLVE_FORCE_GREATS_FINDER (expected kwargs dict)",
        )

    # Executor-managed dependencies are consumed here and must not be forwarded.
    ensure_timeline_precompute = bool(kwargs.pop("ensure_timeline_precompute", False))
    calc_song = kwargs.pop("calc_song", None)
    if kwargs.pop("ga_stage_coords", None) is not None:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="SOLVE_FORCE_GREATS_FINDER GA->FG resident genome-stat staging has been removed",
        )
    kwargs.pop("ga_stage_table_slot", None)
    kwargs.pop("ga_stage_n_slots", None)

    if ensure_timeline_precompute:
        ref_arrays0 = kwargs.get("ref_arrays")
        try:
            song_slot0 = int(kwargs.get("song_slot", 0) or 0)
        except (ValueError, TypeError):
            song_slot0 = 0
        if not isinstance(calc_song, dict) or not isinstance(ref_arrays0, dict):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="SOLVE_FORCE_GREATS_FINDER ensure_timeline_precompute requires calc_song/ref_arrays dicts",
            )
        try:
            precompute_timeline_fn(calc_song, ref_arrays0, song_slot=int(song_slot0))
        except Exception as e:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error=f"SOLVE_FORCE_GREATS_FINDER timeline precompute failed: {type(e).__name__}: {e}",
            )

    fg_tasks = kwargs.pop("fg_tasks", None)
    if fg_tasks is not None:
        if not isinstance(fg_tasks, (list, tuple)):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="Invalid payload for SOLVE_FORCE_GREATS_FINDER (fg_tasks must be list/tuple)",
            )

        reset_before = bool(kwargs.pop("fg_reset_before", False))
        download_after = bool(kwargs.pop("fg_download_after", False))
        try:
            task_count = int(len(fg_tasks))
        except (ValueError, TypeError, AttributeError):
            task_count = 0
        if record_tasks_batch_fn is not None:
            record_tasks_batch_fn(task_count)

        if len(args) != 7:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="Invalid payload for SOLVE_FORCE_GREATS_FINDER (expected 7 positional args)",
            )

        (
            genome_stats_list,
            timestamps_np,
            great_candidate_timestamps_np,
            long_notes,
            last_note_time,
            _fg_configs,
            _ftff_pairs,
        ) = args

        try:
            if genome_stats_list is None:
                n_genomes = int(kwargs.get("n_genomes_override", 0) or 0)
            else:
                n_genomes = int(len(genome_stats_list))
        except (ValueError, TypeError):
            n_genomes = 0
        if n_genomes <= 0:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="Invalid payload for SOLVE_FORCE_GREATS_FINDER (n_genomes <= 0)",
            )

        kwargs_local = dict(kwargs)
        download_topk = kwargs_local.pop("fg_download_topk", None)
        download_base_scores = kwargs_local.pop("fg_download_base_scores", None)
        download_keep_mask = kwargs_local.pop("fg_download_keep_mask", None)
        kwargs_local.pop("n_genomes_override", None)
        kwargs_local["accumulate_global"] = True
        kwargs_local["return_raw"] = True
        kwargs_local["upload_genome_stats"] = bool(kwargs_local.get("upload_genome_stats", True))
        try:
            fg_session_slot = int(kwargs_local.get("song_slot", 0) or 0)
        except (ValueError, TypeError):
            fg_session_slot = 0

        if reset_before:
            reset_global_best_fn(int(n_genomes), session_slot=int(fg_session_slot))

        if fg_tasks:
            tasks_fn(
                genome_stats_list,
                timestamps_np,
                great_candidate_timestamps_np,
                int(long_notes),
                float(last_note_time),
                fg_tasks=fg_tasks,
                **kwargs_local,
            )

        result = None
        if download_after:
            try:
                if download_topk is not None and download_base_scores is not None:
                    result = download_global_best_fn(
                        int(n_genomes),
                        session_slot=int(fg_session_slot),
                        topk=int(download_topk),
                        base_scores=download_base_scores,
                        keep_mask=download_keep_mask,
                    )
                else:
                    result = download_global_best_fn(int(n_genomes), session_slot=int(fg_session_slot))
            except Exception as e:
                logger.debug(f"gpu_executor:_execute_solve_force_greats_finder: {e}")
                result = download_global_best_fn(int(n_genomes), session_slot=int(fg_session_slot))

        return GpuResponse(request_id=request.request_id, success=True, result=result)

    ftff_chunks = kwargs.pop("ftff_chunks", None)
    if ftff_chunks is not None:
        if not isinstance(ftff_chunks, (list, tuple)):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="Invalid payload for SOLVE_FORCE_GREATS_FINDER (ftff_chunks must be list/tuple)",
            )
        base_args = list(args)
        if len(base_args) < 7:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="Invalid payload for SOLVE_FORCE_GREATS_FINDER (ftff_chunks requires >=7 args)",
            )
        result = None
        for chunk in ftff_chunks:
            base_args[6] = chunk
            result = solve_fn(*base_args, **kwargs)
    else:
        result = solve_fn(*args, **kwargs)
    return GpuResponse(
        request_id=request.request_id,
        success=True,
        result=result,
    )
