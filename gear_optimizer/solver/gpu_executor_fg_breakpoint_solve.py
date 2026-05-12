from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from gear_optimizer.core.parsing import env_flag, env_get
from gear_optimizer.solver.gpu_executor_fg_selection import fg_selection_upload_key
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse

logger = logging.getLogger(__name__)


def execute_fg_solve_with_breakpoints(
    request: GpuRequest,
    *,
    in_process_queues: bool,
    raise_if_abort_requested: Callable[[], None],
    run_payload_fn: Callable[..., Any],
) -> GpuResponse:
    """
    Fused FG path for in-process mode.

    The heavy payload solve remains owned by the executor; this wrapper only owns
    in-process gating, abort handling, and response shaping.
    """
    if not in_process_queues:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="FG_SOLVE_WITH_BREAKPOINTS requires in-process queues (avoid IPC pickling)",
        )

    try:
        raise_if_abort_requested()
        result = run_payload_fn(request.payload or {})
        return GpuResponse(request_id=request.request_id, success=True, result=result)
    except Exception as e:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error=f"FG_SOLVE_WITH_BREAKPOINTS: {type(e).__name__}: {e}",
        )


def execute_fg_solve_with_breakpoints_batch(
    request: GpuRequest,
    *,
    in_process_queues: bool,
    raise_if_abort_requested: Callable[[], None],
    run_payload_fn: Callable[..., Any],
    compute_max_fp_matrix_fn: Callable[..., Any],
    decode_cfg_counts_from_max_fp_matrix_fn: Callable[..., Any],
    decode_cfg_counts_from_windows_fn: Callable[..., Any],
    download_packed_topk_batch_fn: Callable[[int], list[Any]],
    download_batch_max_fn: Callable[[], int],
) -> GpuResponse:
    """
    Batch multiple `FG_SOLVE_WITH_BREAKPOINTS` payloads into a single executor request.

    This reduces request/lock overhead when the FG pipeline must split work into multiple
    genome batches (signature chunks) for the same song/group.
    """
    if not in_process_queues:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="FG_SOLVE_WITH_BREAKPOINTS_BATCH requires in-process queues (avoid IPC pickling)",
        )

    payload = request.payload or {}
    payloads = payload.get("payloads")
    if not isinstance(payloads, (list, tuple)):
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="FG_SOLVE_WITH_BREAKPOINTS_BATCH requires payloads: list[dict]",
        )

    try:
        raise_if_abort_requested()
    except Exception as e:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error=str(e),
        )

    debug_batch_pack = env_flag("FG_BREAKPOINTS_BATCH_PACK_DEBUG", "0")
    try:
        min_pack_payloads = int(env_get("FG_BREAKPOINTS_BATCH_PACK_MIN_PAYLOADS", "2") or "2")
    except (ValueError, TypeError):
        min_pack_payloads = 2
    min_pack_payloads = max(1, min(int(min_pack_payloads), 128))
    if debug_batch_pack:
        try:
            logger.debug("[FG][BatchPack] request payloads=%s", len(payloads))
        except Exception as e:
            logger.debug(f"gpu_executor:execute_fg_solve_with_breakpoints_batch: {e}")

    # Fast path: batch-pack top-K results into a staging field, then download once.
    try:
        want_batch_pack = bool(payloads) and int(len(payloads)) >= int(min_pack_payloads)
        if want_batch_pack:
            for p in payloads:
                if not isinstance(p, dict):
                    raise TypeError("FG_SOLVE_WITH_BREAKPOINTS_BATCH payload item must be dict")
                # Only support the reduced-download top-K mode (default for the fast path).
                if p.get("fg_download_topk") is None or p.get("fg_download_base_scores") is None:
                    want_batch_pack = False
                    break

        if want_batch_pack:
            import numpy as np

            try:
                max_batch = int(download_batch_max_fn() or 0)
            except Exception as e:
                logger.debug(f"gpu_executor:execute_fg_solve_with_breakpoints_batch: {e}")
                max_batch = 0
            if max_batch <= 0:
                max_batch = 1

            results: list[Any] = []
            # Hidden host-side bottleneck: when payloads share the same top-K selection
            # inputs (base_scores/keep_mask), repeatedly uploading them for every payload
            # adds avoidable transfer overhead and GPU idle gaps. Reuse uploads across
            # consecutive payloads in this batch when identity + shape context matches.
            last_selection_upload_key: tuple[Any, ...] | None = None
            selection_sig_cache: dict[tuple[Any, ...], tuple[Any, ...]] = {}
            for chunk_start in range(0, int(len(payloads)), int(max_batch)):
                raise_if_abort_requested()
                chunk = list(payloads[chunk_start : chunk_start + int(max_batch)])
                if not chunk:
                    continue

                decode_ctx: list[dict[str, Any]] = []
                for i, p in enumerate(chunk):
                    payload_for_run = p
                    try:
                        n_sel = 0
                        gs = p.get("genome_stats_list")
                        if gs is not None:
                            n_sel = int(len(gs))
                        else:
                            solve_kwargs_i = p.get("solve_kwargs") or {}
                            if isinstance(solve_kwargs_i, dict):
                                n_sel = int(solve_kwargs_i.get("n_genomes_override", 0) or 0)
                        selection_upload_key = fg_selection_upload_key(
                            p,
                            n_active=int(n_sel),
                            sig_cache=selection_sig_cache,
                        )
                        if last_selection_upload_key is not None and selection_upload_key == last_selection_upload_key:
                            payload_for_run = dict(p)
                            payload_for_run["fg_selection_inputs_preuploaded"] = True
                        else:
                            last_selection_upload_key = selection_upload_key
                    except (ValueError, TypeError, AttributeError, KeyError):
                        payload_for_run = p

                    ctx = run_payload_fn(payload_for_run, batch_pack_idx=int(i))
                    if not isinstance(ctx, dict) or not ctx.get("_packed_batch"):
                        raise RuntimeError("FG batch-pack expected packed ctx dict")
                    decode_ctx.append(ctx)

                chunk_results = download_packed_topk_batch_fn(int(len(chunk)))

                # Ensure cfg_counts present (defensive; most paths include it in the packed payload).
                for ctx, result in zip(decode_ctx, chunk_results):
                    if not isinstance(result, dict):
                        results.append(result)
                        continue
                    cfg_counts = result.get("cfg_counts")
                    if cfg_counts is None:
                        # Match single-payload behavior for callers without cfg_counts.
                        n_sections = int(ctx.get("n_sections", 0) or 0)
                        implicit_cfgs = bool(ctx.get("implicit_cfgs", False))
                        cfg_windows = ctx.get("cfg_windows")
                        if implicit_cfgs:
                            try:
                                result_ft = np.asarray(result.get("FT"), dtype=np.int32)
                                result_ff = np.asarray(result.get("FF"), dtype=np.int32)
                                if (
                                    result_ft.ndim == 1
                                    and result_ff.ndim == 1
                                    and int(result_ft.shape[0]) == int(result_ff.shape[0])
                                ):
                                    max_fp_rows = compute_max_fp_matrix_fn(
                                        pair_ft=result_ft,
                                        pair_ff=result_ff,
                                        base_ft=np.asarray(ctx.get("base_ft"), dtype=np.int32),
                                        base_ff=np.asarray(ctx.get("base_ff"), dtype=np.int32),
                                        n_sections=int(n_sections),
                                        song_slot=int(ctx.get("song_slot", 0) or 0),
                                        gem_scale_fever=int(ctx.get("gem_scale_fever", 0) or 0),
                                        non_fever_base_by_ff=ctx.get("non_fever_base_by_ff"),
                                        fp_cap_table=ctx.get("fp_cap_table"),
                                    )
                                    result_pairs = np.stack([result_ft, result_ff], axis=1)
                                    cfg_counts = decode_cfg_counts_from_max_fp_matrix_fn(
                                        result.get("cfg_idx"),
                                        result_ft,
                                        result_ff,
                                        max_fp_rows,
                                        result_pairs,
                                        int(n_sections),
                                    )
                            except (ValueError, TypeError):
                                cfg_counts = None
                        elif cfg_windows:
                            try:
                                cfg_counts = decode_cfg_counts_from_windows_fn(
                                    result.get("cfg_idx"),
                                    cfg_windows,
                                    int(n_sections),
                                )
                            except Exception as e:
                                logger.debug(f"gpu_executor:execute_fg_solve_with_breakpoints_batch: {e}")
                                cfg_counts = None
                        if cfg_counts is not None:
                            result = dict(result)
                            result["cfg_counts"] = cfg_counts
                    results.append(result)

            return GpuResponse(request_id=request.request_id, success=True, result=results)
        elif debug_batch_pack:
            try:
                reason = f"payloads<{int(min_pack_payloads)}"
                if int(len(payloads)) >= int(min_pack_payloads):
                    reason = "unknown"
                    for idx, p in enumerate(payloads):
                        if not isinstance(p, dict):
                            reason = f"payload[{idx}] not dict"
                            break
                        if p.get("fg_download_topk") is None:
                            reason = f"payload[{idx}] fg_download_topk=None"
                            break
                        if p.get("fg_download_base_scores") is None:
                            reason = f"payload[{idx}] fg_download_base_scores=None"
                            break
                logger.debug("[FG][BatchPack] skipped: %s (payloads=%s)", reason, len(payloads))
            except Exception as e:
                logger.debug(f"gpu_executor:execute_fg_solve_with_breakpoints_batch: {e}")
    except Exception as exc:
        if debug_batch_pack:
            try:
                import traceback

                logger.debug("[FG][BatchPack] disabled: %s: %s", type(exc).__name__, exc)
                logger.debug("%s", traceback.format_exc())
            except Exception as e:
                logger.debug(f"gpu_executor:execute_fg_solve_with_breakpoints_batch: {e}")
        # Fall through to per-payload download path.
        pass

    results: list[Any] = []
    try:
        for p in payloads:
            raise_if_abort_requested()
            if not isinstance(p, dict):
                raise TypeError("FG_SOLVE_WITH_BREAKPOINTS_BATCH payload item must be dict")
            results.append(run_payload_fn(p))
    except Exception as e:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error=f"FG_SOLVE_WITH_BREAKPOINTS_BATCH: {type(e).__name__}: {e}",
        )
    return GpuResponse(request_id=request.request_id, success=True, result=results)
