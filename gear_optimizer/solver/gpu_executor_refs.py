from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse



@dataclass(frozen=True)
class LoadRefsOutcome:
    response: GpuResponse
    last_ref_arrays_sig: bytes | None


def execute_load_refs(
    request: GpuRequest,
    *,
    last_ref_arrays_sig: bytes | None,
    load_ref_arrays_fn,
    ref_arrays_sig_fn,
) -> LoadRefsOutcome:
    ref_arrays = request.payload["ref_arrays"]
    sig = ref_arrays_sig_fn(ref_arrays)
    if sig is None or sig != last_ref_arrays_sig:
        load_ref_arrays_fn(ref_arrays)
        last_ref_arrays_sig = sig

    return LoadRefsOutcome(
        response=GpuResponse(
            request_id=request.request_id,
            success=True,
            result=None,
        ),
        last_ref_arrays_sig=last_ref_arrays_sig,
    )


def ref_arrays_sig(ref_arrays: Any) -> bytes | None:
    from .taichi_gem.api.initialization import _ref_arrays_sig as _taichi_ref_arrays_sig
    return _taichi_ref_arrays_sig(ref_arrays)
