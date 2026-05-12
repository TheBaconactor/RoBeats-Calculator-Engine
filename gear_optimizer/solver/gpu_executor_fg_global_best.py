from __future__ import annotations

from collections.abc import Callable
from typing import Any

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse


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
