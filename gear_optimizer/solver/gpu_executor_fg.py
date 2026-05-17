from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from typing import Any

from gear_optimizer.core.cfg_window_decode import decode_cfg_counts_from_windows
from gear_optimizer.solver.gpu_executor_fg_breakpoint_payload import (
    PreparedFgBreakpointPayloadInputs,
    PreparedFgBreakpointSolveSubmission,
)
from gear_optimizer.solver.gpu_executor_fg_breakpoint_tasks import FgBreakpointTaskPlan
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse

logger = logging.getLogger(__name__)


def execute_fg_select_signature_frontier_batch(
    request: GpuRequest,
    *,
    in_process_queues: bool,
    select_fn: Callable[[list[dict[str, Any]]], Any],
) -> GpuResponse:
    if not in_process_queues:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="FG_SELECT_SIGNATURE_FRONTIER_BATCH requires in-process queues (avoid IPC pickling)",
        )

    payload = request.payload or {}
    payloads = payload.get("payloads")
    if not isinstance(payloads, list):
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="FG_SELECT_SIGNATURE_FRONTIER_BATCH requires payload['payloads'] list",
        )

    result = select_fn(payloads)
    return GpuResponse(
        request_id=request.request_id,
        success=True,
        result=result,
    )


def _payload_dict(request: GpuRequest) -> dict[str, Any]:
    payload = getattr(request, "payload", None)
    return payload if isinstance(payload, dict) else {}


def _int_payload(payload: dict[str, Any], key: str) -> int:
    try:
        return int(payload.get(key, 0) or 0)
    except (ValueError, TypeError):
        return 0


def execute_fg_reset_global_best(
    request: GpuRequest,
    *,
    in_process_queues: bool,
    reset_fn: Callable[..., Any],
) -> GpuResponse:
    if not in_process_queues:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="FG_RESET_GLOBAL_BEST requires in-process queues (avoid IPC pickling)",
        )

    payload = _payload_dict(request)
    n_genomes = _int_payload(payload, "n_genomes")
    song_slot = _int_payload(payload, "song_slot")

    reset_fn(int(n_genomes), session_slot=int(song_slot))
    return GpuResponse(
        request_id=request.request_id,
        success=True,
        result=None,
    )


def execute_fg_download_global_best(
    request: GpuRequest,
    *,
    in_process_queues: bool,
    download_fn: Callable[..., Any],
) -> GpuResponse:
    if not in_process_queues:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="FG_DOWNLOAD_GLOBAL_BEST requires in-process queues (avoid IPC pickling)",
        )

    payload = _payload_dict(request)
    n_genomes = _int_payload(payload, "n_genomes")
    song_slot = _int_payload(payload, "song_slot")
    download_topk = payload.get("topk")
    download_base_scores = payload.get("base_scores")
    download_keep_mask = payload.get("keep_mask")
    if download_topk is not None and download_base_scores is not None:
        result = download_fn(
            int(n_genomes),
            session_slot=int(song_slot),
            topk=int(download_topk),
            base_scores=download_base_scores,
            keep_mask=download_keep_mask,
        )
    else:
        result = download_fn(int(n_genomes), session_slot=int(song_slot))
    return GpuResponse(
        request_id=request.request_id,
        success=True,
        result=result,
    )


def decode_cfg_counts_from_windows_for_gpu(cfg_idx: Any, cfg_windows: list[dict], n_sections: int) -> Any:
    return decode_cfg_counts_from_windows(cfg_idx, cfg_windows, n_sections)


