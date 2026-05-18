from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from typing import Any

from gear_optimizer.core.cfg_window_decode import decode_cfg_counts_from_windows
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

# ---- merged from gpu_executor_fg_breakpoint_payload.py ----
import os
import logging
from dataclasses import dataclass

from gear_optimizer.core.parsing import TRUTHY_ENV_VALUES

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedFgBreakpointPayloadInputs:
    n_sections: int
    pairs_arr: Any
    base_arr: Any
    base_ft: Any
    base_ff: Any
    non_fever_base_by_ff: Any
    fp_cap_table: Any
    song_slot: int
    gem_scale_fever: int
    solve_kwargs_payload: dict[str, Any]
    implicit_cfgs: bool


@dataclass(frozen=True)
class PreparedFgBreakpointSolveSubmission:
    genome_stats_list: Any
    timestamps_np: Any
    great_candidate_timestamps_np: Any
    long_notes: int
    last_note_time: float
    kwargs_local: dict[str, Any]
    n_genomes: int


def prepare_fg_breakpoint_payload_inputs(
    payload: dict[str, Any],
    *,
    env_get: Callable[[str, str], str | None] = os.environ.get,
) -> PreparedFgBreakpointPayloadInputs | None:
    import numpy as np

    try:
        n_sections = int(payload.get("n_sections", 0) or 0)
    except (ValueError, TypeError):
        n_sections = 0
    if n_sections <= 0:
        return None

    ftff_pairs = payload.get("ftff_pairs")
    base_stats_pairs = payload.get("base_stats_pairs")
    non_fever_base_by_ff = payload.get("non_fever_base_by_ff")
    fp_cap_table = payload.get("fp_cap_table")
    song_slot = int(payload.get("song_slot", 0) or 0)
    gem_scale_fever = int(payload.get("gem_scale_fever", 3) or 3)

    if ftff_pairs is None or base_stats_pairs is None or non_fever_base_by_ff is None or fp_cap_table is None:
        raise ValueError("FG_SOLVE_WITH_BREAKPOINTS missing required breakpoint inputs")

    try:
        pairs_arr = np.asarray(ftff_pairs, dtype=np.int32)
        base_arr = np.asarray(base_stats_pairs, dtype=np.int32)
        if pairs_arr.ndim != 2 or int(pairs_arr.shape[1]) < 2:
            raise ValueError("ftff_pairs must be shape (n,2)")
        if base_arr.ndim != 2 or int(base_arr.shape[1]) < 2:
            raise ValueError("base_stats_pairs must be shape (n,2)")
    except (ValueError, TypeError) as e:
        raise ValueError(str(e)) from e

    if int(pairs_arr.shape[0]) <= 0:
        return None

    try:
        pairs_arr = np.ascontiguousarray(pairs_arr, dtype=np.int32)
        base_arr = np.ascontiguousarray(base_arr, dtype=np.int32)
        base_ft = np.ascontiguousarray(base_arr[:, 0], dtype=np.int32)
        base_ff = np.ascontiguousarray(base_arr[:, 1], dtype=np.int32)
    except Exception as e:
        raise RuntimeError(f"breakpoint inputs invalid: {type(e).__name__}: {e}") from e

    solve_kwargs_payload = dict(payload.get("solve_kwargs") or {})
    implicit_cfgs = str(env_get("FG_IMPLICIT_CONFIGS", "1") or "").strip().lower() in (TRUTHY_ENV_VALUES | {""})

    return PreparedFgBreakpointPayloadInputs(
        n_sections=int(n_sections),
        pairs_arr=pairs_arr,
        base_arr=base_arr,
        base_ft=base_ft,
        base_ff=base_ff,
        non_fever_base_by_ff=non_fever_base_by_ff,
        fp_cap_table=fp_cap_table,
        song_slot=int(song_slot),
        gem_scale_fever=int(gem_scale_fever),
        solve_kwargs_payload=solve_kwargs_payload,
        implicit_cfgs=bool(implicit_cfgs),
    )


def maybe_precompute_fg_breakpoint_timeline(
    payload: dict[str, Any],
    *,
    precompute_timeline_fn: Callable[..., Any],
) -> None:
    # Optional: precompute the timeline grid in this same executor request to avoid
    # an extra executor request boundary between GA and FG solve steps.
    #
    # This is safe: `precompute_timeline_gpu` is cached per (song_slot, song_key).
    ensure_timeline = bool(payload.get("ensure_timeline_precompute", False))
    if not ensure_timeline:
        return
    try:
        calc_song = payload.get("calc_song")
        solve_kwargs0 = payload.get("solve_kwargs") or {}
        ref_arrays0 = solve_kwargs0.get("ref_arrays")
        if isinstance(calc_song, dict) and isinstance(ref_arrays0, dict):
            precompute_timeline_fn(calc_song, ref_arrays0, song_slot=int(payload.get("song_slot", 0) or 0))
    except Exception as e:
        # Keep fused FG robust; caps can still come from an explicit grid upload.
        logger.debug(f"gpu_executor:maybe_precompute_fg_breakpoint_timeline: {e}")


def prepare_fg_breakpoint_solve_submission(
    payload: dict[str, Any],
    solve_kwargs_payload: dict[str, Any],
) -> PreparedFgBreakpointSolveSubmission:
    genome_stats_list = payload.get("genome_stats_list")
    timestamps_np = payload.get("timestamps_np")
    great_candidate_timestamps_np = payload.get("great_candidate_timestamps_np")
    long_notes = int(payload.get("long_notes", 0) or 0)
    last_note_time = float(payload.get("last_note_time", 0.0) or 0.0)

    kwargs_local = dict(solve_kwargs_payload)
    kwargs_local["accumulate_global"] = True
    kwargs_local["return_raw"] = True

    try:
        if genome_stats_list is None:
            n_genomes = int(kwargs_local.get("n_genomes_override", 0) or 0)
        else:
            n_genomes = int(len(genome_stats_list))
    except (ValueError, TypeError):
        n_genomes = 0
    if n_genomes <= 0:
        raise ValueError("FG_SOLVE_WITH_BREAKPOINTS n_genomes <= 0")

    if payload.get("ga_stage_coords") is not None or bool(kwargs_local.get("genome_stats_preuploaded")):
        raise ValueError("FG resident genome-stat preupload/staging has been removed")

    kwargs_local.pop("n_genomes_override", None)

    return PreparedFgBreakpointSolveSubmission(
        genome_stats_list=genome_stats_list,
        timestamps_np=timestamps_np,
        great_candidate_timestamps_np=great_candidate_timestamps_np,
        long_notes=int(long_notes),
        last_note_time=float(last_note_time),
        kwargs_local=kwargs_local,
        n_genomes=int(n_genomes),
    )

