from __future__ import annotations

from collections.abc import Callable

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse


def request_song_slot(request: GpuRequest) -> int:
    payload = request.payload if isinstance(getattr(request, "payload", None), dict) else {}
    try:
        return int(payload.get("song_slot", 0) or 0)
    except (ValueError, TypeError):
        return 0


def handle_solve_genomes_from_registry(
    request: GpuRequest,
    *,
    execute_fn: Callable[[GpuRequest, int], GpuResponse],
) -> GpuResponse:
    return execute_fn(request, request_song_slot(request))