def decode_cfg_counts_from_max_fp_matrix(
    cfg_idx: Any,
    ft_vals: Any,
    ff_vals: Any,
    max_fp_matrix: Any,
    ftff_pairs: Any,
    n_sections: int,
) -> Any:
    import numpy as np

    if cfg_idx is None or max_fp_matrix is None or ft_vals is None or ff_vals is None:
        return None
    try:
        n_sections_i = int(n_sections)
    except (ValueError, TypeError):
        return None
    if n_sections_i <= 0:
        return None

    try:
        cfg_idx_np = np.asarray(cfg_idx, dtype=np.int64)
        ft_np = np.asarray(ft_vals, dtype=np.int32)
        ff_np = np.asarray(ff_vals, dtype=np.int32)
    except Exception as e:
        logger.debug(f"gpu_executor_fg:decode_cfg_counts_from_max_fp_matrix: {e}")
        return None
    if cfg_idx_np.shape[0] != ft_np.shape[0] or cfg_idx_np.shape[0] != ff_np.shape[0]:
        return None

    try:
        pairs_arr = np.asarray(ftff_pairs, dtype=np.int32)
    except Exception as e:
        logger.debug(f"gpu_executor_fg:decode_cfg_counts_from_max_fp_matrix: {e}")
        return None
    if pairs_arr.ndim != 2 or int(pairs_arr.shape[1]) < 2:
        return None

    try:
        max_fp_arr = np.asarray(max_fp_matrix, dtype=np.int32)
    except Exception as e:
        logger.debug(f"gpu_executor_fg:decode_cfg_counts_from_max_fp_matrix: {e}")
        return None
    if max_fp_arr.ndim != 2 or int(max_fp_arr.shape[0]) != int(pairs_arr.shape[0]):
        return None

    try:
        pair_index: dict[tuple[int, int], int] = {}
        for i in range(int(pairs_arr.shape[0])):
            ft_i = int(pairs_arr[i, 0])
            ff_i = int(pairs_arr[i, 1])
            pair_index[(ft_i, ff_i)] = int(i)
    except (ValueError, TypeError, KeyError, AttributeError):
        return None

    n_out = int(cfg_idx_np.shape[0])
    cfg_counts = np.zeros((int(n_out), int(n_sections_i)), dtype=np.int32)
    for gi in range(int(n_out)):
        row = pair_index.get((int(ft_np[gi]), int(ff_np[gi])), -1)
        if row < 0:
            continue
        idx = int(cfg_idx_np[gi])
        if idx < 0:
            continue
        try:
            max_fp_row = max_fp_arr[row]
        except Exception as e:
            logger.debug(f"gpu_executor_fg:decode_cfg_counts_from_max_fp_matrix: {e}")
            continue
        for s in range(int(n_sections_i) - 1, -1, -1):
            try:
                basev = int(max(0, int(max_fp_row[s] if s < len(max_fp_row) else 0))) + 1
            except (ValueError, TypeError, IndexError):
                basev = 1
            if basev <= 0:
                basev = 1
            val = idx % basev
            idx //= basev
            cfg_counts[gi, s] = int(val)
    return cfg_counts


def fg_selection_array_sig(
    arr: Any,
    *,
    n_active: int,
    sig_cache: dict[tuple[Any, ...], tuple[Any, ...]] | None = None,
) -> tuple[Any, ...]:
    try:
        import numpy as np

        a = np.asarray(arr, dtype=np.int32)
    except (ValueError, TypeError):
        return ("obj", id(arr))

    if a.ndim == 0:
        try:
            return ("scalar", int(a))
        except (ValueError, TypeError):
            return ("scalar", repr(a))

    if a.ndim != 1:
        try:
            a = np.ravel(a)
        except (ValueError, TypeError):
            return ("obj", id(arr))

    try:
        n_total = int(a.shape[0])
    except (ValueError, TypeError, AttributeError):
        return ("obj", id(arr))

    n = max(0, min(int(n_active), int(n_total)))
    if n <= 0:
        return ("empty", int(n_total))

    view = a[:n]
    try:
        ptr = int(view.__array_interface__["data"][0])
    except (ValueError, TypeError, KeyError, AttributeError):
        ptr = int(id(view))
    try:
        strides = tuple(int(x) for x in (view.strides or ()))
    except (ValueError, TypeError, AttributeError):
        strides = ()
    cache_key = (int(id(a)), int(ptr), int(n), strides, str(view.dtype))

    if sig_cache is not None:
        cached = sig_cache.get(cache_key)
        if cached is not None:
            return cached

    if not view.flags["C_CONTIGUOUS"]:
        view = np.ascontiguousarray(view, dtype=np.int32)

    h = hashlib.blake2b(digest_size=12)
    h.update(memoryview(view).cast("B"))
    sig = ("arr", int(n), h.digest())

    if sig_cache is not None:
        sig_cache[cache_key] = sig
    return sig


def fg_selection_upload_key(
    payload: dict[str, Any],
    *,
    n_active: int,
    sig_cache: dict[tuple[Any, ...], tuple[Any, ...]] | None = None,
) -> tuple[Any, ...]:
    topk = int(payload.get("fg_download_topk", 0) or 0)
    base_scores = payload.get("fg_download_base_scores")
    keep_mask = payload.get("fg_download_keep_mask")
    keep_sig = (
        ("none", int(n_active))
        if keep_mask is None
        else fg_selection_array_sig(keep_mask, n_active=int(n_active), sig_cache=sig_cache)
    )
    return (
        int(n_active),
        int(topk),
        fg_selection_array_sig(base_scores, n_active=int(n_active), sig_cache=sig_cache),
        keep_sig,
    )


