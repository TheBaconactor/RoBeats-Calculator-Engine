from __future__ import annotations

from collections.abc import Callable

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse


def execute_precompute_timeline(
    request: GpuRequest,
    *,
    precompute_fn: Callable[[dict, dict, int], None],
) -> GpuResponse:
    payload = request.payload or {}
    calc_song = payload.get("calc_song")
    ref_arrays = payload.get("ref_arrays")
    song_slot = int(payload.get("song_slot", 0) or 0)
    if not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="Invalid payload for PRECOMPUTE_TIMELINE (expected calc_song/ref_arrays dicts)",
        )

    precompute_fn(calc_song, ref_arrays, song_slot)
    return GpuResponse(
        request_id=request.request_id,
        success=True,
        result=None,
    )
