from __future__ import annotations

from dataclasses import dataclass

from gear_optimizer.gamedata import StatCurves
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse



@dataclass(frozen=True)
class LoadRefsOutcome:
    response: GpuResponse
    last_curves_sig: bytes | None


def execute_load_refs(
    request: GpuRequest,
    *,
    last_curves_sig: bytes | None,
    load_curves_fn,
    curves_sig_fn,
) -> LoadRefsOutcome:
    curves = request.payload["curves"]
    sig = curves_sig_fn(curves)
    if sig is None or sig != last_curves_sig:
        load_curves_fn(curves)
        last_curves_sig = sig

    return LoadRefsOutcome(
        response=GpuResponse(
            request_id=request.request_id,
            success=True,
            result=None,
        ),
        last_curves_sig=last_curves_sig,
    )


def curves_sig(curves: StatCurves) -> bytes | None:
    from .taichi_gem.api.initialization import _curves_sig as _taichi_curves_sig
    return _taichi_curves_sig(curves)