# ---- merged from gpu_executor_fg_breakpoint_solve.py ----
from gear_optimizer.core.parsing import env_flag, env_get


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


def run_fg_solve_with_breakpoints_payload(
    payload: dict[str, Any],
    *,
    batch_pack_idx: int | None = None,
    raise_if_abort_requested: Callable[[], None],
    env_get_fn: Callable[..., Any],
    precompute_timeline_fn: Callable[..., Any],
    compute_max_fp_matrix_fn: Callable[..., Any],
    solve_force_greats_finder_gpu_tasks_fn: Callable[..., Any],
    reset_global_best_fn: Callable[..., Any],
    download_global_best_fn: Callable[..., Any],
    pack_global_best_topk_to_batch_fn: Callable[..., Any],
    decode_cfg_counts_from_max_fp_matrix_fn: Callable[..., Any],
    decode_cfg_counts_from_windows_fn: Callable[..., Any],
) -> Any:
    raise_if_abort_requested()

    prepared = prepare_fg_breakpoint_payload_inputs(payload, env_get=env_get_fn)
    if prepared is None:
        return None

    maybe_precompute_fg_breakpoint_timeline(payload, precompute_timeline_fn=precompute_timeline_fn)

    n_sections = prepared.n_sections
    base_ft = prepared.base_ft
    base_ff = prepared.base_ff
    non_fever_base_by_ff = prepared.non_fever_base_by_ff
    fp_cap_table = prepared.fp_cap_table
    song_slot = prepared.song_slot
    gem_scale_fever = prepared.gem_scale_fever
    solve_kwargs_payload = prepared.solve_kwargs_payload
    implicit_cfgs = prepared.implicit_cfgs

    task_plan = build_fg_breakpoint_tasks(
        prepared,
        compute_max_fp_matrix_fn=compute_max_fp_matrix_fn,
    )
    fg_tasks = task_plan.fg_tasks
    cfg_windows = task_plan.cfg_windows
    fused_surface_pair_drops = int(task_plan.surface_pair_drops)
    fused_surface_pair_reduce_sec = float(task_plan.surface_pair_reduce_sec)

    if not fg_tasks:
        return None

    submission = prepare_fg_breakpoint_solve_submission(payload, solve_kwargs_payload)

    if bool(payload.get("fg_reset_before", True)):
        reset_global_best_fn(int(submission.n_genomes), session_slot=int(song_slot))

    solve_force_greats_finder_gpu_tasks_fn(
        submission.genome_stats_list,
        submission.timestamps_np,
        submission.great_candidate_timestamps_np,
        int(submission.long_notes),
        float(submission.last_note_time),
        fg_tasks=fg_tasks,
        **submission.kwargs_local,
    )

    result = pack_or_download_fg_breakpoint_result(
        payload,
        prepared=prepared,
        task_plan=task_plan,
        submission=submission,
        batch_pack_idx=batch_pack_idx,
        pack_topk_fn=pack_global_best_topk_to_batch_fn,
        download_global_best_fn=download_global_best_fn,
    )
    if isinstance(result, dict) and result.get("_packed_batch"):
        return result

    return finalize_fg_breakpoint_result(
        result,
        implicit_cfgs=bool(implicit_cfgs),
        cfg_windows=cfg_windows,
        n_sections=int(n_sections),
        song_slot=int(song_slot),
        gem_scale_fever=int(gem_scale_fever),
        base_ft=base_ft,
        base_ff=base_ff,
        non_fever_base_by_ff=non_fever_base_by_ff,
        fp_cap_table=fp_cap_table,
        fused_surface_pair_drops=int(fused_surface_pair_drops),
        fused_surface_pair_reduce_sec=float(fused_surface_pair_reduce_sec),
        compute_max_fp_matrix_fn=compute_max_fp_matrix_fn,
        decode_cfg_counts_from_max_fp_matrix_fn=decode_cfg_counts_from_max_fp_matrix_fn,
        decode_cfg_counts_from_windows_fn=decode_cfg_counts_from_windows_fn,
    )

# ---- merged from gpu_executor_fg_breakpoint_tasks.py ----
import logging
from dataclasses import dataclass
from time import perf_counter

from gear_optimizer.core.parsing import env_int


@dataclass(frozen=True)
class FgBreakpointTaskPlan:
    fg_tasks: list[dict[str, Any]]
    cfg_windows: list[dict] | None
    surface_pair_drops: int
    surface_pair_reduce_sec: float