def pack_or_download_fg_breakpoint_result(
    payload: dict[str, Any],
    *,
    prepared: PreparedFgBreakpointPayloadInputs,
    task_plan: FgBreakpointTaskPlan,
    submission: PreparedFgBreakpointSolveSubmission,
    batch_pack_idx: int | None,
    pack_topk_fn: Callable[..., Any],
    download_global_best_fn: Callable[..., Any],
) -> Any:
    download_topk = payload.get("fg_download_topk", None)
    download_base_scores = payload.get("fg_download_base_scores", None)
    download_keep_mask = payload.get("fg_download_keep_mask", None)
    if batch_pack_idx is not None and download_topk is not None and download_base_scores is not None:
        skip_selection_upload = bool(payload.get("fg_selection_inputs_preuploaded", False))
        pack_topk_fn(
            int(submission.n_genomes),
            session_slot=int(prepared.song_slot),
            topk=int(download_topk),
            base_scores=download_base_scores,
            keep_mask=download_keep_mask,
            batch_idx=int(batch_pack_idx),
            upload_selection_inputs=not bool(skip_selection_upload),
        )
        return {
            "_packed_batch": True,
            "implicit_cfgs": bool(prepared.implicit_cfgs),
            "cfg_windows": task_plan.cfg_windows,
            "n_sections": int(prepared.n_sections),
            "song_slot": int(prepared.song_slot),
            "gem_scale_fever": int(prepared.gem_scale_fever),
            "base_ft": prepared.base_ft,
            "base_ff": prepared.base_ff,
            "non_fever_base_by_ff": prepared.non_fever_base_by_ff,
            "fp_cap_table": prepared.fp_cap_table,
            "surface_pair_drops": int(task_plan.surface_pair_drops),
            "surface_pair_reduce_ms": int(round(float(task_plan.surface_pair_reduce_sec) * 1000.0)),
        }

    if download_topk is not None and download_base_scores is not None:
        return download_global_best_fn(
            int(submission.n_genomes),
            session_slot=int(prepared.song_slot),
            topk=int(download_topk),
            base_scores=download_base_scores,
            keep_mask=download_keep_mask,
        )
    return download_global_best_fn(int(submission.n_genomes), session_slot=int(prepared.song_slot))


def finalize_fg_breakpoint_result(
    result: Any,
    *,
    implicit_cfgs: bool,
    cfg_windows: list[dict] | None,
    n_sections: int,
    song_slot: int,
    gem_scale_fever: int,
    base_ft: Any,
    base_ff: Any,
    non_fever_base_by_ff: Any,
    fp_cap_table: Any,
    fused_surface_pair_drops: int,
    fused_surface_pair_reduce_sec: float,
    compute_max_fp_matrix_fn: Callable[..., Any],
    decode_cfg_counts_from_max_fp_matrix_fn: Callable[..., Any],
    decode_cfg_counts_from_windows_fn: Callable[..., Any],
) -> Any:
    if not isinstance(result, dict):
        return result

    import numpy as np

    cfg_counts = result.get("cfg_counts")
    if cfg_counts is None:
        if implicit_cfgs:
            try:
                result_ft = np.asarray(result.get("FT"), dtype=np.int32)
                result_ff = np.asarray(result.get("FF"), dtype=np.int32)
                if result_ft.ndim == 1 and result_ff.ndim == 1 and int(result_ft.shape[0]) == int(
                    result_ff.shape[0]
                ):
                    max_fp_rows = compute_max_fp_matrix_fn(
                        pair_ft=result_ft,
                        pair_ff=result_ff,
                        base_ft=base_ft,
                        base_ff=base_ff,
                        n_sections=int(n_sections),
                        song_slot=int(song_slot),
                        gem_scale_fever=int(gem_scale_fever),
                        non_fever_base_by_ff=non_fever_base_by_ff,
                        fp_cap_table=fp_cap_table,
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
            except (ValueError, TypeError, KeyError):
                cfg_counts = None
        elif cfg_windows:
            cfg_counts = decode_cfg_counts_from_windows_fn(result.get("cfg_idx"), cfg_windows, int(n_sections))
    if cfg_counts is not None and result.get("cfg_counts") is None:
        result = dict(result)
        result["cfg_counts"] = cfg_counts
    if fused_surface_pair_drops > 0:
        result = dict(result)
        result["surface_pair_drops"] = int(fused_surface_pair_drops)
        result["surface_pair_reduce_ms"] = int(round(float(fused_surface_pair_reduce_sec) * 1000.0))
    return result