def build_fg_breakpoint_tasks(
    prepared: PreparedFgBreakpointPayloadInputs,
    *,
    compute_max_fp_matrix_fn: Callable[..., Any],
    env_flag_fn: Callable[[str, str], bool] = env_flag,
    env_int_fn: Callable[[str, int], int] = env_int,
    perf_counter_fn: Callable[[], float] = perf_counter,
    fg_max_ftff_fn: Callable[[], int] | None = None,
) -> FgBreakpointTaskPlan:
    import numpy as np

    n_sections = prepared.n_sections
    pairs_arr = prepared.pairs_arr
    base_arr = prepared.base_arr
    base_ft = prepared.base_ft
    base_ff = prepared.base_ff
    non_fever_base_by_ff = prepared.non_fever_base_by_ff
    fp_cap_table = prepared.fp_cap_table
    song_slot = prepared.song_slot
    gem_scale_fever = prepared.gem_scale_fever
    solve_kwargs_payload = prepared.solve_kwargs_payload

    fg_tasks: list[dict[str, Any]] = []
    cfg_windows: list[dict] | None = None
    fused_surface_pair_drops = 0
    fused_surface_pair_reduce_sec = 0.0

    # Default ON: keeping per-pair max-FP computation on-GPU avoids an expensive
    # host download+re-upload cycle that often appears as unexplained idle time.
    use_gpu_max_fp_compute = env_flag_fn("FG_MAX_FP_GPU_COMPUTE", "1")
    if prepared.implicit_cfgs:
        if use_gpu_max_fp_compute:
            max_fp_matrix_for_task = None
            if env_flag_fn("FG_FUSED_SURFACE_PAIR_REDUCTION", "1"):
                pair_reduce_min_pairs = max(1, env_int_fn("FG_FUSED_SURFACE_PAIR_REDUCTION_MIN_PAIRS", 1025))
                if int(pairs_arr.shape[0]) >= int(pair_reduce_min_pairs):
                    _t_surface = perf_counter_fn()
                    try:
                        pair_ft = np.ascontiguousarray(pairs_arr[:, 0], dtype=np.int32)
                        pair_ff = np.ascontiguousarray(pairs_arr[:, 1], dtype=np.int32)
                        max_fp_matrix = compute_max_fp_matrix_fn(
                            pair_ft=pair_ft,
                            pair_ff=pair_ff,
                            base_ft=base_ft,
                            base_ff=base_ff,
                            n_sections=int(n_sections),
                            song_slot=int(song_slot),
                            gem_scale_fever=int(gem_scale_fever),
                            non_fever_base_by_ff=non_fever_base_by_ff,
                            fp_cap_table=fp_cap_table,
                        )
                        from gear_optimizer.helpers.song_helpers.force_greats.ftff_pairs import (
                            reduce_ftff_pairs_by_max_fp_surface,
                        )

                        surface_reduction = reduce_ftff_pairs_by_max_fp_surface(
                            pairs_arr,
                            max_fp_matrix,
                            n_sections=int(n_sections),
                            total_budget=int(solve_kwargs_payload.get("total_budget", 90) or 90),
                            is_p_ft=int(solve_kwargs_payload.get("is_p_ft", 0) or 0),
                            is_s_ft=int(solve_kwargs_payload.get("is_s_ft", 0) or 0),
                            is_p_ff=int(solve_kwargs_payload.get("is_p_ff", 0) or 0),
                            is_s_ff=int(solve_kwargs_payload.get("is_s_ff", 0) or 0),
                        )
                        fused_surface_pair_drops = max(0, int(surface_reduction.dropped))
                        if fused_surface_pair_drops > 0:
                            pairs_arr = np.ascontiguousarray(surface_reduction.pairs, dtype=np.int32)
                            max_fp_matrix_for_task = np.ascontiguousarray(
                                surface_reduction.max_fp_matrix,
                                dtype=np.int16,
                            )
                        else:
                            max_fp_matrix_for_task = np.ascontiguousarray(max_fp_matrix, dtype=np.int16)
                    except Exception as e:
                        raise RuntimeError(f"fused surface pair reduction failed: {type(e).__name__}: {e}") from e
                    finally:
                        fused_surface_pair_reduce_sec = perf_counter_fn() - _t_surface

            if max_fp_matrix_for_task is None:
                # Per-pair max-FP caps (no CPU grouping). The packed-task solver can consume
                # per-pair max-FP caps computed on GPU and decode per-ftff configs on-GPU.
                counts_max_fp_task: Any = {
                    "mode": "gpu",
                    "base_stats_pairs": base_arr,
                    # Reuse pre-split base stat vectors; avoids repeated host slicing
                    # in downstream task preparation.
                    "base_ft": base_ft,
                    "base_ff": base_ff,
                    "non_fever_base_by_ff": non_fever_base_by_ff,
                    "fp_cap_table": fp_cap_table,
                    "n_sections": int(n_sections),
                    "song_slot": int(song_slot),
                    "gem_scale_fever": int(gem_scale_fever),
                }
            else:
                counts_max_fp_task = max_fp_matrix_for_task

            fg_tasks.append(
                {
                    "counts_list": None,
                    "counts_max_fp": counts_max_fp_task,
                    "ftff_pairs": pairs_arr,
                    "base_cfg_offset": 0,
                }
            )
        else:
            # Per-pair max-FP caps with full matrix download (avoid CPU grouping).
            try:
                pair_ft = np.ascontiguousarray(pairs_arr[:, 0], dtype=np.int32)
                pair_ff = np.ascontiguousarray(pairs_arr[:, 1], dtype=np.int32)
                max_fp_matrix = compute_max_fp_matrix_fn(
                    pair_ft=pair_ft,
                    pair_ff=pair_ff,
                    base_ft=base_ft,
                    base_ff=base_ff,
                    n_sections=int(n_sections),
                    song_slot=int(song_slot),
                    gem_scale_fever=int(gem_scale_fever),
                    non_fever_base_by_ff=non_fever_base_by_ff,
                    fp_cap_table=fp_cap_table,
                )
            except Exception as e:
                raise RuntimeError(f"per-pair max-FP compute failed: {type(e).__name__}: {e}") from e
            fg_tasks.append(
                {
                    "counts_list": None,
                    "counts_max_fp": max_fp_matrix,
                    "ftff_pairs": pairs_arr,
                    "base_cfg_offset": 0,
                }
            )
    else:
        # Fallback: group identical max-FP rows on CPU (explicit grouping path).
        try:
            pair_ft = np.ascontiguousarray(pairs_arr[:, 0], dtype=np.int32)
            pair_ff = np.ascontiguousarray(pairs_arr[:, 1], dtype=np.int32)
            max_fp_matrix = compute_max_fp_matrix_fn(
                pair_ft=pair_ft,
                pair_ff=pair_ff,
                base_ft=base_ft,
                base_ff=base_ff,
                n_sections=int(n_sections),
                song_slot=int(song_slot),
                gem_scale_fever=int(gem_scale_fever),
                non_fever_base_by_ff=non_fever_base_by_ff,
                fp_cap_table=fp_cap_table,
            )
            rows = np.ascontiguousarray(max_fp_matrix[:, : int(n_sections)], dtype=np.int16)
            uniq, inv = np.unique(rows, axis=0, return_inverse=True)
        except Exception as e:
            raise RuntimeError(f"grouping failed: {type(e).__name__}: {e}") from e

        cfg_windows = []
        cfg_next_base = 0

        chunk_size = int(fg_max_ftff_fn() if fg_max_ftff_fn is not None else _fg_max_ftff())
        if chunk_size <= 0:
            chunk_size = 1024

        for i_group in range(int(uniq.shape[0])):
            mask = inv == int(i_group)
            if not np.any(mask):
                continue
            group_pairs = pairs_arr[mask]
            try:
                max_fp_norm = [max(0, int(v)) for v in uniq[int(i_group)].tolist()[: int(n_sections)]]
            except (ValueError, TypeError):
                max_fp_norm = [0] * int(n_sections)
            if not max_fp_norm:
                max_fp_norm = [0] * int(n_sections)

            cfg_len = 1
            for v in max_fp_norm[: int(n_sections)]:
                cfg_len *= int(v) + 1
            cfg_len = max(1, int(cfg_len))

            group_cfg_offset = int(cfg_next_base)
            cfg_windows.append(
                {
                    "base": int(group_cfg_offset),
                    "len": int(cfg_len),
                    "kind": "max_fp",
                    "max_fp": list(max_fp_norm),
                    "n_sections": int(n_sections),
                }
            )
            cfg_next_base = int(group_cfg_offset) + int(cfg_len)

            for j in range(0, int(group_pairs.shape[0]), int(chunk_size)):
                chunk = group_pairs[j : j + int(chunk_size)]
                if int(chunk.shape[0]) <= 0:
                    continue
                fg_tasks.append(
                    {
                        "counts_list": None,
                        "counts_max_fp": list(max_fp_norm),
                        "ftff_pairs": np.asarray(chunk, dtype=np.int32),
                        "base_cfg_offset": int(group_cfg_offset),
                    }
                )

    return FgBreakpointTaskPlan(
        fg_tasks=fg_tasks,
        cfg_windows=cfg_windows,
        surface_pair_drops=int(fused_surface_pair_drops),
        surface_pair_reduce_sec=float(fused_surface_pair_reduce_sec),
    )


def _fg_max_ftff() -> int:
    try:
        from .taichi_gem.force_greats import fg_fields

        return int(getattr(fg_fields, "FG_MAX_FTFF", 0) or 0)
    except Exception as e:
        logger.debug(f"gpu_executor:build_fg_breakpoint_tasks: {e}")
        return 0

# ---- merged from gpu_executor_fg_breakpoints.py ----


def execute_fg_compute_breakpoints(
    request: GpuRequest,
    *,
    precompute_timeline_fn: Callable[..., Any],
    compute_matrix_fn: Callable[..., Any],
) -> GpuResponse:
    """
    Compute per-FT/FF breakpoint ranges for ForceGreatsFinder on the GPU-owner thread.

    Returns an (n_pairs, n_sections) int16 array of max fill-penalty caps (FP caps).
    Callers can convert this to `section_breakpoints` by using `range(0, fp + 1)` per section.
    """
    import numpy as np

    payload = request.payload or {}

    ensure_timeline_precompute = bool(payload.get("ensure_timeline_precompute", False))
    if ensure_timeline_precompute:
        calc_song = payload.get("calc_song")
        ref_arrays = payload.get("ref_arrays")
        song_slot0 = int(payload.get("song_slot", 0) or 0)
        if not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_COMPUTE_BREAKPOINTS ensure_timeline_precompute requires calc_song/ref_arrays dicts",
            )
        try:
            precompute_timeline_fn(calc_song, ref_arrays, song_slot=int(song_slot0))
        except Exception as e:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error=f"FG_COMPUTE_BREAKPOINTS timeline precompute failed: {type(e).__name__}: {e}",
            )

    # NOTE: `ftff_pairs`/`base_stats_pairs` may be numpy arrays; never use `or []` which
    # triggers `ValueError: The truth value of an array with more than one element...`.
    ftff_pairs = payload.get("ftff_pairs", None)
    if ftff_pairs is None:
        ftff_pairs = []
    base_stats_pairs = payload.get("base_stats_pairs", None)
    if base_stats_pairs is None:
        base_stats_pairs = []
    n_sections = int(payload.get("n_sections", 0) or 0)
    song_slot = int(payload.get("song_slot", 0) or 0)
    gem_scale_fever = int(payload.get("gem_scale_fever", 3) or 3)

    # Optional precomputed tables (recommended; avoids repeated ceil math).
    non_fever_base_by_ff = payload.get("non_fever_base_by_ff")
    fp_cap_table = payload.get("fp_cap_table")

    if n_sections <= 0:
        return GpuResponse(request_id=request.request_id, success=True, result=np.zeros((0, 0), dtype=np.int16))

    # Accept either Python sequences of (ft, ff) tuples or packed (n,2) int arrays.
    pairs_arr = None
    base_arr = None
    try:
        if isinstance(ftff_pairs, np.ndarray):
            pairs_arr = np.asarray(ftff_pairs, dtype=np.int32)
            if pairs_arr.ndim != 2 or int(pairs_arr.shape[1]) < 2:
                pairs_arr = None
        if isinstance(base_stats_pairs, np.ndarray):
            base_arr = np.asarray(base_stats_pairs, dtype=np.int32)
            if base_arr.ndim != 2 or int(base_arr.shape[1]) < 2:
                base_arr = None
    except Exception as e:
        logger.debug(f"gpu_executor:execute_fg_compute_breakpoints: {e}")
        pairs_arr = None
        base_arr = None

    if pairs_arr is not None and int(pairs_arr.shape[0]) <= 0:
        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=np.zeros((0, int(n_sections)), dtype=np.int16),
        )
    if pairs_arr is not None and (base_arr is not None and int(base_arr.shape[0]) <= 0):
        # No base FT/FF stats to consider -> max FP is 0 everywhere.
        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=np.zeros((int(pairs_arr.shape[0]), int(n_sections)), dtype=np.int16),
        )

    if pairs_arr is None:
        try:
            pairs_list = list(ftff_pairs)
        except Exception as e:
            logger.debug(f"gpu_executor:execute_fg_compute_breakpoints: {e}")
            pairs_list = []
        if not pairs_list:
            return GpuResponse(
                request_id=request.request_id,
                success=True,
                result=np.zeros((0, int(n_sections)), dtype=np.int16),
            )
    else:
        pairs_list = None

    if base_arr is None:
        try:
            base_list = list(base_stats_pairs)
        except Exception as e:
            logger.debug(f"gpu_executor:execute_fg_compute_breakpoints: {e}")
            base_list = []
        if not base_list:
            # No base FT/FF stats to consider -> max FP is 0 everywhere.
            n_pairs = int(pairs_arr.shape[0]) if pairs_arr is not None else int(len(pairs_list))
            return GpuResponse(
                request_id=request.request_id,
                success=True,
                result=np.zeros((n_pairs, int(n_sections)), dtype=np.int16),
            )
    else:
        base_list = None

    # Build pair arrays.
    if pairs_arr is not None:
        try:
            pair_ft = np.ascontiguousarray(pairs_arr[:, 0], dtype=np.int32)
            pair_ff = np.ascontiguousarray(pairs_arr[:, 1], dtype=np.int32)
        except Exception as e:
            logger.debug(f"gpu_executor:execute_fg_compute_breakpoints: {e}")
            pair_ft = np.asarray([], dtype=np.int32)
            pair_ff = np.asarray([], dtype=np.int32)
    else:
        try:
            pair_ft = np.asarray([int(p[0]) for p in pairs_list], dtype=np.int32)
            pair_ff = np.asarray([int(p[1]) for p in pairs_list], dtype=np.int32)
        except (ValueError, TypeError):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_COMPUTE_BREAKPOINTS invalid ftff_pairs (expected list of (ft, ff))",
            )

    # Build base arrays.
    if base_arr is not None:
        try:
            base_ft = np.ascontiguousarray(base_arr[:, 0], dtype=np.int32)
            base_ff = np.ascontiguousarray(base_arr[:, 1], dtype=np.int32)
        except Exception as e:
            logger.debug(f"gpu_executor:execute_fg_compute_breakpoints: {e}")
            base_ft = np.asarray([], dtype=np.int32)
            base_ff = np.asarray([], dtype=np.int32)
    else:
        try:
            base_ft = np.asarray([int(p[0]) for p in base_list], dtype=np.int32)
            base_ff = np.asarray([int(p[1]) for p in base_list], dtype=np.int32)
        except (ValueError, TypeError):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_COMPUTE_BREAKPOINTS invalid base_stats_pairs (expected list of (ft_stat, ff_stat))",
            )

    # Validate tables.
    if non_fever_base_by_ff is None or fp_cap_table is None:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="FG_COMPUTE_BREAKPOINTS missing non_fever_base_by_ff/fp_cap_table",
        )

    non_fever_base_by_ff = np.asarray(non_fever_base_by_ff, dtype=np.int16)
    fp_cap_table = np.asarray(fp_cap_table, dtype=np.int16)
    if non_fever_base_by_ff.ndim != 1 or int(non_fever_base_by_ff.shape[0]) < 161:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="FG_COMPUTE_BREAKPOINTS non_fever_base_by_ff must be shape (>=161,)",
        )
    if fp_cap_table.ndim != 2 or fp_cap_table.shape[0] < 161 or fp_cap_table.shape[1] < 51:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="FG_COMPUTE_BREAKPOINTS fp_cap_table must be shape (>=161, >=51)",
        )

    try:
        out = compute_matrix_fn(
            pair_ft=pair_ft,
            pair_ff=pair_ff,
            base_ft=base_ft,
            base_ff=base_ff,
            n_sections=int(n_sections),
            song_slot=int(song_slot),
            gem_scale_fever=int(gem_scale_fever),
            non_fever_base_by_ff=non_fever_base_by_ff,
            fp_cap_table=fp_cap_table,
        )
    except Exception as e:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error=f"FG_COMPUTE_BREAKPOINTS kernel failed: {type(e).__name__}: {e}",
        )

    return GpuResponse(request_id=request.request_id, success=True, result=out)


def compute_fg_breakpoints_max_fp_matrix(
    *,
    pair_ft,
    pair_ff,
    base_ft,
    base_ff,
    n_sections: int,
    song_slot: int,
    gem_scale_fever: int,
    non_fever_base_by_ff,
    fp_cap_table,
):
    import numpy as np

    # Taichi ndarrays require contiguous host buffers.
    pair_ft = np.ascontiguousarray(pair_ft, dtype=np.int32)
    pair_ff = np.ascontiguousarray(pair_ff, dtype=np.int32)
    base_ft = np.ascontiguousarray(base_ft, dtype=np.int32)
    base_ff = np.ascontiguousarray(base_ff, dtype=np.int32)
    non_fever_base_by_ff = np.ascontiguousarray(non_fever_base_by_ff, dtype=np.int16)
    fp_cap_table = np.ascontiguousarray(fp_cap_table, dtype=np.int16)

    out = np.zeros((int(pair_ft.shape[0]), int(n_sections)), dtype=np.int16)
    from .taichi_gem.kernels import kernels_breakpoints

    kernels_breakpoints.fg_compute_max_fp_by_pair_kernel(
        int(pair_ft.shape[0]),
        int(base_ft.shape[0]),
        int(n_sections),
        int(song_slot),
        int(gem_scale_fever),
        pair_ft,
        pair_ff,
        base_ft,
        base_ff,
        non_fever_base_by_ff,
        fp_cap_table,
        out,
    )
    return out

# ---- merged from gpu_executor_fg_coalesce.py ----
from dataclasses import dataclass

from gear_optimizer.solver.gpu_executor_batching import order_responses_for_requests
from gear_optimizer.solver.gpu_executor_types import GpuRequestType


@dataclass(frozen=True)
class FgBreakpointCoalesceLimits:
    max_payloads: int
    max_pairs: int


@dataclass(frozen=True)
class FgBreakpointPayloadEntry:
    request: GpuRequest
    payload_list: list[dict[str, Any]]
    n_payloads: int
    n_pairs: int


@dataclass(frozen=True)
class FgBreakpointOversizedEntry:
    entry: FgBreakpointPayloadEntry
    chunks: list[list[dict[str, Any]]]


@dataclass(frozen=True)
class FgBreakpointCoalescePlan:
    invalid: list[tuple[GpuRequest, str]]
    oversized: list[FgBreakpointOversizedEntry]
    groups: list[list[FgBreakpointPayloadEntry]]


@dataclass(frozen=True)
class FgBreakpointGroupBundle:
    request: GpuRequest
    slices: list[tuple[GpuRequest, int, int]]
    payload_count: int


@dataclass(frozen=True)
class FgBreakpointSplitRequest:
    request: GpuRequest
    expected_results: int


def load_fg_breakpoint_coalesce_limits(
    *,
    env_get_fn: Callable[[str, Any], Any] = env_get,
) -> FgBreakpointCoalesceLimits:
    try:
        max_payloads = int(env_get_fn("FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAYLOADS", "64") or "64")
    except (ValueError, TypeError):
        max_payloads = 64
    max_payloads = max(1, min(int(max_payloads), 512))
    try:
        max_pairs = int(env_get_fn("FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAIRS", "256") or "256")
    except (ValueError, TypeError):
        max_pairs = 256
    max_pairs = max(0, int(max_pairs))
    return FgBreakpointCoalesceLimits(max_payloads=int(max_payloads), max_pairs=int(max_pairs))


def fg_breakpoint_payload_pair_count(payloads: list[dict[str, Any]], *, max_pairs: int) -> int:
    if max_pairs <= 0:
        return 0

    import numpy as np

    total = 0
    for payload in payloads:
        ftff_pairs = payload.get("ftff_pairs")
        if ftff_pairs is None:
            continue
        try:
            if isinstance(ftff_pairs, np.ndarray):
                total += int(ftff_pairs.shape[0])
            else:
                total += int(len(ftff_pairs))
        except (ValueError, TypeError, AttributeError):
            continue
    return int(total)


def split_fg_breakpoint_payloads_for_coalesce(
    payload_list: list[dict[str, Any]],
    *,
    limits: FgBreakpointCoalesceLimits,
) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = []
    cur_chunk: list[dict[str, Any]] = []
    cur_pairs = 0

    for payload_item in payload_list:
        item_pairs = fg_breakpoint_payload_pair_count([payload_item], max_pairs=int(limits.max_pairs))
        if not cur_chunk:
            cur_chunk = [payload_item]
            cur_pairs = int(item_pairs)
            continue

        exceed_payload_cap = (len(cur_chunk) + 1) > int(limits.max_payloads)
        exceed_pairs_cap = bool(limits.max_pairs > 0 and (cur_pairs + int(item_pairs)) > int(limits.max_pairs))
        if exceed_payload_cap or exceed_pairs_cap:
            chunks.append(cur_chunk)
            cur_chunk = [payload_item]
            cur_pairs = int(item_pairs)
        else:
            cur_chunk.append(payload_item)
            cur_pairs += int(item_pairs)

    if cur_chunk:
        chunks.append(cur_chunk)
    return chunks


def plan_fg_breakpoint_coalescing(
    requests: list[GpuRequest],
    *,
    payload_dict_fn: Callable[[GpuRequest], dict[str, Any]],
    limits: FgBreakpointCoalesceLimits,
) -> FgBreakpointCoalescePlan:
    invalid: list[tuple[GpuRequest, str]] = []
    oversized: list[FgBreakpointOversizedEntry] = []
    groups: list[list[FgBreakpointPayloadEntry]] = []
    cur: list[FgBreakpointPayloadEntry] = []
    cur_payloads = 0
    cur_pairs = 0

    for req in requests:
        payload = payload_dict_fn(req)
        payloads = payload.get("payloads")
        if not isinstance(payloads, (list, tuple)) or not payloads:
            invalid.append((req, "missing/empty payloads list"))
            continue
        ok = True
        for payload_item in payloads:
            if not isinstance(payload_item, dict):
                ok = False
                break
        if not ok:
            invalid.append((req, "payload list contains non-dict item"))
            continue

        payload_list = list(payloads)
        n_payloads = int(len(payload_list))
        if n_payloads <= 0:
            invalid.append((req, "payload list length resolved to zero"))
            continue
        n_pairs = fg_breakpoint_payload_pair_count(payload_list, max_pairs=int(limits.max_pairs))
        entry = FgBreakpointPayloadEntry(
            request=req,
            payload_list=payload_list,
            n_payloads=int(n_payloads),
            n_pairs=int(n_pairs),
        )
        if n_payloads > int(limits.max_payloads) or (limits.max_pairs > 0 and n_pairs > int(limits.max_pairs)):
            oversized.append(
                FgBreakpointOversizedEntry(
                    entry=entry,
                    chunks=split_fg_breakpoint_payloads_for_coalesce(payload_list, limits=limits),
                )
            )
            continue

        if cur and (
            cur_payloads + n_payloads > int(limits.max_payloads)
            or (limits.max_pairs > 0 and cur_pairs + n_pairs > int(limits.max_pairs))
        ):
            groups.append(cur)
            cur = []
            cur_payloads = 0
            cur_pairs = 0

        cur.append(entry)
        cur_payloads += int(n_payloads)
        cur_pairs += int(n_pairs)

    if cur:
        groups.append(cur)

    return FgBreakpointCoalescePlan(
        invalid=invalid,
        oversized=oversized,
        groups=groups,
    )


def build_fg_breakpoint_group_bundle(group: list[FgBreakpointPayloadEntry]) -> FgBreakpointGroupBundle:
    merged_payloads: list[dict[str, Any]] = []
    slices: list[tuple[GpuRequest, int, int]] = []
    for entry in group:
        req = entry.request
        payload_list = entry.payload_list
        n_payloads = int(entry.n_payloads)
        start = len(merged_payloads)
        merged_payloads.extend(payload_list)
        slices.append((req, int(start), int(n_payloads)))

    return FgBreakpointGroupBundle(
        request=GpuRequest(
            request_type=GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
            request_id=-1,
            worker_id=-1,
            payload={"payloads": merged_payloads},
        ),
        slices=slices,
        payload_count=int(len(merged_payloads)),
    )


def split_fg_breakpoint_group_result(
    bundle: FgBreakpointGroupBundle,
    merged_results: Any,
) -> list[GpuResponse]:
    if not isinstance(merged_results, list):
        raise TypeError("merged FG bundle returned non-list result")
    if int(len(merged_results)) != int(bundle.payload_count):
        raise RuntimeError("merged FG bundle length mismatch")

    responses: list[GpuResponse] = []
    for req, start, n in bundle.slices:
        responses.append(
            GpuResponse(
                request_id=req.request_id,
                success=True,
                result=list(merged_results[int(start) : int(start) + int(n)]),
            )
        )
    return responses


def build_fg_breakpoint_split_requests(oversized: FgBreakpointOversizedEntry) -> list[FgBreakpointSplitRequest]:
    req = oversized.entry.request
    split_requests: list[FgBreakpointSplitRequest] = []
    for payload_chunk in oversized.chunks:
        split_requests.append(
            FgBreakpointSplitRequest(
                request=GpuRequest(
                    request_type=GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
                    request_id=int(req.request_id),
                    worker_id=int(req.worker_id),
                    payload={"payloads": payload_chunk},
                ),
                expected_results=int(len(payload_chunk)),
            )
        )
    return split_requests


def merge_fg_breakpoint_split_results(
    split_requests: list[FgBreakpointSplitRequest],
    split_results: list[Any],
) -> list[Any]:
    if int(len(split_results)) != int(len(split_requests)):
        raise RuntimeError("split FG request chunk count mismatch")

    merged_results: list[Any] = []
    for split_request, split_result in zip(split_requests, split_results):
        if not isinstance(split_result, list):
            raise TypeError("split FG request returned non-list result")
        if int(len(split_result)) != int(split_request.expected_results):
            raise RuntimeError("split FG request length mismatch")
        merged_results.extend(split_result)
    return merged_results


def coalesce_fg_solve_with_breakpoints_batch_requests(
    requests: list[GpuRequest],
    *,
    in_process_queues: bool,
    execute_request: Callable[[GpuRequest], GpuResponse],
    execute_batch: Callable[[GpuRequest], GpuResponse],
    payload_dict_fn: Callable[[GpuRequest], dict[str, Any]],
    warn_fallback_fn: Callable[..., None],
    env_get_fn: Callable[[str, Any], Any] = env_get,
) -> list[GpuResponse]:
    if not requests:
        return []

    if not bool(in_process_queues):
        warn_fallback_fn(
            "gpu_executor.fg_breakpoints_coalesce",
            "coalescing unavailable (not in-process); falling back to per-request execution",
            context={"request_count": len(requests)},
        )
        return [execute_request(req) for req in requests]

    coalesce_limits = load_fg_breakpoint_coalesce_limits(env_get_fn=env_get_fn)
    max_payloads = int(coalesce_limits.max_payloads)
    max_pairs = int(coalesce_limits.max_pairs)

    fallback: list[GpuResponse] = []
    direct: list[GpuResponse] = []

    def _append_fallback(req: GpuRequest, reason: str, *, extra: dict[str, Any] | None = None) -> None:
        context = {"request_id": int(getattr(req, "request_id", -1))}
        if extra:
            context.update(extra)
        warn_fallback_fn("gpu_executor.fg_breakpoints_request", reason, context=context)
        fallback.append(execute_request(req))

    coalesce_plan = plan_fg_breakpoint_coalescing(
        requests,
        payload_dict_fn=payload_dict_fn,
        limits=coalesce_limits,
    )

    for req, reason in coalesce_plan.invalid:
        _append_fallback(req, reason)

    for oversized in coalesce_plan.oversized:
        req = oversized.entry.request
        n_payloads = int(oversized.entry.n_payloads)
        n_pairs = int(oversized.entry.n_pairs)
        try:
            split_requests = build_fg_breakpoint_split_requests(oversized)
            split_results: list[Any] = []
            for split_request in split_requests:
                split_resp = execute_batch(split_request.request)
                if not getattr(split_resp, "success", False):
                    raise RuntimeError(f"split FG request failed: {getattr(split_resp, 'error', None)}")
                split_results.append(getattr(split_resp, "result", None))
            merged_results = merge_fg_breakpoint_split_results(split_requests, split_results)
            direct.append(
                GpuResponse(
                    request_id=int(req.request_id),
                    success=True,
                    result=merged_results,
                )
            )
        except Exception as exc:
            warn_fallback_fn(
                "gpu_executor.fg_breakpoints_request_split",
                "failed to split oversized payload list; falling back to per-request execution",
                context={
                    "request_id": int(req.request_id),
                    "payloads": n_payloads,
                    "max_payloads": max_payloads,
                    "pairs": int(n_pairs),
                    "max_pairs": int(max_pairs),
                },
                exc=exc,
            )
            fallback.append(execute_request(req))

    groups = coalesce_plan.groups

    out: list[GpuResponse] = []
    out.extend(direct)
    out.extend(fallback)

    if not groups:
        return order_responses_for_requests(requests, out)

    for group in groups:
        if len(group) == 1:
            out.append(execute_request(group[0][0]))
            continue
        try:
            bundle = build_fg_breakpoint_group_bundle(group)
            merged_resp = execute_batch(bundle.request)
            if not getattr(merged_resp, "success", False):
                raise RuntimeError(f"merged FG bundle failed: {merged_resp.error}")
            out.extend(split_fg_breakpoint_group_result(bundle, getattr(merged_resp, "result", None)))
        except Exception as exc:
            warn_fallback_fn(
                "gpu_executor.fg_breakpoints_group",
                "merged coalesced group failed; falling back to per-request execution",
                context={"group_size": len(group)},
                exc=exc,
            )
            for entry in group:
                out.append(execute_request(entry.request))

    return order_responses_for_requests(requests, out)

# ---- merged from gpu_executor_fg_solve.py ----


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

# ---- merged from gpu_executor_fg_tasks.py ----
from collections.abc import Sequence
from dataclasses import dataclass

from gear_optimizer.core.parsing import env_flag, env_get


@dataclass(frozen=True)
class FgTaskOnlyRequest:
    request: GpuRequest
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    fg_tasks: list[Any]


def load_fg_task_budget(
    *,
    in_process_queues: bool,
    env_get_fn: Callable[..., Any] = env_get,
    env_flag_fn: Callable[..., bool] = env_flag,
) -> int:
    task_budget: int | None = None
    try:
        raw_budget = env_get_fn("FG_TASK_BUDGET")
        if raw_budget is not None and str(raw_budget).strip() != "":
            task_budget = int(str(raw_budget).strip())
    except (ValueError, TypeError):
        task_budget = None

    if task_budget is None:
        inflight_v4 = env_flag_fn("INFLIGHT_V4")
        task_budget = 256 if (inflight_v4 or in_process_queues) else 0

    return max(0, int(task_budget))


def extract_fg_task_only_request(req: GpuRequest, payload: dict[str, Any]) -> FgTaskOnlyRequest | None:
    args = payload.get("args", ())
    kwargs = payload.get("kwargs", {})
    if not isinstance(args, (list, tuple)) or len(args) != 7 or not isinstance(kwargs, dict):
        return None

    fg_tasks = kwargs.get("fg_tasks")
    if not isinstance(fg_tasks, (list, tuple)) or not fg_tasks:
        return None
    if bool(kwargs.get("fg_reset_before", False)) or bool(kwargs.get("fg_download_after", False)):
        return None

    return FgTaskOnlyRequest(
        request=req,
        args=tuple(args),
        kwargs=dict(kwargs),
        fg_tasks=list(fg_tasks),
    )


def fg_task_only_group_key(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[Any, ...] | None:
    try:
        genome_stats_list, timestamps_np, great_candidate_timestamps_np, long_notes, last_note_time, _, _ = args
    except (ValueError, TypeError, IndexError):
        return None

    return (
        id(genome_stats_list),
        id(timestamps_np),
        id(great_candidate_timestamps_np),
        int(kwargs.get("n_sections", 0) or 0),
        int(kwargs.get("song_slot", 0) or 0),
        int(kwargs.get("total_budget", 90) or 90),
        int(kwargs.get("gem_scale_fever", 3) or 3),
        bool(kwargs.get("pair_caps_from_timeline", False)),
        id(kwargs.get("pair_caps_grid")),
        id(kwargs.get("ref_arrays")),
        int(kwargs.get("is_p_ft", 0) or 0),
        int(kwargs.get("is_s_ft", 0) or 0),
        int(kwargs.get("is_p_ff", 0) or 0),
        int(kwargs.get("is_s_ff", 0) or 0),
        int(kwargs.get("is_p_pp", 0) or 0),
        int(kwargs.get("is_s_pp", 0) or 0),
        int(kwargs.get("is_p_cm", 0) or 0),
        int(kwargs.get("is_s_cm", 0) or 0),
        int(kwargs.get("is_p_fm", 0) or 0),
        int(kwargs.get("is_s_fm", 0) or 0),
        int(kwargs.get("is_p_ov", 0) or 0),
        int(kwargs.get("is_s_ov", 0) or 0),
        int(kwargs.get("base_cfg_offset", 0) or 0),
        kwargs.get("cfg_chunk"),
        int(long_notes or 0),
        float(last_note_time or 0.0),
    )


def build_merged_fg_task_kwargs(source: dict[str, Any], *, upload_genome_stats: bool) -> dict[str, Any]:
    merged = dict(source)
    merged.pop("fg_tasks", None)
    merged["accumulate_global"] = True
    merged["return_raw"] = True
    merged["upload_genome_stats"] = bool(upload_genome_stats)
    merged.pop("fg_reset_before", None)
    merged.pop("fg_download_after", None)
    merged.pop("fg_download_topk", None)
    merged.pop("fg_download_base_scores", None)
    merged.pop("fg_download_keep_mask", None)
    merged.pop("n_genomes_override", None)
    return merged


def iter_fg_task_chunks(fg_tasks: Sequence[Any], task_budget: int) -> list[list[Any]]:
    tasks = list(fg_tasks)
    if int(task_budget) <= 0 or len(tasks) <= int(task_budget):
        return [tasks]
    return [tasks[j : j + int(task_budget)] for j in range(0, len(tasks), int(task_budget))]


def coalesce_fg_task_requests(
    requests: list[GpuRequest],
    *,
    in_process_queues: bool,
    execute_request: Callable[[GpuRequest], GpuResponse],
    payload_dict_fn: Callable[[GpuRequest], dict[str, Any]],
    solve_force_greats_finder_gpu_tasks_fn: Callable[..., Any],
    record_fg_tasks_batch: Callable[[int], None],
    record_pack: Callable[[GpuRequestType, float], None],
    perf_counter_fn: Callable[[], float],
    env_get_fn: Callable[..., Any] = env_get,
) -> list[GpuResponse]:
    task_budget = load_fg_task_budget(
        in_process_queues=bool(in_process_queues),
        env_get_fn=env_get_fn,
    )

    def _flush_task_only_segment(seg: list[FgTaskOnlyRequest]) -> dict[int, GpuResponse]:
        if not seg:
            return {}

        groups: dict[tuple[Any, ...], list[FgTaskOnlyRequest]] = {}
        out_by_id: dict[int, GpuResponse] = {}

        for item in seg:
            key = fg_task_only_group_key(item.args, item.kwargs)
            if key is None:
                out_by_id[int(item.request.request_id)] = execute_request(item.request)
                continue
            groups.setdefault(key, []).append(item)

        for _key, items in groups.items():
            if not items:
                continue
            if len(items) == 1:
                req0 = items[0].request
                out_by_id[int(req0.request_id)] = execute_request(req0)
                continue

            req0 = items[0].request
            args0 = items[0].args
            kwargs0 = items[0].kwargs
            genome_stats_list, timestamps_np, great_candidate_timestamps_np, long_notes, last_note_time, _, _ = args0

            merged_tasks: list[Any] = []
            upload_any = False
            for item in items:
                merged_tasks.extend(list(item.fg_tasks))
                upload_any = upload_any or bool(item.kwargs.get("upload_genome_stats", True))
                record_fg_tasks_batch(len(item.fg_tasks))

            kwargs_local = build_merged_fg_task_kwargs(kwargs0, upload_genome_stats=upload_any)

            t_pack0 = perf_counter_fn()
            try:
                upload_this = bool(kwargs_local.get("upload_genome_stats", True))
                for fg_task_chunk in iter_fg_task_chunks(merged_tasks, task_budget):
                    kwargs_local["upload_genome_stats"] = bool(upload_this)
                    solve_force_greats_finder_gpu_tasks_fn(
                        genome_stats_list,
                        timestamps_np,
                        great_candidate_timestamps_np,
                        int(long_notes),
                        float(last_note_time),
                        fg_tasks=fg_task_chunk,
                        **kwargs_local,
                    )
                    upload_this = False
                record_pack(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, perf_counter_fn() - t_pack0)
                for item in items:
                    req = item.request
                    out_by_id[int(req.request_id)] = GpuResponse(request_id=req.request_id, success=True, result=None)
            except Exception as exc:
                record_pack(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, perf_counter_fn() - t_pack0)
                err = f"{type(exc).__name__}: {exc}"
                for item in items:
                    req = item.request
                    out_by_id[int(req.request_id)] = GpuResponse(request_id=req.request_id, success=False, error=err)

        return out_by_id

    responses_by_id: dict[int, GpuResponse] = {}
    segment: list[FgTaskOnlyRequest] = []

    def _flush_segment() -> None:
        nonlocal segment
        if not segment:
            return
        seg_resps = _flush_task_only_segment(segment)
        responses_by_id.update({int(k): v for k, v in seg_resps.items() if v is not None})
        segment = []

    for req in requests:
        extracted = extract_fg_task_only_request(req, payload_dict_fn(req))
        if extracted is not None:
            segment.append(extracted)
            continue

        _flush_segment()
        resp = execute_request(req)
        responses_by_id[int(req.request_id)] = resp

    _flush_segment()
    return order_responses_for_requests(requests, responses_by_id.values())
